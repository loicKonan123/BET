"""Calcul du consensus multi-modèles pour un match — réutilisable.

Centralise la logique « Poisson ajusté (Dixon-Coles MLE) + Elo + marché ->
consensus par pool logarithmique » pour qu'elle soit partagée entre la page
match (`_multi_modeles`) et la génération de tickets (`tickets.py`).
"""
import logging

from .blend import fusionner_1x2
from .dc_service import modele_club, modele_national
from .elo import proba_1x2_elo
from .elo_service import assurer_ratings_club, assurer_ratings_nationaux, rating_de
from .odds_parser import probas_marche_1x2

log = logging.getLogger("edge.consensus")

LIGUES_NATIONALES = {1, 4, 5, 9, 10, 29, 30, 31, 32, 33, 34}
HOTES_WC_2026 = {2, 16, 101}  # USA, Mexico, Canada — terrain réel, pas neutre


def _poisson_ajuste(api, league, season, home_id, away_id):
    """Probabilités 1X2 du Poisson ajusté (Dixon-Coles MLE), ou None."""
    try:
        if league in LIGUES_NATIONALES:
            modele = modele_national(api)
        else:
            modele = modele_club(api, league, [season - 1, season])
        if modele and modele.connait(home_id) and modele.connait(away_id):
            neutre = league == 1 and home_id not in HOTES_WC_2026
            return modele.proba_1x2(home_id, away_id, terrain_neutre=neutre)
    except Exception as e:
        log.exception("poisson ajusté: ÉCHEC league=%s : %s", league, e)
    return None


def consensus_match(api, league: int, season: int, home_id: int, away_id: int,
                    cotes_1x2: dict | None = None,
                    poisson_fallback: dict | None = None) -> dict:
    """Construit le consensus multi-modèles pour un match.

    cotes_1x2 : {'1','X','2': cote} si disponibles (sinon marché omis).
    poisson_fallback : probas Poisson à utiliser si le modèle ajusté manque.

    Renvoie {poisson, poisson_ajuste, elo, elo_info, marche, consensus}.
    """
    # 1 — Poisson ajusté (préféré), sinon fallback fourni
    p_poisson = _poisson_ajuste(api, league, season, home_id, away_id)
    poisson_ajuste = p_poisson is not None
    if p_poisson is None:
        p_poisson = poisson_fallback

    # 2 — Elo
    p_elo = None
    elo_info = None
    try:
        est_national = league in LIGUES_NATIONALES
        if est_national:
            ratings = assurer_ratings_nationaux(api)
        else:
            ratings = assurer_ratings_club(api, league, [season - 1, season])
        r_home = rating_de(ratings, home_id)
        r_away = rating_de(ratings, away_id)
        neutre = league == 1 and home_id not in HOTES_WC_2026
        p_elo = proba_1x2_elo(r_home, r_away, terrain_neutre=neutre)
        elo_info = {"rating_dom": round(r_home), "rating_ext": round(r_away),
                    "ecart": round(r_home - r_away), "terrain_neutre": neutre}
    except Exception as e:
        log.exception("elo: ÉCHEC league=%s : %s", league, e)

    # 3 — Marché (vig retiré, méthode Shin)
    p_marche = None
    if cotes_1x2 and all(cotes_1x2.get(k) for k in ("1", "X", "2")):
        p_marche = probas_marche_1x2(cotes_1x2)

    consensus = fusionner_1x2(p_poisson, p_elo, p_marche)

    return {
        "poisson": {k: round(v, 4) for k, v in p_poisson.items()} if p_poisson else None,
        "poisson_ajuste": poisson_ajuste,
        "elo": {k: round(v, 4) for k, v in p_elo.items()} if p_elo else None,
        "elo_info": elo_info,
        "marche": {k: round(v, 4) for k, v in p_marche.items()} if p_marche else None,
        "consensus": consensus,
    }
