"""
PROMEOS — Tests Demo Seed (regression guards)
1. Monthly readings produce unique (meter_id, timestamp) pairs
2. Seed is idempotent (reset + re-seed does not crash)
3. Reset hard actually deletes all rows
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, MeterReading, Meter, Site, Organisation, FrequencyType


@pytest.fixture
def db():
    """Isolated in-memory DB with schema."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def seeded_db(db):
    """DB with 1 org, 2 sites, 2 meters — ready for readings generation."""
    from models.enums import TypeSite, EnergyVector

    org = Organisation(id=1, nom="Test Corp")
    db.add(org)
    db.flush()

    site1 = Site(id=1, nom="Site A", type=TypeSite.BUREAU)
    site2 = Site(id=2, nom="Site B", type=TypeSite.BUREAU)
    db.add_all([site1, site2])
    db.flush()

    meter1 = Meter(
        id=1,
        site_id=1,
        meter_id="M001",
        name="Compteur A",
        energy_vector=EnergyVector.ELECTRICITY,
        subscribed_power_kva=100,
    )
    meter2 = Meter(
        id=2,
        site_id=2,
        meter_id="M002",
        name="Compteur B",
        energy_vector=EnergyVector.ELECTRICITY,
        subscribed_power_kva=60,
    )
    db.add_all([meter1, meter2])
    db.commit()

    return db, [meter1, meter2]


# ── Timestamp uniqueness ────────────────────────────────────────


class TestMonthlyReadingsUniqueness:
    def test_no_duplicate_timestamps_36_months(self, seeded_db):
        """36 months of readings must produce unique (meter_id, timestamp) pairs."""
        from services.demo_seed.gen_readings import generate_monthly_readings

        db, meters = seeded_db
        rng = random.Random(42)
        count = generate_monthly_readings(
            db,
            meters,
            {1: "office", 2: "hotel"},
            months=36,
            rng=rng,
        )
        db.commit()

        assert count > 0

        # Check uniqueness: count distinct vs total
        total = db.query(MeterReading).count()
        from sqlalchemy import func

        distinct = db.query(func.count(func.distinct(MeterReading.meter_id.op("||")(MeterReading.timestamp)))).scalar()
        assert total == distinct, f"Duplicate readings detected: {total} total vs {distinct} distinct"

    def test_no_duplicate_timestamps_48_months(self, seeded_db):
        """Even with 48 months (4 years) no duplicates."""
        from services.demo_seed.gen_readings import generate_monthly_readings

        db, meters = seeded_db
        rng = random.Random(99)
        count = generate_monthly_readings(
            db,
            meters,
            {1: "warehouse", 2: "school"},
            months=48,
            rng=rng,
        )
        db.commit()

        assert count > 0
        total = db.query(MeterReading).count()
        assert count == total, f"Expected {count} readings, got {total} (duplicates were skipped)"

    def test_timestamps_are_first_of_month(self, seeded_db):
        """All monthly readings must have day=1, hour=0."""
        from services.demo_seed.gen_readings import generate_monthly_readings

        db, meters = seeded_db
        rng = random.Random(42)
        generate_monthly_readings(db, meters, {1: "office", 2: "office"}, months=12, rng=rng)
        db.commit()

        readings = db.query(MeterReading).all()
        for r in readings:
            ts = r.timestamp
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            assert ts.day == 1, f"Reading {r.id}: day={ts.day}, expected 1"
            assert ts.hour == 0, f"Reading {r.id}: hour={ts.hour}, expected 0"

    def test_all_months_covered(self, seeded_db):
        """12 months should produce exactly 12 readings per meter."""
        from services.demo_seed.gen_readings import generate_monthly_readings

        db, meters = seeded_db
        rng = random.Random(42)
        count = generate_monthly_readings(
            db,
            meters,
            {1: "office", 2: "office"},
            months=12,
            rng=rng,
        )
        db.commit()

        # 2 meters × 12 months = 24
        assert count == 24, f"Expected 24, got {count}"

        # Each meter should have exactly 12 readings
        for m in meters:
            meter_count = db.query(MeterReading).filter_by(meter_id=m.id).count()
            assert meter_count == 12, f"Meter {m.id}: {meter_count} readings, expected 12"


# ── Seed idempotency (reset + re-seed) ─────────────────────────


class TestSeedIdempotency:
    def test_double_seed_no_crash(self, seeded_db):
        """Seeding twice (with reset) must not crash on UNIQUE constraint."""
        from services.demo_seed.gen_readings import generate_monthly_readings

        db, meters = seeded_db
        profiles = {1: "office", 2: "hotel"}

        # First seed
        rng1 = random.Random(42)
        c1 = generate_monthly_readings(db, meters, profiles, months=36, rng=rng1)
        db.commit()

        # Simulate reset: delete all readings
        db.query(MeterReading).delete(synchronize_session=False)
        db.commit()
        assert db.query(MeterReading).count() == 0

        # Second seed (same params) — must not crash
        rng2 = random.Random(42)
        c2 = generate_monthly_readings(db, meters, profiles, months=36, rng=rng2)
        db.commit()

        assert c2 == c1, f"Second seed produced {c2} readings vs {c1} first time"

    def test_insert_ignore_on_existing_readings(self, seeded_db):
        """INSERT OR IGNORE must silently skip duplicates without crash."""
        from services.demo_seed.gen_readings import generate_monthly_readings

        db, meters = seeded_db
        profiles = {1: "office", 2: "hotel"}

        # First seed
        rng1 = random.Random(42)
        generate_monthly_readings(db, meters, profiles, months=12, rng=rng1)
        db.commit()
        count_before = db.query(MeterReading).count()

        # Second seed WITHOUT deleting — INSERT OR IGNORE should handle it
        rng2 = random.Random(42)
        generate_monthly_readings(db, meters, profiles, months=12, rng=rng2)
        db.commit()
        count_after = db.query(MeterReading).count()

        # Count should not increase (duplicates ignored)
        assert count_after == count_before, f"Duplicates inserted: {count_after} vs {count_before}"


# ── Reset hard ─────────────────────────────────────────────────


class TestResetHard:
    def test_reset_hard_deletes_readings(self, seeded_db):
        """reset(mode='hard') must delete all MeterReading rows."""
        from services.demo_seed.gen_readings import generate_monthly_readings
        from services.demo_seed import SeedOrchestrator

        db, meters = seeded_db
        rng = random.Random(42)
        generate_monthly_readings(db, meters, {1: "office", 2: "office"}, months=12, rng=rng)
        db.commit()
        assert db.query(MeterReading).count() > 0

        orch = SeedOrchestrator(db)
        result = orch.reset(mode="hard")

        assert db.query(MeterReading).count() == 0
        assert "meter_readings" in result.get("deleted", {})

    def test_reset_hard_no_silent_failures(self, seeded_db):
        """reset(mode='hard') result must not contain 'error:' values."""
        from services.demo_seed import SeedOrchestrator

        db, _ = seeded_db
        orch = SeedOrchestrator(db)
        result = orch.reset(mode="hard")

        deleted = result.get("deleted", {})
        errors = {k: v for k, v in deleted.items() if isinstance(v, str) and v.startswith("error:")}
        assert len(errors) == 0, f"Silent failures in reset: {errors}"


# ── Frequency coherence (Issue #115) ─────────────────────────


class TestFrequencyCoherence:
    """Verify SUM(fine) == coarse at every derivation level."""

    def test_15min_sum_matches_hourly(self, seeded_db):
        """SUM(MIN_15 for hour H) == HOURLY value for H."""
        from services.demo_seed.gen_readings import (
            _gen_15min_meter_readings,
            _derive_hourly_from_15min,
        )
        from models.energy_models import EnergyVector

        db, meters = seeded_db
        rng = random.Random(42)
        meter = meters[0]
        start = datetime(2025, 6, 1)

        readings_15min = _gen_15min_meter_readings(
            meter.id,
            "office",
            {"heat": 1.5, "cool": 0.8, "peak_h": (8, 18)},
            {},
            start,
            3,
            80.0,
            100,
            120.0,
            rng,
            [],
            "",
            {},
        )
        derived_hourly = _derive_hourly_from_15min(readings_15min)

        # Build lookup: (meter_id, hour_ts) → hourly value
        hourly_lookup = {(r.meter_id, r.timestamp): r.value_kwh for r in derived_hourly}

        for hour_ts, hourly_val in hourly_lookup.items():
            meter_id, ts = hour_ts
            sum_15min = sum(
                r.value_kwh for r in readings_15min if r.meter_id == meter_id and r.timestamp.replace(minute=0) == ts
            )
            assert abs(sum_15min - hourly_val) < 0.01, f"15min sum {sum_15min:.3f} != hourly {hourly_val:.3f} at {ts}"

    def test_hourly_sum_matches_daily(self, seeded_db):
        """SUM(HOURLY for day D) == DAILY value for D."""
        from services.demo_seed.gen_readings import (
            _gen_15min_meter_readings,
            _derive_hourly_from_15min,
            _derive_daily_from_hourly,
        )

        db, meters = seeded_db
        rng = random.Random(42)
        meter = meters[0]
        start = datetime(2025, 6, 1)

        readings_15min = _gen_15min_meter_readings(
            meter.id,
            "office",
            {"heat": 1.5, "cool": 0.8, "peak_h": (8, 18)},
            {},
            start,
            5,
            80.0,
            100,
            120.0,
            rng,
            [],
            "",
            {},
        )
        hourly = _derive_hourly_from_15min(readings_15min)
        daily = _derive_daily_from_hourly(hourly)

        for dr in daily:
            sum_hourly = sum(
                r.value_kwh for r in hourly if r.meter_id == dr.meter_id and r.timestamp.date() == dr.timestamp.date()
            )
            assert abs(sum_hourly - dr.value_kwh) < 0.01, (
                f"hourly sum {sum_hourly:.2f} != daily {dr.value_kwh:.2f} at {dr.timestamp.date()}"
            )

    def test_daily_sum_matches_monthly(self, seeded_db):
        """SUM(DAILY for month M) == MONTHLY value for M."""
        from services.demo_seed.gen_readings import (
            _gen_15min_meter_readings,
            _derive_hourly_from_15min,
            _derive_daily_from_hourly,
            _derive_monthly_from_daily,
        )

        db, meters = seeded_db
        rng = random.Random(42)
        meter = meters[0]
        # 62 days spanning June + July to get at least 1 complete month
        start = datetime(2025, 6, 1)

        readings_15min = _gen_15min_meter_readings(
            meter.id,
            "office",
            {"heat": 1.5, "cool": 0.8, "peak_h": (8, 18)},
            {},
            start,
            62,
            80.0,
            100,
            120.0,
            rng,
            [],
            "",
            {},
        )
        hourly = _derive_hourly_from_15min(readings_15min)
        daily = _derive_daily_from_hourly(hourly)
        monthly = _derive_monthly_from_daily(daily)

        for mr in monthly:
            sum_daily = sum(
                r.value_kwh
                for r in daily
                if r.meter_id == mr.meter_id
                and r.timestamp.year == mr.timestamp.year
                and r.timestamp.month == mr.timestamp.month
            )
            assert abs(sum_daily - mr.value_kwh) < 1.0, (
                f"daily sum {sum_daily:.0f} != monthly {mr.value_kwh:.0f} at {mr.timestamp}"
            )
