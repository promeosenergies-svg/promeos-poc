"""
PROMEOS — V2 Offer ↔ Invoice Reconciliation Tests
Tests: reconcile_offer_vs_shadow (pure, no DB), endpoint source guards.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date

from services.offer_invoice_reconcile_v1 import (
    reconcile_offer_vs_shadow,
    _compute_component_deltas,
    _build_explanations,
)
from services.offer_pricing_v1 import compute_offer_quote
from services.billing_shadow_v2 import shadow_billing_v2
from types import SimpleNamespace


# ── Helpers ──────────────────────────────────────────────────────────


def _make_invoice(kwh=1000, total_eur=250.0):
    return SimpleNamespace(
        energy_kwh=kwh,
        total_eur=total_eur,
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
        site_id=1,
        id=1,
        invoice_number="TEST-001",
        contract_id=1,
    )


def _make_contract(energy_type="elec", price_ref=0.18):
    return SimpleNamespace(
        energy_type=SimpleNamespace(value=energy_type),
        price_ref_eur_per_kwh=price_ref,
        id=1,
    )


def _make_line(line_type, amount):
    return SimpleNamespace(
        line_type=SimpleNamespace(value=line_type),
        amount_eur=amount,
    )


def _shadow(kwh=1000, price=0.18, energy_type="elec"):
    inv = _make_invoice(kwh=kwh)
    contract = _make_contract(energy_type=energy_type, price_ref=price)
    lines = [
        _make_line("energy", kwh * price),
        _make_line("network", kwh * 0.0453),
        _make_line("tax", kwh * 0.0225),
    ]
    return shadow_billing_v2(inv, lines, contract)


# ========================================================================
# A. reconcile_offer_vs_shadow (Pure, no DB)
# ========================================================================


class TestReconcileVsShadow:
    """Reconcile offer vs shadow result without DB."""

    def test_fixe_vs_shadow_has_delta(self):
        shadow = _shadow(kwh=1000, price=0.18)
        result = reconcile_offer_vs_shadow(
            strategy="fixe",
            energy_type="elec",
            consumption_kwh=1000,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            price_ref_eur_per_kwh=0.18,
            shadow_result=shadow,
        )
        assert "delta" in result
        assert "totals" in result["delta"]
        assert "by_component" in result["delta"]
        assert result["confidence"] == "HIGH"

    def test_fixe_fourniture_is_higher(self):
        """FIXE strategy = 1.05x, so fourniture delta > 0."""
        shadow = _shadow(kwh=1000, price=0.18)
        result = reconcile_offer_vs_shadow(
            strategy="fixe",
            energy_type="elec",
            consumption_kwh=1000,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            price_ref_eur_per_kwh=0.18,
            shadow_result=shadow,
        )
        fourniture_delta = next(d for d in result["delta"]["by_component"] if d["code"] == "fourniture")
        assert fourniture_delta["delta_ht"] > 0  # FIXE is more expensive

    def test_spot_fourniture_is_lower(self):
        """SPOT strategy = 0.88x, so fourniture delta < 0."""
        shadow = _shadow(kwh=1000, price=0.18)
        result = reconcile_offer_vs_shadow(
            strategy="spot",
            energy_type="elec",
            consumption_kwh=1000,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            price_ref_eur_per_kwh=0.18,
            shadow_result=shadow,
        )
        fourniture_delta = next(d for d in result["delta"]["by_component"] if d["code"] == "fourniture")
        assert fourniture_delta["delta_ht"] < 0  # SPOT is cheaper

    def test_network_delta_zero(self):
        """Network component should be identical (same catalog rate)."""
        shadow = _shadow(kwh=1000, price=0.18)
        result = reconcile_offer_vs_shadow(
            strategy="fixe",
            energy_type="elec",
            consumption_kwh=1000,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            price_ref_eur_per_kwh=0.18,
            shadow_result=shadow,
        )
        reseau_delta = next(d for d in result["delta"]["by_component"] if d["code"] == "reseau")
        assert abs(reseau_delta["delta_ht"]) < 0.01

    def test_explanations_non_empty(self):
        shadow = _shadow(kwh=1000, price=0.18)
        result = reconcile_offer_vs_shadow(
            strategy="fixe",
            energy_type="elec",
            consumption_kwh=1000,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
            price_ref_eur_per_kwh=0.18,
            shadow_result=shadow,
        )
        assert len(result["explanations"]) >= 1

    def test_no_shadow_gives_low_confidence(self):
        result = reconcile_offer_vs_shadow(
            strategy="fixe",
            energy_type="elec",
            consumption_kwh=1000,
            price_ref_eur_per_kwh=0.18,
            shadow_result=None,
        )
        assert result["confidence"] == "LOW"
        assert result["delta"] is None


# ========================================================================
# B. Component Deltas Helper
# ========================================================================


class TestComponentDeltas:
    """_compute_component_deltas produces correct output."""

    def test_matching_components(self):
        offer = {
            "components": [
                {"code": "fourniture", "label": "F", "ht": 200.0},
                {"code": "reseau", "label": "R", "ht": 50.0},
            ]
        }
        shadow = {
            "components": [
                {"code": "fourniture", "label": "F", "ht": 180.0},
                {"code": "reseau", "label": "R", "ht": 50.0},
            ]
        }
        deltas = _compute_component_deltas(offer, shadow)
        assert len(deltas) == 2
        assert deltas[0]["delta_ht"] == 20.0
        assert deltas[1]["delta_ht"] == 0.0

    def test_missing_shadow_component(self):
        offer = {"components": [{"code": "fourniture", "label": "F", "ht": 200.0}]}
        shadow = {"components": []}
        deltas = _compute_component_deltas(offer, shadow)
        assert deltas[0]["shadow_ht"] == 0
        assert deltas[0]["delta_ht"] == 200.0


# ========================================================================
# C. Explanations Builder
# ========================================================================


class TestExplanations:
    """_build_explanations produces useful text."""

    def test_positive_delta_mentions_more_expensive(self):
        explanations = _build_explanations(
            delta_by_component=[],
            delta_totals={"ttc": 50.0},
            missing_data=[],
            strategy="fixe",
            shadow={},
            offer={},
        )
        assert any("plus" in e for e in explanations)

    def test_negative_delta_mentions_savings(self):
        explanations = _build_explanations(
            delta_by_component=[],
            delta_totals={"ttc": -30.0},
            missing_data=[],
            strategy="spot",
            shadow={},
            offer={},
        )
        assert any("économiserait" in e for e in explanations)

    def test_missing_data_warnings(self):
        explanations = _build_explanations(
            delta_by_component=[],
            delta_totals={"ttc": 0},
            missing_data=["price_ref_eur_per_kwh", "contract"],
            strategy="fixe",
            shadow={},
            offer={},
        )
        assert any("défaut" in e for e in explanations)


# ========================================================================
# D. Endpoint Source Guards
# ========================================================================


class TestEndpointSourceGuards:
    """Verify endpoints exist in purchase route source."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        import pathlib

        self.src = (pathlib.Path(__file__).parent.parent / "routes" / "purchase.py").read_text(encoding="utf-8")

    def test_has_quote_offer_endpoint(self):
        assert "/quote-offer" in self.src

    def test_has_quote_multi_endpoint(self):
        assert "/quote-multi" in self.src

    def test_has_reconcile_endpoint(self):
        assert "/reconcile" in self.src

    def test_has_quote_offer_request_schema(self):
        assert "QuoteOfferRequest" in self.src

    def test_has_reconcile_request_schema(self):
        assert "ReconcileRequest" in self.src

    def test_imports_offer_pricing(self):
        assert "offer_pricing_v1" in self.src

    def test_imports_reconcile(self):
        assert "offer_invoice_reconcile_v1" in self.src


# ========================================================================
# E. Offer Pricing Service Source Guards
# ========================================================================


class TestOfferPricingSourceGuards:
    """Verify offer_pricing_v1.py has expected structure."""

    @pytest.fixture(autouse=True)
    def _load_source(self):
        import pathlib

        self.src = (pathlib.Path(__file__).parent.parent / "services" / "offer_pricing_v1.py").read_text(
            encoding="utf-8"
        )

    def test_has_compute_offer_quote(self):
        assert "def compute_offer_quote" in self.src

    def test_has_compute_multi_strategy_quotes(self):
        assert "def compute_multi_strategy_quotes" in self.src

    def test_has_convert_helper(self):
        assert "def convert_eur_mwh_to_eur_kwh" in self.src

    def test_has_safe_div_helper(self):
        assert "def safe_div" in self.src

    def test_uses_catalog(self):
        assert "tax_catalog_service" in self.src

    def test_has_strategy_factors(self):
        assert "STRATEGY_FACTORS" in self.src

    def test_no_hardcoded_turpe_rate(self):
        """Rates should come from catalog, not hardcoded in function body."""
        # Check that TURPE rate is NOT hardcoded inline (only in _FALLBACK_RATES)
        lines = self.src.split("\n")
        fn_body = False
        for line in lines:
            if "def compute_offer_quote" in line:
                fn_body = True
            if fn_body and "0.0453" in line:
                pytest.fail("Hardcoded TURPE rate found in compute_offer_quote body")
            if fn_body and line.strip().startswith("def ") and "compute_offer_quote" not in line:
                break

    def test_model_version(self):
        assert '"offer_v1"' in self.src
