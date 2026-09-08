"""Évalue uniquement les prévisions réellement archivées avant le coup d'envoi."""
import json
import sqlite3
from . import store
from .api_client import CACHE_DIR
from .match_data import score_90, utc, MODEL_VERSION
from .ml import _metriques
import numpy as np


def bilan_prospectif():
    try:
        with store._conn() as connection:
            rows = connection.execute("SELECT * FROM predictions ORDER BY cree_le DESC").fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        rows = []
    latest = {}
    for row in rows:
        if row["fixture_id"] not in latest and utc(row["cree_le"]) < utc(row["date_match"]):
            latest[row["fixture_id"]] = row
    probabilities, labels = [], []
    for fid, row in latest.items():
        try:
            result = json.loads((CACHE_DIR / f"fixtures_id-{fid}.json").read_text(encoding="utf-8"))
            fixture = next(f for f in result.get("response",[]) if f["fixture"]["id"] == fid)
            score = score_90(fixture)
            prediction = json.loads(row["data"])
            if score is None or prediction.get("version_modele") != MODEL_VERSION:
                continue
            p = prediction["probabilites"]
            probabilities.append([p[k] for k in ("1","X","2")])
            labels.append(0 if score[0]>score[1] else 1 if score[0]==score[1] else 2)
        except (OSError, ValueError, KeyError, StopIteration):
            continue
    return {"version_modele":MODEL_VERSION,"matchs_archives":len(latest),
            "matchs_evalues":len(labels),
            "metriques":_metriques(np.array(probabilities),np.array(labels)) if labels else None,
            "note":"Dernière prévision archivée avant le match, résultat à 90 minutes disponible en cache. Aucun taux de réussite n'est extrapolé aux matchs sans résultat."}
