"""
PROMEOS - EMS Weather + Signature Tests
10 tests covering demo weather generation, caching, and energy signature.
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
from services.ems.weather_service import get_weather
from services.ems.signature_service import run_signature


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


def _seed_site(db, lat=48.86):
    site = Site(nom="Weather Test", type=TypeSite.BUREAU, latitude=lat, longitude=2.35)
    db.add(site)
    db.flush()
    return site


class TestWeather:
    def test_demo_generates_365_days(self, db):
        site = _seed_site(db)
        result = get_weather(db, site.id, date(2025, 1, 1), date(2025, 12, 31))
        assert len(result) == 365

    def test_cache_hit(self, db):
        site = _seed_site(db)
        r1 = get_weather(db, site.id, date(2025, 1, 1), date(2025, 1, 10))
        count_before = db.query(EmsWeatherCache).count()

        r2 = get_weather(db, site.id, date(2025, 1, 1), date(2025, 1, 10))
        count_after = db.query(EmsWeatherCache).count()

        assert count_before == count_after
        assert r1 == r2

    def test_sinusoidal_summer_warmer(self, db):
        site = _seed_site(db)
        jan = get_weather(db, site.id, date(2025, 1, 10), date(2025, 1, 20))
        jul = get_weather(db, site.id, date(2025, 7, 10), date(2025, 7, 20))

        jan_avg = sum(d["temp_avg_c"] for d in jan) / len(jan)
        jul_avg = sum(d["temp_avg_c"] for d in jul) / len(jul)
        assert jul_avg > jan_avg + 5  # July significantly warmer

    def test_deterministic_seed(self, db):
        site = _seed_site(db)
        r1 = get_weather(db, site.id, date(2025, 6, 15), date(2025, 6, 15))
        # Delete cache and regenerate
        db.query(EmsWeatherCache).delete()
        db.flush()
        r2 = get_weather(db, site.id, date(2025, 6, 15), date(2025, 6, 15))
        assert r1[0]["temp_avg_c"] == r2[0]["temp_avg_c"]


class TestSignature:
    def test_heating_only(self):
        """Synthetic heating data: constant base + linear heating slope."""
        import numpy as np

        np.random.seed(42)
        temps = np.linspace(-5, 25, 60)
        base = 200
        a = 8.0  # kWh per degree below Tb=15
        kwh = [base + a * max(0, 15 - t) + np.random.normal(0, 5) for t in temps]

        result = run_signature(kwh, temps.tolist())
        assert "error" not in result
        assert result["a_heating"] > 2.0
        assert result["b_cooling"] < 1.0
        assert result["r_squared"] > 0.8
        assert result["label"] == "heating_dominant"

    def test_cooling_only(self):
        import numpy as np

        np.random.seed(42)
        temps = np.linspace(10, 35, 50)
        base = 150
        b = 6.0
        kwh = [base + b * max(0, t - 22) + np.random.normal(0, 5) for t in temps]

        result = run_signature(kwh, temps.tolist())
        assert "error" not in result
        assert result["b_cooling"] > 2.0
        assert result["label"] == "cooling_dominant"

    def test_flat(self):
        import numpy as np

        np.random.seed(42)
        temps = np.linspace(5, 30, 40)
        kwh = [100 + np.random.normal(0, 2) for _ in temps]

        result = run_signature(kwh, temps.tolist())
        assert "error" not in result
        assert result["label"] == "flat"

    def test_insufficient_data(self):
        result = run_signature([100, 200, 300], [10, 15, 20])
        assert result["error"] == "insufficient_data"

    def test_scatter_length(self):
        import numpy as np

        np.random.seed(42)
        n = 30
        temps = np.linspace(0, 25, n)
        kwh = [200 + 5 * max(0, 15 - t) for t in temps]

        result = run_signature(kwh, temps.tolist())
        assert len(result["scatter"]) == n
        assert len(result["fit_line"]) == 50

    def test_endpoint_integration(self, env):
        client, db = env
        site = _seed_site(db)
        m = Meter(meter_id="PRM-SIG-1", name="SigM", site_id=site.id, energy_vector=EnergyVector.ELECTRICITY)
        db.add(m)
        db.flush()

        # Seed 90 days of daily consumption with heating pattern
        import numpy as np

        np.random.seed(42)
        for d in range(90):
            dt = datetime(2025, 1, 1) + timedelta(days=d)
            # Simple heating model: more kWh in winter
            month_factor = abs(d - 45) / 45  # 0 at mid, 1 at extremes
            kwh = 200 + 100 * month_factor + np.random.normal(0, 10)
            db.add(
                MeterReading(
                    meter_id=m.id,
                    timestamp=dt,
                    frequency=FrequencyType.DAILY,
                    value_kwh=max(50, kwh),
                )
            )
        db.flush()

        r = client.post(
            "/api/ems/signature/run",
            params={
                "site_id": site.id,
                "date_from": "2025-01-01",
                "date_to": "2025-04-01",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "base_kwh" in data
        assert "r_squared" in data
        assert "scatter" in data
        assert data["n_points"] > 0
