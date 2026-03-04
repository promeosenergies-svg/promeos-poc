"""
PROMEOS V113 — Data Quality Cause→CTA mapping tests
Tests that each cause_code maps to the correct cta_route and recommended_action.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.data_quality_service import _CAUSES


class TestCauseCTAMapping:
    """Verify each cause_code has correct structure and CTA route."""

    def test_all_causes_have_three_fields(self):
        """Each _CAUSES entry must be a 3-tuple: (label, action, cta_route)."""
        for code, entry in _CAUSES.items():
            assert len(entry) == 3, f"Cause '{code}' should have 3 fields, got {len(entry)}"

    def test_meter_causes_route_to_meters_step(self):
        """Meter-related causes should route to step_meters_connected."""
        meter_causes = ["no_meter", "no_readings", "sparse", "stale", "mapping_missing", "api_error"]
        for code in meter_causes:
            _, _, cta_route = _CAUSES[code]
            assert cta_route == "/onboarding?step=step_meters_connected", (
                f"Cause '{code}' should route to meters step, got '{cta_route}'"
            )

    def test_invoice_causes_route_to_invoices_step(self):
        """Invoice-related causes should route to step_invoices_imported."""
        invoice_causes = ["no_invoices", "sparse_inv", "stale_inv"]
        for code in invoice_causes:
            _, _, cta_route = _CAUSES[code]
            assert cta_route == "/onboarding?step=step_invoices_imported", (
                f"Cause '{code}' should route to invoices step, got '{cta_route}'"
            )

    def test_ok_cause_has_no_cta(self):
        """'ok' cause should have None for recommended_action and cta_route."""
        label, action, cta_route = _CAUSES["ok"]
        assert action is None
        assert cta_route is None
        assert "complet" in label.lower()

    def test_all_non_ok_causes_have_recommended_action(self):
        """Every non-ok cause must have a non-empty recommended_action."""
        for code, (label, action, cta_route) in _CAUSES.items():
            if code == "ok":
                continue
            assert action and len(action) > 5, f"Cause '{code}' must have a recommended_action, got '{action}'"
            assert cta_route and cta_route.startswith("/"), (
                f"Cause '{code}' must have a valid cta_route, got '{cta_route}'"
            )

    def test_minimum_six_causes_plus_ok(self):
        """MVP requires at least 6 remediation causes + 'ok'."""
        non_ok = [k for k in _CAUSES if k != "ok"]
        assert len(non_ok) >= 6, f"Expected >=6 non-ok causes, got {len(non_ok)}: {non_ok}"

    def test_cause_labels_are_french(self):
        """All cause labels should be in French (contain common French chars/words)."""
        french_markers = [
            "aucun",
            "donnees",
            "compteur",
            "facture",
            "partiel",
            "obsolet",
            "complet",
            "erreur",
            "associe",
            "releves",
        ]
        for code, (label, _, _) in _CAUSES.items():
            label_lower = label.lower()
            assert any(m in label_lower for m in french_markers), f"Cause '{code}' label '{label}' doesn't seem French"
