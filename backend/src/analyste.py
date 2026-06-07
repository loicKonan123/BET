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
    # timeout large : le raisonneur (R1) peut réfléchir 1-2 min, on le laisse finir
    return OpenAI(api_key=key, base_url=BASE_URL, timeout=300.0, max_retries=1)


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


def _rangs_equipes(classement: dict | None, home_id: int, away_id: int) -> dict | None:
    """Extrait le rang/points/forme des 2 équipes depuis le classement groupé."""
    if not classement:
        return None
    out = {}
    for groupe in classement.get("groupes", []):
        for l in groupe.get("lignes", []):
            if l.get("equipe_id") == home_id:
                out["domicile"] = {"rang": l.get("rang"), "points": l.get("points"),
                                   "joues": l.get("joues"), "forme": l.get("forme")}
            elif l.get("equipe_id") == away_id:
                out["exterieur"] = {"rang": l.get("rang"), "points": l.get("points"),
                                    "joues": l.get("joues"), "forme": l.get("forme")}
    return out or None


def _resume_forme(forme: str) -> dict:
    """Transforme 'WLWWW' en bilan clair pour éviter les erreurs de comptage du LLM."""
    f = (forme or "").upper()
    v, n, d = f.count("W"), f.count("D"), f.count("L")
    return {
        "bilan": f"{v}V {n}N {d}D sur {len(f)} derniers" if f else "données insuffisantes",
        "sequence": f"{f} (du plus ancien à gauche au plus récent à droite)" if f else None,
    }


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
        "forme": {
            "domicile": _resume_forme(detail["forme"]["domicile"]),
            "exterieur": _resume_forme(detail["forme"]["exterieur"]),
        },
        "probabilites_modele": detail.get("probabilites", {}),
        "marches": [
            {"marche": s["marche"], "proba": s["proba"], "cote": s.get("cote"),
             "value": s.get("value")}
            for s in detail.get("selections", [])
        ],
        "conseil_du_modele": detail.get("conseil"),
        "classement": _rangs_equipes(detail.get("classement"), home["id"], away["id"]),
        "blessures": _blessures(api, fixture_id, home["id"], away["id"]),
        "confrontations_directes": _h2h(api, home["id"], away["id"]),
    }


_SYSTEME = (
    "Tu es un analyste expert en paris sportifs football, rigoureux et concis. "
    "On te fournit un dossier factuel : des probabilités déjà calculées par un modèle "
    "statistique (loi de Poisson) — FIABLES, à NE PAS recalculer — et du contexte "
    "(forme en bilan V/N/D, buts attendus, blessures, confrontations directes, "
    "classement/enjeu, cotes et value par marché). "
    "Les probabilités intègrent DÉJÀ le contexte du match (y compris terrain neutre "
    "en Coupe du Monde) : 'domicile'/'extérieur' ne sont que des étiquettes, ne "
    "re-débats donc PAS de l'avantage du terrain. "
    "Règles : (1) sois rigoureusement COHÉRENT avec les chiffres du dossier, ne te "
    "contredis jamais ; (2) appuie CHAQUE affirmation sur une donnée précise du "
    "dossier ; (3) interdiction des clichés et phrases de remplissage "
    "(ex. 'les équipes sont prudentes en tournoi') ; (4) si une donnée manque "
    "(pas de blessures, pas de H2H), dis-le et reste mesuré au lieu d'inventer ; "
    "(5) raisonne en value : un bon pari combine probabilité ET cote sous-évaluée. "
    "Réponds en français."
)

_INSTRUCTION = """À partir du dossier JSON ci-dessous, rends UNIQUEMENT un objet JSON
valide (aucun texte autour), avec exactement ces clés :

{
  "analyse": "3-4 phrases SPÉCIFIQUES et chiffrées (cite les valeurs du dossier), sans cliché",
  "points_cles": ["fait chiffré 1", "fait chiffré 2", "fait chiffré 3"],
  "facteurs_risque": ["risque concret 1", "risque concret 2"],
  "recommandation": {
    "marche": "le marché conseillé (idéalement le meilleur compromis proba x value)",
    "confiance": "élevée | moyenne | faible",
    "justification": "1 phrase appuyée sur proba ET value"
  },
  "accord_avec_modele": true,
  "nuance": "une phrase qui tempère ou confirme le conseil du modèle"
}

Vérifie la cohérence : les nombres que tu cites doivent correspondre EXACTEMENT au dossier.

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
        max_tokens=8000,  # large : le modèle va au bout sans être coupé
    )
    contenu = resp.choices[0].message.content or ""
    resultat = _extraire_json(contenu)
    resultat["modele"] = modele
    resultat["dossier"] = dossier  # transparence : on renvoie les faits utilisés
    return resultat
