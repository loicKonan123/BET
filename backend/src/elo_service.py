"""Orchestration des ratings Elo : récupération API + cache SQLite.

Sépare la logique métier (récupérer les matchs, gérer le cache) du moteur de
calcul pur (`elo.py`). Les ratings sont mis en cache et rafraîchis seulement
si trop anciens — on évite de rejouer tout l'historique à chaque requête.
"""
from . import store
from .api_client import ApiFootball
from .elo import RATING_INITIAL, construire_ratings

# Compétitions internationales : on en tire un graphe Elo connecté pour les
# sélections nationales (qualifs + phases finales + Nations League + amicaux).
COMPETITIONS_NATIONALES = [1, 4, 5, 9, 10, 29, 30, 31, 32, 33, 34]

# Fraîcheur du cache : on ne reconstruit pas plus d'une fois par 24h.
TTL_HEURES = 24.0


def _fixtures_competition(api: ApiFootball, league_id: int, saisons: list[int]) -> list:
    """Récupère les fixtures d'une compétition sur plusieurs saisons (cache disque)."""
    out = []
    for s in saisons:
        try:
            data = api.get("fixtures", {"league": league_id, "season": s})
            out.extend(data.get("response", []))
        except Exception:
            continue
    return out


def assurer_ratings_nationaux(api: ApiFootball, saisons: list[int] | None = None,
                              forcer: bool = False) -> dict[int, dict]:
    """Garantit une table Elo nationale à jour, la (re)construit si nécessaire."""
    scope = "national"
    age = store.elo_age_heures(scope)
    if not forcer and age is not None and age < TTL_HEURES:
        return store.get_elo_ratings(scope)

    saisons = saisons or [2024, 2025, 2026]
    pool = [
        (lid, _fixtures_competition(api, lid, saisons))
        for lid in COMPETITIONS_NATIONALES
    ]
    ratings = construire_ratings(pool)
    if ratings:
        store.save_elo_ratings(scope, ratings)
        return ratings
    # Échec de construction : on renvoie l'ancien cache s'il existe
    return store.get_elo_ratings(scope)


def assurer_ratings_club(api: ApiFootball, league_id: int, saisons: list[int],
                         forcer: bool = False) -> dict[int, dict]:
    """Idem pour une ligue de clubs (scope 'club:{league_id}')."""
    scope = f"club:{league_id}"
    age = store.elo_age_heures(scope)
    if not forcer and age is not None and age < TTL_HEURES:
        return store.get_elo_ratings(scope)

    pool = [(league_id, _fixtures_competition(api, league_id, saisons))]
    ratings = construire_ratings(pool)
    if ratings:
        store.save_elo_ratings(scope, ratings)
        return ratings
    return store.get_elo_ratings(scope)


def rating_de(ratings: dict[int, dict], team_id: int) -> float:
    """Note Elo d'une équipe, ou la note initiale si inconnue."""
    return ratings.get(team_id, {}).get("rating", RATING_INITIAL)
