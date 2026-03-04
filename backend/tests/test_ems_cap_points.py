"""
PROMEOS - EMS Cap Points Tests
5 tests covering the 5000-point cap enforcement.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime

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
    yield client, session
    app.dependency_overrides.clear()
    session.close()


def _seed_site(db):
    site = Site(nom="Cap Test", type=TypeSite.BUREAU)
    db.add(site)
    db.flush()
    m = Meter(meter_id="PRM-CAP-1", name="M1", site_id=site.id, energy_vector=EnergyVector.ELECTRICITY)
    db.add(m)
    db.flush()
    return site


class TestCapPoints:
    def test_ok_short_range(self, env):
        client, db = env
        _seed_site(db)
        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": "1",
                "date_from": "2025-01-01",
                "date_to": "2025-01-08",
                "granularity": "hourly",
            },
        )
        assert r.status_code == 200

    def test_400_15min_365d(self, env):
        client, db = env
        _seed_site(db)
        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": "1",
                "date_from": "2025-01-01",
                "date_to": "2026-01-01",
                "granularity": "15min",
            },
        )
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert detail["error"] == "too_many_points"
        assert detail["cap"] == 5000

    def test_detail_includes_suggestion(self, env):
        client, db = env
        _seed_site(db)
        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": "1",
                "date_from": "2025-01-01",
                "date_to": "2026-01-01",
                "granularity": "15min",
            },
        )
        detail = r.json()["detail"]
        assert "suggested_granularity" in detail
        assert detail["suggested_granularity"] == "daily"

    def test_auto_avoids_error(self, env):
        client, db = env
        _seed_site(db)
        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": "1",
                "date_from": "2025-01-01",
                "date_to": "2026-01-01",
                "granularity": "auto",
            },
        )
        assert r.status_code == 200

    def test_boundary_5000(self, env):
        """~208 days of daily data = 208 points, well under 5000."""
        client, db = env
        _seed_site(db)
        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": "1",
                "date_from": "2025-01-01",
                "date_to": "2025-07-30",
                "granularity": "daily",
            },
        )
        assert r.status_code == 200
