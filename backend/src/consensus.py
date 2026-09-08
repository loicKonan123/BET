"""Compatibilite : toute nouvelle prevision utilise le service commun."""
from .prediction_service import historique_ligue, predire_historique, charger_modele, xg_cache


def consensus_match(api, league, season, home_id, away_id, cotes_1x2=None,
                    poisson_fallback=None, *, date=None):
    if date is None:
        raise ValueError("La date du match est obligatoire ; utiliser pipeline.analyser_fixture avec FixtureInfo")
    rows = historique_ligue(api, league, season)
    return predire_historique(rows, home_id, away_id, date, cotes=cotes_1x2,
                             model=charger_modele(league), xg=xg_cache(rows)) or {}
