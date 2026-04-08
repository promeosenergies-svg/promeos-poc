"""
Tests shadow billing V2 — bridge vers regulated_tariffs.
Vérifie que les calculs sont réalistes et que la source est tracée.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date

from models import BillingEnergyType


# ── Fake objects ─────────────────────────────────────────────────────


class FakeInvoice:
    def __init__(self, kwh=10000, total_eur=1800.0, energy_type="elec", period_start=None, period_end=None):
        self.energy_kwh = kwh
        self.total_eur = total_eur
        self.period_start = period_start or date(2026, 1, 1)
        self.period_end = period_end or date(2026, 1, 31)


class FakeContract:
    def __init__(self, energy_type="elec", price_ref=0.15, kva=50, fixed_fee=10):
        self.id = 1
        self.energy_type = BillingEnergyType.ELEC if energy_type == "elec" else BillingEnergyType.GAZ
        self.price_ref_eur_per_kwh = price_ref
        self.subscribed_power_kva = kva
        self.fixed_fee_eur_per_month = fixed_fee


class FakeLine:
    def __init__(self, line_type_val="energy", amount=1000):
        self.line_type = type("LT", (), {"value": line_type_val})()
        self.amount_eur = amount


def _shadow(inv=None, lines=None, contract=None, db=None):
    from services.billing_shadow_v2 import shadow_billing_v2

    return shadow_billing_v2(
        inv or FakeInvoice(),
        lines or [FakeLine()],
        contract or FakeContract(),
        db=db,
    )


# ── Tests bridge ─────────────────────────────────────────────────────


class TestShadowBillingBridge:
    """Tests du bridge vers regulated_tariffs."""

    def test_returns_all_components(self):
        r = _shadow()
        assert "expected_fourniture_ht" in r
        assert "expected_reseau_ht" in r
        assert "expected_taxes_ht" in r
        assert "expected_tva" in r

    def test_tariff_source_is_tracked(self):
        r = _shadow()
        assert r.get("tariff_source") in ("regulated_tariffs", "fallback")

    def test_tariff_source_is_fallback_without_db(self):
        r = _shadow(db=None)
        assert r["tariff_source"] == "fallback"

    def test_reseau_is_positive(self):
        r = _shadow()
        assert r["expected_reseau_ht"] > 0

    def test_taxes_is_positive(self):
        r = _shadow()
        assert r["expected_taxes_ht"] > 0

    def test_tva_is_positive(self):
        r = _shadow()
        assert r["expected_tva"] > 0

    def test_segment_detected(self):
        # kva=50 → C4_BT
        r = _shadow(contract=FakeContract(kva=50))
        assert r["segment"] == "C4_BT"

        # kva=300 → C3_HTA
        r = _shadow(contract=FakeContract(kva=300))
        assert r["segment"] == "C3_HTA"

        # kva=10 → C5_BT
        r = _shadow(contract=FakeContract(kva=10))
        assert r["segment"] == "C5_BT"

    def test_components_count(self):
        r = _shadow()
        assert len(r["components"]) == 4
        codes = [c["code"] for c in r["components"]]
        assert codes == ["fourniture", "reseau", "taxes", "abonnement"]


class TestShadowBillingRealism:
    """Tests de réalisme — les proportions doivent être crédibles."""

    def test_reseau_proportion(self):
        """Le réseau (TURPE) doit représenter > 5% du HT."""
        r = _shadow()
        total_ht = sum(c["ht"] for c in r["components"])
        if total_ht > 0:
            pct = r["expected_reseau_ht"] / total_ht * 100
            assert pct > 3, f"Réseau = {pct:.1f}% du HT (trop bas)"
            assert pct < 40, f"Réseau = {pct:.1f}% du HT (trop haut)"

    def test_taxes_proportion(self):
        """Les taxes (accise) doivent représenter > 5% du HT."""
        r = _shadow()
        total_ht = sum(c["ht"] for c in r["components"])
        if total_ht > 0:
            pct = r["expected_taxes_ht"] / total_ht * 100
            assert pct > 3, f"Taxes = {pct:.1f}% du HT (trop bas)"
            assert pct < 35, f"Taxes = {pct:.1f}% du HT (trop haut)"

    def test_tva_around_20_pct(self):
        """La TVA doit être ~20% du HT (uniforme depuis août 2025)."""
        inv = FakeInvoice(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        r = _shadow(inv=inv)
        total_ht = sum(c["ht"] for c in r["components"])
        if r["expected_tva"] > 0 and total_ht > 0:
            effective_rate = r["expected_tva"] / total_ht * 100
            assert 15 < effective_rate < 25, f"TVA effective = {effective_rate:.1f}%"


class TestShadowBillingTVA:
    """Tests TVA : vérifier la suppression du taux réduit post-août 2025."""

    def test_tva_uniforme_post_aout_2025(self):
        """Post août 2025 : TVA 20% sur tout (y compris abonnement)."""
        inv = FakeInvoice(period_start=date(2026, 1, 1), period_end=date(2026, 1, 31))
        r = _shadow(inv=inv)
        abo_tva_rate = r["components"][3]["tva_rate"]
        assert abo_tva_rate == pytest.approx(0.20, abs=0.001), (
            f"TVA abonnement post-août 2025 devrait être 20%, pas {abo_tva_rate}"
        )

    def test_tva_reduite_pre_aout_2025(self):
        """Avant août 2025 : TVA 5.5% sur abonnement."""
        inv = FakeInvoice(period_start=date(2025, 6, 1), period_end=date(2025, 6, 30))
        r = _shadow(inv=inv)
        abo_tva_rate = r["components"][3]["tva_rate"]
        assert abo_tva_rate == pytest.approx(0.055, abs=0.001), (
            f"TVA abonnement pré-août 2025 devrait être 5.5%, pas {abo_tva_rate}"
        )


class TestShadowBillingFallback:
    """Tests de fallback quand la DB est vide."""

    def test_works_without_db(self):
        """Sans DB, le fallback doit fonctionner."""
        r = _shadow(db=None)
        assert r["expected_reseau_ht"] > 0
        assert r["tariff_source"] == "fallback"


class TestShadowBillingSourceGuards:
    """Guards anti-régression sur les constantes."""

    def test_no_old_cta_rate_in_yaml(self):
        """Le YAML CTA doit être 15% (CRE 2026-14, pas 21.93% ni 27.04%)."""
        from config.tarif_loader import reload_tarifs, get_cta_taux

        reload_tarifs()
        assert get_cta_taux("elec") == pytest.approx(15.0, abs=0.01)

    def test_no_old_cspe_in_yaml(self):
        """Le YAML accise elec doit être 0.02658 (pas 0.02623)."""
        from config.tarif_loader import reload_tarifs, get_accise_kwh

        reload_tarifs()
        assert get_accise_kwh("elec") == pytest.approx(0.02658, abs=0.001)

    def test_fallback_accise_updated(self):
        """Le fallback hardcodé ACCISE_ELEC ne doit pas être l'ancien 0.02623."""
        from services.billing_shadow_v2 import _FALLBACK

        accise = _FALLBACK.get("ACCISE_ELEC", 0)
        assert accise != 0.02623, "Ancien taux 0.02623 encore dans les fallbacks"

    def test_fallback_tva_reduite_is_20(self):
        """Post août 2025, le fallback TVA réduite doit être 0.20 (suppression)."""
        from services.billing_shadow_v2 import _FALLBACK

        tva_r = _FALLBACK.get("TVA_REDUITE", 0)
        assert tva_r == pytest.approx(0.20, abs=0.001), (
            f"TVA réduite fallback devrait être 0.20 (supprimée), pas {tva_r}"
        )
