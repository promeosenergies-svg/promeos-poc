"""
PROMEOS — Phase 2 ELEC: Shadow Expected + Explainability Tests
Tests: catalog trace, diagnostics, confidence, contributors.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date

from models import BillingEnergyType, InvoiceLineType


# ── Fake objects for shadow_billing_v2 ─────────────────────────────────


class FakeInvoice:
    total_eur = 1200
    energy_kwh = 5000
    period_start = date(2025, 2, 1)
    period_end = date(2025, 2, 28)
    site_id = 1


class FakeContract:
    id = 42
    energy_type = BillingEnergyType.ELEC
    price_ref_eur_per_kwh = 0.15
    turpe_annual_eur = 500
    fixed_fee_eur_per_month = 10


class FakeContractNone:
    """Contract without price — triggers catalog fallback."""
    id = 99
    energy_type = BillingEnergyType.ELEC
    price_ref_eur_per_kwh = None
    turpe_annual_eur = None
    fixed_fee_eur_per_month = None


class FakeLine:
    line_type = InvoiceLineType.ENERGY
    amount_eur = 800
    kwh = 5000


class FakeNetworkLine:
    line_type = InvoiceLineType.NETWORK
    amount_eur = 300
    kwh = None


class FakeTaxLine:
    line_type = InvoiceLineType.TAX
    amount_eur = 150
    kwh = None


def _shadow(contract=None, lines=None):
    from services.billing_shadow_v2 import shadow_billing_v2

    return shadow_billing_v2(
        FakeInvoice(),
        lines if lines is not None else [FakeLine(), FakeNetworkLine(), FakeTaxLine()],
        contract or FakeContract(),
    )


# ═══════════════════════════════════════════════
# A. Catalog Trace
# ═══════════════════════════════════════════════


class TestCatalogTrace:
    def test_catalog_trace_included(self):
        result = _shadow()
        assert "catalog_trace" in result
        assert isinstance(result["catalog_trace"], list)
        assert len(result["catalog_trace"]) > 0

    def test_catalog_trace_has_version(self):
        result = _shadow()
        for trace in result["catalog_trace"]:
            assert "catalog_version" in trace or "error" in trace

    def test_catalog_trace_elec_codes(self):
        result = _shadow()
        codes = {t.get("code") for t in result["catalog_trace"]}
        assert "TURPE_ENERGIE_C5_BT" in codes
        assert "ACCISE_ELEC" in codes
        assert "TVA_NORMALE" in codes


# ═══════════════════════════════════════════════
# B. Diagnostics & Confidence
# ═══════════════════════════════════════════════


class TestDiagnostics:
    def test_diagnostics_included(self):
        result = _shadow()
        assert "diagnostics" in result
        assert "confidence" in result["diagnostics"]
        assert "assumptions" in result["diagnostics"]
        assert "missing_fields" in result["diagnostics"]

    def test_diagnostics_confidence_high(self):
        """Contract + multi-type lines → high confidence."""
        lines = [FakeLine(), FakeNetworkLine(), FakeTaxLine()]
        result = _shadow(FakeContract(), lines)
        assert result["diagnostics"]["confidence"] == "high"

    def test_diagnostics_confidence_low(self):
        """No contract price, no lines → low confidence."""
        result = _shadow(FakeContractNone(), [])
        assert result["diagnostics"]["confidence"] == "low"

    def test_diagnostics_confidence_medium(self):
        """Contract price but no lines → medium."""
        result = _shadow(FakeContract(), [])
        assert result["diagnostics"]["confidence"] == "medium"

    def test_diagnostics_missing_fields(self):
        """Only energy lines → detects missing network and tax lines."""
        result = _shadow(FakeContract(), [FakeLine()])
        missing = result["diagnostics"]["missing_fields"]
        assert "network_lines" in missing
        assert "tax_lines" in missing

    def test_diagnostics_no_missing_when_complete(self):
        """All line types → no missing fields."""
        lines = [FakeLine(), FakeNetworkLine(), FakeTaxLine()]
        result = _shadow(FakeContract(), lines)
        assert len(result["diagnostics"]["missing_fields"]) == 0

    def test_assumptions_mention_contract(self):
        result = _shadow(FakeContract())
        assumptions = result["diagnostics"]["assumptions"]
        assert any("contrat" in a.lower() for a in assumptions)

    def test_assumptions_mention_catalog_when_no_contract(self):
        result = _shadow(FakeContractNone(), [])
        assumptions = result["diagnostics"]["assumptions"]
        assert any("catalogue" in a.lower() for a in assumptions)


# ═══════════════════════════════════════════════
# C. Price Source
# ═══════════════════════════════════════════════


class TestPriceSource:
    def test_price_source_contract(self):
        result = _shadow(FakeContract())
        assert result["price_source"] == "contract:42"

    def test_price_source_fallback(self):
        result = _shadow(FakeContractNone())
        assert result["price_source"] == "catalog_default"


# ═══════════════════════════════════════════════
# D. Contributors
# ═══════════════════════════════════════════════


class TestContributors:
    def test_contributors_sorted_by_delta(self):
        from services.billing_explainability import compute_contributors

        metrics = {
            "delta_fourniture": 50,
            "delta_reseau": -200,
            "delta_taxes": 30,
            "delta_ttc": -100,
        }
        contributors = compute_contributors(metrics)
        deltas = [abs(c["delta_eur"]) for c in contributors]
        assert deltas == sorted(deltas, reverse=True)

    def test_contributors_max_3(self):
        from services.billing_explainability import compute_contributors

        metrics = {
            "delta_fourniture": 50,
            "delta_reseau": 200,
            "delta_taxes": 30,
            "delta_ttc": 300,
        }
        contributors = compute_contributors(metrics)
        assert len(contributors) <= 3

    def test_contributors_has_explanation(self):
        from services.billing_explainability import compute_contributors

        metrics = {
            "delta_fourniture": 100,
            "delta_reseau": 50,
            "delta_taxes": 20,
            "delta_ttc": 170,
            "price_ref": 0.15,
        }
        contributors = compute_contributors(metrics)
        for c in contributors:
            assert "explanation_fr" in c
            assert len(c["explanation_fr"]) > 0

    def test_contributors_empty_when_no_delta(self):
        from services.billing_explainability import compute_contributors

        metrics = {"delta_fourniture": 0, "delta_reseau": 0, "delta_taxes": 0, "delta_ttc": 0}
        assert compute_contributors(metrics) == []

    def test_contributors_pct_of_total(self):
        from services.billing_explainability import compute_contributors

        metrics = {"delta_fourniture": 100, "delta_reseau": 0, "delta_taxes": 0, "delta_ttc": 100}
        contributors = compute_contributors(metrics)
        assert len(contributors) == 1
        assert contributors[0]["pct_of_total"] == 100.0
