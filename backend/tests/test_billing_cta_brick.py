"""
PROMEOS — Tests CTA brick (billing refactor V112 + Vague 2 review fix).

Vérifie que la CTA est calculée conformément à la doctrine :
- Élec : assiette × taux_dist_ou_trans (simple)
- Gaz distribution : assiette × (taux_dist + taux_trans × coef_transport)
  Au 1/07/2025+ : 0.2080 + 0.0471 × 0.8321 ≈ 0.24719
  Au 1/07/2024 → 30/06/2025 : 0.2080 + 0.0471 × 0.8357 ≈ 0.24736
- Prorata sur 365 jours
- Audit trail présent (source, source_ref, valid_from)
- Césure 1/02/2026 pour CTA élec (21,93% → 15%)
"""

from datetime import date

import pytest

from services.billing_engine.bricks.cta import (
    CtaResult,
    compute_cta,
    compute_cta_from_period_bounds,
)
from services.billing_engine.parameter_store import ParameterStore, reload_yaml_cache


@pytest.fixture(autouse=True)
def _reset_yaml_cache():
    reload_yaml_cache()
    yield
    reload_yaml_cache()


@pytest.fixture
def store():
    return ParameterStore(db=None)


# ── CTA gaz distribution (formule additive 20,80% + 4,71% × coef) ─────────

# Taux effectif au 1/07/2025+ avec coef 83.21%
_GAZ_EFFECTIVE_RATE_2025 = 0.2080 + 0.0471 * 0.8321  # ≈ 0.247192


class TestCtaGazDistribution:
    def test_cta_gaz_full_year(self, store):
        """1 an complet, assiette 100 EUR/an → 100 × (20,80% + 4,71% × 83,21%)."""
        r = compute_cta(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=100.0,
            period_days=365,
            at_date=date(2026, 6, 1),
        )
        assert isinstance(r, CtaResult)
        assert r.rate == pytest.approx(_GAZ_EFFECTIVE_RATE_2025, abs=1e-6)
        assert r.assiette_fixe == pytest.approx(100.0, abs=1e-6)
        assert r.amount_ht == pytest.approx(100.0 * _GAZ_EFFECTIVE_RATE_2025, abs=1e-4)
        assert r.energy == "gaz"
        assert r.network_level == "distribution"

    def test_cta_gaz_monthly_prorata(self, store):
        """30 jours, assiette 1200 EUR/an → assiette effective ≈ 98,63 EUR."""
        r = compute_cta(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=1200.0,
            period_days=30,
            at_date=date(2026, 3, 15),
        )
        expected_assiette = 1200.0 * 30 / 365
        assert r.assiette_fixe == pytest.approx(expected_assiette, abs=1e-4)
        assert r.amount_ht == pytest.approx(expected_assiette * _GAZ_EFFECTIVE_RATE_2025, abs=1e-4)

    def test_cta_gaz_coef_2024_different_from_2025(self, store):
        """Le coefficient transport change au 1/07/2025 (83,57% → 83,21%)."""
        r_2024 = compute_cta(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=1000.0,
            period_days=365,
            at_date=date(2024, 10, 1),
        )
        r_2025 = compute_cta(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=1000.0,
            period_days=365,
            at_date=date(2025, 10, 1),
        )
        # 2024 : 20.80% + 4.71% × 83.57% = 0.24736
        # 2025 : 20.80% + 4.71% × 83.21% = 0.24719
        assert r_2024.rate == pytest.approx(0.2080 + 0.0471 * 0.8357, abs=1e-6)
        assert r_2025.rate == pytest.approx(0.2080 + 0.0471 * 0.8321, abs=1e-6)
        assert r_2024.rate > r_2025.rate  # léger recul

    def test_cta_gaz_transport_level_uses_only_trans_rate(self, store):
        """Client raccordé transport : taux = 4.71% seul (pas de coef)."""
        r = compute_cta(
            store=store,
            energy="gaz",
            network_level="transport",
            fixed_component_annual_eur=1000.0,
            period_days=365,
            at_date=date(2025, 10, 1),
        )
        assert r.rate == pytest.approx(0.0471, abs=1e-6)
        assert r.amount_ht == pytest.approx(47.1, abs=1e-4)


# ── CTA élec césure 1/02/2026 (21,93% → 15%) ──────────────────────────────


class TestCtaElecCesure:
    def test_cta_elec_apres_fev_2026_dist(self, store):
        """CTA élec distribution = 15% depuis 1/02/2026."""
        r = compute_cta(
            store=store,
            energy="elec",
            network_level="distribution",
            fixed_component_annual_eur=500.0,
            period_days=365,
            at_date=date(2026, 4, 1),
        )
        assert r.rate == pytest.approx(0.15, abs=1e-6)
        assert r.amount_ht == pytest.approx(75.0, abs=1e-6)

    def test_cta_elec_apres_fev_2026_transport(self, store):
        """CTA élec transport ≥50kV = 5% depuis 1/02/2026."""
        r = compute_cta(
            store=store,
            energy="elec",
            network_level="transport",
            fixed_component_annual_eur=1000.0,
            period_days=365,
            at_date=date(2026, 4, 1),
        )
        assert r.rate == pytest.approx(0.05, abs=1e-6)
        assert r.amount_ht == pytest.approx(50.0, abs=1e-6)


# ── Audit trail présent ────────────────────────────────────────────────────


class TestCtaAuditTrail:
    def test_cta_carries_resolution(self, store):
        r = compute_cta(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=100.0,
            period_days=365,
            at_date=date(2026, 6, 1),
        )
        assert r.resolution.source == "yaml"
        assert r.resolution.source_ref is not None

    def test_cta_to_dict_format(self, store):
        r = compute_cta(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=100.0,
            period_days=365,
            at_date=date(2026, 6, 1),
        )
        d = r.to_dict()
        assert d["code"] == "cta"
        assert d["label"] == "CTA (gaz distribution)"
        assert d["rate"] == pytest.approx(_GAZ_EFFECTIVE_RATE_2025, abs=1e-6)
        # to_dict() arrondit à 2 décimales via round(ht, 2)
        assert d["ht"] == pytest.approx(100.0 * _GAZ_EFFECTIVE_RATE_2025, abs=1e-2)
        assert d["source"] == "yaml"
        assert d["source_ref"] is not None
        assert d["valid_from"] is not None


# ── Période bornes + découpage ────────────────────────────────────────────


class TestCtaPeriodBounds:
    def test_compute_from_period_bounds_gaz(self, store):
        r = compute_cta_from_period_bounds(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=1200.0,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 5, 1),
        )
        # ~30 jours, assiette ~98,63 EUR, taux effectif ~24,72% → ~24,38 EUR
        expected = (1200.0 * 30 / 365) * _GAZ_EFFECTIVE_RATE_2025
        assert r.amount_ht == pytest.approx(expected, abs=1e-2)

    def test_zero_period_days_defaults_to_one(self, store):
        """period_start == period_end → prorata 1 jour (pas division par 0)."""
        r = compute_cta_from_period_bounds(
            store=store,
            energy="gaz",
            network_level="distribution",
            fixed_component_annual_eur=365.0,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 1),
        )
        # 1 jour, assiette 1 EUR, taux effectif ~24,72%
        assert r.amount_ht == pytest.approx(1.0 * _GAZ_EFFECTIVE_RATE_2025, abs=1e-4)


# ── Zero / edge cases ──────────────────────────────────────────────────────


class TestCtaEdgeCases:
    def test_zero_assiette_returns_zero(self, store):
        r = compute_cta(
            store=store,
            energy="elec",
            network_level="distribution",
            fixed_component_annual_eur=0.0,
            period_days=30,
            at_date=date(2026, 4, 1),
        )
        assert r.amount_ht == 0.0
        assert r.assiette_fixe == 0.0

    def test_negative_period_days_returns_zero(self, store):
        r = compute_cta(
            store=store,
            energy="elec",
            network_level="distribution",
            fixed_component_annual_eur=500.0,
            period_days=-5,
            at_date=date(2026, 4, 1),
        )
        assert r.amount_ht == 0.0
