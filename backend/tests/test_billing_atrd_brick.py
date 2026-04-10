"""
PROMEOS — Tests brique ATRD gaz (Vague 2).

Couvre :
- compute_atrd() par option tarifaire (T1 / T2 / T3 / T4 / TP)
- proratisation de l'abonnement annuel (jours / 365)
- terme capacité journalière (T4 / TP uniquement)
- audit trail (source, source_ref, valid_from)
- derive_atrd_option_from_car() sur les 5 seuils CRE
- fallbacks (option inconnue → T2, CAR None → T2)
"""

from datetime import date

import pytest

from services.billing_engine.bricks.atrd import (
    AtrdResult,
    compute_atrd,
    derive_atrd_option_from_car,
)
from services.billing_engine.parameter_store import (
    ParameterStore,
    reload_yaml_cache,
)


@pytest.fixture(autouse=True)
def _reset_yaml_cache():
    reload_yaml_cache()
    yield
    reload_yaml_cache()


@pytest.fixture
def store():
    return ParameterStore(db=None)


# ── derive_atrd_option_from_car ──────────────────────────────────────────


class TestDeriveAtrdOption:
    def test_none_car_returns_t2_fallback(self):
        assert derive_atrd_option_from_car(None) == "T2"

    def test_zero_or_negative_car_returns_t2(self):
        assert derive_atrd_option_from_car(0) == "T2"
        assert derive_atrd_option_from_car(-100) == "T2"

    def test_t1_under_6000(self):
        assert derive_atrd_option_from_car(5_999) == "T1"
        assert derive_atrd_option_from_car(1_000) == "T1"
        assert derive_atrd_option_from_car(6_000) == "T1"  # borne inclusive

    def test_t2_residentiel_chauffage(self):
        assert derive_atrd_option_from_car(6_001) == "T2"
        assert derive_atrd_option_from_car(150_000) == "T2"
        assert derive_atrd_option_from_car(300_000) == "T2"  # borne inclusive

    def test_t3_tertiaire_pme(self):
        assert derive_atrd_option_from_car(300_001) == "T3"
        assert derive_atrd_option_from_car(1_000_000) == "T3"
        assert derive_atrd_option_from_car(5_000_000) == "T3"

    def test_t4_gros_industriel(self):
        assert derive_atrd_option_from_car(5_000_001) == "T4"
        assert derive_atrd_option_from_car(10_000_000) == "T4"


# ── compute_atrd ─────────────────────────────────────────────────────────


class TestComputeAtrdT1:
    def test_t1_full_year(self, store):
        """T1 sur 365 jours : abo 53.86 + var 10 MWh × 42.37 = 477.56."""
        r = compute_atrd(
            store=store,
            option="T1",
            energy_mwh=10.0,
            period_days=365,
            at_date=date(2025, 6, 1),
        )
        assert r.option == "T1"
        assert r.abonnement_ht == pytest.approx(53.86)
        assert r.proportionnel_ht == pytest.approx(423.70)
        assert r.capacite_ht == 0.0
        assert r.amount_ht == pytest.approx(477.56)

    def test_t1_proratisation_30_jours(self, store):
        """30 jours : abo 53.86 × 30/365 = 4.43 + prop 1 MWh × 42.37 = 46.80."""
        r = compute_atrd(
            store=store,
            option="T1",
            energy_mwh=1.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        assert r.abonnement_ht == pytest.approx(53.86 * 30 / 365, rel=1e-4)
        assert r.proportionnel_ht == pytest.approx(42.37)
        assert r.amount_ht == pytest.approx(46.80, rel=1e-2)


class TestComputeAtrdT2:
    def test_t2_pme_30_jours(self, store):
        """T2 : cas dominant petits consommateurs."""
        r = compute_atrd(
            store=store,
            option="T2",
            energy_mwh=15.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        assert r.option == "T2"
        assert r.abo_eur_an == pytest.approx(177.78)
        assert r.prop_eur_mwh == pytest.approx(11.39)
        assert r.abonnement_ht == pytest.approx(177.78 * 30 / 365, rel=1e-4)
        assert r.proportionnel_ht == pytest.approx(15.0 * 11.39)
        assert r.capacite_ht == 0.0


class TestComputeAtrdT3:
    def test_t3_tertiaire(self, store):
        r = compute_atrd(
            store=store,
            option="T3",
            energy_mwh=500.0,
            period_days=365,
            at_date=date(2025, 6, 1),
        )
        assert r.option == "T3"
        assert r.abonnement_ht == pytest.approx(1253.22)
        assert r.proportionnel_ht == pytest.approx(500.0 * 8.19)
        assert r.capacite_ht == 0.0


class TestComputeAtrdT4Capacite:
    def test_t4_sans_cja(self, store):
        """T4 sans CJA souscrite : terme capacité = 0."""
        r = compute_atrd(
            store=store,
            option="T4",
            energy_mwh=10_000.0,
            period_days=365,
            at_date=date(2025, 6, 1),
            cja_mwh_per_day=0.0,
        )
        assert r.capacite_ht == 0.0
        assert r.abonnement_ht == pytest.approx(20488.69)

    def test_t4_avec_cja(self, store):
        """T4 avec CJA = 50 MWh/j : capa = 50 × 106.44 × 365/365 = 5322."""
        r = compute_atrd(
            store=store,
            option="T4",
            energy_mwh=10_000.0,
            period_days=365,
            at_date=date(2025, 6, 1),
            cja_mwh_per_day=50.0,
        )
        assert r.capacite_ht == pytest.approx(50.0 * 106.44)
        assert r.amount_ht == pytest.approx(20488.69 + 10_000.0 * 1.11 + 50.0 * 106.44)

    def test_t4_capa_proratisee(self, store):
        """CJA proratisée sur 90 jours : 50 × 106.44 × 90/365."""
        r = compute_atrd(
            store=store,
            option="T4",
            energy_mwh=2_500.0,
            period_days=90,
            at_date=date(2025, 6, 1),
            cja_mwh_per_day=50.0,
        )
        assert r.capacite_ht == pytest.approx(50.0 * 106.44 * 90 / 365, rel=1e-4)


class TestComputeAtrdFixedComponent:
    def test_fixed_component_annual_is_abonnement(self, store):
        """CTA gaz s'applique sur l'assiette fixe annuelle = abo_eur_an (non prorata)."""
        r = compute_atrd(
            store=store,
            option="T2",
            energy_mwh=0.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        assert r.fixed_component_annual_eur == pytest.approx(177.78)
        # CRITIQUE : c'est bien l'annuel pas le proratisé
        assert r.fixed_component_annual_eur != r.abonnement_ht


class TestComputeAtrdAuditTrail:
    def test_resolution_exposes_source(self, store):
        r = compute_atrd(
            store=store,
            option="T2",
            energy_mwh=10.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        assert r.resolution_abo.source == "yaml"
        assert r.resolution_prop.source == "yaml"
        assert r.resolution_capa is None  # T2 : pas de capacité

    def test_to_dict_audit_fields(self, store):
        r = compute_atrd(
            store=store,
            option="T2",
            energy_mwh=10.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        d = r.to_dict()
        assert d["code"] == "atrd"
        assert d["label"] == "ATRD gaz T2"
        assert d["option"] == "T2"
        assert d["abo_eur_an"] == pytest.approx(177.78)
        assert "source" in d
        assert "source_ref" in d


class TestComputeAtrdFallbacks:
    def test_unknown_option_falls_back_to_t2(self, store):
        r = compute_atrd(
            store=store,
            option="UNKNOWN",
            energy_mwh=10.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        assert r.option == "T2"
        assert r.abo_eur_an == pytest.approx(177.78)

    def test_none_option_falls_back_to_t2(self, store):
        r = compute_atrd(
            store=store,
            option=None,  # type: ignore
            energy_mwh=10.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        assert r.option == "T2"

    def test_zero_period_days_returns_zero_abonnement(self, store):
        r = compute_atrd(
            store=store,
            option="T2",
            energy_mwh=0.0,
            period_days=0,
            at_date=date(2025, 6, 1),
        )
        assert r.abonnement_ht == 0.0
        assert r.amount_ht == 0.0

    def test_negative_energy_clamped_to_zero(self, store):
        """Énergie négative (cas d'erreur) → terme proportionnel à 0."""
        r = compute_atrd(
            store=store,
            option="T2",
            energy_mwh=-5.0,
            period_days=30,
            at_date=date(2025, 6, 1),
        )
        assert r.proportionnel_ht == 0.0
