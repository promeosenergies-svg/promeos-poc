"""
PROMEOS — Schedule Intervals V1.1 tests
Tests validate_intervals + PUT /api/site/{id}/schedule with multi-interval support.

Covers:
  - Valid single interval per day
  - Valid multiple intervals (adjacent OK)
  - Overlap → 422
  - Invalid time format → 422
  - Midnight crossing (start >= end) → 422
  - Empty day (closed) → valid
  - Legacy open_time/close_time still works
  - intervals_json stored and returned
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Organisation, EntiteJuridique, Portefeuille, TypeSite
from database import get_db
from main import app
from routes.site_config import validate_intervals, _parse_hhmm


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
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_site(db):
    org = Organisation(nom="Sched Test Corp", type_client="bureau", actif=True)
    db.add(org); db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="999777555")
    db.add(ej); db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf); db.flush()
    site = Site(
        nom="Site Sched Test", type=TypeSite.BUREAU,
        adresse="1 rue Test", code_postal="75001", ville="Paris",
        surface_m2=500, portefeuille_id=pf.id,
    )
    db.add(site); db.flush(); db.commit()
    return site


# ═══════════════════════════════════════════════
# A. Pure validation: validate_intervals
# ═══════════════════════════════════════════════

class TestValidateIntervals:
    """Pure function tests for validate_intervals."""

    def test_valid_single_interval(self):
        intervals = {"0": [{"start": "08:00", "end": "19:00"}]}
        assert validate_intervals(intervals) == []

    def test_valid_multi_interval(self):
        intervals = {"0": [
            {"start": "08:00", "end": "12:00"},
            {"start": "13:00", "end": "18:00"},
        ]}
        assert validate_intervals(intervals) == []

    def test_valid_adjacent_intervals(self):
        """Adjacent intervals (end == next start) must be allowed."""
        intervals = {"0": [
            {"start": "08:00", "end": "12:00"},
            {"start": "12:00", "end": "18:00"},
        ]}
        assert validate_intervals(intervals) == []

    def test_valid_empty_day(self):
        """Empty list = day closed = valid."""
        intervals = {"0": [], "5": [], "6": []}
        assert validate_intervals(intervals) == []

    def test_overlap_detected(self):
        intervals = {"0": [
            {"start": "08:00", "end": "14:00"},
            {"start": "11:00", "end": "18:00"},
        ]}
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["code"] == "overlap"
        assert "Chevauchement" in errs[0]["message"] or "chevauchement" in errs[0]["message"]

    def test_start_ge_end(self):
        """start >= end (midnight crossing) → error."""
        intervals = {"0": [{"start": "19:00", "end": "08:00"}]}
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["code"] == "start_ge_end"

    def test_start_eq_end(self):
        """start == end → error."""
        intervals = {"0": [{"start": "08:00", "end": "08:00"}]}
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["code"] == "start_ge_end"

    def test_invalid_time_format(self):
        intervals = {"0": [{"start": "8:00", "end": "19:00"}]}
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["code"] == "invalid_start"

    def test_invalid_hours(self):
        intervals = {"0": [{"start": "25:00", "end": "19:00"}]}
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["code"] == "invalid_start"

    def test_invalid_day_key(self):
        intervals = {"8": [{"start": "08:00", "end": "19:00"}]}
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["code"] == "invalid_day"

    def test_missing_fields(self):
        intervals = {"0": [{"start": "08:00"}]}
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["code"] == "missing_fields"

    def test_invalid_type(self):
        errs = validate_intervals("not a dict")
        assert len(errs) == 1
        assert errs[0]["code"] == "invalid_type"

    def test_multiple_days_partial_errors(self):
        """Errors on one day, valid on another."""
        intervals = {
            "0": [{"start": "08:00", "end": "12:00"}],  # valid
            "1": [{"start": "19:00", "end": "08:00"}],  # invalid
        }
        errs = validate_intervals(intervals)
        assert len(errs) == 1
        assert errs[0]["day"] == "1"


class TestParseHHMM:
    def test_valid(self):
        assert _parse_hhmm("08:00") == 480
        assert _parse_hhmm("23:59") == 1439
        assert _parse_hhmm("00:00") == 0

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            _parse_hhmm("8:00")

    def test_invalid_hours(self):
        with pytest.raises(ValueError):
            _parse_hhmm("25:00")


# ═══════════════════════════════════════════════
# B. API endpoint: PUT /api/site/{id}/schedule
# ═══════════════════════════════════════════════

class TestScheduleAPI:
    """HTTP tests for schedule endpoint with intervals_json."""

    def test_put_valid_intervals_200(self, client, db):
        """Valid intervals_json → 200 + stored."""
        site = _create_site(db)
        intervals = {
            "0": [{"start": "08:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}],
            "1": [{"start": "09:00", "end": "17:00"}],
        }
        payload = {
            "open_days": "0,1",
            "open_time": "08:00",
            "close_time": "18:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "intervals_json": json.dumps(intervals),
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["intervals_json"] is not None
        stored = json.loads(data["intervals_json"])
        assert len(stored["0"]) == 2

    def test_put_overlap_422(self, client, db):
        """Overlapping intervals → 422."""
        site = _create_site(db)
        intervals = {"0": [
            {"start": "08:00", "end": "14:00"},
            {"start": "11:00", "end": "18:00"},
        ]}
        payload = {
            "open_days": "0,1,2,3,4",
            "open_time": "08:00",
            "close_time": "18:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "intervals_json": json.dumps(intervals),
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 422

    def test_put_midnight_crossing_422(self, client, db):
        """Midnight crossing (start > end) → 422."""
        site = _create_site(db)
        intervals = {"0": [{"start": "22:00", "end": "06:00"}]}
        payload = {
            "open_days": "0",
            "open_time": "08:00",
            "close_time": "18:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "intervals_json": json.dumps(intervals),
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 422

    def test_put_invalid_format_422(self, client, db):
        """Bad time format → 422."""
        site = _create_site(db)
        intervals = {"0": [{"start": "8h00", "end": "19:00"}]}
        payload = {
            "open_days": "0",
            "open_time": "08:00",
            "close_time": "19:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "intervals_json": json.dumps(intervals),
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 422

    def test_put_legacy_still_works(self, client, db):
        """Legacy payload without intervals_json → 200."""
        site = _create_site(db)
        payload = {
            "open_days": "0,1,2,3,4",
            "open_time": "08:00",
            "close_time": "19:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_time"] == "08:00"
        assert data["intervals_json"] is None

    def test_put_legacy_start_ge_end_422(self, client, db):
        """Legacy: open_time >= close_time without intervals → 422."""
        site = _create_site(db)
        payload = {
            "open_days": "0,1,2,3,4",
            "open_time": "19:00",
            "close_time": "08:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 422

    def test_get_returns_intervals_json(self, client, db):
        """GET after PUT with intervals → intervals_json in response."""
        site = _create_site(db)
        intervals = {"0": [{"start": "08:00", "end": "12:00"}]}
        payload = {
            "open_days": "0",
            "open_time": "08:00",
            "close_time": "12:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "intervals_json": json.dumps(intervals),
        }
        client.put(f"/api/site/{site.id}/schedule", json=payload)
        resp = client.get(f"/api/site/{site.id}/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert data["intervals_json"] is not None

    def test_put_adjacent_intervals_200(self, client, db):
        """Adjacent intervals (end == next start) → 200 OK."""
        site = _create_site(db)
        intervals = {"0": [
            {"start": "08:00", "end": "12:00"},
            {"start": "12:00", "end": "18:00"},
        ]}
        payload = {
            "open_days": "0",
            "open_time": "08:00",
            "close_time": "18:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "intervals_json": json.dumps(intervals),
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 200

    def test_intervals_syncs_legacy_fields(self, client, db):
        """intervals_json auto-syncs open_days/open_time/close_time."""
        site = _create_site(db)
        intervals = {
            "0": [{"start": "07:00", "end": "12:00"}],
            "1": [{"start": "09:00", "end": "20:00"}],
        }
        payload = {
            "open_days": "0,1,2,3,4",  # will be overridden
            "open_time": "08:00",       # will be overridden
            "close_time": "19:00",      # will be overridden
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "intervals_json": json.dumps(intervals),
        }
        resp = client.put(f"/api/site/{site.id}/schedule", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_time"] == "07:00"  # earliest
        assert data["close_time"] == "20:00"  # latest
        assert "0" in data["open_days"]
        assert "1" in data["open_days"]
