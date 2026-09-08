"""Entraînement local, sans réseau : python entrainer_predictions.py --all."""
import argparse
import json
import pickle
from pathlib import Path
from datetime import datetime, timezone
from threadpoolctl import threadpool_limits

from src.api_client import CACHE_DIR
from src.match_data import MODEL_VERSION, historique_90
from src.prediction_models import entrainer_ensemble
from src.prediction_service import MODEL_DIR, chemin_modele, xg_cache, NATIONAL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--leagues", nargs="+", type=int)
    args = parser.parse_args()
    if not args.all and not args.leagues:
        parser.error("Indiquez --all ou --leagues 39 61 ...")
    pools = {}
    for path in CACHE_DIR.glob("fixtures_league-*.json"):
        for f in json.loads(path.read_text(encoding="utf-8")).get("response",[]):
            lid = f["league"]["id"]
            if args.all or lid in args.leagues or (lid in NATIONAL and any(k in NATIONAL for k in args.leagues or [])):
                pools.setdefault(lid,{})[f["fixture"]["id"]] = f
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    previous = MODEL_DIR / "rapport_validation.json"
    old = json.loads(previous.read_text(encoding="utf-8")) if previous.exists() else {}
    report = {"version":MODEL_VERSION,"cree_le":datetime.now(timezone.utc).isoformat(),
              "ligues":old.get("ligues",{}) if old.get("version")==MODEL_VERSION and not args.all else {}}
    international = [f for lid,pool in pools.items() if lid in NATIONAL for f in pool.values()]
    shared = None
    with threadpool_limits(limits=1):
        for lid, fixtures in sorted(pools.items()):
            if not args.all and lid not in args.leagues:
                continue
            rows = historique_90(international if lid in NATIONAL else list(fixtures.values()))
            print(f"Ligue {lid}: {len(rows)} matchs a 90 minutes",flush=True)
            model = shared if lid in NATIONAL and shared else entrainer_ensemble(rows,xg_cache(rows))
            if model and lid in NATIONAL:
                model.scope = "international"
                model.validation["perimetre"] = "international"
                model.validation["note"] = "Validation sur le pool international commun. " + model.validation["note"] if shared is None else model.validation["note"]
                shared = model
            if model is None:
                report["ligues"][str(lid)] = {"statut":"donnees_insuffisantes","n":len(rows)}
                continue
            path = chemin_modele(lid)
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(pickle.dumps(model))
            temporary.replace(path)
            report["ligues"][str(lid)] = {"statut":"entraine","n":len(rows),**model.validation,"poids":model.weights}
            print(f"  test={model.validation['n_test']} fusion_retenue={model.validation['fusion_retenue']}",flush=True)
    out = MODEL_DIR / "rapport_validation.json"
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print(str(out),flush=True)


if __name__ == "__main__":
    main()
