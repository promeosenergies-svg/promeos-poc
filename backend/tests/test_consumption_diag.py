"""
PROMEOS - Tests Sprint 5: Diagnostic Consommation V1
(seed demo, detect hors horaires / base load / pointe / derive / data gap, endpoints)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import datetime, timedelta, timezone
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
)
from models.energy_models import FrequencyType
from database import get_db
from main import app


@pytest.fixture
def db_session():
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
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_site(db_session, surface=2000):
    """Helper: org + entite + portefeuille + site."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="Principal")
    db_session.add(pf)
    db_session.flush()

    site = Site(
        portefeuille_id=pf.id,
        nom="Bureau Test",
        type=TypeSite.BUREAU,
        surface_m2=surface,
        actif=True,
    )
    db_session.add(site)
    db_session.flush()
    db_session.commit()
    return org, site


def _create_meter(db_session, site_id, meter_id_str="PRM-TEST-0001"):
    """Create a Meter for the given site."""
    m = Meter(
        meter_id=meter_id_str,
        name="Compteur test",
        site_id=site_id,
        subscribed_power_kva=100.0,
        is_active=True,
    )
    db_session.add(m)
    db_session.flush()
    return m


def _inject_readings(db_session, meter, days=30, pattern="bureau", anomaly=True):
    """Inject synthetic hourly MeterReadings for testing.

    Pattern 'bureau': high during 8-19 weekdays, low otherwise.
    If anomaly=True, injects elevated night consumption on days 5-8.
    """
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)
    ts = start
    readings = []

    while ts < now:
        hour = ts.hour
        weekday = ts.weekday()
        day_idx = (ts - start).days
        is_weekend = weekday >= 5

        if pattern == "bureau":
            if not is_weekend and 8 <= hour < 19:
                kwh = 50.0  # Business hours
            else:
                kwh = 20.0  # Off hours base (must be high enough for >35%)

            # Anomaly: elevated night on many days → push hors_horaires above 35%
            if anomaly and day_idx % 3 == 0 and (hour < 7 or hour >= 20):
                kwh = 45.0  # High night consumption

            # Drift: +15% for last week
            if day_idx >= days - 7:
                kwh *= 1.20

        elif pattern == "flat":
            kwh = 30.0  # Constant (high base load ratio)

        elif pattern == "gaps":
            # Normal but skip some hours
            kwh = 25.0
            if day_idx == 10 and 6 <= hour <= 18:
                ts += timedelta(hours=1)
                continue  # Skip → data gap
            if day_idx == 20 and 0 <= hour <= 10:
                ts += timedelta(hours=1)
                continue  # Another gap

        else:
            kwh = 20.0

        readings.append(
            MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=round(kwh, 2),
                quality_score=0.95,
            )
        )
        ts += timedelta(hours=1)

    db_session.bulk_save_objects(readings)
    db_session.commit()
    return len(readings)


# ========================================
# ConsumptionInsight model
# ========================================


class TestConsumptionInsightModel:
    def test_create_insight(self, db_session):
        org, site = _create_org_site(db_session)
        ci = ConsumptionInsight(
            site_id=site.id,
            type="hors_horaires",
            severity="high",
            message="60% hors horaires",
            estimated_loss_kwh=5000,
            estimated_loss_eur=750,
        )
        db_session.add(ci)
        db_session.commit()
        assert ci.id is not None
        assert ci.type == "hors_horaires"

    def test_insight_with_metrics_json(self, db_session):
        org, site = _create_org_site(db_session)
        metrics = {"off_hours_pct": 55.2, "base_load_kw": 12.5}
        ci = ConsumptionInsight(
            site_id=site.id,
            type="base_load",
            severity="medium",
            message="Talon eleve",
            metrics_json=json.dumps(metrics),
        )
        db_session.add(ci)
        db_session.commit()
        loaded = json.loads(ci.metrics_json)
        assert loaded["off_hours_pct"] == 55.2


# ========================================
# generate_demo_consumption
# ========================================


class TestGenerateDemoConso:
    def test_generate_basic(self, db_session):
        from services.consumption_diagnostic import generate_demo_consumption

        org, site = _create_org_site(db_session)
        result = generate_demo_consumption(db_session, site.id, days=7)
        assert result["readings_count"] > 100  # 7 * 24 = 168
        assert result["meter_id"] is not None

    def test_generate_creates_meter(self, db_session):
        from services.consumption_diagnostic import generate_demo_consumption

        org, site = _create_org_site(db_session)
        result = generate_demo_consumption(db_session, site.id, days=3)
        meter = db_session.query(Meter).filter(Meter.site_id == site.id).first()
        assert meter is not None
        assert "DEMO" in meter.meter_id

    def test_generate_replaces_existing_readings(self, db_session):
        from services.consumption_diagnostic import generate_demo_consumption

        org, site = _create_org_site(db_session)
        r1 = generate_demo_consumption(db_session, site.id, days=3)
        r2 = generate_demo_consumption(db_session, site.id, days=3)
        count = db_session.query(MeterReading).count()
        assert count == r2["readings_count"]  # Replaced, not appended

    def test_generate_with_anomaly(self, db_session):
        from services.consumption_diagnostic import generate_demo_consumption

        org, site = _create_org_site(db_session)
        result = generate_demo_consumption(db_session, site.id, days=30, anomaly=True)
        assert result["anomaly_days"] >= 3

    def test_generate_site_not_found(self, db_session):
        from services.consumption_diagnostic import generate_demo_consumption

        result = generate_demo_consumption(db_session, 9999, days=7)
        assert "error" in result


# ========================================
# Detectors (unit tests)
# ========================================


class TestDetectors:
    def test_detect_hors_horaires_bureau_with_anomaly(self, db_session):
        """Bureau pattern with night anomaly → should detect hors horaires."""
        from services.consumption_diagnostic import _detect_hors_horaires

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="bureau", anomaly=True)

        readings = (
            db_session.query(MeterReading)
            .filter(MeterReading.meter_id == meter.id)
            .order_by(MeterReading.timestamp)
            .all()
        )

        result = _detect_hors_horaires(readings)
        assert result is not None
        assert result["type"] == "hors_horaires"
        assert result["metrics"]["off_hours_pct"] > 35

    def test_detect_base_load_flat_pattern(self, db_session):
        """Flat consumption → high base load ratio → detect."""
        from services.consumption_diagnostic import _detect_base_load

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="flat", anomaly=False)

        readings = (
            db_session.query(MeterReading)
            .filter(MeterReading.meter_id == meter.id)
            .order_by(MeterReading.timestamp)
            .all()
        )

        result = _detect_base_load(readings)
        # Flat pattern: Q10 ≈ Q50 → base_ratio ≈ 100% → detected
        assert result is not None
        assert result["type"] == "base_load"
        assert result["metrics"]["base_ratio_pct"] > 40

    def test_detect_derive_with_drift(self, db_session):
        """Bureau pattern with +15% last week drift → detect derive."""
        from services.consumption_diagnostic import _detect_derive

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="bureau", anomaly=False)

        readings = (
            db_session.query(MeterReading)
            .filter(MeterReading.meter_id == meter.id)
            .order_by(MeterReading.timestamp)
            .all()
        )

        result = _detect_derive(readings)
        assert result is not None
        assert result["type"] == "derive"
        assert result["metrics"]["drift_pct"] > 5

    def test_detect_data_gaps(self, db_session):
        """Pattern with gaps → detect data_gap."""
        from services.consumption_diagnostic import _detect_data_gaps

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="gaps", anomaly=False)

        readings = (
            db_session.query(MeterReading)
            .filter(MeterReading.meter_id == meter.id)
            .order_by(MeterReading.timestamp)
            .all()
        )

        result = _detect_data_gaps(readings)
        assert result is not None
        assert result["type"] == "data_gap"
        assert result["metrics"]["gaps_count"] >= 2

    def test_detect_not_enough_data(self, db_session):
        """Less than 2 days of data → all detectors return None."""
        from services.consumption_diagnostic import (
            _detect_hors_horaires,
            _detect_base_load,
            _detect_pointe,
            _detect_derive,
            _detect_data_gaps,
        )

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        # Only 10 readings
        now = datetime.now(timezone.utc)
        for i in range(10):
            db_session.add(
                MeterReading(
                    meter_id=meter.id,
                    timestamp=now - timedelta(hours=10 - i),
                    frequency=FrequencyType.HOURLY,
                    value_kwh=20.0,
                    quality_score=0.95,
                )
            )
        db_session.commit()

        readings = (
            db_session.query(MeterReading)
            .filter(MeterReading.meter_id == meter.id)
            .order_by(MeterReading.timestamp)
            .all()
        )

        assert _detect_hors_horaires(readings) is None
        assert _detect_base_load(readings) is None
        assert _detect_pointe(readings) is None
        assert _detect_derive(readings) is None
        assert _detect_data_gaps(readings) is None


# ========================================
# run_diagnostic (full pipeline)
# ========================================


class TestRunDiagnostic:
    def test_run_diagnostic_bureau(self, db_session):
        """Full diagnostic on bureau with anomaly → produces insights."""
        from services.consumption_diagnostic import run_diagnostic

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="bureau", anomaly=True)

        insights = run_diagnostic(db_session, site.id)
        assert len(insights) >= 2  # At least hors_horaires + derive

        types = [ci.type for ci in insights]
        assert "hors_horaires" in types

        # All persisted
        count = db_session.query(ConsumptionInsight).filter(ConsumptionInsight.site_id == site.id).count()
        assert count == len(insights)

    def test_run_diagnostic_replaces_previous(self, db_session):
        """Re-running diagnostic replaces old insights."""
        from services.consumption_diagnostic import run_diagnostic

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="bureau", anomaly=True)

        insights1 = run_diagnostic(db_session, site.id)
        count1 = db_session.query(ConsumptionInsight).filter(ConsumptionInsight.site_id == site.id).count()

        insights2 = run_diagnostic(db_session, site.id)
        count2 = db_session.query(ConsumptionInsight).filter(ConsumptionInsight.site_id == site.id).count()

        assert count1 == count2  # Replaced, not appended

    def test_run_diagnostic_no_meter(self, db_session):
        """Site with no meter → empty result."""
        from services.consumption_diagnostic import run_diagnostic

        org, site = _create_org_site(db_session)
        insights = run_diagnostic(db_session, site.id)
        assert insights == []

    def test_run_diagnostic_org(self, db_session):
        """Run diagnostics across all org sites."""
        from services.consumption_diagnostic import run_diagnostic_org

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="bureau", anomaly=True)

        result = run_diagnostic_org(db_session, org.id)
        assert result["sites_analyzed"] >= 1
        assert result["total_insights"] >= 1

    def test_insights_summary(self, db_session):
        """get_insights_summary returns aggregated data."""
        from services.consumption_diagnostic import run_diagnostic, get_insights_summary

        org, site = _create_org_site(db_session)
        meter = _create_meter(db_session, site.id)
        _inject_readings(db_session, meter, days=30, pattern="bureau", anomaly=True)

        run_diagnostic(db_session, site.id)
        db_session.commit()

        summary = get_insights_summary(db_session, org.id)
        assert summary["total_insights"] >= 2
        assert summary["sites_with_insights"] == 1
        assert summary["total_loss_eur"] > 0
        assert len(summary["insights"]) >= 2
        # Sorted by severity desc
        sevs = [i["severity"] for i in summary["insights"]]
        sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        assert sev_order.get(sevs[0], 0) >= sev_order.get(sevs[-1], 0)


# ========================================
# API Endpoints
# ========================================


class TestConsumptionEndpoints:
    def test_insights_no_org(self, client):
        # V57: resolve_org_id returns 403 when no org resolvable (was 200 with empty data)
        from services.demo_state import DemoState

        DemoState.clear_demo_org()
        r = client.get("/api/consumption/insights")
        assert r.status_code in (200, 403)

    def test_seed_demo_endpoint(self, client):
        """Seed demo data via API."""
        # Need an org and site first
        client.post("/api/demo/seed")
        r = client.post("/api/consumption/seed-demo")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert len(data["sites"]) >= 1

    def test_diagnose_endpoint(self, client):
        """Seed data, then diagnose."""
        client.post("/api/demo/seed")
        client.post("/api/consumption/seed-demo")
        r = client.post("/api/consumption/diagnose")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["total_insights"] >= 1

    def test_insights_after_diagnose(self, client):
        """After diagnose, insights endpoint returns data."""
        client.post("/api/demo/seed")
        client.post("/api/consumption/seed-demo")
        client.post("/api/consumption/diagnose")
        r = client.get("/api/consumption/insights")
        assert r.status_code == 200
        data = r.json()
        assert data["total_insights"] >= 1
        assert len(data["insights"]) >= 1
        # Check insight structure
        ins = data["insights"][0]
        assert "type" in ins
        assert "severity" in ins
        assert "message" in ins
        assert "estimated_loss_eur" in ins

    def test_site_insights_endpoint(self, client):
        """Get insights for a specific site."""
        client.post("/api/demo/seed")
        client.post("/api/consumption/seed-demo")
        client.post("/api/consumption/diagnose")
        # Get first site
        sites_resp = client.get("/api/sites").json()
        sites = sites_resp if isinstance(sites_resp, list) else sites_resp.get("items", sites_resp.get("sites", []))
        assert len(sites) >= 1
        site_id = sites[0]["id"]
        r = client.get(f"/api/consumption/site/{site_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["site_id"] == site_id
        assert "insights" in data

    def test_site_insights_404(self, client):
        r = client.get("/api/consumption/site/99999")
        assert r.status_code == 404

    def test_diagnose_no_org(self, client):
        # V57: resolve_org_id returns 403 when no org resolvable
        from services.demo_state import DemoState

        DemoState.clear_demo_org()
        r = client.post("/api/consumption/diagnose")
        assert r.status_code in (400, 403)

    def test_seed_no_sites(self, client):
        r = client.post("/api/consumption/seed-demo")
        assert r.status_code == 400


# ========================================
# Dashboard 2min integration
# ========================================


class TestDashboard2MinConso:
    def test_pertes_estimees_includes_conso(self, client):
        """After conso diagnostic, pertes_estimees_eur should include conso losses."""
        client.post("/api/demo/seed")
        client.post("/api/consumption/seed-demo")
        client.post("/api/consumption/diagnose")
        r = client.get("/api/dashboard/2min")
        assert r.status_code == 200
        data = r.json()
        # pertes_estimees_eur should be > 0 (includes conso losses)
        assert data["pertes_estimees_eur"] > 0
