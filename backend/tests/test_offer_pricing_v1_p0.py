"""
PROMEOS — V2 Offer Pricing V1 P0 Invariants
Tests: structural invariants, catalog integration, multi-strategy, helpers.
All pure / deterministic (no DB needed).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import pytest
from datetime import date

from services.offer_pricing_v1 import (
    compute_offer_quote,
    compute_multi_strategy_quotes,
    convert_eur_mwh_to_eur_kwh,
    safe_div,
    STRATEGY_FACTORS,
)


# ── Helpers ──────────────────────────────────────────────────────────


def _quote(
    strategy="fixe", energy_type="elec", kwh=1000, price=0.18, period_start=None, period_end=None, fixed_fee=0.0
):
    return compute_offer_quote(
        strategy=strategy,
        energy_type=energy_type,
        consumption_kwh=kwh,
        period_start=period_start or date(2025, 1, 1),
        period_end=period_end or date(2025, 1, 31),
        price_ref_eur_per_kwh=price,
        fixed_fee_eur_per_month=fixed_fee,
    )


# ========================================================================
# A. Structural Invariants
# ========================================================================


class TestOffer_TotalEqualsSumComponents:
    """OFFER-INV-01: totals.ttc == sum(component.ttc)."""

    def test_fixe_elec(self):
        r = _quote("fixe", "elec", 1000)
        comp_ttc = sum(c["ttc"] for c in r["components"])
        assert abs(r["totals"]["ttc"] - comp_ttc) < 0.02

    def test_indexe_gaz(self):
        r = _quote("indexe", "gaz", 2000, price=0.09)
        comp_ttc = sum(c["ttc"] for c in r["components"])
        assert abs(r["totals"]["ttc"] - comp_ttc) < 0.02

    def test_spot_elec(self):
        r = _quote("spot", "elec", 5000)
        comp_ttc = sum(c["ttc"] for c in r["components"])
        assert abs(r["totals"]["ttc"] - comp_ttc) < 0.02


class TestOffer_HtPlusTvaEqualsTtc:
    """OFFER-INV-02: For each component, ht + tva == ttc."""

    def test_all_components_fixe(self):
        r = _quote("fixe")
        for c in r["components"]:
            assert abs(c["ht"] + c["tva"] - c["ttc"]) < 0.02, f"{c['code']}"

    def test_totals(self):
        r = _quote("fixe")
        assert abs(r["totals"]["ht"] + r["totals"]["tva"] - r["totals"]["ttc"]) < 0.02


class TestOffer_NoNaN:
    """OFFER-INV-03: No NaN or Inf in any numeric field."""

    def test_basic(self):
        r = _quote("fixe", kwh=1000)
        for key in ["ht", "tva", "ttc"]:
            assert not math.isnan(r["totals"][key])
            assert not math.isinf(r["totals"][key])
        for c in r["components"]:
            for key in ["ht", "tva", "ttc", "qty", "unit_rate"]:
                assert not math.isnan(c[key]), f"{c['code']}.{key} is NaN"

    def test_zero_kwh(self):
        r = _quote("fixe", kwh=0)
        for key in ["ht", "tva", "ttc"]:
            assert not math.isnan(r["totals"][key])
            assert not math.isinf(r["totals"][key])


class TestOffer_ZeroKwhReturnsZeroFourniture:
    """OFFER-INV-04: kwh=0 => fourniture/reseau/taxes all 0 HT."""

    def test_zero_kwh(self):
        r = _quote("fixe", kwh=0)
        for c in r["components"]:
            if c["code"] != "abonnement":
                assert c["ht"] == 0.0, f"{c['code']} should be 0 with kwh=0"

    def test_abonnement_still_present(self):
        """Abonnement should still have value even with kwh=0 (fixed fee)."""
        r = _quote("fixe", kwh=0, fixed_fee=10.0)
        abo = next(c for c in r["components"] if c["code"] == "abonnement")
        assert abo["ht"] > 0


class TestOffer_UsesCatalogRates:
    """OFFER-INV-05: trace.source is non-empty for catalog components."""

    def test_reseau_has_trace(self):
        r = _quote("fixe", kwh=1000)
        reseau = next(c for c in r["components"] if c["code"] == "reseau")
        assert "trace" in reseau
        assert reseau["trace"] is not None

    def test_taxes_has_trace(self):
        r = _quote("fixe", kwh=1000)
        taxes = next(c for c in r["components"] if c["code"] == "taxes")
        assert "trace" in taxes
        assert taxes["trace"] is not None

    def test_abonnement_has_trace_elec(self):
        r = _quote("fixe", "elec", kwh=1000)
        abo = next(c for c in r["components"] if c["code"] == "abonnement")
        assert "trace" in abo


class TestOffer_ProrataFactor:
    """OFFER-INV-06: prorata_factor correct for different periods."""

    def test_30_days(self):
        r = _quote(period_start=date(2025, 1, 1), period_end=date(2025, 1, 31))
        assert r["meta"]["prorata_factor"] == pytest.approx(1.0, abs=0.01)

    def test_15_days(self):
        r = _quote(period_start=date(2025, 1, 1), period_end=date(2025, 1, 16))
        assert r["meta"]["prorata_factor"] == pytest.approx(0.5, abs=0.01)

    def test_60_days(self):
        r = _quote(period_start=date(2025, 1, 1), period_end=date(2025, 3, 2))
        assert r["meta"]["prorata_factor"] == pytest.approx(2.0, abs=0.01)

    def test_no_dates_defaults_30(self):
        r = compute_offer_quote(
            strategy="fixe",
            consumption_kwh=1000,
            price_ref_eur_per_kwh=0.18,
        )
        assert r["meta"]["prorata_factor"] == pytest.approx(1.0)
        assert r["meta"]["days_in_period"] == 30


# ========================================================================
# B. Strategy Factors
# ========================================================================


class TestStrategyFactors:
    """Strategy multipliers applied correctly."""

    def test_fixe_premium(self):
        r = _quote("fixe", price=0.10)
        fourniture = next(c for c in r["components"] if c["code"] == "fourniture")
        assert fourniture["unit_rate"] == pytest.approx(0.10 * 1.05, abs=0.001)

    def test_indexe_discount(self):
        r = _quote("indexe", price=0.10)
        fourniture = next(c for c in r["components"] if c["code"] == "fourniture")
        assert fourniture["unit_rate"] == pytest.approx(0.10 * 0.95, abs=0.001)

    def test_spot_discount(self):
        r = _quote("spot", price=0.10)
        fourniture = next(c for c in r["components"] if c["code"] == "fourniture")
        assert fourniture["unit_rate"] == pytest.approx(0.10 * 0.88, abs=0.001)

    def test_fixe_more_expensive_than_spot(self):
        r_fixe = _quote("fixe", kwh=1000, price=0.18)
        r_spot = _quote("spot", kwh=1000, price=0.18)
        assert r_fixe["totals"]["ttc"] > r_spot["totals"]["ttc"]

    def test_meta_includes_factor(self):
        r = _quote("fixe")
        assert r["meta"]["strategy_factor"] == STRATEGY_FACTORS["fixe"]


# ========================================================================
# C. Multi-strategy Quotes
# ========================================================================


class TestMultiStrategyQuotes:
    """compute_multi_strategy_quotes returns all strategies."""

    def test_has_three_strategies(self):
        r = compute_multi_strategy_quotes(
            consumption_kwh=1000,
            price_ref_eur_per_kwh=0.18,
        )
        assert set(r["strategies"].keys()) == {"fixe", "indexe", "spot"}

    def test_comparison_has_ttc(self):
        r = compute_multi_strategy_quotes(
            consumption_kwh=1000,
            price_ref_eur_per_kwh=0.18,
        )
        for strat in ["fixe", "indexe", "spot"]:
            assert "ttc" in r["comparison"][strat]
            assert r["comparison"][strat]["ttc"] > 0

    def test_fixe_most_expensive(self):
        r = compute_multi_strategy_quotes(
            consumption_kwh=1000,
            price_ref_eur_per_kwh=0.18,
        )
        assert r["comparison"]["fixe"]["ttc"] > r["comparison"]["spot"]["ttc"]


# ========================================================================
# D. Helpers
# ========================================================================


class TestHelpers:
    """Helper functions."""

    def test_convert_eur_mwh(self):
        assert convert_eur_mwh_to_eur_kwh(85.0) == pytest.approx(0.085)
        assert convert_eur_mwh_to_eur_kwh(100.0) == pytest.approx(0.10)

    def test_safe_div(self):
        assert safe_div(10, 2) == 5.0
        assert safe_div(10, 0) == 0.0
        assert safe_div(10, 0, default=-1) == -1

    def test_price_ref_mwh_conversion(self):
        """If price_ref_eur_per_mwh is used, it's converted to kWh."""
        r = compute_offer_quote(
            strategy="fixe",
            consumption_kwh=1000,
            price_ref_eur_per_mwh=100.0,  # = 0.10 €/kWh
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )
        assert r["meta"]["base_price_eur_kwh"] == pytest.approx(0.10, abs=0.001)


# ========================================================================
# E. Meta & Model Version
# ========================================================================


class TestMeta:
    """Meta fields present and correct."""

    def test_model_version(self):
        r = _quote("fixe")
        assert r["meta"]["model_version"] == "offer_v1"

    def test_energy_type(self):
        r = _quote("fixe", energy_type="gaz")
        assert r["meta"]["energy_type"] == "GAZ"

    def test_components_count(self):
        r = _quote("fixe")
        assert len(r["components"]) == 4
        codes = [c["code"] for c in r["components"]]
        assert codes == ["fourniture", "reseau", "taxes", "abonnement"]

    def test_breakdown_sums_match_totals(self):
        r = _quote("fixe", kwh=2500, price=0.15)
        comp_ht = sum(c["ht"] for c in r["components"])
        comp_tva = sum(c["tva"] for c in r["components"])
        comp_ttc = sum(c["ttc"] for c in r["components"])
        assert abs(comp_ht - r["totals"]["ht"]) < 0.02
        assert abs(comp_tva - r["totals"]["tva"]) < 0.02
        assert abs(comp_ttc - r["totals"]["ttc"]) < 0.02


# ========================================================================
# F. E2E Offer Calculation
# ========================================================================


class TestE2E_OfferFixeElec:
    """Full offer calculation for FIXE 1000 kWh elec."""

    def test_full_breakdown(self):
        r = _quote("fixe", "elec", kwh=1000, price=0.18, period_start=date(2025, 1, 1), period_end=date(2025, 1, 31))

        # Fourniture: 1000 × 0.18 × 1.05 = 189.00
        fourniture = next(c for c in r["components"] if c["code"] == "fourniture")
        assert fourniture["ht"] == pytest.approx(189.0, abs=0.01)

        # Réseau: 1000 × 0.0453 = 45.30
        reseau = next(c for c in r["components"] if c["code"] == "reseau")
        assert reseau["ht"] == pytest.approx(45.30, abs=0.01)

        # Taxes: 1000 × 0.0225 = 22.50
        taxes = next(c for c in r["components"] if c["code"] == "taxes")
        assert taxes["ht"] == pytest.approx(22.50, abs=0.01)

        # Abonnement: 18.48 × 1.0 = 18.48 (30 days, prorata=1)
        abo = next(c for c in r["components"] if c["code"] == "abonnement")
        assert abo["ht"] == pytest.approx(18.48, abs=0.01)

        # TVA: (189+45.3+22.5)×0.20 + 18.48×0.055
        expected_tva = (189.0 + 45.30 + 22.50) * 0.20 + 18.48 * 0.055
        assert r["totals"]["tva"] == pytest.approx(expected_tva, abs=0.05)
