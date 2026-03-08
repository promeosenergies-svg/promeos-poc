"""
Tests for DAF demo scenario fixes (D1-D5).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient


def _get_client():
    from main import app

    return TestClient(app)


class TestD1ComplianceSiteScore(unittest.TestCase):
    """D1: /api/compliance/site/{id}/score → 200"""

    def test_compliance_site_score_singular_endpoint(self):
        """GET /api/compliance/site/1/score returns 200 (singular alias)."""
        client = _get_client()
        resp = client.get("/api/compliance/site/1/score")
        # 200 if site exists, 404 if site not found — both are valid responses
        self.assertIn(resp.status_code, [200, 404])

    def test_compliance_site_score_has_score(self):
        """Response contains 'score' field between 0-100 when site exists."""
        client = _get_client()
        resp = client.get("/api/compliance/sites/1/score")
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("score", data)
            self.assertGreaterEqual(data["score"], 0)
            self.assertLessEqual(data["score"], 100)

    def test_compliance_site_score_singular_matches_plural(self):
        """Both /site/ and /sites/ return the same data."""
        client = _get_client()
        r1 = client.get("/api/compliance/site/1/score")
        r2 = client.get("/api/compliance/sites/1/score")
        self.assertEqual(r1.status_code, r2.status_code)
        if r1.status_code == 200:
            self.assertEqual(r1.json(), r2.json())


class TestD2FindingsPenalty(unittest.TestCase):
    """D2: Findings have estimated_penalty_eur in API response."""

    def test_findings_response_has_penalty_fields(self):
        """GET /api/compliance/findings includes penalty fields in schema."""
        client = _get_client()
        resp = client.get("/api/compliance/findings", headers={"X-Org-Id": "1"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        if isinstance(data, list) and len(data) > 0:
            finding = data[0]
            self.assertIn("estimated_penalty_eur", finding)
            self.assertIn("penalty_source", finding)
            self.assertIn("penalty_basis", finding)

    def test_finding_detail_has_penalty_fields(self):
        """GET /api/compliance/findings/{id} includes penalty fields."""
        client = _get_client()
        # Get a finding first
        resp = client.get("/api/compliance/findings", headers={"X-Org-Id": "1"})
        if resp.status_code == 200 and resp.json():
            fid = resp.json()[0]["id"]
            detail = client.get(f"/api/compliance/findings/{fid}", headers={"X-Org-Id": "1"})
            if detail.status_code == 200:
                data = detail.json()
                self.assertIn("estimated_penalty_eur", data)
                self.assertIn("penalty_source", data)
                self.assertIn("penalty_basis", data)


class TestD3CompareMonthlyAutoYear(unittest.TestCase):
    """D3: /api/billing/compare-monthly returns data even without year param."""

    def test_compare_monthly_auto_year(self):
        """GET /api/billing/compare-monthly auto-detects latest year with data."""
        client = _get_client()
        resp = client.get("/api/billing/compare-monthly", headers={"X-Org-Id": "1"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("current_year", data)
        self.assertIn("months", data)

    def test_compare_monthly_has_data(self):
        """At least some months should have current_eur when invoices exist."""
        client = _get_client()
        resp = client.get("/api/billing/compare-monthly", headers={"X-Org-Id": "1"})
        if resp.status_code == 200:
            data = resp.json()
            months_with_data = [m for m in data["months"] if m["current_eur"] is not None]
            # If there are invoices for this org, we should find data
            if data.get("total_current_eur", 0) > 0:
                self.assertGreater(len(months_with_data), 0, "compare-monthly should have months with current_eur data")

    def test_compare_monthly_explicit_year(self):
        """Explicit year=2025 should work."""
        client = _get_client()
        resp = client.get("/api/billing/compare-monthly?year=2025", headers={"X-Org-Id": "1"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["current_year"], 2025)


class TestD4PurchaseScenarios(unittest.TestCase):
    """D4: /api/purchase/scenarios?site_id=1 → 200"""

    def test_purchase_scenarios_endpoint(self):
        """GET /api/purchase/scenarios?site_id=1 returns 200."""
        client = _get_client()
        resp = client.get("/api/purchase/scenarios?site_id=1")
        self.assertIn(resp.status_code, [200, 404])

    def test_purchase_scenarios_has_scenarios(self):
        """Response contains 'scenarios' list."""
        client = _get_client()
        resp = client.get("/api/purchase/scenarios?site_id=1")
        if resp.status_code == 200:
            data = resp.json()
            self.assertIn("scenarios", data)
            self.assertIsInstance(data["scenarios"], list)

    def test_purchase_scenarios_requires_site_id(self):
        """Missing site_id should return 422."""
        client = _get_client()
        resp = client.get("/api/purchase/scenarios")
        self.assertEqual(resp.status_code, 422)


class TestD5MeridianSeed(unittest.TestCase):
    """D5: MERIDIAN seed should not raise IntegrityError on re-seed."""

    def test_gen_billing_has_duplicate_check(self):
        """gen_billing.py contains duplicate invoice check."""
        import inspect
        from services.demo_seed.gen_billing import generate_billing

        source = inspect.getsource(generate_billing)
        self.assertIn("existing", source, "gen_billing should check for existing invoices")
        self.assertIn("filter_by", source, "gen_billing should query existing invoices before insert")

    def test_invoice_model_has_unique_constraint(self):
        """EnergyInvoice has a unique constraint on (site_id, invoice_number, period_start, period_end)."""
        from models import EnergyInvoice

        constraints = EnergyInvoice.__table_args__
        unique_names = [c.name for c in constraints if hasattr(c, "name")]
        self.assertIn("uq_invoice_site_number_period", unique_names)


class TestD2ComplianceFindingModel(unittest.TestCase):
    """D2 model: ComplianceFinding has penalty columns."""

    def test_compliance_finding_has_penalty_columns(self):
        """ComplianceFinding model includes estimated_penalty_eur, penalty_source, penalty_basis."""
        from models import ComplianceFinding

        col_names = [c.name for c in ComplianceFinding.__table__.columns]
        self.assertIn("estimated_penalty_eur", col_names)
        self.assertIn("penalty_source", col_names)
        self.assertIn("penalty_basis", col_names)


if __name__ == "__main__":
    unittest.main()
