"""
PROMEOS - EMS Demo Data Generation Tests
10 tests covering generation, idempotence, purge, profiles, anomalies.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models import Base, Site, TypeSite, Meter, MeterReading
from models.ems_models import EmsWeatherCache
from database import get_db


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Pre-seed 12 sites (demo needs existing sites)
    for i in range(12):
        site = Site(nom=f"Site Demo {i}", type=TypeSite.BUREAU, ville=f"Ville {i}")
        session.add(site)
    session.flush()

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


class TestDemoGeneration:
    def test_generate_ok(self, env):
        """Generate demo data returns ok with readings count."""
        client, db = env
        r = client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 3,
                "days": 7,
                "seed": 42,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["total_readings"] > 0
        assert data["sites_generated"] == 3

    def test_generate_creates_meters(self, env):
        """Demo generate creates EMS-DEMO-* meters."""
        client, db = env
        client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 2,
                "days": 3,
                "seed": 42,
            },
        )

        demo_meters = db.query(Meter).filter(Meter.meter_id.like("EMS-DEMO-%")).all()
        assert len(demo_meters) == 2

    def test_generate_creates_readings(self, env):
        """Demo generate creates hourly readings."""
        client, db = env
        client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 1,
                "days": 2,
                "seed": 42,
            },
        )

        count = db.query(MeterReading).join(Meter).filter(Meter.meter_id.like("EMS-DEMO-%")).count()
        # 1 site * 2 days * 24 hours = 48
        assert count == 48

    def test_generate_creates_weather(self, env):
        """Demo generate creates weather cache entries."""
        client, db = env
        client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 1,
                "days": 5,
                "seed": 42,
            },
        )

        weather_count = db.query(EmsWeatherCache).filter(EmsWeatherCache.source == "demo_ems").count()
        assert weather_count == 5

    def test_idempotent_skip(self, env):
        """Second call without force returns 'skipped'."""
        client, db = env
        r1 = client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 2,
                "days": 3,
                "seed": 42,
            },
        )
        assert r1.json()["status"] == "ok"

        r2 = client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 2,
                "days": 3,
                "seed": 42,
            },
        )
        assert r2.json()["status"] == "skipped"

    def test_force_regenerate(self, env):
        """force=true regenerates even if data exists."""
        client, db = env
        client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 2,
                "days": 3,
                "seed": 42,
            },
        )

        r = client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 2,
                "days": 3,
                "seed": 42,
                "force": True,
            },
        )
        assert r.json()["status"] == "ok"

    def test_purge(self, env):
        """Purge removes all demo data."""
        client, db = env
        client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 2,
                "days": 3,
                "seed": 42,
            },
        )

        r = client.post("/api/ems/demo/purge")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["deleted_meters"] == 2
        assert data["deleted_readings"] > 0

        # Verify meters gone
        remaining = db.query(Meter).filter(Meter.meter_id.like("EMS-DEMO-%")).count()
        assert remaining == 0

    def test_purge_no_data(self, env):
        """Purge with no demo data returns cleanly."""
        client, db = env
        r = client.post("/api/ems/demo/purge")
        assert r.status_code == 200
        assert r.json()["deleted_meters"] == 0

    def test_profiles_respect_archetypes(self, env):
        """Generated sites have different archetypes in the report."""
        client, db = env
        r = client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 12,
                "days": 3,
                "seed": 42,
            },
        )
        data = r.json()
        archetypes = {s["archetype"] for s in data["sites"]}
        # Should have at least bureau and retail
        assert "bureau" in archetypes
        assert "retail" in archetypes

    def test_anomalies_injected(self, env):
        """Some sites have anomalies flagged in the report."""
        client, db = env
        r = client.post(
            "/api/ems/demo/generate",
            params={
                "portfolio_size": 12,
                "days": 3,
                "seed": 42,
            },
        )
        data = r.json()
        anomalies = [s["anomaly"] for s in data["sites"] if s["anomaly"]]
        assert len(anomalies) >= 3  # At least 3 of the 4 anomaly types
        types = set(anomalies)
        assert "high_night_base" in types
        assert "progressive_drift" in types
