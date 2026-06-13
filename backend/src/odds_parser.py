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


def _devig_proportionnel(inv: dict[str, float]) -> dict[str, float]:
    """Normalisation proportionnelle (multiplicative) — méthode de base.

    Simple mais ignore le favorite-longshot bias : sur-estime les favoris et
    sous-estime les outsiders. Sert de repli si Shin ne converge pas.
    """
    overround = sum(inv.values())
    return {k: v / overround for k, v in inv.items()}


def _devig_shin(inv: dict[str, float], tol: float = 1e-10, max_iter: int = 100) -> dict[str, float] | None:
    """Retrait de marge par la méthode de Shin (1992).

    Modélise le marché comme un mélange de parieurs informés et non informés ;
    le paramètre z = proportion de money « informé » qui crée la marge. Corrige
    le favorite-longshot bias bien mieux que la normalisation proportionnelle
    (méthode de référence dans la littérature et chez Pinnacle).

    Proba vraie : p_i = [√(z² + 4(1−z)·π_i²/B) − z] / (2(1−z))
    où π_i = 1/cote_i (proba implicite brute), B = Σ π_i (booksum/overround).
    z est résolu par bissection pour que Σ p_i = 1.
    """
    pis = list(inv.values())
    B = sum(pis)
    if B <= 1.0:  # pas de marge (ou cotes incohérentes) -> rien à corriger
        return None

    def somme_probas(z: float) -> float:
        if z >= 1.0:
            return float("inf")
        s = 0.0
        for pi in pis:
            rad = z * z + 4.0 * (1.0 - z) * (pi * pi) / B
            s += (rad ** 0.5 - z) / (2.0 * (1.0 - z))
        return s

    # Σp(z) décroît avec z ; on cherche z tel que Σp(z) = 1 par bissection.
    lo, hi = 0.0, 0.5
    if somme_probas(lo) < 1.0:  # déjà ≤ 1 sans correction : marge dégénérée
        return None
    for _ in range(max_iter):
        mid = (lo + hi) / 2.0
        s = somme_probas(mid)
        if abs(s - 1.0) < tol:
            break
        if s > 1.0:
            lo = mid
        else:
            hi = mid
    z = (lo + hi) / 2.0

    cles = list(inv.keys())
    probas = {}
    for cle, pi in zip(cles, pis):
        rad = z * z + 4.0 * (1.0 - z) * (pi * pi) / B
        probas[cle] = (rad ** 0.5 - z) / (2.0 * (1.0 - z))
    # micro-renormalisation (résidu de bissection)
    tot = sum(probas.values())
    return {k: v / tot for k, v in probas.items()} if tot > 0 else None


def probas_marche_1x2(cotes: dict[str, float], methode: str = "shin") -> dict[str, float] | None:
    """Convertit les cotes 1X2 en probabilités réelles, marge (vig) retirée.

    Une cote implique une proba brute 1/cote. La somme des 1/cote dépasse 1 :
    l'excédent est la marge du bookmaker (~5% consensus, ~2.5% chez Pinnacle).

    methode="shin" (défaut) : corrige le favorite-longshot bias (recommandé).
    methode="proportionnel" : normalisation multiplicative simple.

    Le closing line du marché est le meilleur prédicteur connu : ces probas
    servent d'ancre de calibration. Renvoie None si les 3 cotes manquent.
    """
    try:
        inv = {k: 1.0 / cotes[k] for k in ("1", "X", "2")}
    except (KeyError, ZeroDivisionError):
        return None
    if sum(inv.values()) <= 0:
        return None

    if methode == "shin":
        shin = _devig_shin(inv)
        if shin is not None:
            return shin
    return _devig_proportionnel(inv)
