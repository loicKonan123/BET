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
from .odds_parser import recuperer_prix
from .ligues_mise_o_jeu import LIGUES_SOCCER
from .poisson import compute_probabilities
from .prediction_service import predire_match
from .blend import conseil_consensus
from .team_stats import (
    buts_attendus,
    recuperer_stats,
    recuperer_stats_national,
    recuperer_stats_recentes,
)


def _nom_ligue(league_id: int) -> str:
    return LIGUES_SOCCER.get(league_id, f"Ligue {league_id}")


def _score(fx) -> dict | None:
    """Score réel {domicile, exterieur} si connu (live/terminé), sinon None."""
    if fx.buts_dom is None or fx.buts_ext is None:
        return None
    return {"domicile": fx.buts_dom, "exterieur": fx.buts_ext}

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


def _stats_equipe(api, league, season, team_id, mode, allow_fallback: bool = True):
    """Récupère les stats d'une équipe selon le mode (club ou national)."""
    if mode == "national":
        return recuperer_stats_national(api, team_id)

    courant = recuperer_stats(api, league, season, team_id)
    if courant and (courant.fiable or not allow_fallback):
        return courant

    precedent = None
    if allow_fallback and season:
        precedent = recuperer_stats(api, league, season - 1, team_id)
        if precedent and precedent.fiable:
            return precedent

    recent = recuperer_stats_recentes(api, team_id) if allow_fallback else None
    if recent and recent.fiable:
        return recent

    return courant or precedent or recent


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


def _analyser_commun(api, fx, stats_season=None):
    """Source unique : mêmes cotes, grille, probabilités et identifiant partout."""
    from dataclasses import replace
    target = replace(fx, season=stats_season) if stats_season else fx
    cotes = {}
    provenance = None
    if fx.status in ("NS", "TBD"):
        try:
            cotes, provenance = recuperer_prix(api, fx.fixture_id)
        except Exception:
            pass
    prediction = predire_match(api, target, cotes, provenance)
    if prediction is None:
        return None
    probas = prediction["probabilites"]
    selections = []
    for cle,p in probas.items():
        cote = prediction["cotes"].get(cle)
        selections.append({"cle":cle,"marche":LIBELLES.get(cle,cle),"proba":p,
                           "cote":cote,"proba_implicite":round(1/cote,4) if cote else None,
                           "value":round(p*cote-1,4) if cote else 0.0,
                           "est_value_bet":bool(cote and p*cote>1),"fixture_id":fx.fixture_id,
                           "prediction_id":prediction["prediction_id"]})
    return {"match":f"{fx.home_name} - {fx.away_name}","ligue":_nom_ligue(fx.league),
            "fixture_id":fx.fixture_id,"date":fx.date,"status":fx.status,"score":_score(fx),
            "buts_attendus":prediction["buts_attendus"],"forme":prediction["forme"],
            "probabilites":probas,"consensus":prediction["consensus"]["probabilites"],
            "sources_consensus":prediction["consensus"]["sources_disponibles"],
            "selections":selections,"marches":selections,"multi_modeles":prediction,
            "conseil":conseil_consensus(prediction["consensus"]["probabilites"],prediction["cotes"]),
            "prediction_id":prediction["prediction_id"],"version_modele":prediction["version_modele"],
            "cadre_prediction":prediction["cadre"],"calcule_le":prediction["calcule_le"]}


@dataclass
class FixtureInfo:
    fixture_id: int
    league: int
    season: int
    home_id: int
    away_id: int
    home_name: str
    away_name: str
    date: str = ""    # datetime ISO du coup d'envoi
    status: str = "NS"  # code statut API-Football
    buts_dom: int | None = None  # score réel (live ou terminé)
    buts_ext: int | None = None


STATUTS_UPCOMING = {"NS", "TBD"}
STATUTS_LIVE     = {"1H", "HT", "2H", "ET", "BT", "P", "SUSP", "INT", "LIVE"}
STATUTS_TERMINES = {"FT", "AET", "PEN", "AWD", "WO"}


def fixtures_depuis_reponse(
    reponse: list,
    league_id: int | None = None,
    ligues_autorisees: set[int] | None = None,
    statuts_autorises: set[str] | None = None,
) -> list[FixtureInfo]:
    """Convertit la réponse `fixtures` de l'API en liste de FixtureInfo.

    statuts_autorises : None = tous les statuts. Passer STATUTS_UPCOMING pour
        le mode génération de tickets (matchs pas encore joués uniquement).
    """
    out = []
    for f in reponse:
        status = f["fixture"]["status"]["short"]
        if statuts_autorises is not None and status not in statuts_autorises:
            continue
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
            date=f["fixture"].get("date", ""),
            status=status,
            buts_dom=f.get("goals", {}).get("home"),
            buts_ext=f.get("goals", {}).get("away"),
        ))
    return out


def analyser_fixture(api, fx, stats_season=None):
    return _analyser_commun(api, fx, stats_season)


def analyser_fixture_sans_cotes(api, fx, stats_season=None):
    # Alias conserve pour les clients existants : prediction canonique identique.
    return _analyser_commun(api, fx, stats_season)


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
        if a.get("cadre_prediction") != "avant_match":
            continue
        for s in a["selections"]:
            if s.get("cote") and s["cote"] > 1 and s["value"] > value_min:
                out.append(Selection(
                    match=a["match"], marche=s["marche"],
                    proba=s["proba"], cote=s["cote"],
                    ligue=a.get("ligue", ""),
                    fixture_id=s.get("fixture_id", a.get("fixture_id", 0)),
                    cle=s.get("cle", ""),
                    match_date=s.get("match_date", a.get("date", "")),
                    prediction_id=a.get("prediction_id", ""), version_modele=a.get("version_modele", ""),
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
                 "cote": s.cote, "proba": round(s.proba, 4),
                 "fixture_id": s.fixture_id, "cle": s.cle,
                 "match_date": s.match_date, "prediction_id":s.prediction_id, "version_modele":s.version_modele}
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
