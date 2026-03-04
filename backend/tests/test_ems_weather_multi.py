"""
PROMEOS - EMS Weather Multi-Site + Availability Tests
Covers: get_weather_multi envelope, multi_city_risk, availability in timeseries.
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
from models.ems_models import EmsWeatherCache
from models.energy_models import EnergyVector, FrequencyType
from database import get_db
from services.ems.weather_service import get_weather_multi


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


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
    yield client, session
    app.dependency_overrides.clear()
    session.close()


def _seed_sites(db, n=3, lat_base=48.86, lat_spread=0.5):
    """Create n sites with spread latitudes."""
    sites = []
    for i in range(n):
        s = Site(
            nom=f"Site Multi {i + 1}",
            type=TypeSite.BUREAU,
            latitude=lat_base + i * lat_spread,
            longitude=2.35,
        )
        db.add(s)
        sites.append(s)
    db.flush()
    return sites


class TestWeatherMulti:
    def test_returns_dict_with_days_and_meta(self, db):
        sites = _seed_sites(db, 2)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 6, 1), date(2025, 6, 10))
        assert "days" in result
        assert "meta" in result
        assert len(result["days"]) == 10

    def test_envelope_bounds(self, db):
        sites = _seed_sites(db, 3, lat_spread=1.0)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 1, 15), date(2025, 1, 25))
        for day in result["days"]:
            assert day["envelope_min_c"] <= day["temp_avg_c"]
            assert day["envelope_max_c"] >= day["temp_avg_c"]

    def test_single_site_no_envelope_spread(self, db):
        sites = _seed_sites(db, 1)
        result = get_weather_multi(db, [sites[0].id], date(2025, 3, 1), date(2025, 3, 5))
        for day in result["days"]:
            assert day["envelope_min_c"] == day["temp_avg_c"]
            assert day["envelope_max_c"] == day["temp_avg_c"]

    def test_multi_city_risk_close(self, db):
        sites = _seed_sites(db, 3, lat_base=48.86, lat_spread=0.5)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 1, 1), date(2025, 1, 5))
        assert result["meta"]["multi_city_risk"] is False

    def test_multi_city_risk_far(self, db):
        sites = _seed_sites(db, 3, lat_base=44.0, lat_spread=2.5)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 1, 1), date(2025, 1, 5))
        assert result["meta"]["multi_city_risk"] is True

    def test_empty_site_ids(self, db):
        result = get_weather_multi(db, [], date(2025, 1, 1), date(2025, 1, 5))
        assert result["days"] == []
        assert result["meta"]["n_sites"] == 0

    def test_meta_n_sites(self, db):
        sites = _seed_sites(db, 4)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 6, 1), date(2025, 6, 3))
        assert result["meta"]["n_sites"] == 4

    def test_source_demo_avg_multi(self, db):
        sites = _seed_sites(db, 2)
        result = get_weather_multi(db, [s.id for s in sites], date(2025, 7, 1), date(2025, 7, 3))
        for day in result["days"]:
            assert day["source"] == "demo_avg"


class TestWeatherEndpoint:
    def test_weather_multi_endpoint(self, env):
        client, db = env
        sites = _seed_sites(db, 2)
        ids = ",".join(str(s.id) for s in sites)
        r = client.get(
            "/api/ems/weather",
            params={
                "site_ids": ids,
                "date_from": "2025-06-01",
                "date_to": "2025-06-05",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["mode"] == "average"
        assert "meta" in data
        assert len(data["days"]) == 5


class TestAvailability:
    def test_timeseries_includes_availability(self, env):
        client, db = env
        site = Site(nom="Avail Test", type=TypeSite.BUREAU, latitude=48.86, longitude=2.35)
        db.add(site)
        db.flush()
        m = Meter(meter_id="PRM-AVAIL-1", name="AvailM", site_id=site.id, energy_vector=EnergyVector.ELECTRICITY)
        db.add(m)
        db.flush()

        # Seed 30 days of hourly data
        for d in range(30):
            dt = datetime(2025, 1, 1) + timedelta(days=d)
            for h in range(24):
                ts = dt.replace(hour=h)
                db.add(
                    MeterReading(
                        meter_id=m.id,
                        timestamp=ts,
                        frequency=FrequencyType.HOURLY,
                        value_kwh=50.0,
                    )
                )
        db.flush()

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-31",
                "granularity": "daily",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "availability" in data
        assert len(data["availability"]) >= 1
        avail = data["availability"][0]
        assert "coverage_pct" in avail
        assert "gaps" in avail
        assert avail["coverage_pct"] > 0

    def test_availability_detects_gap(self, env):
        client, db = env
        site = Site(nom="Gap Test", type=TypeSite.BUREAU, latitude=48.86, longitude=2.35)
        db.add(site)
        db.flush()
        m = Meter(meter_id="PRM-GAP-1", name="GapM", site_id=site.id, energy_vector=EnergyVector.ELECTRICITY)
        db.add(m)
        db.flush()

        # Seed days 1-10 and 20-30 (gap of 9 days in the middle)
        for d in list(range(10)) + list(range(19, 30)):
            dt = datetime(2025, 1, 1) + timedelta(days=d)
            db.add(
                MeterReading(
                    meter_id=m.id,
                    timestamp=dt,
                    frequency=FrequencyType.DAILY,
                    value_kwh=50.0,
                )
            )
        db.flush()

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-31",
                "granularity": "daily",
            },
        )
        assert r.status_code == 200
        data = r.json()
        avail = data["availability"][0]
        assert avail["coverage_pct"] < 100
        assert len(avail["gaps"]) >= 1
