import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import app
from src.api_client import ApiFootball, CACHE_DIR


def fixture(fid, league, kickoff):
    return {"fixture":{"id":fid,"date":kickoff,"status":{"short":"NS"}},
            "league":{"id":league,"name":"Competition"},
            "teams":{"home":{"id":1,"name":"A"},"away":{"id":2,"name":"B"}},
            "goals":{"home":None,"away":None}}


class ScoresJourTests(unittest.TestCase):
    @patch.object(app, "ApiFootball")
    def test_toutes_competitions_et_fin_de_soiree(self, api):
        api.return_value.get.return_value = {"response":[
            fixture(2,999999,"2026-09-09T02:00:00Z"),
            fixture(1,39,"2026-09-08T17:00:00Z")]}
        response = json.loads(app.scores_du_jour("2026-09-08").body)
        self.assertEqual([m["fixture_id"] for m in response["matchs"]],[1,2])
        api.return_value.get.assert_called_once_with("fixtures", {"date":"2026-09-08","timezone":"America/Toronto"}, ttl=60)

    @patch.object(app, "ApiFootball")
    def test_date_par_defaut_montreal_pas_utc(self, api):
        class Horloge(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026,9,9,1,tzinfo=timezone.utc).astimezone(tz)
        api.return_value.get.return_value = {"response":[]}
        with patch.object(app,"datetime",Horloge):
            response = json.loads(app.scores_du_jour().body)
        self.assertEqual(response["date"],"2026-09-08")

    def test_cache_timezone_reste_dans_le_dossier(self):
        api = ApiFootball(key="test")
        path = api._cache_path("fixtures",{"date":"2026-09-08","timezone":"America/Toronto"})
        self.assertEqual(path.parent,CACHE_DIR)
        self.assertIn("America%2FToronto",path.name)
        self.assertEqual(api._cache_path("fixtures",{"id":123}).name,"fixtures_id-123.json")

    @patch.object(app,"ApiFootball")
    def test_date_invalide_sans_appel_fournisseur(self, api):
        with self.assertRaises(app.HTTPException) as error:
            app.scores_du_jour("2026-99-09")
        self.assertEqual(error.exception.status_code,400)
        api.assert_not_called()

    @patch.object(app,"ApiFootball")
    def test_live_sans_filtre_cache_de_competition(self, api):
        api.return_value.get.return_value = {"response":[fixture(2,999999,"2026-09-09T02:00:00Z")]}
        self.assertEqual(len(json.loads(app.live_matches().body)),1)


if __name__ == "__main__":
    unittest.main()
