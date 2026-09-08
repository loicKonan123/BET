import copy
import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import numpy as np
from threadpoolctl import threadpool_limits

from src.match_data import historique_90, score_90, MODEL_VERSION
from src.prediction_models import grille, aligner_grille, marches_grille, replay, Historique, entrainer_ensemble
from src.prediction_service import predire_historique
from src.tickets import selection_confiance


def fixtures(n=36):
    date = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return [{"fixture":{"id":i+1,"date":(date+timedelta(days=i)).isoformat(),"status":{"short":"FT"}},
             "league":{"id":61,"season":2024},
             "teams":{"home":{"id":1,"name":"A"},"away":{"id":2,"name":"B"}},
             "goals":{"home":i%3,"away":(i+1)%3},
             "score":{"fulltime":{"home":i%3,"away":(i+1)%3}}} for i in range(n)]


class PredictionTests(unittest.TestCase):
    def test_prolongations_et_resultats_inconnus(self):
        rows = fixtures(2)
        rows[0]["fixture"]["status"]["short"] = "AET"
        rows[0]["goals"] = {"home":4,"away":1}
        self.assertEqual(score_90(rows[0]), (0, 1))
        del rows[0]["score"]
        self.assertIsNone(score_90(rows[0]))
        self.assertEqual(historique_90(rows, "2024-01-02T02:00:00Z"), [])

    def test_grille_et_marches_coherents(self):
        p = [.48,.32,.20]
        grid = aligner_grille(grille(1.6, 1.2, .15), p)
        markets = marches_grille(grid)
        np.testing.assert_allclose([markets[k] for k in ("1","X","2")], p)
        self.assertAlmostEqual(markets["1X"], .8)
        self.assertGreaterEqual(markets["over_1.5"], markets["over_2.5"])
        for a,b in (("btts_oui","btts_non"),("over_2.5","under_2.5")):
            self.assertAlmostEqual(markets[a]+markets[b], 1)

    def test_replay_ne_voit_pas_resultat_courant(self):
        rows = fixtures()
        modified = copy.deepcopy(rows)
        modified[20]["score"]["fulltime"] = {"home":9,"away":0}
        a,b = replay(rows, {}), replay(modified, {})
        for i in range(21):
            np.testing.assert_allclose(a[i]["x"], b[i]["x"], equal_nan=True)
            np.testing.assert_allclose(a[i]["dynamique"], b[i]["dynamique"])

    def test_xg_perimes_sortent_de_la_fenetre(self):
        state = Historique()
        rows = fixtures(8)
        for f in rows:
            state.update(f, {1:{1:2.,2:1.}})
        x = state.features(1, 2, "2024-01-10T00:00:00Z")
        self.assertEqual(x[-1], 0)
        self.assertTrue(np.isnan(x[15]))

    def test_production_et_historique_identiques(self):
        from src.pipeline import FixtureInfo, analyser_fixture, analyser_fixture_sans_cotes
        fx = FixtureInfo(100,61,2024,1,2,"A","B", "2030-01-01T12:00:00Z")
        rows = fixtures()
        with threadpool_limits(limits=1):
            prediction = predire_historique(rows,1,2,fx.date)
        prediction.update(cotes={}, prediction_id="snapshot", cadre="avant_match", calcule_le=fx.date)
        with patch("src.pipeline.predire_match", return_value=prediction), patch("src.pipeline.recuperer_prix",return_value=({},None)):
            a = analyser_fixture(None, fx)
            b = analyser_fixture_sans_cotes(None, fx)
        self.assertEqual(a,b)
        self.assertEqual(a["consensus"], {k:a["probabilites"][k] for k in ("1","X","2")})
        self.assertEqual(a["version_modele"], MODEL_VERSION)

    def test_selection_exige_cote_utilisable(self):
        p = {"1":.6,"X":.25,"2":.15}
        self.assertIsNone(selection_confiance(p, {}))
        self.assertEqual(selection_confiance(p, {"1":float("nan"),"1X":1.2})[0], "1X")

    def test_ticket_ignore_probabilites_client(self):
        import app
        detail={"cadre_prediction":"avant_match","probabilites":{"1":.6},
                "match":"A - B","ligue":"L","date":"2030-01-01", "prediction_id":"s", "version_modele":MODEL_VERSION}
        body=app.TicketIn(cote_totale=99,proba_reussite=.99,
                         selections=[app.SelectionIn(match="faux",marche="1",cote=2,proba=.99,fixture_id=1,cle="1")])
        with patch.object(app,"_detail_match",return_value=detail):
            result=app._ticket_canonique(body)
        self.assertEqual(result["proba_reussite"], .6)
        self.assertEqual(result["cote_totale"], 2)
        self.assertEqual(result["selections"][0]["prediction_id"], "s")

    def test_validation_chronologique_et_poids_conditionnels(self):
        rows = fixtures(240)
        for f in rows[::5]:
            f["score"]["fulltime"] = {"home":1,"away":1}
        with threadpool_limits(limits=1):
            model = entrainer_ensemble(rows,{})
        self.assertIsNotNone(model)
        self.assertAlmostEqual(sum(model.weights.values()),1)
        windows = model.validation["fenetres_test"]
        self.assertEqual(len(windows),2)
        self.assertEqual(model.validation["fusion_retenue"], all(w["log_loss_candidate"] < w["log_loss_reference"] for w in windows))
        if not model.validation["fusion_retenue"]:
            self.assertAlmostEqual(model.weights["elo"],.7)

    def test_journal_immuable(self):
        from src import store
        with tempfile.TemporaryDirectory() as directory, patch.object(store,"DB_PATH",Path(directory)/"test.db"):
            store.sauver_prediction(1,"p","2030-01-01",{"probabilites":{"1":.6}})
            store.sauver_prediction(1,"p","2030-01-01",{"probabilites":{"1":.9}})
            with store._conn() as connection:
                rows=connection.execute("SELECT data FROM predictions").fetchall()
            self.assertEqual(len(rows),1)
            self.assertEqual(json.loads(rows[0]["data"])["probabilites"]["1"],.6)

    def test_absences_collectees_apres_match_exclues(self):
        from src.prediction_context import collecter_contexte
        from src.pipeline import FixtureInfo
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            (path/"injuries_fixture-100.json").write_text(json.dumps({"response":[{"team":{"id":1},"player":{"id":7}}]}))
            fx=FixtureInfo(100,61,2024,1,2,"A","B","2024-02-01T00:00:00Z")
            with patch("src.prediction_context.CACHE_DIR",path), patch("src.prediction_context.CONTEXT_DIR",path/"archive"):
                self.assertEqual(collecter_contexte(fx,fixtures()),{})


if __name__ == "__main__":
    unittest.main()
