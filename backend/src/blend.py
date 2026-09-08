"""Fusion des probabilités Poisson/Dixon-Coles, Elo, marché et ML optionnel.

Les sources partagent certaines données : elles ne sont pas indépendantes.
Le pool logarithmique utilise les poids existants ; il ne garantit ni une
meilleure calibration ni une supériorité sur le marché. Ces propriétés doivent
être mesurées hors échantillon. Les diagnostics décrivent le désaccord et la
sensibilité, pas une probabilité de réussite supplémentaire.
"""
from math import exp, isfinite, log

# Poids optimisés empiriquement (minimisation du log-loss sur 1669 matchs
# walk-forward, toutes ligues club en cache). L'Elo s'est révélé plus fiable
# que le Poisson sur l'ensemble (Elo seul 1.031 vs Poisson seul 1.122) ; on
# garde toutefois une part au Poisson, mieux nourri en production (~2 saisons
# ajustées vs demi-saison au backtest). Voir docs/plan.md.
# Poids par défaut quand le marché est disponible
POIDS_AVEC_MARCHE = {"marche": 0.50, "elo": 0.30, "poisson": 0.20}
# Poids quand le marché manque (matchs lointains, ligues mineures)
POIDS_SANS_MARCHE = {"elo": 0.70, "poisson": 0.30}

CLES_1X2 = ("1", "X", "2")


def valider_1x2(p: dict | None) -> dict[str, float] | None:
    """Écarte les sources incomplètes, non numériques ou non probabilistes."""
    if not isinstance(p, dict):
        return None
    values = [p.get(k) for k in CLES_1X2]
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not isfinite(v) or not 0 <= v <= 1 for v in values):
        return None
    total = sum(values)
    if abs(total - 1.0) > 0.02:
        return None
    return {k: p[k] / total for k in CLES_1X2}


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


# Poids fixe du ML quand il est présent. Le ML (xG) est corrélé à l'Elo
# (il l'utilise comme feature), donc on l'insère avec un poids modéré et on
# réduit proportionnellement les autres sources — ça préserve leurs ratios
# déjà validés tout en intégrant le signal xG neuf.
POIDS_ML = 0.22


def fusionner_1x2(
    poisson: dict[str, float] | None,
    elo: dict[str, float] | None,
    marche: dict[str, float] | None,
    ml: dict[str, float] | None = None,
    autres: dict | None = None,
    poids_config: dict | None = None,
) -> dict:
    """Combine les sources disponibles en un consensus 1X2 pondéré.

    Renvoie {probabilites, poids_utilises, sources_disponibles, accord}.
    `accord` = écart max entre sources (faible = consensus fort).
    """
    sources = {}
    for nom, p in {"poisson": poisson, "elo": elo, "marche": marche, "ml": ml, **(autres or {})}.items():
        valide = valider_1x2(p)
        if valide is not None:
            sources[nom] = valide

    if not sources:
        return {"probabilites": None, "poids_utilises": {},
                "sources_disponibles": [], "accord": None}

    # Poids des sources « classiques » (hors ML), selon les valeurs validées
    base = POIDS_AVEC_MARCHE if "marche" in sources else POIDS_SANS_MARCHE
    classiques = [s for s in sources if s != "ml"]
    poids = {s: base.get(s, 0.0) for s in classiques}
    total_poids = sum(poids.values())
    if total_poids <= 0:
        poids = {s: 1.0 / len(classiques) for s in classiques} if classiques else {}
        total_poids = 1.0 if classiques else 0.0
    poids = {s: w / total_poids for s, w in poids.items()}

    # Insère le ML : il prend POIDS_ML, les autres sont réduits d'autant.
    if "ml" in sources:
        if poids:
            poids = {s: w * (1.0 - POIDS_ML) for s, w in poids.items()}
            poids["ml"] = POIDS_ML
        else:
            poids = {"ml": 1.0}

    if poids_config is not None:
        poids = {s: max(float(poids_config.get(s, 0)), 0) for s in sources}
        sources = {s: p for s, p in sources.items() if poids[s] > 1e-8}
        if not sources:
            return {"probabilites": None, "poids_utilises": {}, "sources_disponibles": [], "accord": None}
        total = sum(poids[s] for s in sources)
        poids = {s: poids[s]/total for s in sources}

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

    # Mesure les trois issues : un désaccord sur le nul ne doit pas disparaître.
    plages = {
        k: {"min": round(min(p[k] for p in sources.values()), 4),
            "max": round(max(p[k] for p in sources.values()), 4)}
        for k in CLES_1X2
    }
    accord = (round(max(v["max"] - v["min"] for v in plages.values()), 4)
              if len(sources) > 1 else None)
    favori = max(consensus, key=consensus.get)
    # Sensibilité à une source : mêmes poids relatifs, une source retirée.
    sensibilite = {}
    for retiree in sources if len(sources) > 1 else []:
        autres = [s for s in sources if s != retiree]
        total = sum(poids[s] for s in autres)
        sans = _normaliser({
            k: exp(sum(poids[s] / total * log(max(sources[s][k], EPS)) for s in autres))
            for k in CLES_1X2
        })
        sensibilite[retiree] = {
            "probabilites": {k: round(v, 4) for k, v in sans.items()},
            "ecart_max": round(max(abs(sans[k] - consensus[k]) for k in CLES_1X2), 4),
            "favori_change": max(sans, key=sans.get) != favori,
        }

    arrondies = {k: round(v, 4) for k, v in consensus.items()}
    arrondies[favori] = round(arrondies[favori] + 1 - sum(arrondies.values()), 4)
    return {
        "probabilites": arrondies,
        "poids_utilises": {s: round(w, 3) for s, w in poids.items()},
        "sources_disponibles": list(sources.keys()),
        "accord": accord,
        "diagnostic": {
            "plages": plages,
            "sensibilite": sensibilite,
            "favori_stable": (all(not s["favori_change"] for s in sensibilite.values())
                              if sensibilite else None),
            "note": "Les sources sont corrélées. Leur accord ne mesure pas la calibration. "
                    "Les plages sont des écarts entre modèles, pas des intervalles de confiance.",
        },
    }
