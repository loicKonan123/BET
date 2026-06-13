"""Orchestration du modèle Dixon-Coles ajusté (MLE) : fetch API + cache mémoire.

Sépare la logique métier (récupérer les matchs d'une ligue/compétition) du
moteur d'estimation pur (`dixon_coles_fit`). Le fit est rapide (<1s) et les
fixtures sont déjà en cache disque, donc on garde un simple cache mémoire par
processus avec TTL — pas de sérialisation des vecteurs numpy.
"""
import time

from .api_client import ApiFootball
from .dixon_coles_fit import ModeleDixonColes, ajuster

COMPETITIONS_NATIONALES = [1, 4, 5, 9, 10, 29, 30, 31, 32, 33, 34]
TTL_SECONDES = 24 * 3600.0

# scope -> (timestamp, ModeleDixonColes | None)
_CACHE: dict[str, tuple[float, ModeleDixonColes | None]] = {}


def _fixtures(api: ApiFootball, league_id: int, saisons: list[int]) -> list:
    out = []
    for s in saisons:
        try:
            data = api.get("fixtures", {"league": league_id, "season": s})
            out.extend(data.get("response", []))
        except Exception:
            continue
    return out


def _depuis_cache(scope: str) -> ModeleDixonColes | None | str:
    """Renvoie le modèle si frais, sinon la sentinelle 'expire'."""
    entry = _CACHE.get(scope)
    if entry and (time.time() - entry[0]) < TTL_SECONDES:
        return entry[1]
    return "expire"


def modele_club(api: ApiFootball, league_id: int, saisons: list[int],
                forcer: bool = False) -> ModeleDixonColes | None:
    """Modèle Dixon-Coles ajusté pour une ligue de clubs (cache mémoire)."""
    scope = f"club:{league_id}"
    if not forcer:
        cached = _depuis_cache(scope)
        if cached != "expire":
            return cached

    pool = _fixtures(api, league_id, saisons)
    modele = ajuster(pool)
    _CACHE[scope] = (time.time(), modele)
    return modele


def modele_national(api: ApiFootball, saisons: list[int] | None = None,
                    forcer: bool = False) -> ModeleDixonColes | None:
    """Modèle Dixon-Coles ajusté sur le pool international (sélections)."""
    scope = "national"
    if not forcer:
        cached = _depuis_cache(scope)
        if cached != "expire":
            return cached

    saisons = saisons or [2024, 2025, 2026]
    pool = []
    for lid in COMPETITIONS_NATIONALES:
        pool.extend(_fixtures(api, lid, saisons))
    modele = ajuster(pool)
    _CACHE[scope] = (time.time(), modele)
    return modele
