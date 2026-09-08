"""Contrat commun : résultats à 90 minutes et informations connues avant match."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from math import isfinite

MODEL_VERSION = "edge-90-v1"
FINISHED = {"FT", "AET", "PEN"}


def utc(value):
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def score_90(f: dict):
    status = f.get("fixture", {}).get("status", {}).get("short")
    if status not in FINISHED:
        return None
    score = (f.get("score") or {}).get("fulltime") or {}
    # Repli uniquement pour FT : les buts AET/PEN peuvent inclure la prolongation.
    if status == "FT" and any(score.get(k) is None for k in ("home", "away")):
        score = f.get("goals") or {}
    values = [score.get(k) for k in ("home", "away")]
    if any(isinstance(v, bool) or not isinstance(v, (int, float))
           or not isfinite(v) or v < 0 or int(v) != v for v in values):
        return None
    return tuple(int(v) for v in values)


def historique_90(fixtures, avant=None):
    """Déduplique, trie et exclut les résultats pas encore connus à `avant`.

    En l'absence d'heure de fin archivée, délai conservateur de trois heures
    après le coup d'envoi. Les scores affichés en direct ne sont pas modifiés.
    """
    limite = utc(avant) if avant is not None else datetime.now(timezone.utc)
    out = {}
    for f in fixtures:
        score = score_90(f)
        try:
            date = utc(f["fixture"]["date"])
            fid = f["fixture"]["id"]
        except (KeyError, AttributeError, ValueError, TypeError):
            continue
        if score is None or date + timedelta(hours=3) >= limite:
            continue
        row = deepcopy(f)
        row["goals"] = dict(zip(("home", "away"), score))
        out[fid] = row
    return sorted(out.values(), key=lambda f: (utc(f["fixture"]["date"]), f["fixture"]["id"]))
