"""
PROMEOS — P1 Backend Tests
Tests for reference_profile and weather_hourly endpoints.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models import Base, Site, TypeSite, Meter, MeterReading
from models.energy_models import EnergyVector, FrequencyType
from database import get_db


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)

    # Seed a site + meter + 30 days of readings
    site = Site(nom="P1 Test Site", type=TypeSite.BUREAU, latitude=48.86, longitude=2.35)
    session.add(site)
    session.flush()

    m = Meter(meter_id="PRM-P1-01", name="P1 Meter", site_id=site.id, energy_vector=EnergyVector.ELECTRICITY)
    session.add(m)
    session.flush()

    for d in range(30):
        dt = datetime(2025, 3, 1) + timedelta(days=d)
        for h in range(24):
            session.add(MeterReading(
                meter_id=m.id,
                timestamp=dt.replace(hour=h),
                frequency=FrequencyType.HOURLY,
                value_kwh=10 + h * 0.5,
            ))
    session.flush()

    yield client, session, site
    app.dependency_overrides.clear()
    session.close()


class TestReferenceProfile:
    """P1-1: /api/ems/reference_profile endpoint."""

    def test_returns_200(self, env):
        client, _, site = env
        r = client.get("/api/ems/reference_profile", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-10",
            "famille": "entreprise",
            "puissance": "9-12",
        })
        assert r.status_code == 200

    def test_returns_series(self, env):
        client, _, site = env
        r = client.get("/api/ems/reference_profile", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-05",
            "famille": "habitat",
            "puissance": "6-9",
            "granularity": "daily",
        })
        data = r.json()
        assert "series" in data
        assert len(data["series"]) == 5  # 5 days
        assert data["famille"] == "habitat"
        assert data["puissance"] == "6-9"

    def test_returns_kpi_delta(self, env):
        client, _, site = env
        r = client.get("/api/ems/reference_profile", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-15",
            "famille": "entreprise",
            "puissance": "9-12",
            "granularity": "daily",
        })
        data = r.json()
        kpi = data.get("kpi")
        assert kpi is not None
        assert "actual_kwh" in kpi
        assert "reference_kwh" in kpi
        assert "delta_pct" in kpi
        assert "coverage_pct" in kpi
        assert "confidence" in kpi

    def test_hourly_granularity(self, env):
        client, _, site = env
        r = client.get("/api/ems/reference_profile", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-02",
            "famille": "entreprise",
            "puissance": "9-12",
            "granularity": "hourly",
        })
        data = r.json()
        # 2 days * 24h = 48 hourly points
        assert len(data["series"]) == 48

    def test_weekend_factor_applied(self, env):
        client, _, site = env
        # 2025-03-01 is Saturday, 2025-03-03 is Monday
        r = client.get("/api/ems/reference_profile", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-03",
            "famille": "entreprise",
            "puissance": "9-12",
            "granularity": "daily",
        })
        data = r.json()
        # Weekend (Saturday) daily total should be less than weekday (Monday)
        # for entreprise (factor=0.4)
        series = data["series"]
        sat = next(p for p in series if p["t"].startswith("2025-03-01"))
        mon = next(p for p in series if p["t"].startswith("2025-03-03"))
        assert sat["v"] < mon["v"]


class TestWeatherHourly:
    """P1-3: /api/ems/weather_hourly endpoint."""

    def test_returns_200(self, env):
        client, _, site = env
        r = client.get("/api/ems/weather_hourly", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-05",
        })
        assert r.status_code == 200

    def test_returns_utc_timezone(self, env):
        client, _, site = env
        r = client.get("/api/ems/weather_hourly", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-03",
        })
        data = r.json()
        assert data["timezone"] == "UTC"

    def test_timestamps_end_with_z(self, env):
        client, _, site = env
        r = client.get("/api/ems/weather_hourly", params={
            "site_id": site.id,
            "date_from": "2025-03-01",
            "date_to": "2025-03-02",
        })
        data = r.json()
        hours = data.get("hours", [])
        assert len(hours) > 0
        for h in hours:
            assert h["t"].endswith("Z"), f"Timestamp {h['t']} should end with Z"

    def test_24_hours_per_day(self, env):
        client, _, site = env
        r = client.get("/api/ems/weather_hourly", params={
            "site_id": site.id,
            "date_from": "2025-06-15",
            "date_to": "2025-06-15",
        })
        data = r.json()
        hours = data.get("hours", [])
        assert len(hours) == 24

    def test_sinusoidal_intraday_pattern(self, env):
        """Min near 5h UTC, max near 15h UTC (sinusoidal)."""
        client, _, site = env
        r = client.get("/api/ems/weather_hourly", params={
            "site_id": site.id,
            "date_from": "2025-07-15",
            "date_to": "2025-07-15",
        })
        data = r.json()
        hours = data.get("hours", [])
        if len(hours) == 24:
            # Temperature at 15h should be warmer than at 5h
            t5 = hours[5]["temp_c"]
            t15 = hours[15]["temp_c"]
            assert t15 > t5
