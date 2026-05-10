"""
PROMEOS — Tests ParameterStore (billing refactor V112)

Vérifie le versioning temporel des paramètres réglementés :
- TURPE 6 → TURPE 7 césure 1/02/2025 (mouvement tarifaire EXCEPTIONNEL CRE 2025-78,
  pas le calendrier annuel 1/08 habituel — cf. AUDIT_TURPE7_DATES_2026_05_07.md
  + Phase L33.4 doctrine SoT alignment).
- Accise gaz 3 périodes (jan-jul 2025, aout 2025, fev 2026+)
- TVA réduite 5,5% supprimée au 1/08/2025 (LFI 2025)
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


# ── TURPE césure 1/02/2025 (TURPE 6 → TURPE 7) ────────────────────────────
# Phase L33.4 doctrine SoT alignment : la césure TURPE n'est PAS au calendrier
# annuel habituel (1/08), mais au 1/02/2025 par DÉROGATION CRE délibération
# 2025-78 — mouvement tarifaire EXCEPTIONNEL annoncé par communiqué CRE
# 12/12/2024. Phase L34.1 met les tests en cohérence avec YAML+catalog+doctrine.


class TestTurpeTemporalCesure:
    def test_turpe6_c5_bt_before_cesure(self, store):
        """Janvier 2025 → TURPE 6 C5 BT = 0.0282 EUR/kWh (régime ancien)."""
        r = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 1, 5))
        assert r.source == "yaml"
        assert r.value == pytest.approx(0.0282, abs=1e-6)
        assert r.valid_from == date(2021, 8, 1)
        assert r.valid_to == date(2025, 1, 31)

    def test_turpe7_c5_bt_after_cesure(self, store):
        """Octobre 2025 → TURPE 7 C5 BT = 0.0453 EUR/kWh (post-bascule 1/02/2025)."""
        r = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 10, 1))
        assert r.source == "yaml"
        assert r.value == pytest.approx(0.0453, abs=1e-6)
        assert r.valid_from == date(2025, 2, 1)

    def test_turpe_exactly_at_cesure(self, store):
        """1/02/2025 exactement → TURPE 7 (nouvelle grille inclusive)."""
        r = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 2, 1))
        assert r.value == pytest.approx(0.0453, abs=1e-6)
        assert r.valid_from == date(2025, 2, 1)

    def test_turpe6_c4_bt_before_cesure(self, store):
        r = store.get("TURPE_ENERGIE_C4_BT", at_date=date(2025, 1, 5))
        assert r.value == pytest.approx(0.0313, abs=1e-6)

    def test_turpe7_c4_bt_after_cesure(self, store):
        r = store.get("TURPE_ENERGIE_C4_BT", at_date=date(2026, 1, 1))
        assert r.value == pytest.approx(0.0390, abs=1e-6)

    def test_turpe_gestion_tracks_cesure(self, store):
        before = store.get("TURPE_GESTION_C5_BT", at_date=date(2025, 1, 5))
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
        assert trace["valid_from"] == "2025-02-01"
        assert isinstance(trace["value"], float)

    def test_cesure_invoice_spans_two_regimes(self, store):
        """
        Cas canonique : facture du 15/01/2025 au 15/02/2025 traversant la
        césure TURPE 6 → TURPE 7 du 1/02/2025. Le moteur doit savoir qu'il
        existe DEUX valeurs applicables sur la période (à prorater au découpage
        temporel côté compute_slice, pas ici).
        """
        mid_jan = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 1, 15))
        mid_feb = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 2, 15))
        assert mid_jan.value != mid_feb.value
        assert mid_jan.valid_from == date(2021, 8, 1)
        assert mid_feb.valid_from == date(2025, 2, 1)


# ── Césures multiples 2025 — Phase L34.1 doctrine SoT alignment ──────────
# Phase L33.4 a corrigé YAML+catalog+doctrine pour refléter la réalité
# réglementaire : la césure TURPE 6→7 est au 1/02/2025 (mouvement EXCEPTIONNEL
# CRE 2025-78), pas au 1/08/2025. Les deux censures restent distinctes :
#   - 1/02/2025 : TURPE 6 → TURPE 7 (CRE 2025-78)
#   - 1/08/2025 : TVA réduite 5,5% → 20% (LFI 2025) + accise gaz baisse post-bouclier
# L'ATRD7 gaz reste stable (révision annuelle 1/07).


class TestCesureTurpe1Fev2025:
    """Césure SOLO TURPE 6 → TURPE 7 au 1/02/2025 (mouvement exceptionnel)."""

    def test_turpe_cesure_before(self, store):
        """31/01/2025 : dernier jour TURPE 6."""
        turpe = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 1, 31))
        assert turpe.source == "yaml"
        assert turpe.value == pytest.approx(0.0282)  # TURPE 6
        assert turpe.valid_from == date(2021, 8, 1)
        assert turpe.valid_to == date(2025, 1, 31)

    def test_turpe_cesure_at(self, store):
        """1/02/2025 : bascule TURPE 7."""
        turpe = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 2, 1))
        assert turpe.value == pytest.approx(0.0453)  # TURPE 7
        assert turpe.valid_from == date(2025, 2, 1)

    def test_turpe_cesure_after(self, store):
        """15/02/2025 : régime TURPE 7 confirmé mi-mois."""
        turpe = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 2, 15))
        assert turpe.valid_from == date(2025, 2, 1)
        assert turpe.value == pytest.approx(0.0453)


class TestCesureDouble1Aout2025:
    """Césure DOUBLE TVA 5,5%→20% + accise gaz au 1/08/2025 (LFI 2025)."""

    def test_double_cesure_before(self, store):
        """31/07/2025 : TVA réduite 5,5% encore + accise gaz "2025_jan"."""
        d = date(2025, 7, 31)
        tva_red = store.get("TVA_REDUITE", at_date=d)
        accise_gaz = store.get("ACCISE_GAZ", at_date=d)

        assert tva_red.value == pytest.approx(0.055)
        assert accise_gaz.valid_from == date(2025, 1, 1)

    def test_double_cesure_at(self, store):
        """1/08/2025 : bascule simultanée TVA→20% + accise gaz nouvelle période."""
        d = date(2025, 8, 1)
        tva_red = store.get("TVA_REDUITE", at_date=d)
        accise_gaz = store.get("ACCISE_GAZ", at_date=d)

        # TVA réduite supprimée → pointe désormais sur le taux normal 20%
        assert tva_red.value == pytest.approx(0.20)
        assert tva_red.valid_from == date(2025, 8, 1)
        # Accise gaz nouvelle période
        assert accise_gaz.valid_from == date(2025, 8, 1)

    def test_double_cesure_after(self, store):
        """15/08/2025 : régime nouveau confirmé mi-mois."""
        d = date(2025, 8, 15)
        tva_red = store.get("TVA_REDUITE", at_date=d)
        accise_gaz = store.get("ACCISE_GAZ", at_date=d)

        assert tva_red.value == pytest.approx(0.20)
        assert accise_gaz.valid_from == date(2025, 8, 1)

    def test_turpe_unchanged_at_aout_cesure(self, store):
        """Le TURPE ne bouge PAS au 1/08/2025 (sa césure était au 1/02/2025)."""
        before = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 7, 31))
        at = store.get("TURPE_ENERGIE_C5_BT", at_date=date(2025, 8, 1))
        # Même grille TURPE 7 — pas de changement à la double césure TVA/accise
        assert before.value == at.value == pytest.approx(0.0453)
        assert before.valid_from == at.valid_from == date(2025, 2, 1)

    def test_atrd7_gaz_stable_across_double_cesure(self, store):
        """
        L'ATRD7 gaz ne change PAS à la césure du 1/08/2025 (TVA/accise).
        Note : la révision annuelle ATRD7 est au 1/07/2025 — une césure
        distincte (cf. TestAtrdRevision2025).
        """
        before = store.get("ATRD_GAZ_T2_ABO", at_date=date(2025, 7, 31))
        at = store.get("ATRD_GAZ_T2_ABO", at_date=date(2025, 8, 1))
        after = store.get("ATRD_GAZ_T2_ABO", at_date=date(2025, 8, 15))
        # Les 3 dates sont post-révision ATRD7 2025 → même valeur 186.12
        assert before.value == at.value == after.value == pytest.approx(186.12)
        assert before.valid_from == date(2025, 7, 1)

    def test_invoice_spanning_double_cesure(self, store):
        """
        Facture 15/07/2025 → 15/08/2025 : l'appelant doit obtenir 2 valeurs
        distinctes pour TVA + accise gaz (TURPE inchangé sur la période car
        sa propre césure date du 1/02/2025).
        """
        d_jul = date(2025, 7, 15)
        d_aug = date(2025, 8, 15)

        # TVA réduite
        assert store.get("TVA_REDUITE", at_date=d_jul).value == pytest.approx(0.055)
        assert store.get("TVA_REDUITE", at_date=d_aug).value == pytest.approx(0.20)
        # Accise gaz
        assert store.get("ACCISE_GAZ", at_date=d_jul).valid_from == date(2025, 1, 1)
        assert store.get("ACCISE_GAZ", at_date=d_aug).valid_from == date(2025, 8, 1)
        # TURPE INCHANGÉ sur cette période (TURPE 7 actif depuis 1/02/2025)
        assert (
            store.get("TURPE_ENERGIE_C5_BT", at_date=d_jul).valid_from
            == store.get("TURPE_ENERGIE_C5_BT", at_date=d_aug).valid_from
            == date(2025, 2, 1)
        )
