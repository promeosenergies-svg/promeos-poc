"""
PROMEOS - EMS DST Bucketization Tests
4 tests verifying correct aggregation through DST transitions.
Since timestamps are UTC-naive, DST handling verifies correct bucketing
when real-world data has 23 or 25 hourly readings per calendar day.
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


def _seed(db):
    site = Site(id=1, nom="DST", type=TypeSite.BUREAU)
    db.add(site)
    db.flush()
    m = Meter(meter_id="PRM-DST-1", name="DST-M", site_id=1, energy_vector=EnergyVector.ELECTRICITY)
    db.add(m)
    db.flush()
    return m


class TestDST:
    def test_23h_day_spring(self, db):
        """Spring forward: only 23 readings for March 30, 2025 (CET→CEST)."""
        m = _seed(db)
        # Simulate 23 readings for that day
        base = datetime(2025, 3, 30)
        for h in range(23):
            db.add(
                MeterReading(
                    meter_id=m.id,
                    timestamp=base + timedelta(hours=h),
                    frequency=FrequencyType.HOURLY,
                    value_kwh=1.0,
                )
            )
        db.flush()

        result = query_timeseries(db, [1], None, base, base + timedelta(days=1), "daily", "aggregate", "kwh")
        assert len(result["series"]) == 1
        assert len(result["series"][0]["data"]) == 1
        assert result["series"][0]["data"][0]["v"] == 23.0

    def test_25h_day_fall(self, db):
        """Fall back: 25 readings for October 26, 2025 (CEST→CET)."""
        m = _seed(db)
        base = datetime(2025, 10, 26)
        for h in range(25):
            db.add(
                MeterReading(
                    meter_id=m.id,
                    timestamp=base + timedelta(hours=h),
                    frequency=FrequencyType.HOURLY,
                    value_kwh=1.0,
                )
            )
        db.flush()

        result = query_timeseries(db, [1], None, base, base + timedelta(days=2), "daily", "aggregate", "kwh")
        # 25 readings: 24 in day 1 bucket, 1 in day 2 bucket
        total = sum(pt["v"] for s in result["series"] for pt in s["data"])
        assert total == 25.0

    def test_hourly_no_gaps(self, db):
        """Hourly buckets through DST transition have no duplicate/missing buckets."""
        m = _seed(db)
        base = datetime(2025, 3, 29, 22)  # 22:00 the day before spring forward
        for h in range(8):  # 22:00 - 05:00 next day
            db.add(
                MeterReading(
                    meter_id=m.id,
                    timestamp=base + timedelta(hours=h),
                    frequency=FrequencyType.HOURLY,
                    value_kwh=1.0,
                )
            )
        db.flush()

        result = query_timeseries(
            db,
            [1],
            None,
            base,
            base + timedelta(hours=8),
            "hourly",
            "aggregate",
            "kwh",
        )
        assert len(result["series"][0]["data"]) == 8

    def test_monthly_ignores_dst(self, db):
        """Monthly aggregation is not affected by DST."""
        m = _seed(db)
        # Seed March + April data
        for d in range(60):
            dt = datetime(2025, 3, 1) + timedelta(days=d)
            db.add(
                MeterReading(
                    meter_id=m.id,
                    timestamp=dt,
                    frequency=FrequencyType.DAILY,
                    value_kwh=10.0,
                )
            )
        db.flush()

        result = query_timeseries(
            db,
            [1],
            None,
            datetime(2025, 3, 1),
            datetime(2025, 5, 1),
            "monthly",
            "aggregate",
            "kwh",
        )
        assert len(result["series"][0]["data"]) == 2
        buckets = [pt["t"] for pt in result["series"][0]["data"]]
        assert "2025-03" in buckets
        assert "2025-04" in buckets
