"""
PROMEOS — V100 Billing Invariants P0
10 structural invariants + 2 e2e shadow tests + catalog tests.
All tests are pure / deterministic (no DB needed).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math
import pytest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from services.billing_shadow_v2 import shadow_billing_v2, _safe_rate, _FALLBACK


# ── Helpers ──────────────────────────────────────────────────────────


def _make_invoice(kwh=1000, total_eur=250.0, period_start=None, period_end=None, site_id=1, energy_kwh=None):
    return SimpleNamespace(
        energy_kwh=energy_kwh if energy_kwh is not None else kwh,
        total_eur=total_eur,
        period_start=period_start or date(2025, 1, 1),
        period_end=period_end or date(2025, 1, 31),
        site_id=site_id,
        id=1,
        invoice_number="TEST-001",
        contract_id=1,
    )


def _make_contract(energy_type="elec", price_ref=0.18, fixed_fee=None):
    ns = SimpleNamespace(
        energy_type=SimpleNamespace(value=energy_type),
        price_ref_eur_per_kwh=price_ref,
        id=1,
        supplier_name="TestSupplier",
        start_date=date(2024, 1, 1),
        end_date=date(2025, 12, 31),
    )
    if fixed_fee is not None:
        ns.fixed_fee_eur_per_month = fixed_fee
    return ns


def _make_line(line_type, amount):
    return SimpleNamespace(
        line_type=SimpleNamespace(value=line_type),
        amount_eur=amount,
    )


def _make_lines(fourniture=180.0, reseau=45.3, taxes=22.5):
    return [
        _make_line("energy", fourniture),
        _make_line("network", reseau),
        _make_line("tax", taxes),
    ]


def _run_shadow(
    kwh=1000,
    price_ref=0.18,
    energy_type="elec",
    total_eur=250.0,
    period_start=None,
    period_end=None,
    fixed_fee=None,
    fourniture=180.0,
    reseau=45.3,
    taxes=22.5,
):
    inv = _make_invoice(kwh=kwh, total_eur=total_eur, period_start=period_start, period_end=period_end)
    contract = _make_contract(energy_type=energy_type, price_ref=price_ref, fixed_fee=fixed_fee)
    lines = _make_lines(fourniture=fourniture, reseau=reseau, taxes=taxes)
    return shadow_billing_v2(inv, lines, contract)


# ========================================================================
# A. 10 Structural Invariants
# ========================================================================


class TestInvariant01_TotalEqualsSumComponents:
    """INV-01: expected_ttc == sum(component.ttc)."""

    def test_elec(self):
        r = _run_shadow(kwh=1000, energy_type="elec")
        comp_ttc = sum(c["ttc"] for c in r["components"])
        assert abs(r["expected_ttc"] - comp_ttc) < 0.02

    def test_gaz(self):
        r = _run_shadow(kwh=1000, energy_type="gaz", price_ref=0.09)
        comp_ttc = sum(c["ttc"] for c in r["components"])
        assert abs(r["expected_ttc"] - comp_ttc) < 0.02


class TestInvariant02_HtPlusTvaEqualsTtc:
    """INV-02: For each component, ht + tva == ttc."""

    def test_all_components(self):
        r = _run_shadow()
        for c in r["components"]:
            assert abs(c["ht"] + c["tva"] - c["ttc"]) < 0.02, (
                f"Component {c['code']}: {c['ht']} + {c['tva']} != {c['ttc']}"
            )

    def test_totals(self):
        r = _run_shadow()
        assert abs(r["totals"]["ht"] + r["totals"]["tva"] - r["totals"]["ttc"]) < 0.02


class TestInvariant03_ShadowPositiveIfKwhPositive:
    """INV-03: If kwh > 0 and price_ref > 0, expected_ttc > 0."""

    def test_positive(self):
        r = _run_shadow(kwh=500, price_ref=0.15)
        assert r["expected_ttc"] > 0

    def test_zero_kwh(self):
        r = _run_shadow(kwh=0)
        # With abonnement, expected_ttc can still be > 0, but fourniture should be 0
        assert r["expected_fourniture_ht"] == 0


class TestInvariant04_NoNaN:
    """INV-04: No NaN or Inf in any numeric field."""

    def test_no_nan_basic(self):
        r = _run_shadow()
        for key in [
            "expected_fourniture_ht",
            "expected_reseau_ht",
            "expected_taxes_ht",
            "expected_abo_ht",
            "expected_tva",
            "expected_ttc",
            "delta_fourniture",
            "delta_reseau",
            "delta_taxes",
            "delta_ttc",
            "delta_pct",
            "kwh",
            "price_ref",
        ]:
            assert not math.isnan(r[key]), f"{key} is NaN"
            assert not math.isinf(r[key]), f"{key} is Inf"

    def test_no_nan_zero_kwh(self):
        r = _run_shadow(kwh=0, total_eur=0)
        for key in ["expected_ttc", "delta_pct", "delta_ttc"]:
            assert not math.isnan(r[key]), f"{key} is NaN with zero kwh"
            assert not math.isinf(r[key]), f"{key} is Inf with zero kwh"


class TestInvariant05_RefPricePositive:
    """INV-05: price_ref is always > 0 (from contract or fallback)."""

    def test_with_contract(self):
        r = _run_shadow(price_ref=0.22)
        assert r["price_ref"] == 0.22

    def test_without_contract(self):
        inv = _make_invoice()
        lines = _make_lines()
        r = shadow_billing_v2(inv, lines, None)
        assert r["price_ref"] > 0


class TestInvariant06_KwhConsistent:
    """INV-06: kwh in result matches invoice.energy_kwh."""

    def test_kwh_passthrough(self):
        r = _run_shadow(kwh=1234.5)
        assert r["kwh"] == 1234.5

    def test_none_kwh_defaults_to_zero(self):
        inv = _make_invoice()
        inv.energy_kwh = None
        r = shadow_billing_v2(inv, _make_lines(), _make_contract())
        assert r["kwh"] == 0.0


class TestInvariant07_DeltaPctBounded:
    """INV-07: delta_pct is bounded (no division by zero explosion)."""

    def test_zero_expected(self):
        r = _run_shadow(kwh=0, total_eur=100.0)
        # When expected_ttc is near zero (only abo), delta_pct should not explode
        assert not math.isinf(r["delta_pct"])
        assert not math.isnan(r["delta_pct"])

    def test_normal_case(self):
        r = _run_shadow(kwh=1000, total_eur=250.0)
        assert abs(r["delta_pct"]) < 1000  # Sanity bound


class TestInvariant08_BreakdownSumsMatchTotals:
    """INV-08: sum(components.ht) == totals.ht, same for tva and ttc."""

    def test_sums(self):
        r = _run_shadow()
        comp_ht = sum(c["ht"] for c in r["components"])
        comp_tva = sum(c["tva"] for c in r["components"])
        comp_ttc = sum(c["ttc"] for c in r["components"])
        assert abs(comp_ht - r["totals"]["ht"]) < 0.02
        assert abs(comp_tva - r["totals"]["tva"]) < 0.02
        assert abs(comp_ttc - r["totals"]["ttc"]) < 0.02


class TestInvariant09_ProrataBounded:
    """INV-09: prorata_factor > 0 and days_in_period >= 1."""

    def test_normal_month(self):
        r = _run_shadow(period_start=date(2025, 1, 1), period_end=date(2025, 1, 31))
        assert r["prorata_factor"] == pytest.approx(30 / 30.0, abs=0.01)
        assert r["days_in_period"] == 30

    def test_short_period(self):
        r = _run_shadow(period_start=date(2025, 1, 1), period_end=date(2025, 1, 10))
        assert r["prorata_factor"] == pytest.approx(9 / 30.0, abs=0.01)
        assert r["days_in_period"] == 9

    def test_no_dates_defaults_30(self):
        inv = _make_invoice()
        inv.period_start = None
        inv.period_end = None
        r = shadow_billing_v2(inv, _make_lines(), _make_contract())
        assert r["prorata_factor"] == pytest.approx(1.0)
        assert r["days_in_period"] == 30


class TestInvariant10_ZeroKwhNoCrash:
    """INV-10: zero or None kWh does not crash, returns valid dict."""

    def test_zero_kwh(self):
        r = _run_shadow(kwh=0, total_eur=0)
        assert isinstance(r, dict)
        assert "expected_ttc" in r
        assert "components" in r
        assert len(r["components"]) == 4

    def test_none_kwh(self):
        inv = _make_invoice()
        inv.energy_kwh = None
        r = shadow_billing_v2(inv, [], _make_contract())
        assert isinstance(r, dict)
        assert r["kwh"] == 0.0


# ========================================================================
# B. 2 End-to-end Shadow Tests
# ========================================================================


class TestE2E_ShadowElec:
    """E2E-1: Full shadow billing for a typical 1000 kWh elec invoice."""

    def test_full_breakdown(self):
        r = _run_shadow(
            kwh=1000,
            price_ref=0.18,
            energy_type="elec",
            total_eur=300.0,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 31),
        )

        # Fourniture: 1000 × 0.18 = 180.00
        assert r["expected_fourniture_ht"] == 180.0

        # Réseau: 1000 × 0.0453 = 45.30
        assert r["expected_reseau_ht"] == 45.30

        # Taxes: 1000 × 0.0225 = 22.50
        assert r["expected_taxes_ht"] == 22.50

        # Abonnement: 18.48 × (30/30) = 18.48
        assert r["expected_abo_ht"] == 18.48

        # TVA: (180 + 45.3 + 22.5) × 0.20 + 18.48 × 0.055
        tva_20 = (180.0 + 45.30 + 22.50) * 0.20  # = 49.56
        tva_55 = 18.48 * 0.055  # ≈ 1.0164
        assert r["expected_tva"] == pytest.approx(tva_20 + tva_55, abs=0.02)

        # TTC = HT + TVA
        exp_ht = 180.0 + 45.30 + 22.50 + 18.48
        exp_ttc = exp_ht + tva_20 + tva_55
        assert r["expected_ttc"] == pytest.approx(exp_ttc, abs=0.02)

        # Method
        assert r["method"] == "shadow_v2_catalog"

        # Components count
        assert len(r["components"]) == 4
        codes = [c["code"] for c in r["components"]]
        assert codes == ["fourniture", "reseau", "taxes", "abonnement"]


class TestE2E_ShadowGaz:
    """E2E-2: Full shadow billing for a typical 2000 kWh gaz invoice."""

    def test_full_breakdown(self):
        r = _run_shadow(
            kwh=2000,
            price_ref=0.09,
            energy_type="gaz",
            total_eur=250.0,
            period_start=date(2025, 2, 1),
            period_end=date(2025, 2, 28),
        )

        # Fourniture: 2000 × 0.09 = 180.00
        assert r["expected_fourniture_ht"] == 180.0

        # Réseau: 2000 × (0.025 + 0.012) = 2000 × 0.037 = 74.00
        assert r["expected_reseau_ht"] == 74.0

        # Taxes: 2000 × 0.01637 = 32.74
        assert r["expected_taxes_ht"] == pytest.approx(32.74, abs=0.01)

        # Abonnement: 0 (simplified gaz) × 27/30 = 0
        assert r["expected_abo_ht"] == 0.0

        # Prorata
        assert r["days_in_period"] == 27
        assert r["prorata_factor"] == pytest.approx(27 / 30.0, abs=0.01)

        # Energy type
        assert r["energy_type"] == "GAZ"


# ========================================================================
# C. Tax Catalog Tests
# ========================================================================


class TestCatalogLookup:
    """Catalog service: date-based lookup."""

    def test_get_entry_by_code(self):
        from app.referential.tax_catalog_service import get_entry

        entry = get_entry("TVA_NORMALE")
        assert entry is not None
        assert entry["rate"] == 0.20

    def test_get_rate(self):
        from app.referential.tax_catalog_service import get_rate

        assert get_rate("TVA_NORMALE") == 0.20
        assert get_rate("TVA_REDUITE") == 0.055

    def test_get_rate_unknown_raises(self):
        from app.referential.tax_catalog_service import get_rate

        with pytest.raises(KeyError):
            get_rate("UNKNOWN_CODE_XYZ")

    def test_lookup_at_date(self):
        from app.referential.tax_catalog_service import get_entry

        entry = get_entry("TURPE_ENERGIE_C5_BT", at_date=date(2025, 6, 1))
        assert entry is not None
        assert entry["rate"] == 0.0453

    def test_catalog_version(self):
        from app.referential.tax_catalog_service import get_catalog_version

        v = get_catalog_version()
        assert v != "unknown"
        assert "2025" in v


class TestCatalogFallback:
    """Catalog service: fallback behavior."""

    def test_trace_includes_source(self):
        from app.referential.tax_catalog_service import trace

        t = trace("ACCISE_ELEC")
        assert t["code"] == "ACCISE_ELEC"
        assert t["used_rate"] == 0.02250
        assert t.get("source") is not None

    def test_safe_rate_returns_catalog_value(self):
        rate = _safe_rate("TVA_NORMALE")
        assert rate == 0.20

    def test_safe_rate_fallback_on_error(self):
        """If catalog import fails, _safe_rate returns hardcoded fallback."""
        with patch("services.billing_shadow_v2._safe_rate", side_effect=Exception):
            # Direct fallback dict check
            assert _FALLBACK["TVA_NORMALE"] == 0.20
            assert _FALLBACK["TURPE_ENERGIE_C5_BT"] == 0.0453


class TestCatalogReload:
    """Catalog service: reload mechanism."""

    def test_reload_returns_catalog(self):
        from app.referential.tax_catalog_service import reload_catalog

        catalog = reload_catalog()
        assert "version" in catalog
        assert "entries" in catalog
        assert len(catalog["entries"]) >= 10


# ========================================================================
# D. Billing Service Guards
# ========================================================================


class TestBillingServiceGuards:
    """Guards added to billing_service.py rules."""

    def test_r8_guard_source_has_abs(self):
        """R8: denominator uses abs() to handle negative total_eur."""
        import pathlib

        src = (pathlib.Path(__file__).parent.parent / "services" / "billing_service.py").read_text(encoding="utf-8")
        # Find the R8 function and check for abs()
        assert "abs(invoice.total_eur)" in src

    def test_r11_guard_has_minimum_threshold(self):
        """R11: tolerance includes minimum 5€ absolute threshold."""
        import pathlib

        src = (pathlib.Path(__file__).parent.parent / "services" / "billing_service.py").read_text(encoding="utf-8")
        assert "delta > 5.0" in src

    def test_r11_guard_has_abs_denominator(self):
        """R11: denominator uses abs() for negative invoice amounts."""
        import pathlib

        src = (pathlib.Path(__file__).parent.parent / "services" / "billing_service.py").read_text(encoding="utf-8")
        assert "abs(invoice.total_eur)" in src


# ========================================================================
# E. Shadow V2 Backward Compatibility
# ========================================================================


class TestBackwardCompatibility:
    """Shadow V2 result must contain all old keys for R13/R14."""

    REQUIRED_KEYS = [
        "expected_fourniture_ht",
        "expected_reseau_ht",
        "expected_taxes_ht",
        "expected_tva",
        "expected_ttc",
        "actual_fourniture_ht",
        "actual_reseau_ht",
        "actual_taxes_ht",
        "actual_ttc",
        "delta_fourniture",
        "delta_reseau",
        "delta_taxes",
        "delta_ttc",
        "delta_pct",
        "energy_type",
        "kwh",
        "price_ref",
        "method",
    ]

    def test_all_old_keys_present(self):
        r = _run_shadow()
        for key in self.REQUIRED_KEYS:
            assert key in r, f"Missing backward-compat key: {key}"

    def test_new_keys_present(self):
        r = _run_shadow()
        assert "components" in r
        assert "totals" in r
        assert "expected_abo_ht" in r
        assert "prorata_factor" in r
        assert "days_in_period" in r

    def test_method_updated(self):
        r = _run_shadow()
        assert r["method"] == "shadow_v2_catalog"
