"""
PROMEOS - Tests Sprint V10: Consumption World-Class
Tunnel, Targets, TOU Schedules, HP/HC, Gas Summary
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import datetime, timedelta, date, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Meter,
    MeterReading,
    ConsumptionInsight,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    TypeSite,
    ConsumptionTarget,
    TOUSchedule,
)
from models.energy_models import EnergyVector, FrequencyType
from database import get_db
from main import app


# ========================================
# Fixtures
# ========================================


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
    """Helper: create org + entite + portefeuille + site."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="Default", description="Default")
    db.add(pf)
    db.flush()
    site = Site(
        nom="Bureau Lyon",
        portefeuille_id=pf.id,
        type=TypeSite.BUREAU,
        adresse="10 rue de Lyon",
        code_postal="69003",
        ville="Lyon",
        surface_m2=surface,
        actif=True,
    )
    db.add(site)
    db.commit()
    return org, site


def _create_meter(db, site, energy_vector=EnergyVector.ELECTRICITY, meter_id="PRM-001"):
    """Helper: create a meter for site."""
    meter = Meter(
        meter_id=meter_id,
        name=f"Compteur {meter_id}",
        energy_vector=energy_vector,
        site_id=site.id,
        subscribed_power_kva=60.0,
        is_active=True,
    )
    db.add(meter)
    db.commit()
    return meter


def _seed_readings(db, meter, days=30, interval_hours=1, base_kwh=10.0, pattern="office"):
    """Helper: seed hourly readings with office pattern."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    readings = []
    for d in range(days):
        day_start = now - timedelta(days=days - d)
        for h in range(0, 24, interval_hours):
            ts = day_start.replace(hour=h)
            if pattern == "office":
                is_weekend = ts.weekday() >= 5
                if is_weekend:
                    kwh = base_kwh * 0.3
                elif 8 <= h < 19:
                    kwh = base_kwh * (1.0 + 0.1 * (h - 8))
                elif 0 <= h < 6:
                    kwh = base_kwh * 0.2
                else:
                    kwh = base_kwh * 0.5
            else:
                kwh = base_kwh

            r = MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=kwh,
            )
            readings.append(r)
    db.add_all(readings)
    db.commit()
    return readings


# ========================================
# TestTunnelService
# ========================================


class TestTunnelService:
    """Tests for tunnel_service: envelope computation."""

    def test_tunnel_empty_no_meter(self, db):
        """Tunnel with no meter returns empty envelope."""
        from services.tunnel_service import compute_tunnel

        _, site = _create_org_site(db)
        result = compute_tunnel(db, site.id, days=30)
        assert result["readings_count"] == 0
        assert result["confidence"] == "low"
        assert len(result["envelope"]["weekday"]) == 24
        assert len(result["envelope"]["weekend"]) == 24

    def test_tunnel_insufficient_data(self, db):
        """Tunnel with < 48 readings returns empty envelope."""
        from services.tunnel_service import compute_tunnel

        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, days=1)  # ~24 readings, below threshold
        result = compute_tunnel(db, site.id, days=30)
        assert result["readings_count"] < 48
        assert result["confidence"] == "low"

    def test_tunnel_valid_envelope(self, db):
        """Tunnel with sufficient data returns valid P10-P90 envelope."""
        from services.tunnel_service import compute_tunnel

        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, days=30)
        result = compute_tunnel(db, site.id, days=30)
        assert result["readings_count"] >= 48
        assert result["confidence"] in ("medium", "high")
        assert result["site_id"] == site.id

        # Envelope structure
        envelope = result["envelope"]
        assert "weekday" in envelope
        assert "weekend" in envelope
        for slot in envelope["weekday"]:
            assert "p10" in slot
            assert "p50" in slot
            assert "p90" in slot
            assert slot["p10"] <= slot["p50"] <= slot["p90"]

    def test_tunnel_outside_pct(self, db):
        """Tunnel computes outside_pct for recent readings."""
        from services.tunnel_service import compute_tunnel

        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, days=60)
        result = compute_tunnel(db, site.id, days=60)
        # Normal office pattern should have low outside %
        assert 0 <= result["outside_pct"] <= 100
        assert result["total_evaluated"] >= 0

    def test_tunnel_gas_filter(self, db):
        """Tunnel filters by energy type (gas)."""
        from services.tunnel_service import compute_tunnel

        _, site = _create_org_site(db)
        _create_meter(db, site, energy_vector=EnergyVector.ELECTRICITY)
        result = compute_tunnel(db, site.id, days=30, energy_type="gas")
        assert result["readings_count"] == 0

    def test_tunnel_confidence_scoring(self, db):
        """Tunnel confidence is high with dense data."""
        from services.tunnel_service import compute_tunnel

        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, days=90, base_kwh=15.0)
        result = compute_tunnel(db, site.id, days=90)
        assert result["confidence_score"] > 0
        assert result["confidence"] in ("medium", "high")


class TestTunnelEndpoint:
    """Tests for GET /api/consumption/tunnel endpoint."""

    def test_tunnel_endpoint_200(self, client, db):
        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, days=30)
        resp = client.get(f"/api/consumption/tunnel?site_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "envelope" in data
        assert data["site_id"] == site.id

    def test_tunnel_endpoint_404(self, client, db):
        resp = client.get("/api/consumption/tunnel?site_id=9999")
        assert resp.status_code == 404

    def test_tunnel_endpoint_gas(self, client, db):
        _, site = _create_org_site(db)
        resp = client.get(f"/api/consumption/tunnel?site_id={site.id}&energy_type=gas")
        assert resp.status_code == 200
        assert resp.json()["readings_count"] == 0


# ========================================
# TestTargetsService
# ========================================


class TestTargetsService:
    """Tests for targets_service: CRUD + progression."""

    def test_create_target(self, db):
        from services.targets_service import create_target, get_targets

        _, site = _create_org_site(db)
        t = create_target(db, site.id, "electricity", "monthly", 2026, 1, target_kwh=5000)
        assert t["site_id"] == site.id
        assert t["target_kwh"] == 5000
        assert t["month"] == 1

    def test_create_target_upsert(self, db):
        """Creating duplicate target updates existing."""
        from services.targets_service import create_target

        _, site = _create_org_site(db)
        t1 = create_target(db, site.id, "electricity", "monthly", 2026, 1, target_kwh=5000)
        t2 = create_target(db, site.id, "electricity", "monthly", 2026, 1, target_kwh=6000)
        assert t2["target_kwh"] == 6000
        # Same record updated
        assert t1["id"] == t2["id"]

    def test_list_targets(self, db):
        from services.targets_service import create_target, get_targets

        _, site = _create_org_site(db)
        create_target(db, site.id, "electricity", "monthly", 2026, 1, target_kwh=5000)
        create_target(db, site.id, "electricity", "monthly", 2026, 2, target_kwh=4800)
        targets = get_targets(db, site.id, year=2026)
        assert len(targets) == 2

    def test_update_target(self, db):
        from services.targets_service import create_target, update_target

        _, site = _create_org_site(db)
        t = create_target(db, site.id, "electricity", "monthly", 2026, 3, target_kwh=5000)
        updated = update_target(db, t["id"], actual_kwh=4500)
        assert updated["actual_kwh"] == 4500

    def test_delete_target(self, db):
        from services.targets_service import create_target, delete_target, get_targets

        _, site = _create_org_site(db)
        t = create_target(db, site.id, "electricity", "monthly", 2026, 4, target_kwh=5000)
        assert delete_target(db, t["id"]) is True
        assert len(get_targets(db, site.id, year=2026)) == 0

    def test_delete_nonexistent(self, db):
        from services.targets_service import delete_target

        assert delete_target(db, 9999) is False

    def test_progression_no_targets(self, db):
        from services.targets_service import get_progression

        _, site = _create_org_site(db)
        prog = get_progression(db, site.id, year=2026)
        assert prog["yearly_target_kwh"] == 0
        assert len(prog["months"]) == 12

    def test_progression_with_targets(self, db):
        from services.targets_service import create_target, update_target, get_progression

        _, site = _create_org_site(db)
        for m in range(1, 13):
            t = create_target(db, site.id, "electricity", "monthly", 2026, m, target_kwh=5000)
            if m <= 2:  # Set actuals for Jan-Feb
                update_target(db, t["id"], actual_kwh=4800)

        prog = get_progression(db, site.id, year=2026)
        assert prog["yearly_target_kwh"] == 60000
        assert prog["ytd_actual_kwh"] > 0
        assert prog["forecast_year_kwh"] > 0
        assert prog["alert"] in ("on_track", "at_risk", "over_budget")
        assert len(prog["months"]) == 12

    def test_progression_over_budget(self, db):
        from services.targets_service import create_target, update_target, get_progression

        _, site = _create_org_site(db)
        for m in range(1, 13):
            t = create_target(db, site.id, "electricity", "monthly", 2026, m, target_kwh=5000)
            update_target(db, t["id"], actual_kwh=8000)  # All months over budget

        prog = get_progression(db, site.id, year=2026)
        assert prog["alert"] == "over_budget"


class TestTargetsEndpoint:
    """Tests for /api/consumption/targets endpoints."""

    def test_create_target_endpoint(self, client, db):
        _, site = _create_org_site(db)
        resp = client.post(
            "/api/consumption/targets",
            json={
                "site_id": site.id,
                "energy_type": "electricity",
                "period": "monthly",
                "year": 2026,
                "month": 1,
                "target_kwh": 5000,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["target_kwh"] == 5000

    def test_list_targets_endpoint(self, client, db):
        _, site = _create_org_site(db)
        client.post(
            "/api/consumption/targets",
            json={
                "site_id": site.id,
                "period": "monthly",
                "year": 2026,
                "month": 1,
                "target_kwh": 5000,
            },
        )
        resp = client.get(f"/api/consumption/targets?site_id={site.id}&year=2026")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_patch_target_endpoint(self, client, db):
        _, site = _create_org_site(db)
        create_resp = client.post(
            "/api/consumption/targets",
            json={
                "site_id": site.id,
                "period": "monthly",
                "year": 2026,
                "month": 5,
                "target_kwh": 5000,
            },
        )
        tid = create_resp.json()["id"]
        resp = client.patch(f"/api/consumption/targets/{tid}", json={"actual_kwh": 4900})
        assert resp.status_code == 200
        assert resp.json()["actual_kwh"] == 4900

    def test_delete_target_endpoint(self, client, db):
        _, site = _create_org_site(db)
        create_resp = client.post(
            "/api/consumption/targets",
            json={
                "site_id": site.id,
                "period": "monthly",
                "year": 2026,
                "month": 6,
                "target_kwh": 3000,
            },
        )
        tid = create_resp.json()["id"]
        resp = client.delete(f"/api/consumption/targets/{tid}")
        assert resp.status_code == 200

    def test_delete_target_404(self, client, db):
        resp = client.delete("/api/consumption/targets/9999")
        assert resp.status_code == 404

    def test_progression_endpoint(self, client, db):
        _, site = _create_org_site(db)
        resp = client.get(f"/api/consumption/targets/progression?site_id={site.id}&year=2026")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["months"]) == 12


# ========================================
# TestTOUService
# ========================================


class TestTOUService:
    """Tests for tou_service: schedule CRUD + HP/HC ratio."""

    def test_default_schedule(self, db):
        from services.tou_service import get_active_schedule

        _, site = _create_org_site(db)
        active = get_active_schedule(db, site.id)
        assert active is not None
        assert active["is_default"] is True
        assert "windows" in active

    def test_create_schedule(self, db):
        from services.tou_service import create_schedule, get_schedules

        _, site = _create_org_site(db)
        windows = [
            {"day_types": ["weekday"], "start": "07:00", "end": "23:00", "period": "HP", "price_eur_kwh": 0.20},
            {"day_types": ["weekday"], "start": "23:00", "end": "07:00", "period": "HC", "price_eur_kwh": 0.14},
            {"day_types": ["weekend"], "start": "00:00", "end": "24:00", "period": "HC", "price_eur_kwh": 0.14},
        ]
        sched = create_schedule(
            db,
            site_id=site.id,
            meter_id=None,
            name="TURPE 7",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            windows=windows,
            source="turpe",
            price_hp_eur_kwh=0.20,
            price_hc_eur_kwh=0.14,
        )
        assert sched["name"] == "TURPE 7"
        assert sched["is_default"] is False
        assert len(sched["windows"]) == 3

    def test_active_schedule_versioning(self, db):
        from services.tou_service import create_schedule, get_active_schedule

        _, site = _create_org_site(db)
        windows_v1 = [
            {"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP"},
            {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC"},
        ]
        windows_v2 = [
            {"day_types": ["weekday"], "start": "07:00", "end": "23:00", "period": "HP"},
            {"day_types": ["weekday"], "start": "23:00", "end": "07:00", "period": "HC"},
        ]
        create_schedule(
            db,
            site_id=site.id,
            meter_id=None,
            name="V1",
            effective_from=date(2024, 1, 1),
            effective_to=None,
            windows=windows_v1,
            price_hp_eur_kwh=0.18,
            price_hc_eur_kwh=0.12,
        )
        create_schedule(
            db,
            site_id=site.id,
            meter_id=None,
            name="V2",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            windows=windows_v2,
            price_hp_eur_kwh=0.20,
            price_hc_eur_kwh=0.14,
        )

        active = get_active_schedule(db, site.id, ref_date=date(2025, 6, 1))
        assert active["name"] == "V2"

    def test_update_schedule(self, db):
        from services.tou_service import create_schedule, update_schedule

        _, site = _create_org_site(db)
        sched = create_schedule(
            db,
            site_id=site.id,
            meter_id=None,
            name="Test",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            windows=[],
            price_hp_eur_kwh=0.18,
            price_hc_eur_kwh=0.12,
        )
        updated = update_schedule(db, sched["id"], name="Test Updated", price_hp_eur_kwh=0.22)
        assert updated["name"] == "Test Updated"
        assert updated["price_hp_eur_kwh"] == 0.22

    def test_delete_schedule(self, db):
        from services.tou_service import create_schedule, delete_schedule, get_schedules

        _, site = _create_org_site(db)
        sched = create_schedule(
            db,
            site_id=site.id,
            meter_id=None,
            name="To Delete",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            windows=[],
        )
        assert delete_schedule(db, sched["id"]) is True
        active = get_schedules(db, site_id=site.id, active_only=True)
        assert all(s["id"] != sched["id"] or not s.get("is_active") for s in active)

    def test_hp_hc_ratio_no_data(self, db):
        from services.tou_service import compute_hp_hc_ratio

        _, site = _create_org_site(db)
        result = compute_hp_hc_ratio(db, site.id, days=30)
        assert result["total_kwh"] == 0
        assert result["confidence"] == "low"

    def test_hp_hc_ratio_with_data(self, db):
        from services.tou_service import compute_hp_hc_ratio

        _, site = _create_org_site(db)
        meter = _create_meter(db, site)
        _seed_readings(db, meter, days=30)
        result = compute_hp_hc_ratio(db, site.id, days=30)
        assert result["total_kwh"] > 0
        assert 0 <= result["hp_ratio"] <= 1
        assert result["hp_cost_eur"] >= 0
        assert result["hc_cost_eur"] >= 0

    def test_classify_period(self):
        """Test HP/HC classification logic."""
        from services.tou_service import _classify_period, DEFAULT_WINDOWS

        # Weekday 10:00 → HP
        ts_hp = datetime(2025, 6, 2, 10, 0)  # Monday
        assert _classify_period(ts_hp, DEFAULT_WINDOWS) == "HP"

        # Weekday 23:00 → HC
        ts_hc = datetime(2025, 6, 2, 23, 0)  # Monday
        assert _classify_period(ts_hc, DEFAULT_WINDOWS) == "HC"

        # Weekend → HC
        ts_we = datetime(2025, 6, 7, 14, 0)  # Saturday
        assert _classify_period(ts_we, DEFAULT_WINDOWS) == "HC"


class TestTOUEndpoint:
    """Tests for /api/consumption/tou_schedules endpoints."""

    def test_list_tou_empty(self, client, db):
        _, site = _create_org_site(db)
        resp = client.get(f"/api/consumption/tou_schedules?site_id={site.id}")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_tou_endpoint(self, client, db):
        _, site = _create_org_site(db)
        resp = client.post(
            "/api/consumption/tou_schedules",
            json={
                "site_id": site.id,
                "name": "TURPE 7 Test",
                "effective_from": "2025-01-01",
                "windows": [
                    {"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP"},
                    {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC"},
                ],
                "source": "manual",
                "price_hp_eur_kwh": 0.18,
                "price_hc_eur_kwh": 0.12,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "TURPE 7 Test"
        assert len(data["windows"]) == 2

    def test_active_tou_endpoint(self, client, db):
        _, site = _create_org_site(db)
        resp = client.get(f"/api/consumption/tou_schedules/active?site_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_default"] is True

    def test_patch_tou_endpoint(self, client, db):
        _, site = _create_org_site(db)
        create_resp = client.post(
            "/api/consumption/tou_schedules",
            json={
                "site_id": site.id,
                "name": "Test",
                "effective_from": "2025-01-01",
                "windows": [],
                "price_hp_eur_kwh": 0.18,
                "price_hc_eur_kwh": 0.12,
            },
        )
        sid = create_resp.json()["id"]
        resp = client.patch(f"/api/consumption/tou_schedules/{sid}", json={"name": "Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete_tou_endpoint(self, client, db):
        _, site = _create_org_site(db)
        create_resp = client.post(
            "/api/consumption/tou_schedules",
            json={
                "site_id": site.id,
                "name": "To Delete",
                "effective_from": "2025-01-01",
                "windows": [],
            },
        )
        sid = create_resp.json()["id"]
        resp = client.delete(f"/api/consumption/tou_schedules/{sid}")
        assert resp.status_code == 200

    def test_hp_hc_endpoint(self, client, db):
        _, site = _create_org_site(db)
        resp = client.get(f"/api/consumption/hp_hc?site_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "hp_ratio" in data


# ========================================
# TestGasSummary
# ========================================


class TestGasSummary:
    """Tests for gas summary endpoint."""

    def test_gas_summary_no_meters(self, client, db):
        _, site = _create_org_site(db)
        resp = client.get(f"/api/consumption/gas/summary?site_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["readings_count"] == 0
        assert data["energy_type"] == "gas"

    def test_gas_summary_with_data(self, client, db):
        _, site = _create_org_site(db)
        meter = _create_meter(db, site, energy_vector=EnergyVector.GAS, meter_id="PCE-001")
        _seed_readings(db, meter, days=30, pattern="flat", base_kwh=50.0)
        resp = client.get(f"/api/consumption/gas/summary?site_id={site.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["readings_count"] > 0
        assert data["total_kwh"] > 0
        assert data["avg_daily_kwh"] > 0

    def test_gas_summary_elec_ignored(self, client, db):
        """Gas endpoint ignores electricity meters."""
        _, site = _create_org_site(db)
        meter = _create_meter(db, site, energy_vector=EnergyVector.ELECTRICITY, meter_id="PRM-ELEC")
        _seed_readings(db, meter, days=30)
        resp = client.get(f"/api/consumption/gas/summary?site_id={site.id}")
        assert resp.status_code == 200
        assert resp.json()["readings_count"] == 0


# ========================================
# TestConfidenceGating
# ========================================


class TestConfidenceGating:
    """Tests for confidence scoring in tunnel/HP-HC."""

    def test_tunnel_low_confidence(self, db):
        from services.tunnel_service import _compute_confidence

        score, level = _compute_confidence(50, 90)
        assert level == "low"

    def test_tunnel_medium_confidence(self, db):
        from services.tunnel_service import _compute_confidence

        score, level = _compute_confidence(1200, 90)  # ratio ~0.55, >= 200 readings
        assert level == "medium"

    def test_tunnel_high_confidence(self, db):
        from services.tunnel_service import _compute_confidence

        score, level = _compute_confidence(2000, 90)
        assert level == "high"
        assert score >= 80


# ========================================
# TestEdgeCases
# ========================================


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_target_yearly_period(self, db):
        from services.targets_service import create_target

        _, site = _create_org_site(db)
        t = create_target(db, site.id, "electricity", "yearly", 2026, None, target_kwh=60000)
        assert t["period"] == "yearly"
        assert t["month"] is None

    def test_target_with_co2(self, db):
        from services.targets_service import create_target

        _, site = _create_org_site(db)
        t = create_target(db, site.id, "gas", "monthly", 2026, 1, target_kwh=5000, target_co2e_kg=1200)
        assert t["target_co2e_kg"] == 1200
        assert t["energy_type"] == "gas"

    def test_tunnel_with_gas_meter(self, db):
        from services.tunnel_service import compute_tunnel

        _, site = _create_org_site(db)
        meter = _create_meter(db, site, energy_vector=EnergyVector.GAS, meter_id="PCE-002")
        _seed_readings(db, meter, days=30, base_kwh=50.0, pattern="flat")
        result = compute_tunnel(db, site.id, days=30, energy_type="gas")
        assert result["readings_count"] > 0
        assert result["energy_type"] == "gas"

    def test_tou_schedule_meter_level(self, db):
        """Meter-level schedule takes precedence over site-level."""
        from services.tou_service import create_schedule, get_active_schedule

        _, site = _create_org_site(db)
        meter = _create_meter(db, site)

        create_schedule(
            db,
            site_id=site.id,
            meter_id=None,
            name="Site Level",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            windows=[],
            price_hp_eur_kwh=0.18,
            price_hc_eur_kwh=0.12,
        )
        create_schedule(
            db,
            site_id=None,
            meter_id=meter.id,
            name="Meter Level",
            effective_from=date(2025, 1, 1),
            effective_to=None,
            windows=[],
            price_hp_eur_kwh=0.22,
            price_hc_eur_kwh=0.15,
        )

        active = get_active_schedule(db, site.id, meter_id=meter.id, ref_date=date(2025, 6, 1))
        assert active["name"] == "Meter Level"

    def test_update_nonexistent_target(self, db):
        from services.targets_service import update_target

        assert update_target(db, 9999, target_kwh=100) is None

    def test_update_nonexistent_schedule(self, db):
        from services.tou_service import update_schedule

        assert update_schedule(db, 9999, name="X") is None

    def test_delete_nonexistent_schedule(self, db):
        from services.tou_service import delete_schedule

        assert delete_schedule(db, 9999) is False
