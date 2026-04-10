"""
PROMEOS — Tests ParameterStore (billing refactor V112)

Vérifie le versioning temporel des paramètres réglementés :
- TURPE 6 → TURPE 7 césure 1/08/2025
- Accise gaz 3 périodes (jan-jul 2025, aout 2025, fev 2026+)
- TVA réduite supprimée au 1/08/2025
- CTA élec / gaz
- Codes inconnus = missing + warning (pas de hardcode silencieux)
"""

from datetime import date

import pytest

from services.billing_engine.parameter_store import (
    KNOWN_CODES,
    ParameterResolution,
    ParameterStore,
    default_store,
    reload_yaml_cache,
)


@pytest.fixture(autouse=True)
def _reset_yaml_cache():
    """Reload YAML cache avant chaque test pour isoler."""
    reload_yaml_cache()
    yield
    reload_yaml_cache()


@pytest.fixture
def store():
    return ParameterStore(db=None)


# ── TURPE césure 1/08/2025 (TURPE 6 → TURPE 7) ────────────────────────────


class TestTurpeTemporalCesure:
    def test_turpe6_c5_bt_before_cesure(self, store):
        """Juin 2025 → TURPE 6 C5 BT = 0.0282 EUR/kWh."""
        r = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 6, 1))
        assert r.source == "yaml"
        assert r.value == pytest.approx(0.0282, abs=1e-6)
        assert r.valid_from == date(2021, 8, 1)
        assert r.valid_to == date(2025, 7, 31)

    def test_turpe7_c5_bt_after_cesure(self, store):
        """Octobre 2025 → TURPE 7 C5 BT = 0.0453 EUR/kWh."""
        r = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 10, 1))
        assert r.source == "yaml"
        assert r.value == pytest.approx(0.0453, abs=1e-6)
        assert r.valid_from == date(2025, 8, 1)

    def test_turpe_exactly_at_cesure(self, store):
        """1/08/2025 exactement → TURPE 7 (nouvelle grille inclusive)."""
        r = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 8, 1))
        assert r.value == pytest.approx(0.0453, abs=1e-6)
        assert r.valid_from == date(2025, 8, 1)

    def test_turpe6_c4_bt_before_cesure(self, store):
        r = store.get("TURPE_ENERGIE_C4_BT", at_date=date(2025, 6, 1))
        assert r.value == pytest.approx(0.0313, abs=1e-6)

    def test_turpe7_c4_bt_after_cesure(self, store):
        r = store.get("TURPE_ENERGIE_C4_BT", at_date=date(2026, 1, 1))
        assert r.value == pytest.approx(0.0390, abs=1e-6)

    def test_turpe_gestion_tracks_cesure(self, store):
        before = store.get("TURPE_GESTION_C5_BT", at_date=date(2025, 6, 1))
        after = store.get("TURPE_GESTION_C5_BT", at_date=date(2025, 10, 1))
        assert before.value == pytest.approx(2.14, abs=1e-6)
        assert after.value == pytest.approx(18.48, abs=1e-6)


# ── Accise gaz : 3 périodes successives ───────────────────────────────────


class TestAcciseGazMultiPeriod:
    def test_accise_gaz_jan_jul_2025(self, store):
        """Jan-jul 2025 : 16.37 EUR/MWh (hérité 2024)."""
        r = store.get("ACCISE_GAZ", at_date=date(2025, 3, 15))
        assert r.value == pytest.approx(0.01637, abs=1e-6)
        assert r.valid_from == date(2025, 1, 1)

    def test_accise_gaz_aout_2025(self, store):
        """Aout 2025 → jan 2026 : 10.54 EUR/MWh (baisse post-bouclier)."""
        r = store.get("ACCISE_GAZ", at_date=date(2025, 11, 1))
        assert r.value == pytest.approx(0.01054, abs=1e-6)
        assert r.valid_from == date(2025, 8, 1)

    def test_accise_gaz_fev_2026(self, store):
        """Fev 2026+ : 10.73 EUR/MWh (indexation inflation)."""
        r = store.get("ACCISE_GAZ", at_date=date(2026, 4, 1))
        assert r.value == pytest.approx(0.01073, abs=1e-6)
        assert r.valid_from == date(2026, 2, 1)

    def test_accise_gaz_at_cesure_1_aout_2025(self, store):
        """Exactement 1/08/2025 → nouvelle grille 10.54."""
        r = store.get("ACCISE_GAZ", at_date=date(2025, 8, 1))
        assert r.value == pytest.approx(0.01054, abs=1e-6)

    def test_accise_gaz_at_cesure_1_fev_2026(self, store):
        """Exactement 1/02/2026 → nouvelle grille 10.73."""
        r = store.get("ACCISE_GAZ", at_date=date(2026, 2, 1))
        assert r.value == pytest.approx(0.01073, abs=1e-6)


# ── TVA réduite supprimée 1/08/2025 ───────────────────────────────────────


class TestTvaReduiteSuppression:
    def test_tva_reduite_before_suppression(self, store):
        r = store.get("TVA_REDUITE", at_date=date(2025, 6, 1))
        assert r.value == pytest.approx(0.055, abs=1e-6)
        assert r.valid_to == date(2025, 7, 31)

    def test_tva_reduite_at_suppression(self, store):
        """1/08/2025 : TVA réduite = TVA normale (20%)."""
        r = store.get("TVA_REDUITE", at_date=date(2025, 8, 1))
        assert r.value == pytest.approx(0.20, abs=1e-6)
        assert r.valid_from == date(2025, 8, 1)

    def test_tva_reduite_after_suppression(self, store):
        r = store.get("TVA_REDUITE", at_date=date(2026, 3, 15))
        assert r.value == pytest.approx(0.20, abs=1e-6)

    def test_tva_normale_unchanged_by_suppression(self, store):
        for d in [date(2024, 1, 1), date(2025, 8, 1), date(2026, 6, 1)]:
            r = store.get("TVA_NORMALE", at_date=d)
            assert r.value == pytest.approx(0.20, abs=1e-6)


# ── CTA : élec vs gaz ─────────────────────────────────────────────────────


class TestCta:
    def test_cta_gaz_distribution(self, store):
        """CTA gaz distribution = 20.80% (2025+)."""
        r = store.get("CTA_GAZ_DIST_RATE", at_date=date(2026, 1, 1))
        assert r.value == pytest.approx(0.208, abs=1e-6)

    def test_cta_elec_distribution_fev_2026(self, store):
        """CTA élec distribution = 15% depuis fév 2026 (était 21.93%)."""
        r = store.get("CTA_ELEC_DIST_RATE", at_date=date(2026, 4, 1))
        assert r.value == pytest.approx(0.15, abs=1e-6)

    def test_cta_elec_transport_fev_2026(self, store):
        """CTA élec transport ≥50kV = 5% depuis fév 2026 (était 10.11%)."""
        r = store.get("CTA_ELEC_TRANS_RATE", at_date=date(2026, 4, 1))
        assert r.value == pytest.approx(0.05, abs=1e-6)

    def test_cta_elec_distribution_historical_before_2026(self, store):
        """CTA élec distribution historique = 21,93% entre 1/08/2021 et 31/01/2026."""
        for d in [date(2021, 8, 1), date(2023, 6, 15), date(2025, 12, 1), date(2026, 1, 31)]:
            r = store.get("CTA_ELEC_DIST_RATE", at_date=d)
            assert r.value == pytest.approx(0.2193, abs=1e-6), f"failed at {d}"
            assert r.source == "yaml"
            assert r.valid_from == date(2021, 8, 1)
            assert r.valid_to == date(2026, 1, 31)

    def test_cta_elec_transport_historical_before_2026(self, store):
        """CTA élec transport ≥50kV historique = 10,11% entre 1/08/2021 et 31/01/2026."""
        r = store.get("CTA_ELEC_TRANS_RATE", at_date=date(2025, 6, 15))
        assert r.value == pytest.approx(0.1011, abs=1e-6)
        assert r.valid_from == date(2021, 8, 1)
        assert r.valid_to == date(2026, 1, 31)

    def test_cta_elec_cesure_1_fev_2026(self, store):
        """Césure exacte : 31/01/2026 → 21,93%, 1/02/2026 → 15%."""
        r_before = store.get("CTA_ELEC_DIST_RATE", at_date=date(2026, 1, 31))
        r_after = store.get("CTA_ELEC_DIST_RATE", at_date=date(2026, 2, 1))
        assert r_before.value == pytest.approx(0.2193, abs=1e-6)
        assert r_after.value == pytest.approx(0.15, abs=1e-6)
        assert r_before.valid_to == date(2026, 1, 31)
        assert r_after.valid_from == date(2026, 2, 1)


# ── Codes inconnus + missing ──────────────────────────────────────────────


class TestMissingAndUnknown:
    def test_unknown_code_returns_missing(self, store, caplog):
        r = store.get("FOO_BAR_UNKNOWN", at_date=date(2026, 1, 1))
        assert r.source == "missing"
        assert r.value == 0.0
        assert "code inconnu" in caplog.text or "aucune valeur" in caplog.text

    def test_get_value_with_default_on_missing(self, store):
        v = store.get_value("FOO_BAR_UNKNOWN", at_date=date(2026, 1, 1), default=9.99)
        assert v == 9.99

    def test_known_codes_set_is_complete(self):
        """Sanity check : tous les codes critiques sont listés."""
        required = {
            "TURPE_ENERGIE_C5_BT",
            "ACCISE_ELEC",
            "ACCISE_GAZ",
            "TVA_NORMALE",
            "TVA_REDUITE",
            "CTA_ELEC_DIST_RATE",
            "CTA_GAZ_DIST_RATE",
        }
        assert required.issubset(KNOWN_CODES)


# ── Audit trail : source_ref présent ──────────────────────────────────────


class TestAuditTrail:
    def test_resolution_carries_source_ref(self, store):
        r = store.get("ACCISE_GAZ", at_date=date(2025, 8, 15))
        assert r.source_ref is not None
        assert "EUR/MWh" in r.source_ref or "10.54" in r.source_ref

    def test_to_trace_serializable(self, store):
        r = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 10, 1))
        trace = r.to_trace()
        assert trace["code"] == "TURPE_ENERGIE_C5_BT"
        assert trace["source"] == "yaml"
        assert trace["valid_from"] == "2025-08-01"
        assert isinstance(trace["value"], float)

    def test_cesure_invoice_spans_two_regimes(self, store):
        """
        Cas canonique : facture du 15/07/2025 au 15/08/2025 traversant la
        double césure TURPE + TVA + accise gaz. Le moteur doit savoir qu'il
        existe DEUX valeurs applicables sur la période (à prorater au découpage
        temporel côté compute_slice, pas ici).
        """
        mid_jul = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 7, 15))
        mid_aug = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 8, 15))
        assert mid_jul.value != mid_aug.value
        assert mid_jul.valid_from == date(2021, 8, 1)
        assert mid_aug.valid_from == date(2025, 8, 1)


# ── Césure triple 1/08/2025 — Vague 2 ────────────────────────────────────
# Vérifie qu'une seule date (1/08/2025) déclenche simultanément :
#   1. TURPE 6 → TURPE 7
#   2. TVA réduite 5,5% → TVA normale 20% sur abonnement/CTA
#   3. Accise gaz 2025_jan → accise gaz 2025_aout (suppression bouclier)
# Sans oublier que l'ATRD7 gaz reste stable (valid_from 2024-07-01).


class TestCesureTriple1Aout2025:
    def test_triple_cesure_before(self, store):
        """31/07/2025 : dernier jour du régime ancien (TURPE 6 + TVA 5,5% + accise gaz jan 2025)."""
        d = date(2025, 7, 31)
        turpe = store.get("TURPE_ENERGIE_C5_BT", at_date=d)
        tva_red = store.get("TVA_REDUITE", at_date=d)
        accise_gaz = store.get("ACCISE_GAZ", at_date=d)

        assert turpe.source == "yaml"
        assert turpe.valid_from == date(2021, 8, 1)  # TURPE 6
        assert tva_red.value == pytest.approx(0.055)  # TVA réduite encore en vigueur
        assert accise_gaz.valid_from == date(2025, 1, 1)  # accise gaz "2025_jan"

    def test_triple_cesure_at(self, store):
        """1/08/2025 : jour de bascule — les 3 nouveaux régimes prennent effet."""
        d = date(2025, 8, 1)
        turpe = store.get("TURPE_ENERGIE_C5_BT", at_date=d)
        tva_red = store.get("TVA_REDUITE", at_date=d)
        accise_gaz = store.get("ACCISE_GAZ", at_date=d)

        assert turpe.valid_from == date(2025, 8, 1)  # TURPE 7
        # TVA réduite supprimée → pointe désormais sur le taux normal 20%
        assert tva_red.value == pytest.approx(0.20)
        assert tva_red.valid_from == date(2025, 8, 1)
        # Accise gaz nouvelle période
        assert accise_gaz.valid_from == date(2025, 8, 1)

    def test_triple_cesure_after(self, store):
        """15/08/2025 : régime nouveau confirmé mi-mois."""
        d = date(2025, 8, 15)
        turpe = store.get("TURPE_ENERGIE_C5_BT", at_date=d)
        tva_red = store.get("TVA_REDUITE", at_date=d)
        accise_gaz = store.get("ACCISE_GAZ", at_date=d)

        assert turpe.valid_from == date(2025, 8, 1)
        assert tva_red.value == pytest.approx(0.20)
        assert accise_gaz.valid_from == date(2025, 8, 1)

    def test_atrd7_gaz_stable_across_cesure(self, store):
        """L'ATRD7 gaz (1/07/2024) ne change PAS à la césure du 1/08/2025."""
        before = store.get("ATRD_GAZ_T2_ABO", at_date=date(2025, 7, 31))
        at = store.get("ATRD_GAZ_T2_ABO", at_date=date(2025, 8, 1))
        after = store.get("ATRD_GAZ_T2_ABO", at_date=date(2025, 8, 15))
        assert before.value == at.value == after.value == pytest.approx(177.78)
        assert before.valid_from == date(2024, 7, 1)

    def test_invoice_spanning_triple_cesure(self, store):
        """
        Facture 15/07/2025 → 15/08/2025 : l'appelant doit obtenir 2 valeurs
        distinctes pour chacun des 3 mécanismes simultanément.
        """
        d_jul = date(2025, 7, 15)
        d_aug = date(2025, 8, 15)

        # TURPE
        assert (
            store.get("TURPE_ENERGIE_C5_BT", at_date=d_jul).value
            != store.get("TURPE_ENERGIE_C5_BT", at_date=d_aug).value
        )
        # TVA réduite
        assert store.get("TVA_REDUITE", at_date=d_jul).value == pytest.approx(0.055)
        assert store.get("TVA_REDUITE", at_date=d_aug).value == pytest.approx(0.20)
        # Accise gaz
        assert store.get("ACCISE_GAZ", at_date=d_jul).valid_from == date(2025, 1, 1)
        assert store.get("ACCISE_GAZ", at_date=d_aug).valid_from == date(2025, 8, 1)
