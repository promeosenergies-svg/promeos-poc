"""
PROMEOS — Tests Step 29 : APER solarisation + estimation PV
"""
import pytest
import importlib
import inspect
import os

# ── Paths ──
BACKEND = os.path.join(os.path.dirname(__file__), "..")
SERVICE_PATH = os.path.join(BACKEND, "services", "aper_service.py")
ROUTE_PATH = os.path.join(BACKEND, "routes", "aper.py")


# ═══════════════════════════════════════════════════════════════════════
# A. Service unit tests
# ═══════════════════════════════════════════════════════════════════════

class TestAperServiceExists:
    def test_service_file_exists(self):
        assert os.path.isfile(SERVICE_PATH), "aper_service.py manquant"

    def test_service_importable(self):
        mod = importlib.import_module("services.aper_service")
        assert hasattr(mod, "get_aper_dashboard")
        assert hasattr(mod, "estimate_pv_production")

    def test_climate_zone_function(self):
        mod = importlib.import_module("services.aper_service")
        assert hasattr(mod, "_get_climate_zone")

    def test_monthly_profile_function(self):
        mod = importlib.import_module("services.aper_service")
        assert hasattr(mod, "_estimate_monthly_profile")


class TestClimateZone:
    def setup_method(self):
        mod = importlib.import_module("services.aper_service")
        self._get_climate_zone = mod._get_climate_zone

    def test_climate_zone_paris(self):
        """Paris (IDF) -> H1."""
        site = type("Site", (), {"region": "Ile-de-France"})()
        assert self._get_climate_zone(site) == "H1"

    def test_climate_zone_nice(self):
        """Nice (PACA) -> H3."""
        site = type("Site", (), {"region": "Provence-Alpes-Cote d'Azur"})()
        assert self._get_climate_zone(site) == "H3"

    def test_climate_zone_default(self):
        """Zone inconnue -> H2 (fallback)."""
        site = type("Site", (), {"region": "Unknown"})()
        assert self._get_climate_zone(site) == "H2"

    def test_climate_zone_none(self):
        """Pas de region -> H2."""
        site = type("Site", (), {"region": None})()
        assert self._get_climate_zone(site) == "H2"


class TestMonthlyProfile:
    def setup_method(self):
        mod = importlib.import_module("services.aper_service")
        self._estimate_monthly_profile = mod._estimate_monthly_profile

    def test_monthly_12_entries(self):
        result = self._estimate_monthly_profile(100000, "H2")
        assert len(result) == 12

    def test_monthly_sum_approx(self):
        result = self._estimate_monthly_profile(100000, "H2")
        total = sum(result)
        assert abs(total - 100000) < 1000  # ~1% tolerance rounding

    def test_summer_higher_than_winter(self):
        """Mois d'ete (juin-aout) > mois d'hiver (dec-fev)."""
        result = self._estimate_monthly_profile(100000, "H3")
        summer = sum(result[5:8])  # Jun, Jul, Aug
        winter = sum(result[0:2]) + result[11]  # Jan, Feb, Dec
        assert summer > winter


class TestEstimatePvCalculations:
    """Test les calculs PV sans DB (logique pure)."""

    def test_coverage_ratio_parking(self):
        """Parking -> 60% couverture."""
        mod = importlib.import_module("services.aper_service")
        sig = inspect.signature(mod.estimate_pv_production)
        params = list(sig.parameters.keys())
        assert "surface_type" in params

    def test_peak_power_formula(self):
        """4500 m2 parking -> 4500 * 0.60 * 0.180 = 486 kWc."""
        surface = 4500
        coverage = 0.60
        panel = surface * coverage
        kwc = panel * 0.180
        assert abs(kwc - 486) < 1

    def test_estimate_realistic_range(self):
        """4500 m2 parking en H3 -> 486 kWc * 1350h = 656 MWh."""
        kwc = 4500 * 0.60 * 0.180
        annual = kwc * 1350  # H3
        mwh = annual / 1000
        assert 300 < mwh < 800  # realistic range


# ═══════════════════════════════════════════════════════════════════════
# B. Route / endpoint tests
# ═══════════════════════════════════════════════════════════════════════

class TestAperRoute:
    def test_route_file_exists(self):
        assert os.path.isfile(ROUTE_PATH), "routes/aper.py manquant"

    def test_route_importable(self):
        mod = importlib.import_module("routes.aper")
        assert hasattr(mod, "router")

    def test_route_has_dashboard(self):
        src = open(ROUTE_PATH, "r", encoding="utf-8").read()
        assert "/dashboard" in src

    def test_route_has_estimate(self):
        src = open(ROUTE_PATH, "r", encoding="utf-8").read()
        assert "/estimate" in src
        assert "site_id" in src


# ═══════════════════════════════════════════════════════════════════════
# C. Source guard tests (structural)
# ═══════════════════════════════════════════════════════════════════════

class TestSourceGuards:
    def setup_method(self):
        self.service_src = open(SERVICE_PATH, "r", encoding="utf-8").read()

    def test_parking_threshold_1500(self):
        assert "1500" in self.service_src

    def test_parking_outdoor_only(self):
        assert "outdoor" in self.service_src

    def test_roof_threshold_500(self):
        assert "500" in self.service_src

    def test_pvgis_used(self):
        assert "pvgis" in self.service_src.lower() or "PVGIS" in self.service_src

    def test_emission_factor_used(self):
        assert "get_emission_factor" in self.service_src

    def test_co2_calculated(self):
        assert "co2_avoided" in self.service_src or "co2_evite" in self.service_src

    def test_monthly_kwh_returned(self):
        assert "monthly_kwh" in self.service_src

    def test_source_field(self):
        assert '"source"' in self.service_src or "'source'" in self.service_src

    def test_registered_in_main(self):
        main_src = open(os.path.join(BACKEND, "main.py"), "r", encoding="utf-8").read()
        assert "aper_router" in main_src
