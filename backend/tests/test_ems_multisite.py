"""
PROMEOS - EMS Multi-site Tests
5 tests covering multi-site aggregation, anti double-counting, and gas monthly.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, TypeSite, Meter, MeterReading
from models.energy_models import EnergyVector, FrequencyType
from services.ems.timeseries_service import query_timeseries


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed_site(db, name, site_id=None):
    site = Site(nom=name, type=TypeSite.BUREAU)
    if site_id:
        site.id = site_id
    db.add(site)
    db.flush()
    return site


def _seed_meter(db, site_id, name, vector=EnergyVector.ELECTRICITY):
    m = Meter(meter_id=f"PRM-{site_id}-{name}", name=name, site_id=site_id, energy_vector=vector)
    db.add(m)
    db.flush()
    return m


def _seed_readings(db, meter_id, days=3, kwh=10.0, freq=FrequencyType.HOURLY, start=None):
    start = start or datetime(2025, 1, 1)
    readings = []
    if freq == FrequencyType.MONTHLY:
        for d in range(days):
            readings.append(MeterReading(
                meter_id=meter_id,
                timestamp=start + timedelta(days=30 * d),
                frequency=freq,
                value_kwh=kwh,
            ))
    else:
        for d in range(days):
            for h in range(24):
                readings.append(MeterReading(
                    meter_id=meter_id,
                    timestamp=start + timedelta(days=d, hours=h),
                    frequency=freq,
                    value_kwh=kwh,
                ))
    db.bulk_save_objects(readings)
    db.flush()


class TestMultiSite:

    def test_aggregate_two_sites(self, db):
        s1 = _seed_site(db, "Site A")
        s2 = _seed_site(db, "Site B")
        m1 = _seed_meter(db, s1.id, "M1")
        m2 = _seed_meter(db, s2.id, "M2")
        _seed_readings(db, m1.id, days=2, kwh=10)
        _seed_readings(db, m2.id, days=2, kwh=5)

        result = query_timeseries(
            db, [s1.id, s2.id], None,
            datetime(2025, 1, 1), datetime(2025, 1, 3),
            "daily", "aggregate", "kwh",
        )
        assert len(result["series"]) == 1
        assert result["series"][0]["key"] == "total"
        # Daily: (10+5)*24 = 360
        assert result["series"][0]["data"][0]["v"] == 360.0

    def test_split_two_sites(self, db):
        s1 = _seed_site(db, "Site A")
        s2 = _seed_site(db, "Site B")
        m1 = _seed_meter(db, s1.id, "M1")
        m2 = _seed_meter(db, s2.id, "M2")
        _seed_readings(db, m1.id, days=2)
        _seed_readings(db, m2.id, days=2)

        result = query_timeseries(
            db, [s1.id, s2.id], None,
            datetime(2025, 1, 1), datetime(2025, 1, 3),
            "daily", "split", "kwh",
        )
        assert len(result["series"]) == 2

    def test_stack_two_sites(self, db):
        s1 = _seed_site(db, "Site A")
        s2 = _seed_site(db, "Site B")
        m1 = _seed_meter(db, s1.id, "M1")
        m2 = _seed_meter(db, s2.id, "M2")
        _seed_readings(db, m1.id, days=2)
        _seed_readings(db, m2.id, days=2)

        result = query_timeseries(
            db, [s1.id, s2.id], None,
            datetime(2025, 1, 1), datetime(2025, 1, 3),
            "daily", "stack", "kwh",
        )
        assert len(result["series"]) == 2

    def test_no_double_counting(self, db):
        """Two meters on same site: aggregate sums correctly without double counting."""
        site = _seed_site(db, "Single Site")
        m1 = _seed_meter(db, site.id, "M1")
        m2 = _seed_meter(db, site.id, "M2")
        _seed_readings(db, m1.id, days=1, kwh=10)
        _seed_readings(db, m2.id, days=1, kwh=5)

        result = query_timeseries(
            db, [site.id], None,
            datetime(2025, 1, 1), datetime(2025, 1, 2),
            "daily", "aggregate", "kwh",
        )
        # (10+5) * 24 = 360
        assert result["series"][0]["data"][0]["v"] == 360.0

    def test_gas_monthly_native(self, db):
        """Gas meter with monthly frequency: data not interpolated."""
        site = _seed_site(db, "Gas Site")
        gas = _seed_meter(db, site.id, "Gas", EnergyVector.GAS)
        # Seed 3 monthly readings on 1st of each month
        for month in [1, 2, 3]:
            db.add(MeterReading(
                meter_id=gas.id,
                timestamp=datetime(2025, month, 1),
                frequency=FrequencyType.MONTHLY,
                value_kwh=1000,
            ))
        db.flush()

        result = query_timeseries(
            db, [site.id], None,
            datetime(2025, 1, 1), datetime(2025, 4, 1),
            "monthly", "aggregate", "kwh", "gas",
        )
        assert len(result["series"]) == 1
        assert len(result["series"][0]["data"]) == 3
