"""Chef d'orchestre : matchs -> probabilités -> value bets -> 5 combinés.

Produit une sortie JSON structurée (pensée pour être lue par une IA/LLM
plus tard) et un export Excel pour tes clients.

Coût API par match analysé : 3 requêtes (stats dom + stats ext + cotes).
Avec 100 req/jour on peut donc analyser ~30 matchs/jour.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from .api_client import ApiFootball
from .combines import Selection, generer_combines
from .odds_parser import recuperer_cotes
from .ligues_mise_o_jeu import LIGUES_SOCCER
from .poisson import compute_probabilities
from .team_stats import buts_attendus, recuperer_stats, recuperer_stats_national


def _nom_ligue(league_id: int) -> str:
    return LIGUES_SOCCER.get(league_id, f"Ligue {league_id}")

# Compétitions de sélections nationales -> on calcule la force via les
# derniers matchs internationaux, pas via une saison de ligue.
LIGUES_NATIONALES = {
    1,    # Coupe du Monde
    4,    # Euro
    5,    # UEFA Nations League
    9,    # Copa América
    10,   # Friendlies (internationaux)
    29, 30, 31, 32, 33, 34,  # qualifications Coupe du Monde (par confédération)
}


def _stats_equipe(api, league, season, team_id, mode):
    """Récupère les stats d'une équipe selon le mode (club ou national)."""
    if mode == "national":
        return recuperer_stats_national(api, team_id)
    return recuperer_stats(api, league, season, team_id)


def _mode_pour_ligue(league_id: int) -> str:
    return "national" if league_id in LIGUES_NATIONALES else "club"

# Libellés lisibles pour les clients
LIBELLES = {
    "1": "Victoire domicile",
    "X": "Match nul",
    "2": "Victoire extérieur",
    "over_2.5": "Plus de 2.5 buts",
    "under_2.5": "Moins de 2.5 buts",
    "btts_oui": "Les 2 équipes marquent",
    "btts_non": "Une équipe garde sa cage inviolée",
    "1X": "Domicile ou nul (double chance)",
    "12": "Pas de match nul (double chance)",
    "X2": "Extérieur ou nul (double chance)",
}


@dataclass
class FixtureInfo:
    fixture_id: int
    league: int
    season: int
    home_id: int
    away_id: int
    home_name: str
    away_name: str


def fixtures_depuis_reponse(
    reponse: list,
    league_id: int | None = None,
    ligues_autorisees: set[int] | None = None,
) -> list[FixtureInfo]:
    """Convertit la réponse `fixtures` de l'API en liste de FixtureInfo.

    league_id : ne garder qu'une ligue précise.
    ligues_autorisees : VALIDATEUR — ne garder que les ligues de cet ensemble
        (ex: la liste blanche Mise-o-jeu) pour ne jamais proposer un match injouable.
    """
    out = []
    for f in reponse:
        lid = f["league"]["id"]
        if league_id is not None and lid != league_id:
            continue
        if ligues_autorisees is not None and lid not in ligues_autorisees:
            continue
        out.append(FixtureInfo(
            fixture_id=f["fixture"]["id"],
            league=f["league"]["id"],
            season=f["league"]["season"],
            home_id=f["teams"]["home"]["id"],
            away_id=f["teams"]["away"]["id"],
            home_name=f["teams"]["home"]["name"],
            away_name=f["teams"]["away"]["name"],
        ))
    return out


def analyser_fixture(
    api: ApiFootball,
    fx: FixtureInfo,
    stats_season: int | None = None,
) -> dict | None:
    """Analyse un match : renvoie un dict structuré, ou None si données manquantes.

    stats_season : saison à utiliser pour les stats. None => saison du match.
    (Sur le plan gratuit on met 2024 ; avec une clé prod on laisse None.)
    """
    mode = _mode_pour_ligue(fx.league)
    saison_stats = stats_season or fx.season
    dom = _stats_equipe(api, fx.league, saison_stats, fx.home_id, mode)
    ext = _stats_equipe(api, fx.league, saison_stats, fx.away_id, mode)
    if not dom or not ext or not dom.fiable or not ext.fiable:
        return None

    lam_dom, lam_ext = buts_attendus(dom, ext)
    proba = compute_probabilities(lam_dom, lam_ext)
    probas = proba.as_market_dict()

    cotes = recuperer_cotes(api, fx.fixture_id)
    if not cotes:
        return None

    match_label = f"{fx.home_name} - {fx.away_name}"
    selections = []
    for cle, cote in cotes.items():
        p = probas.get(cle)
        if p is None:
            continue
        sel = Selection(match=match_label, marche=LIBELLES.get(cle, cle), proba=p, cote=cote)
        selections.append({
            "cle": cle,
            "marche": sel.marche,
            "proba": round(p, 4),
            "cote": cote,
            "proba_implicite": round(sel.proba_implicite, 4),
            "value": round(sel.value, 4),
            "est_value_bet": sel.est_value_bet,
        })

    return {
        "match": match_label,
        "ligue": _nom_ligue(fx.league),
        "fixture_id": fx.fixture_id,
        "buts_attendus": {"domicile": round(lam_dom, 2), "exterieur": round(lam_ext, 2)},
        "forme": {"domicile": dom.forme[-5:], "exterieur": ext.forme[-5:]},
        "probabilites": {k: round(v, 4) for k, v in probas.items()},
        "selections": selections,
    }


def analyser_fixture_sans_cotes(
    api: ApiFootball,
    fx: FixtureInfo,
    stats_season: int | None = None,
) -> dict | None:
    """Comme analyser_fixture mais SANS cotes : renvoie les probas par marché.

    Sert au mode saisie manuelle : on calcule TA proba, tu fournis la cote
    Mise-o-jeu toi-même côté interface.
    """
    mode = _mode_pour_ligue(fx.league)
    saison_stats = stats_season or fx.season
    dom = _stats_equipe(api, fx.league, saison_stats, fx.home_id, mode)
    ext = _stats_equipe(api, fx.league, saison_stats, fx.away_id, mode)
    if not dom or not ext or not dom.fiable or not ext.fiable:
        return None

    lam_dom, lam_ext = buts_attendus(dom, ext)
    probas = compute_probabilities(lam_dom, lam_ext).as_market_dict()

    match_label = f"{fx.home_name} - {fx.away_name}"
    marches = [
        {"cle": cle, "marche": LIBELLES.get(cle, cle), "proba": round(p, 4)}
        for cle, p in probas.items()
    ]
    return {
        "match": match_label,
        "ligue": _nom_ligue(fx.league),
        "fixture_id": fx.fixture_id,
        "buts_attendus": {"domicile": round(lam_dom, 2), "exterieur": round(lam_ext, 2)},
        "forme": {"domicile": dom.forme[-5:], "exterieur": ext.forme[-5:]},
        "probabilites": {k: round(v, 4) for k, v in probas.items()},
        "marches": marches,
    }


def conseil_de_paris(selections: list[dict]) -> dict | None:
    """Choisit le meilleur pari à conseiller parmi les sélections analysées.

    Priorité : un value bet (value > 0) assez sûr (proba >= 0.5).
    Sinon le meilleur value bet. Sinon la sélection la plus probable.
    Renvoie {marche, proba, cote, value, raison} ou None si pas de sélection.
    """
    if not selections:
        return None

    values = [s for s in selections if s.get("value", 0) > 0]
    surs = [s for s in values if s.get("proba", 0) >= 0.5]

    if surs:
        choix = max(surs, key=lambda s: s["proba"])
        raison = "Value bet fiable : forte probabilité ET cote sous-évaluée."
    elif values:
        choix = max(values, key=lambda s: s["value"])
        raison = "Meilleure value détectée du match (cote sous-évaluée)."
    else:
        choix = max(selections, key=lambda s: s["proba"])
        raison = "Pas de value claire — sélection la plus probable du match."

    return {
        "marche": choix["marche"],
        "proba": choix["proba"],
        "cote": choix.get("cote"),
        "value": choix.get("value", 0),
        "raison": raison,
    }


def combines_depuis_selections(
    selections_brutes: list[dict],
    nb_combines: int = 3,
    cote_cible: float = 3.0,
    tolerance: float = 0.5,
) -> list[dict]:
    """Construit les combinés à partir de sélections saisies manuellement.

    selections_brutes : [{match, marche, proba, cote}, ...]
    """
    pool = [
        Selection(match=s["match"], marche=s["marche"],
                  proba=float(s["proba"]), cote=float(s["cote"]),
                  ligue=s.get("ligue", ""))
        for s in selections_brutes
        if s.get("cote")  # ignore les sélections sans cote saisie
    ]
    combines = generer_combines(
        pool, nb_combines=nb_combines, cote_cible=cote_cible,
        tolerance=tolerance, value_min=-1.0,
    )
    return [
        {
            "cote_totale": round(c.cote_totale, 2),
            "proba_reussite": round(c.proba_combinee, 4),
            "value": round(c.value_combinee, 4),
            "selections": [
                {"match": s.match, "ligue": s.ligue, "marche": s.marche,
                 "cote": s.cote, "proba": round(s.proba, 4)}
                for s in c.selections
            ],
        }
        for c in combines
    ]


def _selections_objets(analyses: list[dict], value_min: float) -> list[Selection]:
    """Reconstruit des objets Selection (value bets uniquement) pour les combinés."""
    out = []
    for a in analyses:
        for s in a["selections"]:
            if s["value"] > value_min:
                out.append(Selection(
                    match=a["match"], marche=s["marche"],
                    proba=s["proba"], cote=s["cote"],
                    ligue=a.get("ligue", ""),
                ))
    return out


def generer_pronostics(
    api: ApiFootball,
    fixtures: list[FixtureInfo],
    nb_combines: int = 5,
    cote_cible: float = 3.0,
    value_min: float = 0.0,
    stats_season: int | None = None,
) -> dict:
    """Pipeline complet : analyse les matchs et génère les combinés."""
    analyses = []
    for fx in fixtures:
        res = analyser_fixture(api, fx, stats_season=stats_season)
        if res:
            analyses.append(res)

    # Passe 1 : uniquement les value bets (l'idéal, rentable à long terme)
    pool = _selections_objets(analyses, value_min)
    combines = generer_combines(pool, nb_combines=nb_combines, cote_cible=cote_cible)

    # Passe 2 : si pas assez de tickets, on complète avec les sélections à
    # plus forte probabilité (même sans value positive) pour remplir l'objectif.
    if len(combines) < nb_combines:
        pool_large = _selections_objets(analyses, value_min=-1.0)
        combines = generer_combines(
            pool_large, nb_combines=nb_combines, cote_cible=cote_cible,
            tolerance=0.7, value_min=-1.0,
        )

    combines_json = []
    for c in combines:
        combines_json.append({
            "cote_totale": round(c.cote_totale, 2),
            "proba_reussite": round(c.proba_combinee, 4),
            "value": round(c.value_combinee, 4),
            "selections": [
                {"match": s.match, "ligue": s.ligue, "marche": s.marche,
                 "cote": s.cote, "proba": round(s.proba, 4)}
                for s in c.selections
            ],
        })

    return {
        "genere_le": datetime.now(timezone.utc).isoformat(),
        "nb_matchs_analyses": len(analyses),
        "nb_combines": len(combines_json),
        "combines": combines_json,
        "analyses": analyses,
    }


def sauver_json(resultat: dict, chemin: str | Path) -> None:
    Path(chemin).write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
