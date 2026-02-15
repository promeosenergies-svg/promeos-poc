"""
PROMEOS - EMS Overlay Mode Tests
8 tests covering overlay series-per-site, max 8 sites cap, "Autres" bucket, labels.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

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


def _seed_site(db, name="Test Site"):
    site = Site(nom=name, type=TypeSite.BUREAU)
    db.add(site)
    db.flush()
    return site


def _seed_meter(db, site_id, name="M1"):
    m = Meter(meter_id=f"PRM-{site_id}-{name}", name=name, site_id=site_id)
    db.add(m)
    db.flush()
    return m


def _seed_readings(db, meter_id, days=3, kwh=10.0):
    start = datetime(2025, 1, 1)
    readings = []
    for d in range(days):
        for h in range(24):
            readings.append(MeterReading(
                meter_id=meter_id,
                timestamp=start + timedelta(days=d, hours=h),
                frequency=FrequencyType.HOURLY,
                value_kwh=kwh,
                quality_score=0.95,
                is_estimated=False,
            ))
    db.bulk_save_objects(readings)
    db.flush()


class TestOverlayMode:

    def test_overlay_two_sites(self, env):
        """Overlay mode produces one series per site."""
        client, db = env
        s1 = _seed_site(db, "Site A")
        s2 = _seed_site(db, "Site B")
        m1 = _seed_meter(db, s1.id, "M1")
        m2 = _seed_meter(db, s2.id, "M2")
        _seed_readings(db, m1.id, days=2, kwh=10)
        _seed_readings(db, m2.id, days=2, kwh=5)

        r = client.get("/api/ems/timeseries", params={
            "site_ids": f"{s1.id},{s2.id}",
            "date_from": "2025-01-01", "date_to": "2025-01-03",
            "granularity": "daily", "mode": "overlay",
        })
        assert r.status_code == 200
        data = r.json()
        assert len(data["series"]) == 2
        keys = {s["key"] for s in data["series"]}
        assert f"site_{s1.id}" in keys
        assert f"site_{s2.id}" in keys

    def test_overlay_labels_are_site_names(self, env):
        """Each overlay series label should be the site name."""
        client, db = env
        s1 = _seed_site(db, "Bureau Paris")
        s2 = _seed_site(db, "Retail Lyon")
        _seed_readings(db, _seed_meter(db, s1.id, "M1").id, days=1)
        _seed_readings(db, _seed_meter(db, s2.id, "M2").id, days=1)

        r = client.get("/api/ems/timeseries", params={
            "site_ids": f"{s1.id},{s2.id}",
            "date_from": "2025-01-01", "date_to": "2025-01-02",
            "granularity": "daily", "mode": "overlay",
        })
        labels = {s["label"] for s in r.json()["series"]}
        assert "Bureau Paris" in labels
        assert "Retail Lyon" in labels

    def test_overlay_single_site(self, env):
        """Overlay with a single site produces exactly one series."""
        client, db = env
        s1 = _seed_site(db, "Solo Site")
        _seed_readings(db, _seed_meter(db, s1.id, "M1").id, days=2)

        r = client.get("/api/ems/timeseries", params={
            "site_ids": str(s1.id),
            "date_from": "2025-01-01", "date_to": "2025-01-03",
            "granularity": "daily", "mode": "overlay",
        })
        assert len(r.json()["series"]) == 1

    def test_overlay_aggregates_meters_within_site(self, env):
        """If a site has 2 meters, overlay sums them into one series."""
        client, db = env
        site = _seed_site(db, "Multi Meter Site")
        m1 = _seed_meter(db, site.id, "M1")
        m2 = _seed_meter(db, site.id, "M2")
        _seed_readings(db, m1.id, days=1, kwh=10)
        _seed_readings(db, m2.id, days=1, kwh=5)

        r = client.get("/api/ems/timeseries", params={
            "site_ids": str(site.id),
            "date_from": "2025-01-01", "date_to": "2025-01-02",
            "granularity": "daily", "mode": "overlay",
        })
        series = r.json()["series"]
        assert len(series) == 1
        # Daily: (10 + 5) * 24 = 360
        assert series[0]["data"][0]["v"] == 360.0

    def test_overlay_max_8_sites(self, env):
        """With exactly 8 sites, overlay produces 8 series (no 'Autres')."""
        client, db = env
        site_ids = []
        for i in range(8):
            s = _seed_site(db, f"Site {i}")
            _seed_readings(db, _seed_meter(db, s.id, f"M{i}").id, days=1)
            site_ids.append(s.id)

        r = client.get("/api/ems/timeseries", params={
            "site_ids": ",".join(str(x) for x in site_ids),
            "date_from": "2025-01-01", "date_to": "2025-01-02",
            "granularity": "daily", "mode": "overlay",
        })
        assert len(r.json()["series"]) == 8
        keys = [s["key"] for s in r.json()["series"]]
        assert "others" not in keys

    def test_overlay_9_sites_creates_autres(self, env):
        """With 9 sites, overlay produces 8 main + 1 'Autres' series."""
        client, db = env
        site_ids = []
        for i in range(9):
            s = _seed_site(db, f"Site {i}")
            _seed_readings(db, _seed_meter(db, s.id, f"M{i}").id, days=1)
            site_ids.append(s.id)

        r = client.get("/api/ems/timeseries", params={
            "site_ids": ",".join(str(x) for x in site_ids),
            "date_from": "2025-01-01", "date_to": "2025-01-02",
            "granularity": "daily", "mode": "overlay",
        })
        series = r.json()["series"]
        assert len(series) == 9  # 8 main + 1 "Autres"
        assert series[-1]["key"] == "others"
        assert "Autres" in series[-1]["label"]
        assert "1 sites" in series[-1]["label"]

    def test_overlay_12_sites_4_in_autres(self, env):
        """With 12 sites, Autres groups 4 overflow sites."""
        client, db = env
        site_ids = []
        for i in range(12):
            s = _seed_site(db, f"Site {i}")
            _seed_readings(db, _seed_meter(db, s.id, f"M{i}").id, days=1)
            site_ids.append(s.id)

        r = client.get("/api/ems/timeseries", params={
            "site_ids": ",".join(str(x) for x in site_ids),
            "date_from": "2025-01-01", "date_to": "2025-01-02",
            "granularity": "daily", "mode": "overlay",
        })
        series = r.json()["series"]
        assert len(series) == 9  # 8 main + "Autres"
        assert series[-1]["key"] == "others"
        assert "4 sites" in series[-1]["label"]

    def test_overlay_mode_accepted_by_api(self, env):
        """Overlay is a valid mode parameter (no 400)."""
        client, db = env
        s = _seed_site(db, "Test")
        r = client.get("/api/ems/timeseries", params={
            "site_ids": str(s.id),
            "date_from": "2025-01-01", "date_to": "2025-01-02",
            "granularity": "daily", "mode": "overlay",
        })
        assert r.status_code == 200
