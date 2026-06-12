"""Cerveau analyste — DeepSeek produit les probabilités finales.

Pipeline :
  1. Poisson calcule les buts attendus + probas de base (référence statistique).
  2. On assemble un dossier complet : Poisson + H2H + forme dom/ext + classement
     + blessures + contexte tournoi + motivation + facteurs qualitatifs.
  3. DeepSeek (deepseek-reasoner) raisonne sur TOUT et produit ses propres
     probabilités finales, une prédiction et une recommandation.

L'IA n'est PAS contrainte par le Poisson : elle peut l'ajuster vers le haut
ou le bas selon les facteurs que le modèle statistique ne voit pas.
"""
import json
import os
import re

from openai import OpenAI

from .api_client import ApiFootball

BASE_URL = "https://api.deepseek.com"

# Nations hôtes du Mondial 2026 (terrain réel = domicile, pas neutre)
HOTES_WC_2026 = {2, 16, 101}  # USA, Mexico, Canada

# Compétitions de sélections nationales
LIGUES_NATIONALES = {1, 4, 5, 9, 10, 29, 30, 31, 32, 33, 34}


def _client() -> OpenAI:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY manquante (vérifie backend/.env)")
    return OpenAI(api_key=key, base_url=BASE_URL, timeout=300.0, max_retries=1)


def _blessures(api: ApiFootball, fixture_id: int, home_id: int, away_id: int) -> dict:
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
    f = (forme or "").upper()
    v, n, d = f.count("W"), f.count("D"), f.count("L")
    return {
        "bilan": f"{v}V {n}N {d}D sur {len(f)} derniers" if f else "données insuffisantes",
        "sequence": f"{f} (gauche=ancien, droite=récent)" if f else None,
    }


def _contexte_tournoi(detail: dict) -> dict:
    """Construit le contexte qualitatif du tournoi pour l'IA."""
    league_id = detail.get("league_id", 0)
    home_id = detail.get("home", {}).get("id", 0)
    away_id = detail.get("away", {}).get("id", 0)
    round_str = detail.get("round", "")

    ctx = {
        "competition": detail.get("ligue", ""),
        "phase": round_str,
        "est_competition_nationale": league_id in LIGUES_NATIONALES,
    }

    # Détecte si une équipe joue sur son propre territoire (WC host)
    if league_id == 1:  # Coupe du Monde
        if home_id in HOTES_WC_2026:
            ctx["terrain"] = f"L'équipe à domicile ({detail.get('home', {}).get('name', '')}) est NATION HÔTE du Mondial 2026 — avantage réel de terrain (public, habitudes, pression)."
        elif away_id in HOTES_WC_2026:
            ctx["terrain"] = f"L'équipe à l'extérieur ({detail.get('away', {}).get('name', '')}) est NATION HÔTE mais joue en déplacement relatif."
        else:
            ctx["terrain"] = "Terrain neutre (Mondial 2026, aucune des deux équipes n'est nation hôte)."
    else:
        ctx["terrain"] = "Match sur terrain officiel (avantage domicile standard)."

    return ctx


def _stats_detaillees(detail: dict) -> dict | None:
    """Extrait les stats dom/ext séparées si présentes dans le détail."""
    ba = detail.get("buts_attendus")
    if not ba:
        return None
    return {
        "buts_attendus_poisson": ba,
        "note": "Ces valeurs intègrent les stats historiques dom/ext séparées des deux équipes.",
    }


def _bloc_multi_modeles(mm: dict | None) -> dict | None:
    """Met en forme la vue multi-modèles (Poisson + Elo + marché + consensus)."""
    if not mm:
        return None
    cons = mm.get("consensus", {})
    return {
        "poisson_1x2": mm.get("poisson"),
        "elo_1x2": mm.get("elo"),
        "elo_details": mm.get("elo_info"),
        "marche_1x2_sans_vig": mm.get("marche"),
        "consensus_pondere": cons.get("probabilites"),
        "poids_consensus": cons.get("poids_utilises"),
        "accord_entre_sources": cons.get("accord"),
        "note": (
            "Trois modèles indépendants : Poisson (forme buts), Elo (force globale, "
            "corrige la qualité des adversaires), marché (closing line sans marge — "
            "le meilleur prédicteur connu). Le consensus est leur moyenne pondérée. "
            "Un 'accord' faible = les modèles convergent (prédiction sûre) ; un accord "
            "élevé = désaccord, sois prudent et explique pourquoi."
        ),
    }


def collecter_dossier(api: ApiFootball, detail: dict) -> dict:
    """Assemble le dossier complet : Poisson + H2H + forme + classement + contexte."""
    home = detail["home"]
    away = detail["away"]
    fixture_id = detail["fixture_id"]

    return {
        "match": detail["match"],
        "fixture_id": fixture_id,
        "date": detail.get("date"),
        "contexte_tournoi": _contexte_tournoi(detail),
        "reference_statistique_poisson": {
            "buts_attendus": detail.get("buts_attendus"),
            "probabilites_brutes": detail.get("probabilites", {}),
            "note": (
                "Probabilités du modèle Poisson/Dixon-Coles (moyennes buts dom/ext). "
                "Une des trois sources — voir aussi Elo et marché ci-dessous."
            ),
        },
        "modeles_multiples": _bloc_multi_modeles(detail.get("multi_modeles")),
        "forme_recente": {
            "domicile": _resume_forme(detail["forme"]["domicile"]),
            "exterieur": _resume_forme(detail["forme"]["exterieur"]),
        },
        "classement": _rangs_equipes(detail.get("classement"), home["id"], away["id"]),
        "blessures": _blessures(api, fixture_id, home["id"], away["id"]),
        "confrontations_directes": _h2h(api, home["id"], away["id"]),
        "cotes_et_marches": [
            {"marche": s["marche"], "proba_poisson": s["proba"],
             "cote": s.get("cote"), "value": s.get("value")}
            for s in detail.get("selections", [])
        ],
    }


_SYSTEME = """\
Tu es EDGE Analyste, un système de prédiction expert en football. Tu reçois un \
dossier complet sur un match : statistiques Poisson, forme récente, H2H, classement, \
blessures, cotes bookmakers et contexte du tournoi.

Tu reçois TROIS modèles statistiques (Poisson, Elo, marché) et leur consensus \
pondéré. Pars de ce consensus comme ANCRE — c'est une base solide, surtout le \
marché (closing line) qui est très dur à battre. Puis ajuste avec ton jugement.

Ton rôle : produire une VRAIE prédiction, pas juste répéter un modèle.
Tu dois intégrer tout ce que les modèles statistiques ne voient pas :
- Contexte (phase du tournoi, enjeu, doit-gagner ?)
- Terrain (nation hôte, supporters, pression)
- Forme récente vs historique (une équipe en feu vs stats moyennes)
- Qualité des adversaires récents (stats gonflées contre équipes faibles ?)
- H2H (certaines équipes dominent psychologiquement les autres)
- Blessures clés

Tu peux (et dois si justifié) t'écarter des probabilités Poisson.

Règles strictes :
1. Appuie chaque affirmation sur une donnée précise du dossier.
2. Pas de clichés ("les deux équipes se respectent", "match serré attendu").
3. Si une donnée manque, dis-le brièvement — ne l'invente pas.
4. Sois cohérent : tes probabilités IA doivent sommer à 1.0 (±0.01).
5. Réponds en français.
"""

_INSTRUCTION = """\
À partir du dossier JSON ci-dessous, rends UNIQUEMENT un objet JSON valide \
(aucun texte autour, aucune balise ```), avec exactement ces clés :

{
  "probabilites_ia": {
    "victoire_domicile": 0.00,
    "nul": 0.00,
    "victoire_exterieur": 0.00
  },
  "prediction": "Victoire domicile | Nul | Victoire extérieur",
  "confiance": "élevée | moyenne | faible",
  "analyse": "3-4 phrases spécifiques et chiffrées, sans cliché",
  "points_cles": ["fait 1", "fait 2", "fait 3"],
  "facteurs_correctifs_vs_poisson": [
    "Raison pour laquelle l'IA s'écarte (ou confirme) le modèle Poisson"
  ],
  "recommandation": {
    "marche": "marché conseillé",
    "confiance": "élevée | moyenne | faible",
    "justification": "1 phrase précise (proba IA + cote si disponible)"
  }
}

Vérifie : probabilites_ia.victoire_domicile + nul + victoire_exterieur ≈ 1.0

DOSSIER :
"""


def _extraire_json(texte: str) -> dict:
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
        "probabilites_ia": None,
        "prediction": None,
        "confiance": None,
        "analyse": texte,
        "points_cles": [],
        "facteurs_correctifs_vs_poisson": [],
        "recommandation": None,
    }


def analyser_avec_ia(api: ApiFootball, detail: dict) -> dict:
    """Construit le dossier, interroge DeepSeek, renvoie l'analyse complète."""
    dossier = collecter_dossier(api, detail)
    modele = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")

    client = _client()
    resp = client.chat.completions.create(
        model=modele,
        messages=[
            {"role": "system", "content": _SYSTEME},
            {"role": "user", "content": _INSTRUCTION + json.dumps(dossier, ensure_ascii=False, indent=2)},
        ],
        max_tokens=8000,
    )
    contenu = resp.choices[0].message.content or ""
    resultat = _extraire_json(contenu)
    resultat["modele"] = modele
    resultat["dossier"] = dossier
    return resultat
