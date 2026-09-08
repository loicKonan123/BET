"""Point d'entrée unique des prévisions EDGE, utilisé par toutes les pages."""
import hashlib
import json
import logging
import pickle
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import RLock

from .api_client import BACKEND_DIR
from .blend import fusionner_1x2
from .match_data import MODEL_VERSION, historique_90, utc
from .prediction_models import Ensemble, Historique, aligner_grille, marches_grille
from .dixon_coles_fit import ajuster
from .odds_parser import probas_marche_1x2
from .prediction_context import collecter_contexte

log = logging.getLogger("edge.prediction")
MODEL_DIR = BACKEND_DIR / "data" / "prediction_models"
NATIONAL = {1,4,5,9,10,29,30,31,32,33,34}
_CACHE = {}
_LOCK = RLock()


def chemin_modele(league):
    league = 1 if league in NATIONAL else league
    return MODEL_DIR / f"{MODEL_VERSION}_{league}.pkl"


def charger_modele(league):
    path = chemin_modele(league)
    if not path.exists():
        return None
    key = ("model", league, path.stat().st_mtime_ns)
    with _LOCK:
        if key not in _CACHE:
            try:
                model = pickle.loads(path.read_bytes())
                if model.version != MODEL_VERSION:
                    return None
                _CACHE[key] = model
            except Exception:
                log.exception("Modèle inutilisable ligue=%s", league)
                return None
        return _CACHE[key]


def historique_ligue(api, league, season):
    key = ("history", league, season)
    with _LOCK:
        entry = _CACHE.get(key)
        if entry and time.monotonic()-entry[0] < 300:
            return entry[1]
    rows = []
    # Les sélections nécessitent un graphe international, pas une seule coupe.
    for lid in sorted(NATIONAL) if league in NATIONAL else [league]:
        # Même profondeur historique que l'entraînement local ; rafraîchit ensuite
        # les saisons récentes, qui remplacent les lignes déjà présentes.
        for path in (BACKEND_DIR / "data" / "cache").glob(f"fixtures_league-{lid}_season-*.json"):
            try:
                rows.extend(json.loads(path.read_text(encoding="utf-8")).get("response", []))
            except (OSError, ValueError):
                continue
        for saison in (season-1, season):
            try:
                rows.extend(api.get("fixtures", {"league":lid,"season":saison}, ttl=21600).get("response", []))
            except Exception:
                log.warning("Historique indisponible ligue=%s saison=%s", lid, saison)
    with _LOCK:
        _CACHE[key] = (time.monotonic(),rows)
    return rows


def xg_cache(fixtures):
    from .ml import extraire_xg
    out = {}
    for f in fixtures:
        fid = f["fixture"]["id"]
        path = BACKEND_DIR / "data" / "cache" / f"fixtures_statistics_fixture-{fid}.json"
        if path.exists():
            try:
                out[fid] = extraire_xg(json.loads(path.read_text(encoding="utf-8")).get("response", []))
            except (ValueError, OSError):
                continue
    return out


def predire_historique(fixtures, home, away, date, cotes=None, model=None, xg=None, contexte=None, neutre=False):
    """Mêmes calculs en production et en backtest ; aucun accès réseau ici."""
    rows = historique_90(fixtures, date)
    if len(rows) < 20:
        return None
    state = Historique()
    for f in rows:
        state.update(f, xg or {})
    if min(len(state.equipes[home].forme), len(state.equipes[away].forme)) < 4:
        return None
    eligible = model and model.version == MODEL_VERSION and utc(model.trained_until) + timedelta(hours=3) < utc(date)
    if not eligible:
        model = Ensemble()
        # Ajustement quotidien réutilisé pour les matchs partageant l'historique.
        ref = utc(date).replace(hour=0, minute=0, second=0, microsecond=0)
        dc_key = ("dc", ref.isoformat(), tuple((f["fixture"]["id"],f["goals"]["home"],f["goals"]["away"]) for f in rows))
        with _LOCK:
            if dc_key not in _CACHE:
                _CACHE[dc_key] = ajuster(rows, ref_date=ref)
            model.dc = _CACHE[dc_key]
    sources, grid, forme = model.sources(state, home, away, date, contexte, neutre)
    probs = {name:dict(zip(("1","X","2"),map(float,p))) for name,p in sources.items()}
    market = probas_marche_1x2(cotes) if cotes and all(cotes.get(k,0)>1 for k in ("1","X","2")) else None
    weights = dict(model.weights or {"poisson":0.3,"elo":0.7})
    if market:
        weights = {k:v*0.5 for k,v in weights.items()}
        weights["marche"] = 0.5  # Poids marché explicite ; non appris sans archives datées.
    consensus = fusionner_1x2(probs.get("poisson"),probs.get("elo"),market,probs.get("ml"),
                             autres={k:v for k,v in probs.items() if k not in ("poisson","elo","ml")},
                             poids_config=weights)
    p = consensus["probabilites"]
    if not p:
        return None
    aligned = aligner_grille(grid,[p[k] for k in ("1","X","2")])
    marches = marches_grille(aligned)
    # Fixe l'identité numérique des 1X2 et doubles chances dans toutes les sorties.
    marches.update(p)
    marches.update({"1X":round(p["1"]+p["X"],4), "X2":round(p["X"]+p["2"],4), "12":round(p["1"]+p["2"],4)})
    import numpy as np
    h,a = np.indices(aligned.shape)
    return {**probs,"marche":market,"poisson_ajuste":model.dc is not None,
            "elo_info":{"rating_dom":round(state.equipes[home].elo),"rating_ext":round(state.equipes[away].elo),
                        "ecart":round(state.equipes[home].elo-state.equipes[away].elo),"terrain_neutre":neutre},
            "consensus":consensus,"probabilites":marches,
            "buts_attendus":{"domicile":round(float((h*aligned).sum()),2),"exterieur":round(float((a*aligned).sum()),2)},
            "forme":forme,"validation":model.validation,
            "version_modele":MODEL_VERSION,"derniere_observation":rows[-1]["fixture"]["date"],
            "modele_entraine":bool(eligible)}


def predire_match(api, fx, cotes=None, provenance=None):
    """Prévision canonique pour une fixture : même instantané pour tous les écrans."""
    now = datetime.now(timezone.utc)
    date = utc(fx.date)
    rows = historique_90(historique_ligue(api,fx.league,fx.season), min(date,now))
    contexte = collecter_contexte(fx, rows)
    # Ne jamais utiliser des cotes collectées après le début pour un backtest.
    avant_match = utc(fx.date)>now and fx.status in ("NS","TBD")
    cotes = cotes if avant_match else {}
    model = charger_modele(fx.league)
    if fx.league in NATIONAL and getattr(model, "scope", None) != "international":
        model = None
    history_id = hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()[:12]
    provenance = provenance if avant_match else None
    price_id = json.dumps([cotes or {}, provenance, contexte],sort_keys=True)
    key = ("prediction",fx.fixture_id,fx.date,history_id,price_id,
           chemin_modele(fx.league).stat().st_mtime_ns if chemin_modele(fx.league).exists() else 0)
    with _LOCK:
        entry = _CACHE.get(key)
        if entry and time.monotonic()-entry[0] < 300:
            return entry[1]
    xkey = ("xg",history_id)
    with _LOCK:
        xentry = _CACHE.get(xkey)
    xg = xentry[1] if xentry and time.monotonic()-xentry[0]<3600 else xg_cache(rows)
    with _LOCK:
        _CACHE[xkey] = (time.monotonic(),xg)
    result = predire_historique(rows,fx.home_id,fx.away_id,date,cotes,model,xg,contexte,
                               neutre=fx.league==1 and fx.home_id not in {2,16,101})
    if result:
        identity = hashlib.sha256(json.dumps({"fixture":fx.fixture_id,"date":fx.date,"history":history_id,
                    "cotes":cotes,"provenance":provenance,"contexte":contexte,"model":key[-1],"p":result["probabilites"]},sort_keys=True).encode()).hexdigest()[:20]
        result.update({"prediction_id":identity,"calcule_le":now.isoformat(),
                       "cadre":"avant_match" if avant_match else "reconstruction_avant_match",
                       "cotes":cotes or {}, "provenance_cotes":provenance, "contexte":contexte})
        if avant_match:
            from .store import sauver_prediction
            sauver_prediction(fx.fixture_id,identity,fx.date,result)
        with _LOCK:
            if len(_CACHE)>600:
                _CACHE.clear()
            _CACHE[key] = (time.monotonic(),result)
    return result
