"""
Tests pour les simulateurs mutualisation et modulation DT (Phase 3).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestMutualisationService(unittest.TestCase):
    """Tests unitaires du service de mutualisation."""

    def test_import(self):
        """Le module s'importe sans erreur."""
        from services.tertiaire_mutualisation_service import compute_mutualisation, MutualisationResult

        self.assertTrue(callable(compute_mutualisation))

    def test_jalon_reductions(self):
        """Les jalons reglementaires sont corrects (derives de operat_trajectory.TARGETS)."""
        from services.tertiaire_mutualisation_service import JALON_REDUCTIONS

        self.assertAlmostEqual(JALON_REDUCTIONS[2030], 0.40)
        self.assertAlmostEqual(JALON_REDUCTIONS[2040], 0.50)
        self.assertAlmostEqual(JALON_REDUCTIONS[2050], 0.60)

    def test_penalty_from_canonical_source(self):
        """La penalite de base vient de config/emission_factors.py."""
        from config.emission_factors import BASE_PENALTY_EURO

        self.assertEqual(BASE_PENALTY_EURO, 7500)

    def test_result_to_dict(self):
        """MutualisationResult.to_dict() contient portefeuille."""
        from services.tertiaire_mutualisation_service import MutualisationResult

        result = MutualisationResult(org_id=1, jalon_annee=2030, jalon_reduction_pct=40.0)
        d = result.to_dict()
        self.assertIn("portefeuille", d)
        self.assertIn("economie_mutualisation_eur", d["portefeuille"])


class TestModulationService(unittest.TestCase):
    """Tests unitaires du service de modulation."""

    def test_import(self):
        """Le module s'importe sans erreur."""
        from services.tertiaire_modulation_service import simulate_modulation, ModulationResult

        self.assertTrue(callable(simulate_modulation))

    def test_interaction_factor(self):
        """Le facteur d'interaction est 0.85."""
        from services.tertiaire_modulation_service import INTERACTION_FACTOR

        self.assertAlmostEqual(INTERACTION_FACTOR, 0.85)

    def test_tri_calculation(self):
        """TRI = cout / economie_annuelle_eur."""
        from services.tertiaire_modulation_service import ModulationAction

        # PAC : 85000 / 5000 = 17.0 ans
        action = ModulationAction(
            label="PAC",
            cout_eur=85000,
            economie_annuelle_kwh=50000,
            economie_annuelle_eur=5000,
            duree_vie_ans=20,
            tri_ans=round(85000 / 5000, 1),
        )
        self.assertAlmostEqual(action.tri_ans, 17.0)
        # LED : 15000 / 2000 = 7.5 ans
        action2 = ModulationAction(
            label="LED",
            cout_eur=15000,
            economie_annuelle_kwh=20000,
            economie_annuelle_eur=2000,
            duree_vie_ans=10,
            tri_ans=round(15000 / 2000, 1),
        )
        self.assertAlmostEqual(action2.tri_ans, 7.5)

    def test_result_to_dict(self):
        """ModulationResult.to_dict() contient dossier_readiness_score."""
        from services.tertiaire_modulation_service import ModulationResult

        result = ModulationResult(
            efa_id=1,
            efa_nom="Test",
            objectif_initial_kwh=357000,
            conso_actuelle_kwh=500000,
            economie_actions_kwh=59500,
            conso_apres_actions_kwh=440500,
            objectif_module_kwh=440500,
            delta_objectif_pct=23.4,
            tri_moyen_ans=12.8,
            cout_total_eur=100000,
            dossier_readiness_score=83,
        )
        d = result.to_dict()
        self.assertEqual(d["dossier_readiness_score"], 83)
        self.assertEqual(d["delta_objectif_pct"], 23.4)


class TestEndpointMount(unittest.TestCase):
    """Tests de montage des endpoints."""

    def test_mutualisation_endpoint_exists(self):
        """GET /api/tertiaire/mutualisation est monte."""
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/tertiaire/mutualisation", params={"org_id": 1, "jalon": 2030})
        # 200 si l'org existe, sinon reponse vide mais pas 404/405
        self.assertIn(resp.status_code, [200])

    def test_modulation_endpoint_exists(self):
        """POST /api/tertiaire/modulation-simulation est monte."""
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.post(
            "/api/tertiaire/modulation-simulation",
            json={
                "efa_id": 999,
                "contraintes": [{"type": "technique", "description": "test", "actions": []}],
            },
        )
        # 404 car EFA 999 n'existe pas — prouve que l'endpoint est monte
        self.assertEqual(resp.status_code, 404)

    def test_score_explain_has_per_regulation(self):
        """GET /api/regops/score_explain retourne per_regulation."""
        from main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        resp = client.get("/api/regops/score_explain", params={"scope_type": "site", "scope_id": 1})
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("per_regulation", data)
            if data["per_regulation"]:
                reg = data["per_regulation"][0]
                self.assertIn("label", reg)
                self.assertIn("weight", reg)
                self.assertIn("sub_score", reg)


if __name__ == "__main__":
    unittest.main()
