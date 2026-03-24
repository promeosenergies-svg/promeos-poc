"""
PROMEOS — Tests billing_engine/catalog.py (Sprint QA S)
Couvre :
  - Structure des taux TURPE 7 C4/C5
  - Résolution temporelle TICGN, ACCISE, CTA
  - get_rate() et get_rate_source()
  - Taux vérifiés contre les sources officielles documentées dans le catalog

Sources de vérité :
  TURPE 7 : CRE délibération n°2025-78 (13/03/2025), en vigueur 01/08/2025
  TICGN : Arrêtés Légifrance (voir source dans chaque entrée catalog)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date

from services.billing_engine.catalog import (
    TURPE7_RATES,
    get_rate,
    get_rate_source,
    _resolve_temporal_code,
)


class TestCatalogStructure:
    """Vérifie que les entrées clés existent et ont les champs obligatoires."""

    REQUIRED_KEYS = [
        "TURPE_GESTION_C4",
        "TURPE_GESTION_C5",
        "TURPE_COMPTAGE_C4",
        "TURPE_COMPTAGE_C5",
        "TICGN_2024",
        "TICGN_AOUT2025",
        "TICGN_FEV2026",
    ]

    @pytest.mark.parametrize("key", REQUIRED_KEYS)
    def test_key_exists(self, key):
        assert key in TURPE7_RATES, f"Clé manquante dans le catalogue : {key}"

    @pytest.mark.parametrize("key", REQUIRED_KEYS)
    def test_entry_has_required_fields(self, key):
        entry = TURPE7_RATES[key]
        assert "rate" in entry, f"{key} manque le champ 'rate'"
        assert "unit" in entry, f"{key} manque le champ 'unit'"
        assert "source" in entry, f"{key} manque le champ 'source'"
        assert isinstance(entry["rate"], (int, float)), f"{key}.rate doit être numérique"
        assert entry["rate"] > 0, f"{key}.rate doit être > 0"


class TestTurpe7Rates:
    """Vérifie les taux TURPE 7 contre les valeurs CRE officielles."""

    def test_gestion_c4_rate(self):
        """CRE n°2025-78 p.13 : composante gestion C4 = 217.80 EUR/an."""
        assert get_rate("TURPE_GESTION_C4") == 217.80

    def test_gestion_c5_rate(self):
        """CRE n°2025-78 p.16 : composante gestion C5 = 16.80 EUR/an."""
        assert get_rate("TURPE_GESTION_C5") == 16.80

    def test_gestion_c4_tva_reduite(self):
        """Gestion soumise à TVA réduite 5.5%."""
        assert TURPE7_RATES["TURPE_GESTION_C4"]["tva_rate"] == 0.055

    def test_gestion_c5_tva_reduite(self):
        assert TURPE7_RATES["TURPE_GESTION_C5"]["tva_rate"] == 0.055


class TestTicgnTemporalResolution:
    """Vérifie la résolution temporelle TICGN (3 périodes)."""

    def test_ticgn_before_aug2025(self):
        """Avant août 2025 → TICGN_2024 = 0.01637 EUR/kWh."""
        assert _resolve_temporal_code("TICGN", date(2025, 3, 15)) == "TICGN_2024"
        assert get_rate("TICGN", date(2025, 3, 15)) == 0.01637

    def test_ticgn_aug2025_to_jan2026(self):
        """Août 2025 → jan 2026 → TICGN_AOUT2025 = 0.01054 EUR/kWh."""
        assert _resolve_temporal_code("TICGN", date(2025, 9, 1)) == "TICGN_AOUT2025"
        assert get_rate("TICGN", date(2025, 9, 1)) == 0.01054

    def test_ticgn_from_feb2026(self):
        """Février 2026+ → TICGN_FEV2026 = 0.01073 EUR/kWh."""
        assert _resolve_temporal_code("TICGN", date(2026, 3, 1)) == "TICGN_FEV2026"
        assert get_rate("TICGN", date(2026, 3, 1)) == 0.01073

    def test_ticgn_boundary_aug2025(self):
        """Exactement le 1er août 2025 → TICGN_AOUT2025."""
        assert _resolve_temporal_code("TICGN", date(2025, 8, 1)) == "TICGN_AOUT2025"

    def test_ticgn_boundary_feb2026(self):
        """Exactement le 1er février 2026 → TICGN_FEV2026."""
        assert _resolve_temporal_code("TICGN", date(2026, 2, 1)) == "TICGN_FEV2026"


class TestAcciseResolution:
    """Vérifie la résolution temporelle ACCISE ELEC."""

    def test_accise_before_feb2024(self):
        """Avant fév 2024 (bouclier) → ACCISE_ELEC_2023."""
        assert _resolve_temporal_code("ACCISE_ELEC", date(2023, 12, 1)) == "ACCISE_ELEC_2023"

    def test_accise_feb2024_to_dec2024(self):
        """Fév 2024 → déc 2024 → ACCISE_ELEC_2024."""
        assert _resolve_temporal_code("ACCISE_ELEC", date(2024, 6, 1)) == "ACCISE_ELEC_2024"

    def test_accise_aug2025(self):
        """Août 2025 → ACCISE_ELEC_AOUT2025."""
        assert _resolve_temporal_code("ACCISE_ELEC", date(2025, 10, 1)) == "ACCISE_ELEC_AOUT2025"

    def test_accise_feb2026(self):
        """Février 2026+ → ACCISE_ELEC_FEV2026."""
        assert _resolve_temporal_code("ACCISE_ELEC", date(2026, 3, 1)) == "ACCISE_ELEC_FEV2026"


class TestGetRateErrors:
    """Vérifie le comportement sur codes inconnus."""

    def test_unknown_code_raises_keyerror(self):
        with pytest.raises(KeyError, match="not found"):
            get_rate("INEXISTANT_CODE")

    def test_get_rate_source_returns_ratesource(self):
        source = get_rate_source("TURPE_GESTION_C4")
        assert source.rate == 217.80
        assert "CRE" in source.source

    def test_no_date_returns_base_code(self):
        """Sans date, _resolve_temporal_code retourne le code tel quel."""
        assert _resolve_temporal_code("TICGN", None) == "TICGN"
