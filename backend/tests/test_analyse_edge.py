"""Régressions hors réseau du contrat IA et des diagnostics de confluence."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.analyse_editoriale import VERSION_ANALYSE, valider_analyse
from src.analyste import (
    _fusion_equipe, _historique_avant, _reperes_marche,
    analyser_avec_ia, collecter_dossier,
)
from src.blend import fusionner_1x2


P = {"1": 0.5, "X": 0.3, "2": 0.2}


def detail_match():
    return {
        "fixture_id": 10, "match": "A - B", "date": "2026-09-07T18:00:00Z",
        "home": {"id": 1, "name": "A"}, "away": {"id": 2, "name": "B"},
        "forme": {"domicile": "WWD", "exterieur": "LDW"},
        "multi_modeles": {"poisson": P, "ml": P, "consensus": fusionner_1x2(P, P, None)},
        "selections": [{"cle": "1", "marche": "Victoire domicile", "proba": 0.5, "cote": 2.2}],
        "compos": [{"equipe": "A", "formation": "4-3-3", "titulaires": []}],
        "derniers_matchs_dom": [{"date": "2026-09-01T18:00:00Z", "score": "2-1"}],
        "h2h": [],
    }


def reponse_valide():
    return {
        "probabilites_ia": {"victoire_domicile": 0.5, "nul": 0.3, "victoire_exterieur": 0.2},
        "prediction": "Victoire domicile", "confiance": "moyenne", "analyse": "Analyse de test.",
        "analyse_detaillee": {k: "Un argument documenté." for k in (
            "lecture_match", "duel_tactique", "signaux_statistiques", "scenario_alternatif",
            "marche_value", "risques", "verdict")},
        "points_cles": ["Un fait"], "facteurs_correctifs_vs_poisson": [],
        "recommandation": {"marche": "Pas de pari", "confiance": "faible", "justification": "Cote incertaine."},
    }


class ConfluenceTests(unittest.TestCase):
    def test_desaccord_sur_nul_detecte(self):
        result = fusionner_1x2(P, {"1": 0.5, "X": 0.1, "2": 0.4}, None)
        self.assertAlmostEqual(result["accord"], 0.2)

    def test_source_unique_pas_convergence(self):
        result = fusionner_1x2(P, None, None)
        self.assertIsNone(result["accord"])
        self.assertIsNone(result["diagnostic"]["favori_stable"])

    def test_sources_invalides_exclues(self):
        for valeur in (None, float("nan"), -0.1, "0.5", True, 2):
            with self.subTest(valeur=valeur):
                result = fusionner_1x2({"1": valeur, "X": 0.3, "2": 0.2}, P, None)
                self.assertEqual(result["sources_disponibles"], ["elo"])
        self.assertIsNone(fusionner_1x2(None, None, None)["probabilites"])

    def test_sensibilite_favori_change(self):
        result = fusionner_1x2(P, {"1": 0.1, "X": 0.2, "2": 0.7}, None)
        self.assertFalse(result["diagnostic"]["favori_stable"])
        self.assertEqual(result["diagnostic"]["sensibilite"]["elo"]["probabilites"], P)
        self.assertAlmostEqual(sum(result["probabilites"].values()), 1, places=3)

    def test_avis_ia_invalide_ne_casse_pas_fusion(self):
        self.assertEqual(_fusion_equipe({"1": None}, P), P)


class DossierTests(unittest.TestCase):
    def test_historique_exclut_match_et_futur(self):
        rows = [{"date": d} for d in ("2026-09-01", "2026-09-07T18:00:00Z", "2026-09-08", "inconnue")]
        self.assertEqual(_historique_avant(rows, "2026-09-07T18:00:00Z"), rows[:1])
        self.assertEqual(_historique_avant(rows, None), [])

    def test_prix_calcules_et_absence_cote(self):
        result = _reperes_marche(detail_match())
        self.assertEqual(result[0]["cote_juste"], 2)
        self.assertEqual(result[0]["esperance_theorique"], 0.1)
        self.assertIsNone(result[1]["esperance_theorique"])

    def test_cotes_invalides(self):
        for cote in (float("nan"), True, 0, "2.0"):
            detail = detail_match()
            detail["selections"][0]["cote"] = cote
            self.assertIsNone(_reperes_marche(detail)[0]["cote_disponible"])

    def test_dossier_enrichi_et_couverture_blessures(self):
        api = Mock()
        api.get.return_value = {"response": []}
        result = collecter_dossier(api, detail_match())
        self.assertTrue(result["compositions_disponibles"])
        self.assertTrue(result["derniers_matchs"]["domicile"])
        self.assertEqual(result["modeles_multiples"]["ml_1x2"], P)
        self.assertEqual(result["blessures"]["statut"], "aucune_absence_renseignee")
        api.get.side_effect = RuntimeError("API indisponible")
        self.assertEqual(collecter_dossier(api, detail_match())["blessures"]["statut"], "indisponible")


class ContratTests(unittest.TestCase):
    def test_structure_et_probabilites(self):
        self.assertEqual(valider_analyse(reponse_valide())["confiance"], "moyenne")
        for changement in ("section", "proba", "somme"):
            result = copy.deepcopy(reponse_valide())
            if changement == "section":
                result["analyse_detaillee"]["duel_tactique"] = " "
            elif changement == "proba":
                result["probabilites_ia"]["nul"] = None
            else:
                result["probabilites_ia"]["nul"] = 0.8
            with self.assertRaises(ValueError):
                valider_analyse(result)

    @patch("src.analyste._client")
    def test_generation_validee_et_versionnee(self, client):
        import json
        client.return_value.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(reponse_valide())))
        ])
        api = Mock()
        api.get.return_value = {"response": []}
        result = analyser_avec_ia(api, detail_match())
        self.assertEqual(result["version_analyse"], VERSION_ANALYSE)
        self.assertEqual(result["probabilites_finales"], P)
        self.assertIn("duel_tactique", result["analyse_detaillee"])

    @patch("src.analyste._client")
    def test_reponse_tronquee_refusee(self, client):
        client.return_value.chat.completions.create.return_value = SimpleNamespace(choices=[
            SimpleNamespace(finish_reason="length")
        ])
        api = Mock()
        api.get.return_value = {"response": []}
        with patch.dict("os.environ", {"DEEPSEEK_ANALYSIS_MODE": "approfondi", "DEEPSEEK_MODEL": "deepseek-reasoner", "DEEPSEEK_MAX_TOKENS": "32768"}):
            with self.assertRaisesRegex(ValueError, "limite de génération"):
                analyser_avec_ia(api, detail_match())
        self.assertEqual(client.return_value.chat.completions.create.call_count, 2)

    @patch("src.analyste._client")
    def test_troncature_reprise_avec_budget_superieur(self, client):
        import json
        create = client.return_value.chat.completions.create
        create.side_effect = [
            SimpleNamespace(choices=[SimpleNamespace(finish_reason="length")]),
            SimpleNamespace(choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=json.dumps(reponse_valide())))]),
        ]
        api = Mock()
        api.get.return_value = {"response": []}
        with patch.dict("os.environ", {"DEEPSEEK_ANALYSIS_MODE": "approfondi", "DEEPSEEK_MODEL": "deepseek-reasoner", "DEEPSEEK_MAX_TOKENS": "8000"}):
            result = analyser_avec_ia(api, detail_match())
        self.assertEqual(result["probabilites_finales"], P)
        self.assertEqual([c.kwargs["max_tokens"] for c in create.call_args_list], [8000, 32768])
        self.assertEqual(create.call_args_list[0].kwargs["messages"], create.call_args_list[1].kwargs["messages"])
        api.get.assert_called_once()  # Pas de nouvelle collecte du dossier.

    @patch("src.analyste._client")
    def test_plafond_sans_reprise_inutile(self, client):
        client.return_value.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(finish_reason="length")])
        api = Mock()
        api.get.return_value = {"response": []}
        with patch.dict("os.environ", {"DEEPSEEK_ANALYSIS_MODE": "approfondi", "DEEPSEEK_MODEL": "deepseek-reasoner", "DEEPSEEK_MAX_TOKENS": "65536"}):
            with self.assertRaises(ValueError):
                analyser_avec_ia(api, detail_match())
        self.assertEqual(client.return_value.chat.completions.create.call_count, 1)

    @patch("src.analyste._client")
    def test_mode_rapide_un_appel_sans_raisonnement(self, client):
        import json
        create = client.return_value.chat.completions.create
        create.return_value = SimpleNamespace(choices=[SimpleNamespace(
            finish_reason="stop", message=SimpleNamespace(content=json.dumps(reponse_valide())))])
        api = Mock()
        api.get.return_value = {"response": []}
        with patch.dict("os.environ", {"DEEPSEEK_ANALYSIS_MODE": "rapide", "DEEPSEEK_MODEL": "deepseek-reasoner", "DEEPSEEK_MAX_TOKENS": "32768"}):
            result = analyser_avec_ia(api, detail_match())
        create.assert_called_once()
        self.assertEqual(create.call_args.kwargs["model"], "deepseek-v4-flash")
        self.assertEqual(create.call_args.kwargs["max_tokens"], 8192)
        self.assertEqual(create.call_args.kwargs["extra_body"], {"thinking": {"type": "disabled"}})
        self.assertEqual(result["mode_generation"], "rapide")
        self.assertEqual(len(result["analyse_detaillee"]), 7)
        client.assert_called_once_with(rapide=True)

    @patch("src.analyste._client")
    def test_mode_rapide_ne_relance_pas_reponse_tronquee(self, client):
        create = client.return_value.chat.completions.create
        create.return_value = SimpleNamespace(choices=[SimpleNamespace(finish_reason="length")])
        api = Mock()
        api.get.return_value = {"response": []}
        with patch.dict("os.environ", {"DEEPSEEK_ANALYSIS_MODE": "rapide", "DEEPSEEK_MAX_TOKENS": "8192"}):
            with self.assertRaises(ValueError):
                analyser_avec_ia(api, detail_match())
        create.assert_called_once()

    def test_cache_ancien_ne_declenche_pas_ia(self):
        import app
        with patch.object(app.store, "get_analyse_ia", return_value={"analyse_detaillee": {"verdict": "ancien"}}), \
             patch.object(app, "analyser_avec_ia") as generer:
            response = app.match_ia(10, cache_only=1)
            self.assertIn(b'"cache_absent":true', response.body)
            generer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
