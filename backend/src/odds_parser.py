"""Extrait les cotes des marchés voulus depuis la réponse `odds` d'API-Football.

IDs des marchés (bets) chez API-Football :
    1  = Match Winner          (Home / Draw / Away)        -> 1X2
    5  = Goals Over/Under      (Over 2.5 / Under 2.5)
    8  = Both Teams Score      (Yes / No)                  -> BTTS
    12 = Double Chance         (Home/Draw, Home/Away, Draw/Away)

On moyenne les cotes de tous les bookmakers (consensus du marché) pour
chaque sélection. Plus robuste qu'un seul bookmaker.
"""
from collections import defaultdict
from statistics import mean

from .api_client import ApiFootball

# Correspondance marché -> (id du bet, valeur recherchée) -> clé de sortie
_CIBLES = {
    1: {  # Match Winner
        "Home": "1",
        "Draw": "X",
        "Away": "2",
    },
    5: {  # Over/Under
        "Over 2.5": "over_2.5",
        "Under 2.5": "under_2.5",
    },
    8: {  # Both Teams Score
        "Yes": "btts_oui",
        "No": "btts_non",
    },
    12: {  # Double Chance
        "Home/Draw": "1X",
        "Home/Away": "12",
        "Draw/Away": "X2",
    },
}


def parser_cotes(resp: list) -> dict[str, float]:
    """Renvoie {clé_marché: cote_moyenne}, ex {'1': 1.85, 'X': 3.4, 'over_2.5': 1.9}."""
    collecte: dict[str, list[float]] = defaultdict(list)

    if not resp:
        return {}

    for bookmaker in resp[0].get("bookmakers", []):
        for bet in bookmaker.get("bets", []):
            cibles = _CIBLES.get(bet.get("id"))
            if not cibles:
                continue
            for v in bet.get("values", []):
                cle = cibles.get(v.get("value"))
                if cle is None:
                    continue
                try:
                    collecte[cle].append(float(v["odd"]))
                except (TypeError, ValueError, KeyError):
                    continue

    return {cle: round(mean(cotes), 2) for cle, cotes in collecte.items() if cotes}


def recuperer_cotes(api: ApiFootball, fixture_id: int) -> dict[str, float]:
    """Appelle l'API (1 requête) et renvoie les cotes moyennes par marché."""
    data = api.get("odds", {"fixture": fixture_id})
    return parser_cotes(data.get("response", []))
