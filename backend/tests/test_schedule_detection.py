"""
PROMEOS — Schedule Detection V0 tests
Tests auto-detection algorithm on synthetic load curves + API endpoints.

Covers:
  - detect_schedule on synthetic 15min data (clear office pattern)
  - compare_schedules (declared vs detected)
  - Insufficient data raises ValueError
  - Confidence scoring (coverage, stability, separation)
  - API endpoints: /activity/detected, /activity/compare, /activity/apply_detected
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import math
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, EntiteJuridique, Portefeuille
from models.enums import TypeSite
from models.energy_models import Meter, MeterReading, FrequencyType, EnergyVector
from models.site_operating_schedule import SiteOperatingSchedule
from database import get_db
from main import app


# ═══════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════

@pytest.fixture
def db():
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
def site_with_meter(db):
    """Create org → ej → ptf → site → meter chain."""
    org = Organisation(nom="Test Org", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(nom="Test EJ", siren="000000001", organisation_id=org.id)
    db.add(ej)
    db.flush()
    ptf = Portefeuille(nom="Test PTF", entite_juridique_id=ej.id)
    db.add(ptf)
    db.flush()
    site = Site(
        nom="Bureau Test", type=TypeSite.BUREAU,
        portefeuille_id=ptf.id, adresse="1 rue Test",
        surface_m2=500, actif=True,
    )
    db.add(site)
    db.flush()
    meter = Meter(
        meter_id="PRM-TEST-001", name="Compteur principal",
        energy_vector=EnergyVector.ELECTRICITY, site_id=site.id,
        is_active=True,
    )
    db.add(meter)
    db.flush()
    return site, meter


def _generate_office_load(db, meter, days=60, step_min=15):
    """Generate synthetic 15-min load data: office pattern Mon-Fri 08:00-18:00.

    Active hours: baseload (5 kWh) + activity (15 kWh) = 20 kWh
    Inactive hours: baseload only (5 kWh)
    Weekend: baseload only (5 kWh)
    """
    baseload = 5.0
    activity = 15.0
    now = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)

    readings = []
    t = start
    while t < now:
        dow = t.weekday()  # 0=Mon, 6=Sun
        hour = t.hour
        minute = t.minute
        total_min = hour * 60 + minute

        # Office pattern: Mon-Fri 08:00 to 18:00
        is_active = dow < 5 and 8 * 60 <= total_min < 18 * 60

        value = baseload + (activity if is_active else 0.0)

        readings.append(MeterReading(
            meter_id=meter.id,
            timestamp=t,
            frequency=FrequencyType.MIN_15 if step_min == 15 else FrequencyType.HOURLY,
            value_kwh=value,
            is_estimated=False,
        ))

        t += timedelta(minutes=step_min)

    db.bulk_save_objects(readings)
    db.flush()
    return len(readings)


@pytest.fixture
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════
# A. Unit tests: detection algorithm
# ═══════════════════════════════════════════════

class TestDetectSchedule:
    """Tests for detect_schedule on synthetic data."""

    def test_detects_office_pattern(self, db, site_with_meter):
        """Synthetic office load → detected schedule should be Mon-Fri ~08:00-18:00."""
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        from services.schedule_detection_service import detect_schedule
        result = detect_schedule(db, site.id, window_days=60)

        assert result["site_id"] == site.id
        assert "detected_schedule" in result
        assert "confidence" in result
        sched = result["detected_schedule"]

        # Mon-Fri should have intervals, Sat/Sun should be empty or minimal
        for dow in ["0", "1", "2", "3", "4"]:
            assert len(sched[dow]) >= 1, f"Weekday {dow} should have at least 1 interval"

        # Check first weekday interval roughly covers office hours
        mon_interval = sched["0"][0]
        assert mon_interval["start"] <= "09:00", f"Start {mon_interval['start']} should be <= 09:00"
        assert mon_interval["end"] >= "17:00", f"End {mon_interval['end']} should be >= 17:00"

    def test_weekend_empty_or_minimal(self, db, site_with_meter):
        """Weekend should have no intervals in office-only pattern."""
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        from services.schedule_detection_service import detect_schedule
        result = detect_schedule(db, site.id, window_days=60)
        sched = result["detected_schedule"]

        # Saturday and Sunday should have no intervals (pure baseload)
        for dow in ["5", "6"]:
            assert len(sched[dow]) == 0, f"Weekend day {dow} should be empty, got {sched[dow]}"

    def test_confidence_high_for_clean_data(self, db, site_with_meter):
        """Clean synthetic data should produce high confidence."""
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        from services.schedule_detection_service import detect_schedule
        result = detect_schedule(db, site.id, window_days=60)

        assert result["confidence"] >= 0.5, f"Confidence {result['confidence']} should be >= 0.5"
        assert result["confidence_label"] in ["ELEVEE", "MOYEN"]

    def test_evidence_fields_present(self, db, site_with_meter):
        """Evidence dict should contain all expected fields."""
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        from services.schedule_detection_service import detect_schedule
        result = detect_schedule(db, site.id, window_days=60)
        ev = result["evidence"]

        assert "coverage" in ev
        assert "stability_score" in ev
        assert "separation_score" in ev
        assert "baseload_stats" in ev
        assert ev["coverage_days"] > 0

    def test_insufficient_data_raises(self, db, site_with_meter):
        """Less than MIN_DAYS should raise ValueError."""
        site, meter = site_with_meter
        # Generate only 3 days of data
        _generate_office_load(db, meter, days=3, step_min=15)

        from services.schedule_detection_service import detect_schedule
        with pytest.raises(ValueError, match="insuffisantes"):
            detect_schedule(db, site.id, window_days=60)


# ═══════════════════════════════════════════════
# B. Unit tests: compare_schedules
# ═══════════════════════════════════════════════

class TestCompareSchedules:
    """Tests for compare_schedules function."""

    def test_identical_schedules(self):
        from services.schedule_detection_service import compare_schedules
        sched = {
            "0": [{"start": "08:00", "end": "18:00"}],
            "1": [{"start": "08:00", "end": "18:00"}],
            "2": [{"start": "08:00", "end": "18:00"}],
            "3": [{"start": "08:00", "end": "18:00"}],
            "4": [{"start": "08:00", "end": "18:00"}],
            "5": [],
            "6": [],
        }
        result = compare_schedules(sched, sched)
        assert result["global_status"] == "OK"
        for k in ["0", "1", "2", "3", "4", "5", "6"]:
            assert result["diff"][k]["status"] == "OK"

    def test_mismatch_different_hours(self):
        from services.schedule_detection_service import compare_schedules
        declared = {"0": [{"start": "08:00", "end": "18:00"}], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []}
        detected = {"0": [{"start": "06:00", "end": "20:00"}], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []}
        result = compare_schedules(declared, detected)
        assert result["global_status"] == "MISMATCH"
        assert result["diff"]["0"]["status"] == "MISMATCH"
        assert result["diff"]["0"]["delta_minutes"] == 240  # (14h - 10h) * 60

    def test_mismatch_different_interval_count(self):
        from services.schedule_detection_service import compare_schedules
        declared = {"0": [{"start": "08:00", "end": "18:00"}], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []}
        detected = {
            "0": [{"start": "08:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}],
            "1": [], "2": [], "3": [], "4": [], "5": [], "6": [],
        }
        result = compare_schedules(declared, detected)
        assert result["global_status"] == "MISMATCH"
        # Different interval counts triggers mismatch even if total minutes close
        assert result["diff"]["0"]["declared_intervals"] == 1
        assert result["diff"]["0"]["detected_intervals"] == 2

    def test_small_delta_ok(self):
        from services.schedule_detection_service import compare_schedules
        declared = {"0": [{"start": "08:00", "end": "18:00"}], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []}
        detected = {"0": [{"start": "08:00", "end": "18:30"}], "1": [], "2": [], "3": [], "4": [], "5": [], "6": []}
        result = compare_schedules(declared, detected)
        # 30min delta, same interval count → OK (threshold is 60min)
        assert result["diff"]["0"]["status"] == "OK"


# ═══════════════════════════════════════════════
# C. API endpoint tests
# ═══════════════════════════════════════════════

class TestDetectionAPI:
    """Tests for the 3 detection endpoints."""

    def test_detected_endpoint(self, db, client, site_with_meter):
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        resp = client.get(f"/api/consumption-context/site/{site.id}/activity/detected")
        assert resp.status_code == 200
        data = resp.json()
        assert "detected_schedule" in data
        assert "confidence" in data
        assert "evidence" in data

    def test_detected_insufficient_data(self, db, client, site_with_meter):
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=3, step_min=15)

        resp = client.get(f"/api/consumption-context/site/{site.id}/activity/detected")
        assert resp.status_code == 422

    def test_detected_site_not_found(self, client):
        resp = client.get("/api/consumption-context/site/99999/activity/detected")
        assert resp.status_code == 404

    def test_compare_endpoint(self, db, client, site_with_meter):
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        resp = client.get(f"/api/consumption-context/site/{site.id}/activity/compare")
        assert resp.status_code == 200
        data = resp.json()
        assert "declared" in data
        assert "detected" in data
        assert "comparison" in data
        assert "confidence" in data
        assert data["comparison"]["global_status"] in ["OK", "MISMATCH"]

    def test_apply_detected_endpoint(self, db, client, site_with_meter):
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        resp = client.post(f"/api/consumption-context/site/{site.id}/activity/apply_detected")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert "detected_schedule" in data
        assert "confidence" in data

        # Verify saved in DB
        sched = db.query(SiteOperatingSchedule).filter(
            SiteOperatingSchedule.site_id == site.id
        ).first()
        assert sched is not None
        assert sched.intervals_json is not None
        intervals = json.loads(sched.intervals_json)
        # Should have weekday intervals
        assert len(intervals["0"]) >= 1

    def test_apply_detected_updates_existing(self, db, client, site_with_meter):
        """Apply should update existing schedule, not create duplicate."""
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=60, step_min=15)

        # Create initial schedule
        sched = SiteOperatingSchedule(
            site_id=site.id, timezone="Europe/Paris",
            open_days="0,1,2,3,4", open_time="09:00", close_time="17:00",
        )
        db.add(sched)
        db.commit()

        resp = client.post(f"/api/consumption-context/site/{site.id}/activity/apply_detected")
        assert resp.status_code == 200

        # Should still be exactly 1 schedule
        count = db.query(SiteOperatingSchedule).filter(
            SiteOperatingSchedule.site_id == site.id
        ).count()
        assert count == 1

        # Verify it was updated
        updated = db.query(SiteOperatingSchedule).filter(
            SiteOperatingSchedule.site_id == site.id
        ).first()
        assert updated.intervals_json is not None

    def test_apply_detected_insufficient_data(self, db, client, site_with_meter):
        site, meter = site_with_meter
        _generate_office_load(db, meter, days=3, step_min=15)

        resp = client.post(f"/api/consumption-context/site/{site.id}/activity/apply_detected")
        assert resp.status_code == 422


# ═══════════════════════════════════════════════
# D. Helper unit tests
# ═══════════════════════════════════════════════

class TestHelpers:
    """Tests for internal helper functions."""

    def test_quantile(self):
        from services.schedule_detection_service import _quantile
        assert _quantile([1, 2, 3, 4, 5], 0.5) == 3.0
        assert _quantile([1, 2, 3, 4, 5], 0.0) == 1.0
        assert _quantile([1, 2, 3, 4, 5], 1.0) == 5.0
        assert _quantile([], 0.5) == 0.0

    def test_minutes_to_hhmm(self):
        from services.schedule_detection_service import _minutes_to_hhmm
        assert _minutes_to_hhmm(0) == "00:00"
        assert _minutes_to_hhmm(480) == "08:00"
        assert _minutes_to_hhmm(1080) == "18:00"
        assert _minutes_to_hhmm(1439) == "23:59"

    def test_hhmm_to_min(self):
        from services.schedule_detection_service import _hhmm_to_min
        assert _hhmm_to_min("08:00") == 480
        assert _hhmm_to_min("18:00") == 1080
        assert _hhmm_to_min("00:00") == 0

    def test_get_declared_intervals_default(self, db, site_with_meter):
        """No schedule → default Mon-Fri 08:00-19:00."""
        site, _ = site_with_meter
        from services.schedule_detection_service import get_declared_intervals
        result = get_declared_intervals(db, site.id)
        assert len(result["0"]) == 1
        assert result["0"][0]["start"] == "08:00"
        assert result["5"] == []
