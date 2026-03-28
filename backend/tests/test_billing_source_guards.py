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

    def test_no_cta_15_percent(self):
        """CTA ne doit jamais être 15% — valeur erronée."""
        from services.billing_engine import catalog

        source = inspect.getsource(catalog)
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if "CTA" in line.upper() and "15.00" in line and "#" not in line.split("15.00")[0]:
                pytest.fail(f"CTA 15% trouvé ligne {i + 1}: {line.strip()}")

    def test_cta_2026_is_27_04(self):
        """CTA post-2026 doit être 27.04%."""
        from services.billing_engine.catalog import get_rate

        cta = get_rate("CTA_ELEC", date(2026, 3, 1))
        assert cta == pytest.approx(27.04, abs=0.01)

    def test_cta_pre_2026_is_21_93(self):
        """CTA pré-2026 doit être 21.93%."""
        from services.billing_engine.catalog import get_rate

        cta = get_rate("CTA_ELEC", date(2025, 6, 1))
        assert cta == pytest.approx(21.93, abs=0.01)

    def test_cta_switch_at_jan_2026(self):
        """CTA bascule au 1er janvier 2026 (pas février)."""
        from services.billing_engine.catalog import get_rate

        cta_dec = get_rate("CTA_ELEC", date(2025, 12, 31))
        cta_jan = get_rate("CTA_ELEC", date(2026, 1, 1))
        assert cta_dec == pytest.approx(21.93, abs=0.01)
        assert cta_jan == pytest.approx(27.04, abs=0.01)

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

    def test_yaml_cta_is_27_04(self):
        """Le YAML CTA doit être 27.04%."""
        from config.tarif_loader import reload_tarifs, get_cta_taux

        reload_tarifs()
        assert get_cta_taux("elec") == pytest.approx(27.04, abs=0.01)

    def test_yaml_cspe_is_02658(self):
        """Le YAML accise elec doit être 0.02658."""
        from config.tarif_loader import reload_tarifs, get_accise_kwh

        reload_tarifs()
        assert get_accise_kwh("elec") == pytest.approx(0.02658, abs=0.001)

    def test_co2_elec_is_0052(self):
        """CO₂ élec = 0.052 kgCO₂/kWh (ADEME V23.6)."""
        from config.emission_factors import EMISSION_FACTORS

        assert EMISSION_FACTORS["ELEC"]["kgco2e_per_kwh"] == 0.052
