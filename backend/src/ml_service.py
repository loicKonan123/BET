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
import pickle
import time
from pathlib import Path

from .api_client import BACKEND_DIR, ApiFootball
from .ml import ModeleML, entrainer, extraire_xg

log = logging.getLogger("edge.ml")

TTL_SECONDES = 24 * 3600.0

# Persistance disque des modèles entraînés (survit aux redémarrages)
MODELS_DIR = BACKEND_DIR / "data" / "ml_models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# scope -> ModeleML | None  (+ horodatage de fraîcheur) — cache mémoire
_CACHE: dict[str, tuple[float, ModeleML | None]] = {}


def _chemin(league_id: int) -> Path:
    return MODELS_DIR / f"club_{league_id}.pkl"


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
    if modele is not None:
        try:
            _chemin(league_id).write_bytes(pickle.dumps(modele))
        except Exception as e:
            log.warning("ml: sauvegarde disque échouée ligue=%s : %s", league_id, e)
    log.info("ml: ligue=%s -> %s", league_id, "modèle prêt" if modele else "données insuffisantes")
    return modele


def modele_club_si_pret(league_id: int) -> ModeleML | None:
    """Renvoie le modèle entraîné (mémoire, sinon disque). Jamais d'appel API.

    Ne déclenche pas d'entraînement : si aucun modèle n'existe, renvoie None et
    le consensus ignore simplement la source ML.
    """
    entry = _CACHE.get(f"club:{league_id}")
    if entry:
        return entry[1]
    # Pas en mémoire : tente le chargement depuis le disque
    chemin = _chemin(league_id)
    if chemin.exists():
        try:
            modele = pickle.loads(chemin.read_bytes())
            _CACHE[f"club:{league_id}"] = (time.time(), modele)
            return modele
        except Exception as e:
            log.warning("ml: chargement disque échoué ligue=%s : %s", league_id, e)
    return None
