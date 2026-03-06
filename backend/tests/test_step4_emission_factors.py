"""
PROMEOS — Step 4: Emission Factors Tests
Vérifie que les facteurs CO2 sont centralisés dans config/emission_factors.py
et que les hardcodes 0.052 ont été migrés.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from pathlib import Path
from config.emission_factors import get_emission_factor, get_emission_source, EMISSION_FACTORS


# ── A. Config values ─────────────────────────────────────────────────────────

class TestConfigValues:
    def test_elec_factor(self):
        assert get_emission_factor("ELEC") == 0.0569

    def test_gaz_factor(self):
        assert get_emission_factor("GAZ") == 0.2270

    def test_unknown_fallback_to_elec(self):
        assert get_emission_factor("EAU") == 0.0569

    def test_case_insensitive(self):
        assert get_emission_factor("elec") == get_emission_factor("ELEC")
        assert get_emission_factor("gaz") == get_emission_factor("GAZ")

    def test_source_label_elec(self):
        assert "ADEME" in get_emission_source("ELEC")

    def test_source_label_gaz(self):
        assert "gaz naturel" in get_emission_source("GAZ")

    def test_factors_dict_has_elec_and_gaz(self):
        assert "ELEC" in EMISSION_FACTORS
        assert "GAZ" in EMISSION_FACTORS

    def test_gaz_higher_than_elec(self):
        """Gas natural has higher CO2 factor than French electricity mix."""
        assert get_emission_factor("GAZ") > get_emission_factor("ELEC")


# ── B. No hardcoded 0.052 in production code ─────────────────────────────────

class TestNoHardcodes:
    def test_no_hardcoded_052_in_emissions_service(self):
        """emissions_service.py should not contain literal 0.052."""
        src = Path(__file__).parent.parent / "services" / "emissions_service.py"
        content = src.read_text(encoding="utf-8")
        # Filter out comments
        lines = [l for l in content.split("\n") if not l.strip().startswith("#")]
        code = "\n".join(lines)
        assert "0.052" not in code, "Hardcoded 0.052 still in emissions_service.py"

    def test_no_hardcoded_052_in_portfolio(self):
        """routes/portfolio.py should not contain literal 0.052."""
        src = Path(__file__).parent.parent / "routes" / "portfolio.py"
        content = src.read_text(encoding="utf-8")
        lines = [l for l in content.split("\n") if not l.strip().startswith("#")]
        code = "\n".join(lines)
        assert "0.052" not in code, "Hardcoded 0.052 still in portfolio.py"

    def test_no_hardcoded_052_in_monitoring_seed(self):
        """routes/monitoring.py seed should not contain literal 0.052."""
        src = Path(__file__).parent.parent / "routes" / "monitoring.py"
        content = src.read_text(encoding="utf-8")
        # Find the seed_emission_factors function
        lines = content.split("\n")
        in_seed = False
        for line in lines:
            if "def seed_emission_factors" in line:
                in_seed = True
            elif in_seed and line.startswith("def ") or (in_seed and line.startswith("@router")):
                break
            elif in_seed and "0.052" in line and not line.strip().startswith("#"):
                pytest.fail("Hardcoded 0.052 in seed_emission_factors")


# ── C. emissions_service uses config ──────────────────────────────────────────

class TestServiceUsesConfig:
    def test_default_factor_is_ademe(self):
        """DEFAULT_FACTOR_KGCO2E should equal config ELEC factor."""
        from services.emissions_service import DEFAULT_FACTOR_KGCO2E
        assert DEFAULT_FACTOR_KGCO2E == 0.0569

    def test_service_imports_config(self):
        """emissions_service.py imports from config.emission_factors."""
        src = Path(__file__).parent.parent / "services" / "emissions_service.py"
        content = src.read_text(encoding="utf-8")
        assert "config.emission_factors" in content


# ── D. Config file structure ──────────────────────────────────────────────────

class TestConfigFileExists:
    def test_config_file_exists(self):
        path = Path(__file__).parent.parent / "config" / "emission_factors.py"
        assert path.exists(), "config/emission_factors.py does not exist"

    def test_config_exports_functions(self):
        from config.emission_factors import get_emission_factor, get_emission_source
        assert callable(get_emission_factor)
        assert callable(get_emission_source)
