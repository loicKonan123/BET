"""Orchestration du modèle ML : récupération des stats xG + entraînement + cache.

L'entraînement est COÛTEUX (1 appel API `fixtures/statistics` par match), donc
on le sépare de la prédiction :
  - `entrainer_club()` : construit le dataset (fetch + cache disque) et entraîne.
    À déclencher explicitement (endpoint/scripts), pas pendant une requête user.
  - `modele_club_si_pret()` : renvoie le modèle déjà en mémoire, ou None.
    Le consensus l'appelle : si le modèle n'est pas prêt, la source ML est
    simplement omise (dégradation propre).
"""
import logging

from .api_client import ApiFootball
from .ml import ModeleML, entrainer, extraire_xg

log = logging.getLogger("edge.ml")

TTL_SECONDES = 24 * 3600.0

# scope -> ModeleML | None  (+ horodatage de fraîcheur)
import time
_CACHE: dict[str, tuple[float, ModeleML | None]] = {}


def _fixtures(api: ApiFootball, league_id: int, saisons: list[int]) -> list:
    out = []
    for s in saisons:
        try:
            out.extend(api.get("fixtures", {"league": league_id, "season": s}).get("response", []))
        except Exception:
            continue
    return out


def _collecter_xg(api: ApiFootball, fixtures: list) -> dict[int, dict]:
    """Récupère le xG par match (cache disque). 1 appel API par match au 1er passage."""
    xg: dict[int, dict] = {}
    termines = [f for f in fixtures
                if f.get("fixture", {}).get("status", {}).get("short") in ("FT", "AET", "PEN")]
    total = len(termines)
    for i, f in enumerate(termines):
        fid = f["fixture"]["id"]
        try:
            data = api.get("fixtures/statistics", {"fixture": fid})
            xg[fid] = extraire_xg(data.get("response", []))
        except Exception as e:
            log.warning("ml: stats échec fixture=%s : %s", fid, e)
        if i % 100 == 0:
            log.info("ml: collecte stats %s/%s", i, total)
    return xg


def entrainer_club(api: ApiFootball, league_id: int, saisons: list[int]) -> ModeleML | None:
    """Construit le dataset (fetch xG) et entraîne le modèle pour une ligue."""
    scope = f"club:{league_id}"
    log.info("ml: entraînement ligue=%s saisons=%s…", league_id, saisons)
    fixtures = _fixtures(api, league_id, saisons)
    xg = _collecter_xg(api, fixtures)
    modele = entrainer(fixtures, xg)
    _CACHE[scope] = (time.time(), modele)
    log.info("ml: ligue=%s -> %s", league_id, "modèle prêt" if modele else "données insuffisantes")
    return modele


def modele_club_si_pret(league_id: int) -> ModeleML | None:
    """Renvoie le modèle en cache mémoire s'il est frais, sinon None (pas de fetch)."""
    entry = _CACHE.get(f"club:{league_id}")
    if entry and (time.time() - entry[0]) < TTL_SECONDES:
        return entry[1]
    return None
