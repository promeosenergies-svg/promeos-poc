"""
PROMEOS — Tests Consumption Context V0
~20 tests: behavior_score, weekend_active, profile, activity, API endpoints.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    Meter, MeterReading, TypeSite, ConsumptionInsight,
)
from models.energy_models import FrequencyType, EnergyVector
from models.site_operating_schedule import SiteOperatingSchedule
from database import get_db
from main import app

from services.consumption_context_service import (
    compute_behavior_score,
    detect_weekend_active,
)


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


def _create_org_site(db, surface=2000):
    org = Organisation(nom="Context Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="999888777")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Site Context Test", type=TypeSite.BUREAU,
        adresse="1 rue Test", code_postal="75001", ville="Paris",
        surface_m2=surface, portefeuille_id=pf.id,
    )
    db.add(site)
    db.flush()
    return org, site


def _create_meter_with_readings(db, site, days=30, hourly_kwh=10.0,
                                weekend_factor=0.2):
    """Create a meter + hourly readings for `days` days."""
    import uuid
    meter = Meter(
        site_id=site.id,
        meter_id=f"PRM-{uuid.uuid4().hex[:8]}",
        name="Meter Elec",
        energy_vector=EnergyVector.ELECTRICITY,
        is_active=True,
    )
    db.add(meter)
    db.flush()

    now = datetime.utcnow()
    start = now - timedelta(days=days)
    t = start
    while t < now:
        wd = t.weekday()
        val = hourly_kwh * weekend_factor if wd >= 5 else hourly_kwh
        db.add(MeterReading(
            meter_id=meter.id,
            timestamp=t,
            value_kwh=val,
            frequency=FrequencyType.HOURLY,
        ))
        t += timedelta(hours=1)
    db.flush()
    return meter


# ═══════════════════════════════════════════════
# A. behavior_score — pure computation
# ═══════════════════════════════════════════════

class TestBehaviorScore:
    """Pure function: compute_behavior_score."""

    def test_perfect_score(self):
        """All KPIs = 0 → score = 100."""
        score, bd = compute_behavior_score(0, 0, 0, 0)
        assert score == 100
        assert bd["total_penalty"] == 0

    def test_worst_score(self):
        """Extreme KPIs → score near 0 (< 30)."""
        score, bd = compute_behavior_score(100, 100, 50, 1.0)
        assert score < 30
        assert score >= 0

    def test_medium_score(self):
        """Moderate KPIs → score between 40-70."""
        score, bd = compute_behavior_score(15, 45, 5, 0.4)
        assert 30 <= score <= 80

    def test_penalties_capped(self):
        """Each penalty is individually capped."""
        score, bd = compute_behavior_score(200, 200, 200, 5.0)
        assert bd["offhours_penalty"] == 40
        assert bd["baseload_penalty"] == 25
        assert bd["drift_penalty"] == 20
        assert bd["weekend_penalty"] == 15
        assert score == 0  # 100 - (40+25+20+15) = 0

    def test_negative_kpis_no_penalty(self):
        """Negative KPIs → penalties floor at 0."""
        score, bd = compute_behavior_score(-10, -10, -10, -1)
        assert score == 100
        assert bd["total_penalty"] == 0


# ═══════════════════════════════════════════════
# B. weekend_active — pure computation
# ═══════════════════════════════════════════════

class TestWeekendActive:
    """detect_weekend_active: dict-based readings."""

    @staticmethod
    def _make_readings(n_weekday, n_weekend, wd_val=10, we_val=2):
        readings = []
        # weekday readings (Mon=0)
        for i in range(n_weekday):
            readings.append({"weekday": 0, "value_kwh": wd_val})
        # weekend readings (Sat=5)
        for i in range(n_weekend):
            readings.append({"weekday": 5, "value_kwh": we_val})
        return readings

    def test_detected_high(self):
        """ratio > 0.8 → detected=True, severity=high."""
        r = self._make_readings(40, 20, wd_val=10, we_val=9)
        res = detect_weekend_active(r, {"open_days": {0, 1, 2, 3, 4}})
        assert res["detected"] is True
        assert res["severity"] == "high"

    def test_detected_medium(self):
        """0.5 < ratio < 0.8 → detected=True, severity=medium."""
        r = self._make_readings(40, 20, wd_val=10, we_val=6)
        res = detect_weekend_active(r, {"open_days": {0, 1, 2, 3, 4}})
        assert res["detected"] is True
        assert res["severity"] == "medium"

    def test_not_detected_low_ratio(self):
        """ratio < 0.5 → detected=False."""
        r = self._make_readings(40, 20, wd_val=10, we_val=3)
        res = detect_weekend_active(r, {"open_days": {0, 1, 2, 3, 4}})
        assert res["detected"] is False

    def test_24_7_skip(self):
        """is_24_7 → always not detected."""
        r = self._make_readings(40, 20, wd_val=10, we_val=9)
        res = detect_weekend_active(r, {"is_24_7": True})
        assert res["detected"] is False
        assert res["reason"] == "is_24_7"

    def test_weekends_open_skip(self):
        """open_days includes 5 and 6 → not detected."""
        r = self._make_readings(40, 20, wd_val=10, we_val=9)
        res = detect_weekend_active(r, {"open_days": {0, 1, 2, 3, 4, 5, 6}})
        assert res["detected"] is False
        assert res["reason"] == "weekends_open"

    def test_insufficient_data(self):
        """< 48 readings → insufficient_data."""
        r = self._make_readings(10, 5)
        res = detect_weekend_active(r, {"open_days": {0, 1, 2, 3, 4}})
        assert res["detected"] is False
        assert res["reason"] == "insufficient_data"


# ═══════════════════════════════════════════════
# C. profile — via DB
# ═══════════════════════════════════════════════

class TestConsumptionProfile:
    """get_consumption_profile: requires DB with meter + readings."""

    def test_daily_profile_24_points(self, db):
        """daily_profile always has 24 entries."""
        from services.consumption_context_service import get_consumption_profile
        _, site = _create_org_site(db)
        _create_meter_with_readings(db, site, days=7)
        db.commit()
        result = get_consumption_profile(db, site.id, days=7)
        assert len(result["daily_profile"]) == 24

    def test_baseload_positive(self, db):
        """baseload_kw >= 0 when readings exist."""
        from services.consumption_context_service import get_consumption_profile
        _, site = _create_org_site(db)
        _create_meter_with_readings(db, site, days=7, hourly_kwh=5.0)
        db.commit()
        result = get_consumption_profile(db, site.id, days=7)
        assert result["baseload_kw"] >= 0
        assert result["peak_kw"] >= result["baseload_kw"]

    def test_empty_readings(self, db):
        """No readings → baseload=0, daily_profile all zeros, heatmap empty."""
        from services.consumption_context_service import get_consumption_profile
        _, site = _create_org_site(db)
        db.commit()
        result = get_consumption_profile(db, site.id, days=30)
        assert result["baseload_kw"] == 0
        assert result["peak_kw"] == 0
        assert len(result["daily_profile"]) == 24
        for pt in result["daily_profile"]:
            assert pt["avg_kwh"] == 0


# ═══════════════════════════════════════════════
# D. activity context
# ═══════════════════════════════════════════════

class TestActivityContext:
    """get_activity_context: schedule, archetype, TOU."""

    def test_default_schedule(self, db):
        """No SiteOperatingSchedule → default Mon-Fri 08-19."""
        from services.consumption_context_service import get_activity_context
        _, site = _create_org_site(db)
        db.commit()
        result = get_activity_context(db, site.id)
        assert result["schedule"]["source"] == "default"
        assert result["schedule"]["open_time"] == "08:00"
        assert result["schedule"]["close_time"] == "19:00"
        assert result["schedule"]["is_24_7"] is False

    def test_with_schedule(self, db):
        """Explicit SiteOperatingSchedule → source=database."""
        from services.consumption_context_service import get_activity_context
        _, site = _create_org_site(db)
        sched = SiteOperatingSchedule(
            site_id=site.id,
            open_days="0,1,2,3,4,5",
            open_time="07:00",
            close_time="21:00",
            is_24_7=False,
            timezone="Europe/Paris",
        )
        db.add(sched)
        db.commit()
        result = get_activity_context(db, site.id)
        assert result["schedule"]["source"] == "database"
        assert result["schedule"]["open_time"] == "07:00"
        assert result["schedule"]["close_time"] == "21:00"
        assert result["schedule"]["open_days"] == "0,1,2,3,4,5"


# ═══════════════════════════════════════════════
# E. API endpoints
# ═══════════════════════════════════════════════

class TestAPIEndpoints:
    """HTTP endpoint smoke tests."""

    def test_full_context_200(self, client, db):
        _, site = _create_org_site(db)
        _create_meter_with_readings(db, site, days=7)
        db.commit()
        resp = client.get(f"/api/consumption-context/site/{site.id}?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "profile" in data
        assert "activity" in data
        assert "anomalies" in data

    def test_profile_200(self, client, db):
        _, site = _create_org_site(db)
        db.commit()
        resp = client.get(f"/api/consumption-context/site/{site.id}/profile?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_profile" in data
        assert "baseload_kw" in data

    def test_anomalies_200(self, client, db):
        _, site = _create_org_site(db)
        db.commit()
        resp = client.get(f"/api/consumption-context/site/{site.id}/anomalies?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "behavior_score" in data
        assert 0 <= data["behavior_score"] <= 100

    def test_diagnose_200(self, client, db):
        _, site = _create_org_site(db)
        db.commit()
        resp = client.post(f"/api/consumption-context/site/{site.id}/diagnose?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "behavior_score" in data

    def test_activity_200(self, client, db):
        _, site = _create_org_site(db)
        db.commit()
        resp = client.get(f"/api/consumption-context/site/{site.id}/activity")
        assert resp.status_code == 200
        data = resp.json()
        assert "schedule" in data
        assert "schedule_params" in data

    def test_site_404(self, client, db):
        resp = client.get("/api/consumption-context/site/999999")
        assert resp.status_code == 404
