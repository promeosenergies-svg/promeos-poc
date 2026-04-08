"""
Source guards — constantes réglementaires billing.
Empêche toute régression sur les valeurs canoniques.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import inspect
from datetime import date


class TestCatalogSourceGuards:
    """Vérifie que le catalog n'a pas de valeurs obsolètes."""

    def test_cta_2026_is_15(self):
        """CTA distribution post-fév 2026 = 15% (CRE 2026-14, arrêté JORF 28/01/2026)."""
        from services.billing_engine.catalog import get_rate

        cta = get_rate("CTA_ELEC", date(2026, 3, 1))
        assert cta == pytest.approx(15.0, abs=0.01)

    def test_cta_transport_2026_is_5(self):
        """CTA transport ≥50kV post-fév 2026 = 5% (CRE 2026-14)."""
        from services.billing_engine.catalog import get_rate

        cta = get_rate("CTA_ELEC_TRANSPORT", date(2026, 3, 1))
        assert cta == pytest.approx(5.0, abs=0.01)

    def test_cta_pre_2026_is_21_93(self):
        """CTA distribution pré-fév 2026 = 21.93%."""
        from services.billing_engine.catalog import get_rate

        cta = get_rate("CTA_ELEC", date(2025, 6, 1))
        assert cta == pytest.approx(21.93, abs=0.01)

    def test_cta_switch_at_feb_2026(self):
        """CTA bascule au 1er février 2026 (arrêté CTA, CRE 2026-14)."""
        from services.billing_engine.catalog import get_rate

        cta_jan = get_rate("CTA_ELEC", date(2026, 1, 31))
        cta_feb = get_rate("CTA_ELEC", date(2026, 2, 1))
        assert cta_jan == pytest.approx(21.93, abs=0.01)
        assert cta_feb == pytest.approx(15.0, abs=0.01)

    def test_tva_suppression_post_aug_2025(self):
        """TVA 5.5% supprimée post-août 2025 sur TURPE fixe."""
        from services.billing_engine.catalog import get_tva_rate_for

        tva_pre = get_tva_rate_for("TURPE_GESTION_C4", date(2025, 7, 1))
        tva_post = get_tva_rate_for("TURPE_GESTION_C4", date(2025, 9, 1))
        assert tva_pre == pytest.approx(0.055, abs=0.001)
        assert tva_post == pytest.approx(0.20, abs=0.001)


class TestSeedSourceGuards:
    """Vérifie que le seed n'a pas de valeurs hardcodées obsolètes."""

    def test_no_hardcoded_0045_network(self):
        """Le réseau 0.045 EUR/kWh ne doit plus être dans le seed."""
        from services import billing_seed

        source = inspect.getsource(billing_seed)
        # 0.045 comme multiplicateur réseau = ancien taux approximatif
        occurrences = source.count("* 0.045")
        assert occurrences == 0, f"0.045 network rate trouvé {occurrences} fois dans billing_seed"

    def test_no_hardcoded_00225_taxes(self):
        """Le taxes 0.0225 EUR/kWh ne doit plus être dans le seed."""
        from services import billing_seed

        source = inspect.getsource(billing_seed)
        occurrences = source.count("* 0.0225")
        assert occurrences == 0, f"0.0225 tax rate trouvé {occurrences} fois dans billing_seed"


class TestShadowBillingSourceGuards:
    """Vérifie les constantes shadow billing."""

    def test_yaml_cta_is_15(self):
        """Le YAML CTA distribution doit être 15% (CRE 2026-14)."""
        from config.tarif_loader import reload_tarifs, get_cta_taux

        reload_tarifs()
        assert get_cta_taux("elec") == pytest.approx(15.0, abs=0.01)

    def test_yaml_cspe_is_02658(self):
        """Le YAML accise elec doit être 0.02658."""
        from config.tarif_loader import reload_tarifs, get_accise_kwh

        reload_tarifs()
        assert get_accise_kwh("elec") == pytest.approx(0.02658, abs=0.001)

    def test_co2_elec_is_0052(self):
        """CO₂ élec = 0.052 kgCO₂/kWh (ADEME V23.6)."""
        from config.emission_factors import EMISSION_FACTORS

        assert EMISSION_FACTORS["ELEC"]["kgco2e_per_kwh"] == 0.052
