"""Cerveau analyste (LLM DeepSeek).

Le LLM NE CALCULE PAS les probabilités (c'est le rôle de Poisson). Il reçoit
un « dossier » de faits réels — probas du modèle, buts attendus, forme,
blessures, confrontations directes — et produit une analyse fine + un conseil
nuancé, en raisonnant par-dessus les chiffres.

DeepSeek est compatible OpenAI : on utilise le SDK openai pointé sur leur URL.
"""
import json
import os
import re

from openai import OpenAI

from .api_client import ApiFootball

BASE_URL = "https://api.deepseek.com"


def _client() -> OpenAI:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY manquante (vérifie backend/.env)")
    return OpenAI(api_key=key, base_url=BASE_URL)


def _blessures(api: ApiFootball, fixture_id: int, home_id: int, away_id: int) -> dict:
    """Récupère les blessures/suspensions par équipe (tolérant aux erreurs)."""
    out = {"domicile": [], "exterieur": []}
    try:
        data = api.get("injuries", {"fixture": fixture_id})
    except Exception:
        return out
    for item in data.get("response", []):
        joueur = item.get("player", {})
        team_id = item.get("team", {}).get("id")
        ligne = f"{joueur.get('name', '?')} ({joueur.get('reason', '?')})"
        if team_id == home_id:
            out["domicile"].append(ligne)
        elif team_id == away_id:
            out["exterieur"].append(ligne)
    return out


def _h2h(api: ApiFootball, home_id: int, away_id: int, n: int = 5) -> list[str]:
    """Derniers face-à-face (tolérant aux erreurs)."""
    try:
        data = api.get("fixtures/headtohead", {"h2h": f"{home_id}-{away_id}", "last": n})
    except Exception:
        return []
    out = []
    for f in data.get("response", []):
        h = f["teams"]["home"]
        a = f["teams"]["away"]
        gh = f.get("goals", {}).get("home")
        ga = f.get("goals", {}).get("away")
        date = f.get("fixture", {}).get("date", "")[:10]
        out.append(f"{h['name']} {gh}-{ga} {a['name']} ({date})")
    return out


def collecter_dossier(api: ApiFootball, detail: dict) -> dict:
    """Assemble le dossier de faits à partir du détail du match + données qualitatives."""
    home = detail["home"]
    away = detail["away"]
    fixture_id = detail["fixture_id"]
    return {
        "match": detail["match"],
        "competition": detail.get("ligue"),
        "date": detail.get("date"),
        "buts_attendus": detail["buts_attendus"],
        "forme_recente": detail["forme"],
        "probabilites_modele": detail.get("probabilites", {}),
        "marches": [
            {"marche": s["marche"], "proba": s["proba"], "cote": s.get("cote"),
             "value": s.get("value")}
            for s in detail.get("selections", [])
        ],
        "conseil_du_modele": detail.get("conseil"),
        "blessures": _blessures(api, fixture_id, home["id"], away["id"]),
        "confrontations_directes": _h2h(api, home["id"], away["id"]),
    }


_SYSTEME = (
    "Tu es un analyste expert en paris sportifs football. On te fournit un dossier "
    "factuel : des probabilités déjà calculées par un modèle statistique (loi de "
    "Poisson) — que tu dois considérer comme FIABLES et NE PAS recalculer — ainsi "
    "que des données de contexte (forme, blessures, confrontations directes, cotes). "
    "Ton rôle : raisonner par-dessus ces faits pour produire une analyse fine, "
    "repérer ce que les chiffres seuls ratent (absences clés, enjeu, déséquilibres), "
    "et donner un conseil nuancé. Réponds en français."
)

_INSTRUCTION = """À partir du dossier JSON ci-dessous, rends UNIQUEMENT un objet JSON
valide (aucun texte autour), avec exactement ces clés :

{
  "analyse": "2-4 phrases d'analyse fine et nuancée",
  "points_cles": ["point 1", "point 2", "point 3"],
  "facteurs_risque": ["risque 1", "risque 2"],
  "recommandation": {
    "marche": "le marché conseillé",
    "confiance": "élevée | moyenne | faible",
    "justification": "1 phrase"
  },
  "accord_avec_modele": true,
  "nuance": "une phrase qui tempère ou confirme le conseil du modèle"
}

DOSSIER :
"""


def _extraire_json(texte: str) -> dict:
    """Parse le JSON renvoyé, même s'il est entouré de texte ou de balises ```."""
    texte = texte.strip()
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", texte, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {
        "analyse": texte,
        "points_cles": [],
        "facteurs_risque": [],
        "recommandation": None,
        "accord_avec_modele": None,
        "nuance": "",
    }


def analyser_avec_ia(api: ApiFootball, detail: dict) -> dict:
    """Construit le dossier, interroge DeepSeek, renvoie l'analyse structurée."""
    dossier = collecter_dossier(api, detail)
    modele = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

    client = _client()
    resp = client.chat.completions.create(
        model=modele,
        messages=[
            {"role": "system", "content": _SYSTEME},
            {"role": "user", "content": _INSTRUCTION + json.dumps(dossier, ensure_ascii=False, indent=2)},
        ],
        max_tokens=1500,
    )
    contenu = resp.choices[0].message.content or ""
    resultat = _extraire_json(contenu)
    resultat["modele"] = modele
    resultat["dossier"] = dossier  # transparence : on renvoie les faits utilisés
    return resultat
