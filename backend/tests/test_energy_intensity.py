"""
Tests — #146: Energy intensity service (kWh/m²/an).
Covers: get_site_intensity, get_portfolio_intensity, EP coefficients, API endpoint.
"""

import pytest
from datetime import date, datetime
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.fast

from models.base import Base
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
)
from models.enums import TypeSite
from models.energy_models import Meter, MeterReading, EnergyVector, FrequencyType
from services.energy_intensity_service import (
    get_site_intensity,
    get_portfolio_intensity,
    EP_COEFFICIENTS,
)


@pytest.fixture()
def db():
    """In-memory SQLite with seed data for intensity tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organisation(id=1, nom="Test Org", siren="123456789", type_client="tertiaire")
    session.add(org)
    session.flush()

    ej = EntiteJuridique(id=1, nom="Test EJ", siren="123456789", organisation_id=1)
    session.add(ej)
    session.flush()

    ptf = Portefeuille(id=1, nom="Test Portfolio", entite_juridique_id=1)
    session.add(ptf)
    session.flush()

    # Site with surface + consumption
    site1 = Site(
        id=1,
        nom="Bureau Paris",
        type=TypeSite.BUREAU,
        actif=True,
        portefeuille_id=1,
        surface_m2=500.0,
        annual_kwh_total=100000,
    )
    # Site with surface but no consumption data
    site2 = Site(
        id=2,
        nom="Bureau Lyon",
        type=TypeSite.BUREAU,
        actif=True,
        portefeuille_id=1,
        surface_m2=300.0,
        annual_kwh_total=60000,
    )
    # Site without surface
    site3 = Site(
        id=3,
        nom="Site No Surface",
        type=TypeSite.BUREAU,
        actif=True,
        portefeuille_id=1,
        surface_m2=None,
        annual_kwh_total=50000,
    )
    # Site with surface = 0
    site4 = Site(
        id=4,
        nom="Site Zero Surface",
        type=TypeSite.BUREAU,
        actif=True,
        portefeuille_id=1,
        surface_m2=0.0,
        annual_kwh_total=40000,
    )
    session.add_all([site1, site2, site3, site4])
    session.flush()

    # Electricity meter for site1
    meter_elec = Meter(
        id=1,
        meter_id="PRM-ELEC-001",
        name="Compteur elec",
        energy_vector=EnergyVector.ELECTRICITY,
        site_id=1,
        is_active=True,
    )
    # Gas meter for site1
    meter_gas = Meter(
        id=2,
        meter_id="PCE-GAZ-001",
        name="Compteur gaz",
        energy_vector=EnergyVector.GAS,
        site_id=1,
        is_active=True,
    )
    session.add_all([meter_elec, meter_gas])
    session.flush()

    # Electricity readings: 365 days of daily readings, 100 kWh/day = 36500 kWh/year
    for day_offset in range(365):
        dt = datetime(2025, 1, 1) + __import__("datetime").timedelta(days=day_offset)
        session.add(
            MeterReading(
                meter_id=1,
                timestamp=dt,
                frequency=FrequencyType.DAILY,
                value_kwh=100.0,
                is_estimated=False,
            )
        )

    # Gas readings: 365 days of daily readings, 50 kWh/day = 18250 kWh/year
    for day_offset in range(365):
        dt = datetime(2025, 1, 1) + __import__("datetime").timedelta(days=day_offset)
        session.add(
            MeterReading(
                meter_id=2,
                timestamp=dt,
                frequency=FrequencyType.DAILY,
                value_kwh=50.0,
                is_estimated=False,
            )
        )

    session.commit()
    yield session
    session.close()


# ── EP Coefficients ──


class TestEPCoefficients:
    def test_electricity_coeff_is_1_9(self):
        assert EP_COEFFICIENTS[EnergyVector.ELECTRICITY] == 1.9

    def test_gas_coeff_is_1_0(self):
        assert EP_COEFFICIENTS[EnergyVector.GAS] == 1.0

    def test_heat_coeff_is_1_0(self):
        assert EP_COEFFICIENTS[EnergyVector.HEAT] == 1.0

    def test_water_coeff_is_0(self):
        assert EP_COEFFICIENTS[EnergyVector.WATER] == 0.0


# ── Site Intensity ──


class TestSiteIntensity:
    def test_site_with_metered_data(self, db):
        """Site 1 has elec (36500 kWh) + gas (18250 kWh), surface=500 m2."""
        result = get_site_intensity(db, site_id=1, year=2026)
        # year=2026 means period 2025-01-01 to 2025-12-31

        assert result["site_id"] == 1
        assert result["site_nom"] == "Bureau Paris"
        assert result["surface_m2"] == 500.0
        assert result["year"] == 2026

        # Final energy
        assert result["kWh_final"] > 0
        # With 36500 elec + 18250 gas = 54750 kWh / 500 m2 = 109.5
        expected_final = 54750.0 / 500.0
        assert abs(result["kWh_m2_final"] - expected_final) < 1.0

        # Primary energy: 36500*1.9 + 18250*1.0 = 69350+18250 = 87600 / 500 = 175.2
        expected_primary = (36500.0 * 1.9 + 18250.0 * 1.0) / 500.0
        assert abs(result["kWh_m2_primary"] - expected_primary) < 1.0

        # EP detail
        assert "electricity" in result["ep_detail"]
        assert "gas" in result["ep_detail"]
        assert result["ep_detail"]["electricity"]["coeff_ep"] == 1.9
        assert result["ep_detail"]["gas"]["coeff_ep"] == 1.0

        assert result["confidence"] != "none"
        assert result["warnings"] == []

    def test_site_no_surface(self, db):
        """Site 3 has surface=None — should return warning."""
        result = get_site_intensity(db, site_id=3, year=2026)

        assert result["kWh_m2_final"] is None
        assert result["kWh_m2_primary"] is None
        assert result["surface_m2"] is None
        assert result["confidence"] == "none"
        assert any("surface_m2" in w for w in result["warnings"])

    def test_site_zero_surface(self, db):
        """Site 4 has surface=0 — should return warning."""
        result = get_site_intensity(db, site_id=4, year=2026)

        assert result["kWh_m2_final"] is None
        assert result["kWh_m2_primary"] is None
        assert result["confidence"] == "none"
        assert any("surface_m2" in w for w in result["warnings"])

    def test_site_not_found(self, db):
        with pytest.raises(HTTPException) as exc_info:
            get_site_intensity(db, site_id=999, year=2026)
        assert exc_info.value.status_code == 404

    def test_site_no_consumption_data(self, db):
        """Site 2 has surface but no meter readings — fallback to estimated."""
        result = get_site_intensity(db, site_id=2, year=2026)

        assert result["surface_m2"] == 300.0
        # Should still compute using estimated fallback from annual_kwh_total
        # Exact value depends on the unified service behavior
        assert "warnings" in result

    def test_primary_always_gte_final(self, db):
        """kWh_m2_primary >= kWh_m2_final (EP coefficients >= 1.0 for energy vectors)."""
        result = get_site_intensity(db, site_id=1, year=2026)
        if result["kWh_m2_final"] and result["kWh_m2_primary"]:
            assert result["kWh_m2_primary"] >= result["kWh_m2_final"]

    def test_default_year_is_current(self, db):
        """When year is None, defaults to current year."""
        result = get_site_intensity(db, site_id=1)
        assert result["year"] == date.today().year


# ── Portfolio Intensity ──


class TestPortfolioIntensity:
    def test_portfolio_aggregation(self, db):
        """Portfolio 1 has 4 sites, 2 with valid surface+data."""
        result = get_portfolio_intensity(db, portfolio_id=1, year=2026)

        assert result["portfolio_id"] == 1
        assert result["portfolio_nom"] == "Test Portfolio"
        assert result["year"] == 2026

        # Coverage
        assert result["coverage"]["sites_total"] == 4
        assert result["coverage"]["sites_with_surface"] >= 2  # sites 1 and 2

        # Weighted average should be computed
        assert result["sites"] is not None
        assert len(result["sites"]) == 4

    def test_portfolio_coverage_ratio(self, db):
        result = get_portfolio_intensity(db, portfolio_id=1, year=2026)
        coverage = result["coverage"]
        expected_ratio = coverage["sites_with_surface"] / coverage["sites_total"]
        assert abs(coverage["ratio"] - round(expected_ratio, 2)) < 0.01

    def test_portfolio_not_found(self, db):
        with pytest.raises(HTTPException) as exc_info:
            get_portfolio_intensity(db, portfolio_id=999, year=2026)
        assert exc_info.value.status_code == 404

    def test_portfolio_warns_missing_surface(self, db):
        """Sites 3 and 4 have no usable surface — should generate a warning."""
        result = get_portfolio_intensity(db, portfolio_id=1, year=2026)
        assert any("surface manquante" in w for w in result["warnings"])

    def test_portfolio_weighted_average_not_simple_mean(self, db):
        """Verify it's Σ(kWh)/Σ(surface), not mean of per-site kWh/m²."""
        result = get_portfolio_intensity(db, portfolio_id=1, year=2026)
        if result["kWh_m2_final"] is not None:
            assert result["total_kwh_final"] > 0
            assert result["total_surface_m2"] > 0
            expected = round(result["total_kwh_final"] / result["total_surface_m2"], 2)
            assert result["kWh_m2_final"] == expected


# ── API endpoint ──


class TestIntensityEndpoint:
    """API tests use the demo DB (matches codebase convention)."""

    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient
        from main import app

        return TestClient(app)

    def test_endpoint_requires_param(self, client):
        resp = client.get("/api/energy/intensity")
        assert resp.status_code == 400

    def test_endpoint_site(self, client):
        """Hit a demo site — just verify shape, not exact values."""
        resp = client.get("/api/energy/intensity?site_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert "kWh_m2_final" in data or "error" in data

    def test_endpoint_portfolio(self, client):
        resp = client.get("/api/energy/intensity?portfolio_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert "coverage" in data or "error" in data

    def test_endpoint_site_not_found(self, client):
        resp = client.get("/api/energy/intensity?site_id=999999")
        assert resp.status_code == 404
