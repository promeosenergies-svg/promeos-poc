"""
PROMEOS - EMS Timeseries Contract Tests
13 tests covering schema, modes, metrics, filters.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
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


def _seed_meter(db, site_id, name="M1", vector=EnergyVector.ELECTRICITY):
    m = Meter(meter_id=f"PRM-{site_id}-{name}", name=name, site_id=site_id, energy_vector=vector)
    db.add(m)
    db.flush()
    return m


def _seed_readings(db, meter_id, days=7, start=None, freq=FrequencyType.HOURLY, kwh=10.0):
    start = start or datetime(2025, 1, 1)
    readings = []
    for d in range(days):
        for h in range(24):
            readings.append(
                MeterReading(
                    meter_id=meter_id,
                    timestamp=start + timedelta(days=d, hours=h),
                    frequency=freq,
                    value_kwh=kwh,
                    quality_score=0.95,
                    is_estimated=False,
                )
            )
    db.bulk_save_objects(readings)
    db.flush()
    return len(readings)


class TestTimeseriesContract:
    def test_aggregate_single_series(self, env):
        client, db = env
        site = _seed_site(db)
        m1 = _seed_meter(db, site.id, "M1")
        m2 = _seed_meter(db, site.id, "M2")
        _seed_readings(db, m1.id, days=3, kwh=10)
        _seed_readings(db, m2.id, days=3, kwh=5)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-04",
                "granularity": "daily",
                "mode": "aggregate",
                "metric": "kwh",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data["series"]) == 1
        assert data["series"][0]["key"] == "total"
        assert len(data["series"][0]["data"]) == 3

    def test_stack_two_series(self, env):
        client, db = env
        site1 = _seed_site(db, "Site A")
        site2 = _seed_site(db, "Site B")
        m1 = _seed_meter(db, site1.id, "M1")
        m2 = _seed_meter(db, site2.id, "M2")
        _seed_readings(db, m1.id, days=3, kwh=10)
        _seed_readings(db, m2.id, days=3, kwh=5)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": f"{site1.id},{site2.id}",
                "date_from": "2025-01-01",
                "date_to": "2025-01-04",
                "granularity": "daily",
                "mode": "stack",
            },
        )
        assert r.status_code == 200
        series = r.json()["series"]
        assert len(series) == 2
        keys = {s["key"] for s in series}
        assert keys == {f"site_{site1.id}", f"site_{site2.id}"}

    def test_split_max_8_plus_others(self, env):
        client, db = env
        site = _seed_site(db)
        for i in range(10):
            m = _seed_meter(db, site.id, f"M{i}")
            _seed_readings(db, m.id, days=2, kwh=1)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-03",
                "granularity": "daily",
                "mode": "split",
            },
        )
        assert r.status_code == 200
        series = r.json()["series"]
        assert len(series) == 9  # 8 + "Autres"
        assert series[-1]["key"] == "others"

    def test_daily_bucket_format(self, env):
        client, db = env
        site = _seed_site(db)
        m = _seed_meter(db, site.id)
        _seed_readings(db, m.id, days=3)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-04",
                "granularity": "daily",
            },
        )
        assert r.status_code == 200
        ts = r.json()["series"][0]["data"][0]["t"]
        assert ts == "2025-01-01"

    def test_monthly_bucket_format(self, env):
        client, db = env
        site = _seed_site(db)
        m = _seed_meter(db, site.id)
        _seed_readings(db, m.id, days=60, start=datetime(2025, 1, 1))

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-03-01",
                "granularity": "monthly",
            },
        )
        assert r.status_code == 200
        data = r.json()["series"][0]["data"]
        assert data[0]["t"] == "2025-01"

    def test_kw_metric(self, env):
        client, db = env
        site = _seed_site(db)
        m = _seed_meter(db, site.id)
        _seed_readings(db, m.id, days=1, kwh=24.0)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-02",
                "granularity": "daily",
                "metric": "kw",
            },
        )
        assert r.status_code == 200
        # 24 readings * 24 kWh = 576 kWh/day, /24h = 24 kW
        val = r.json()["series"][0]["data"][0]["v"]
        assert val == 24.0

    def test_hourly_kw_same_as_kwh(self, env):
        client, db = env
        site = _seed_site(db)
        m = _seed_meter(db, site.id)
        _seed_readings(db, m.id, days=1, kwh=5.0)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-02",
                "granularity": "hourly",
                "metric": "kw",
            },
        )
        # hourly bucket = 1h, so kW = kWh/1 = kWh
        val = r.json()["series"][0]["data"][0]["v"]
        assert val == 5.0

    def test_quality_metadata(self, env):
        client, db = env
        site = _seed_site(db)
        m = _seed_meter(db, site.id)
        _seed_readings(db, m.id, days=1)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-02",
                "granularity": "daily",
            },
        )
        pt = r.json()["series"][0]["data"][0]
        assert "quality" in pt
        assert "estimated_pct" in pt
        assert pt["quality"] == 0.95

    def test_energy_vector_filter(self, env):
        client, db = env
        site = _seed_site(db)
        elec = _seed_meter(db, site.id, "Elec", EnergyVector.ELECTRICITY)
        gas = _seed_meter(db, site.id, "Gas", EnergyVector.GAS)
        _seed_readings(db, elec.id, days=2, kwh=10)
        _seed_readings(db, gas.id, days=2, kwh=3)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-03",
                "granularity": "daily",
                "energy_vector": "gas",
            },
        )
        assert r.status_code == 200
        assert r.json()["meta"]["n_meters"] == 1
        # daily gas: 24h * 3 kWh = 72 kWh
        assert r.json()["series"][0]["data"][0]["v"] == 72.0

    def test_date_range_filter(self, env):
        client, db = env
        site = _seed_site(db)
        m = _seed_meter(db, site.id)
        _seed_readings(db, m.id, days=10)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-03",
                "date_to": "2025-01-06",
                "granularity": "daily",
            },
        )
        assert r.status_code == 200
        assert len(r.json()["series"][0]["data"]) == 3

    def test_empty_site(self, env):
        client, db = env
        site = _seed_site(db)

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-04",
                "granularity": "daily",
            },
        )
        assert r.status_code == 200
        assert r.json()["series"] == []

    def test_suggest_7d(self, env):
        client, _ = env
        r = client.get(
            "/api/ems/timeseries/suggest",
            params={
                "date_from": "2025-01-01",
                "date_to": "2025-01-08",
            },
        )
        assert r.status_code == 200
        assert r.json()["granularity"] == "hourly"

    def test_suggest_180d(self, env):
        client, _ = env
        r = client.get(
            "/api/ems/timeseries/suggest",
            params={
                "date_from": "2025-01-01",
                "date_to": "2025-07-01",
            },
        )
        assert r.status_code == 200
        assert r.json()["granularity"] == "daily"

    def test_hourly_aggregation_with_enedis_mixed_frequencies(self, env):
        """Enedis pattern: HOURLY at :00 (full hour) + MIN_15 at :15/:30/:45 only.

        Each hourly bucket must equal the HOURLY reading (10.0 kWh), not the
        sum of the 3 MIN_15 readings (7.5 kWh).  Regression test for #97.
        """
        client, db = env
        site = _seed_site(db, "Enedis Site")
        meter = _seed_meter(db, site.id, "PRM-ENEDIS")

        readings = []
        start = datetime(2025, 1, 1)
        days = 3
        for d in range(days):
            for h in range(24):
                ts_base = start + timedelta(days=d, hours=h)
                # HOURLY reading at :00 — represents the full hour (10 kWh)
                readings.append(
                    MeterReading(
                        meter_id=meter.id,
                        timestamp=ts_base,
                        frequency=FrequencyType.HOURLY,
                        value_kwh=10.0,
                        quality_score=0.95,
                        is_estimated=False,
                    )
                )
                # MIN_15 readings at :15, :30, :45 only (2.5 kWh each)
                for minute in (15, 30, 45):
                    readings.append(
                        MeterReading(
                            meter_id=meter.id,
                            timestamp=ts_base + timedelta(minutes=minute),
                            frequency=FrequencyType.MIN_15,
                            value_kwh=2.5,
                            quality_score=0.95,
                            is_estimated=False,
                        )
                    )
        db.bulk_save_objects(readings)
        db.flush()

        r = client.get(
            "/api/ems/timeseries",
            params={
                "site_ids": str(site.id),
                "date_from": "2025-01-01",
                "date_to": "2025-01-04",
                "granularity": "hourly",
                "mode": "aggregate",
                "metric": "kwh",
            },
        )
        assert r.status_code == 200
        data = r.json()
        series = data["series"]
        assert len(series) == 1
        # Each hourly bucket should be 10.0 kWh (HOURLY reading), not 7.5 (3×MIN_15)
        for pt in series[0]["data"]:
            assert pt["v"] == pytest.approx(10.0, abs=0.1), (
                f"Bucket {pt['t']}: expected 10.0 kWh, got {pt['v']} (Enedis mixed-frequency underestimate bug #97)"
            )
