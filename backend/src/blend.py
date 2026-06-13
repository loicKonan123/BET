"""Fusion des sources de probabilité (consensus statistique multi-modèles).

EDGE dispose de trois estimations indépendantes du 1X2 :
  1. Poisson/Dixon-Coles sur les moyennes buts dom/ext (forme de marque).
  2. Elo (force globale, corrige la force de calendrier).
  3. Marché (closing line Pinnacle/consensus, vig retiré) — meilleur prédicteur connu.

On les combine par POOL LOGARITHMIQUE (moyenne géométrique pondérée). La
recherche (Ranjan & Gneiting, JRSS-B 2010) montre qu'une moyenne linéaire de
prévisions calibrées est nécessairement décalibrée et trop molle ; le pool
logarithmique minimise la divergence KL aux sources et préserve la netteté
(externally Bayesian). Le marché, quand il est disponible, reçoit le poids le
plus fort (dur à battre). En son absence, Elo et Poisson se partagent le poids.

Le résultat sert d'ANCRE statistique. DeepSeek reste l'arbitre final : il voit
les trois sources + le consensus, et peut s'en écarter s'il détecte un facteur
qualitatif majeur (blessure clé, enjeu, météo).
"""
from math import exp, log

# Poids par défaut quand le marché est disponible
POIDS_AVEC_MARCHE = {"marche": 0.50, "elo": 0.27, "poisson": 0.23}
# Poids quand le marché manque (matchs lointains, ligues mineures)
POIDS_SANS_MARCHE = {"elo": 0.55, "poisson": 0.45}

CLES_1X2 = ("1", "X", "2")


def _normaliser(p: dict[str, float]) -> dict[str, float]:
    s = sum(p.get(k, 0.0) for k in CLES_1X2)
    if s <= 0:
        return {k: 1 / 3 for k in CLES_1X2}
    return {k: p.get(k, 0.0) / s for k in CLES_1X2}


def conseil_consensus(consensus: dict[str, float] | None,
                      cotes: dict[str, float]) -> dict | None:
    """Bilan du consensus : le verdict synthétique des 3 modèles fusionnés.

    Ce n'est PAS une chasse à la value : c'est la conclusion du consensus —
    l'issue la plus probable, son niveau de confiance, et la value affichée
    seulement comme contexte honnête (positive = cote intéressante, négative =
    le marché est plus court que nous).

    Quand l'issue franche (1X2) est peu probable (match ouvert), on bascule sur
    la double chance la plus solide pour donner un repère fiable.
    """
    if not consensus:
        return None

    c1, cX, c2 = consensus.get("1", 0), consensus.get("X", 0), consensus.get("2", 0)
    libelles = {
        "1": "Victoire domicile", "X": "Match nul", "2": "Victoire extérieur",
        "1X": "Domicile ou nul (double chance)",
        "12": "Pas de match nul (double chance)",
        "X2": "Extérieur ou nul (double chance)",
    }

    # 1 — Issue franche la plus probable (le favori du consensus)
    issue = max((("1", c1), ("X", cX), ("2", c2)), key=lambda kv: kv[1])
    cle, proba = issue

    # 2 — Si le favori est peu net (< 50%), on propose plutôt la meilleure
    #     double chance comme repère solide.
    if proba < 0.50:
        dc = {"1X": c1 + cX, "12": c1 + c2, "X2": cX + c2}
        cle_dc = max(dc, key=dc.get)
        cle, proba = cle_dc, dc[cle_dc]

    cote = cotes.get(cle)
    value = round(proba * cote - 1.0, 4) if cote else 0.0

    # 3 — Niveau de confiance d'après la probabilité consensus
    if proba >= 0.65:
        confiance, mot = "élevée", "très probable"
    elif proba >= 0.50:
        confiance, mot = "moyenne", "probable"
    else:
        confiance, mot = "faible", "incertain (match ouvert)"

    # 4 — Mention de value honnête
    if cote and value >= 0.05:
        note_value = f" La cote ({cote}) offre une value de +{round(value*100)}% face au marché."
    elif cote and value < -0.05:
        note_value = f" Le marché est plus court que nous (cote {cote}) — pas de value."
    else:
        note_value = ""

    raison = f"Bilan du consensus : {libelles[cle].lower()} {mot} ({round(proba*100)}%).{note_value}"

    return {"marche": libelles[cle], "proba": round(proba, 4),
            "cote": cote, "value": value, "confiance": confiance, "raison": raison}


def fusionner_1x2(
    poisson: dict[str, float] | None,
    elo: dict[str, float] | None,
    marche: dict[str, float] | None,
) -> dict:
    """Combine les sources disponibles en un consensus 1X2 pondéré.

    Renvoie {probabilites, poids_utilises, sources_disponibles, accord}.
    `accord` = écart max entre sources (faible = consensus fort).
    """
    sources = {}
    if poisson:
        sources["poisson"] = _normaliser(poisson)
    if elo:
        sources["elo"] = _normaliser(elo)
    if marche:
        sources["marche"] = _normaliser(marche)

    if not sources:
        return {"probabilites": None, "poids_utilises": {},
                "sources_disponibles": [], "accord": None}

    base = POIDS_AVEC_MARCHE if "marche" in sources else POIDS_SANS_MARCHE
    # Ne garde que les poids des sources présentes, puis renormalise les poids
    poids = {s: base.get(s, 0.0) for s in sources}
    total_poids = sum(poids.values())
    if total_poids <= 0:
        poids = {s: 1.0 / len(sources) for s in sources}
        total_poids = 1.0
    poids = {s: w / total_poids for s, w in poids.items()}

    # Pool LOGARITHMIQUE : moyenne géométrique pondérée des probabilités.
    # consensus_k ∝ exp(Σ_s w_s · ln p_s,k). Préserve la netteté (contrairement
    # à la moyenne arithmétique qui lisse vers l'uniforme) et minimise la
    # divergence KL aux sources. Garde-fou EPS pour éviter ln(0).
    EPS = 1e-9
    consensus = {
        k: exp(sum(poids[s] * log(max(sources[s][k], EPS)) for s in sources))
        for k in CLES_1X2
    }
    consensus = _normaliser(consensus)

    # Mesure d'accord entre sources : écart max sur la proba de victoire dom
    if len(sources) > 1:
        vals = [sources[s]["1"] for s in sources]
        accord = round(max(vals) - min(vals), 4)
    else:
        accord = 0.0

    return {
        "probabilites": {k: round(v, 4) for k, v in consensus.items()},
        "poids_utilises": {s: round(w, 3) for s, w in poids.items()},
        "sources_disponibles": list(sources.keys()),
        "accord": accord,
    }
