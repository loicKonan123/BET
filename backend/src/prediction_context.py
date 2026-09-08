"""Contexte observable : conserve la date de collecte, sans inventer les absences."""
import json
from datetime import datetime, timezone
from .api_client import CACHE_DIR, BACKEND_DIR
from .match_data import utc

CONTEXT_DIR = BACKEND_DIR / "data" / "prediction_context"


def contexte_archive(fixture_id, date):
    path = CONTEXT_DIR / f"{fixture_id}.json"
    try:
        ctx = json.loads(path.read_text(encoding="utf-8"))
        return ctx if utc(ctx["observe_le"]) < utc(date) else {}
    except (OSError, ValueError, KeyError, TypeError):
        return {}


def collecter_contexte(fx, historique):
    """Les caches écrits après le coup d'envoi sont exclus de l'entraînement.

    Aucun appel réseau supplémentaire. La composition peut être absente ;
    dans ce cas sa stabilité reste inconnue et n'est jamais remplacée par zéro.
    """
    cutoff = min(utc(fx.date), datetime.now(timezone.utc))
    ctx = contexte_archive(fx.fixture_id, fx.date)
    observations = []
    def lire(endpoint, fid):
        path = CACHE_DIR / f"{endpoint}_fixture-{fid}.json"
        try:
            observed = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if observed >= cutoff:
                return None
            data = json.loads(path.read_text(encoding="utf-8")).get("response", [])
            observations.append(observed)
            return data
        except (OSError, ValueError, TypeError):
            return None
    injuries = lire("injuries", fx.fixture_id)
    # Une liste vide ne prouve pas une couverture exhaustive des blessures.
    if injuries:
        for tid, side in ((fx.home_id,"dom"),(fx.away_id,"ext")):
            people = {r.get("player",{}).get("id") for r in injuries if r.get("team",{}).get("id")==tid}
            people.discard(None)
            if people:
                ctx[f"absents_{side}"] = len(people)
    lineups = lire("fixtures_lineups", fx.fixture_id)
    if lineups:
        for tid, side in ((fx.home_id,"dom"),(fx.away_id,"ext")):
            current = next((r for r in lineups if r.get("team",{}).get("id")==tid), {})
            starters = {r.get("player",{}).get("id") for r in current.get("startXI",[])} - {None}
            if len(starters) != 11:
                continue
            past = [f for f in historique if tid in (f["teams"]["home"]["id"], f["teams"]["away"]["id"])]
            if not past:
                continue
            previous = lire("fixtures_lineups", past[-1]["fixture"]["id"]) or []
            roster = next((r for r in previous if r.get("team",{}).get("id")==tid), {})
            old = {r.get("player",{}).get("id") for r in roster.get("startXI",[])} - {None}
            if len(old) == 11:
                ctx[f"stabilite_{side}"] = len(starters & old)/11
    if observations and any(k != "observe_le" for k in ctx):
        ctx["observe_le"] = max(observations+[utc(ctx["observe_le"])] if ctx.get("observe_le") else observations).isoformat()
        CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
        path = CONTEXT_DIR / f"{fx.fixture_id}.json"
        # Le premier état pré-match est conservé pour l'apprentissage reproductible.
        try:
            with path.open("x", encoding="utf-8") as stream:
                json.dump(ctx, stream, ensure_ascii=False, allow_nan=False)
        except FileExistsError:
            pass
    return ctx
