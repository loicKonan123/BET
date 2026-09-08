import json
import unittest
from contextlib import ExitStack
from unittest.mock import Mock, patch

import app


class MatchSansAnalyseTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.api = Mock()
        self.api.get.return_value = {"response": [{
            "fixture": {"id": 123, "date": "2026-09-08T20:00:00Z", "status": {"short": "FT"}},
            "league": {"id": 99999, "season": 2026, "name": "Competition"},
            "teams": {"home": {"id": 1, "name": "A"}, "away": {"id": 2, "name": "B"}},
            "goals": {"home": 2, "away": 1},
        }]}
        self.stack.enter_context(patch.object(app, "ApiFootball", return_value=self.api))
        self.analyse = self.stack.enter_context(patch.object(app, "analyser_fixture", return_value=None))
        for name, result in [("_classement", None), ("_derniers_matchs", []), ("_h2h", []), ("_compos", [{"equipe": "A"}])]:
            self.stack.enter_context(patch.object(app, name, return_value=result))

    def test_fiche_accessible_sans_probabilites_inventees(self):
        response = app.match_detail(123)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.body)
        self.assertFalse(data["analyse_disponible"])
        self.assertEqual(data["home"]["name"], "A")
        self.assertEqual(data["score"], {"domicile": 2, "exterieur": 1})
        self.assertEqual(data["compos"], [{"equipe": "A"}])
        for field in ("probabilites", "buts_attendus", "conseil", "selections", "multi_modeles"):
            self.assertNotIn(field, data)

    def test_tickets_et_ia_exigent_encore_une_analyse(self):
        with self.assertRaises(app.HTTPException) as error:
            app._detail_match(self.api, 123)
        self.assertEqual(error.exception.status_code, 422)

    def test_match_introuvable_reste_404(self):
        self.api.get.return_value = {"response": []}
        with self.assertRaises(app.HTTPException) as error:
            app.match_detail(123)
        self.assertEqual(error.exception.status_code, 404)

    def test_analyse_disponible_conservee(self):
        self.analyse.return_value = {"prediction_id": "test", "probabilites": {"1": 0.5, "X": 0.3, "2": 0.2}}
        data = json.loads(app.match_detail(123).body)
        self.assertEqual(data["prediction_id"], "test")
        self.assertEqual(data["probabilites"]["1"], 0.5)
        self.assertNotEqual(data.get("analyse_disponible"), False)


if __name__ == "__main__":
    unittest.main()
