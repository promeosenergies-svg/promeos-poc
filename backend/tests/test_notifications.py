"""
PROMEOS - Tests Sprint 10.2: Notifications & Alert Center V1
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    ComplianceFinding, ConsumptionInsight, BillingInsight,
    EnergyContract,
    ActionItem, ActionSyncBatch, ActionStatus, ActionSourceType,
    NotificationEvent, NotificationBatch, NotificationPreference,
    NotificationSeverity, NotificationStatus, NotificationSourceType,
    InsightStatus, TypeSite, BillingEnergyType,
)
from database import get_db
from main import app
from services.notification_service import sync_notifications


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


def _create_org_site(db_session, site_name="Site Test"):
    """Create org + entite + portefeuille + site."""
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
        nom=site_name,
        type=TypeSite.BUREAU,
        surface_m2=2000,
        actif=True,
    )
    db_session.add(site)
    db_session.flush()
    return org, site


def _seed_compliance(db_session, site_id, severity="high", deadline_days=20):
    """Create NOK compliance finding."""
    f = ComplianceFinding(
        site_id=site_id,
        regulation="bacs",
        rule_id="BACS_GTB_REQUIRED",
        status="NOK",
        severity=severity,
        evidence="GTB non installee",
        recommended_actions_json=json.dumps(["Installer GTB conforme"]),
        insight_status=InsightStatus.OPEN,
        deadline=date.today() + timedelta(days=deadline_days),
    )
    db_session.add(f)
    db_session.flush()
    return f


def _seed_billing(db_session, site_id, loss_eur=5500):
    """Create billing insight with loss."""
    ins = BillingInsight(
        site_id=site_id,
        type="shadow_gap",
        severity="high",
        message=f"Ecart shadow billing: {loss_eur} EUR",
        estimated_loss_eur=loss_eur,
        recommended_actions_json=json.dumps(["Verifier le compteur"]),
        insight_status=InsightStatus.OPEN,
    )
    db_session.add(ins)
    db_session.flush()
    return ins


def _seed_contract(db_session, site_id, days_until_end=25):
    """Create energy contract with upcoming renewal."""
    c = EnergyContract(
        site_id=site_id,
        energy_type=BillingEnergyType.ELEC,
        supplier_name="EDF",
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() + timedelta(days=days_until_end),
    )
    db_session.add(c)
    db_session.flush()
    return c


def _seed_consumption(db_session, site_id, loss_eur=6000):
    """Create consumption insight with loss."""
    ins = ConsumptionInsight(
        site_id=site_id,
        type="derive",
        severity="high",
        message=f"Derive importante: {loss_eur} EUR/an de perte",
        estimated_loss_eur=loss_eur,
        estimated_loss_kwh=loss_eur * 5,
    )
    db_session.add(ins)
    db_session.flush()
    return ins


def _seed_overdue_action(db_session, org_id, site_id):
    """Create overdue action item."""
    a = ActionItem(
        org_id=org_id,
        site_id=site_id,
        source_type=ActionSourceType.COMPLIANCE,
        source_id="999",
        source_key="overdue_test:0",
        title="Action en retard test",
        priority=1,
        severity="critical",
        status=ActionStatus.OPEN,
        due_date=date.today() - timedelta(days=20),
    )
    db_session.add(a)
    db_session.flush()
    return a


def _seed_full_demo(db_session):
    """Full demo: org + site + compliance + billing + contract + conso + overdue action."""
    org, site = _create_org_site(db_session)
    _seed_compliance(db_session, site.id, severity="high", deadline_days=20)
    _seed_billing(db_session, site.id, loss_eur=5500)
    _seed_contract(db_session, site.id, days_until_end=25)
    _seed_consumption(db_session, site.id, loss_eur=6000)
    _seed_overdue_action(db_session, org.id, site.id)
    db_session.commit()
    return org, site


# ========================================
# Test: Sync idempotent
# ========================================

class TestSyncIdempotent:
    def test_double_sync_no_duplicates(self, db_session):
        org, site = _seed_full_demo(db_session)

        r1 = sync_notifications(db_session, org.id, "test")
        r2 = sync_notifications(db_session, org.id, "test")

        assert r2["created"] == 0, "Second sync should not create new events"
        assert r2["skipped"] > 0, "Second sync should skip identical events"

        total = db_session.query(NotificationEvent).filter(
            NotificationEvent.org_id == org.id
        ).count()
        assert total == r1["created"], f"Total events should match first sync created count"

    def test_batch_created(self, db_session):
        org, site = _seed_full_demo(db_session)

        sync_notifications(db_session, org.id, "test")

        batches = db_session.query(NotificationBatch).filter(
            NotificationBatch.org_id == org.id
        ).all()
        assert len(batches) >= 1
        assert batches[0].created_count > 0


# ========================================
# Test: Severity mapping
# ========================================

class TestSeverityMapping:
    def test_compliance_nok_high_is_critical(self, db_session):
        org, site = _create_org_site(db_session)
        _seed_compliance(db_session, site.id, severity="high", deadline_days=20)
        db_session.commit()

        sync_notifications(db_session, org.id, "test")

        events = db_session.query(NotificationEvent).filter(
            NotificationEvent.source_type == NotificationSourceType.COMPLIANCE
        ).all()
        assert len(events) >= 1
        assert events[0].severity == NotificationSeverity.CRITICAL

    def test_contract_30_days_critical(self, db_session):
        org, site = _create_org_site(db_session)
        _seed_contract(db_session, site.id, days_until_end=25)
        db_session.commit()

        sync_notifications(db_session, org.id, "test")

        events = db_session.query(NotificationEvent).filter(
            NotificationEvent.source_type == NotificationSourceType.PURCHASE
        ).all()
        assert len(events) >= 1
        assert events[0].severity == NotificationSeverity.CRITICAL

    def test_contract_60_days_warn(self, db_session):
        org, site = _create_org_site(db_session)
        _seed_contract(db_session, site.id, days_until_end=50)
        db_session.commit()

        sync_notifications(db_session, org.id, "test")

        events = db_session.query(NotificationEvent).filter(
            NotificationEvent.source_type == NotificationSourceType.PURCHASE
        ).all()
        assert len(events) >= 1
        assert events[0].severity == NotificationSeverity.WARN


# ========================================
# Test: PATCH status (READ/DISMISSED)
# ========================================

class TestPatchStatus:
    def test_patch_read(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        events = db_session.query(NotificationEvent).all()
        assert len(events) > 0

        evt_id = events[0].id
        r = client.patch(f"/api/notifications/{evt_id}", json={"status": "read"})
        assert r.status_code == 200
        assert r.json()["result"] == "updated"

        db_session.refresh(events[0])
        assert events[0].status == NotificationStatus.READ

    def test_patch_dismissed(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        events = db_session.query(NotificationEvent).all()
        evt_id = events[0].id

        r = client.patch(f"/api/notifications/{evt_id}", json={"status": "dismissed"})
        assert r.status_code == 200

        db_session.refresh(events[0])
        assert events[0].status == NotificationStatus.DISMISSED

    def test_patch_invalid_status(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        events = db_session.query(NotificationEvent).all()
        evt_id = events[0].id

        r = client.patch(f"/api/notifications/{evt_id}", json={"status": "invalid"})
        assert r.status_code == 400

    def test_patch_404(self, client, db_session):
        r = client.patch("/api/notifications/99999", json={"status": "read"})
        assert r.status_code == 404


# ========================================
# Test: Preserve workflow on resync
# ========================================

class TestPreserveWorkflow:
    def test_resync_preserves_read_status(self, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        # Mark first event as READ
        events = db_session.query(NotificationEvent).all()
        events[0].status = NotificationStatus.READ
        db_session.commit()

        # Resync
        sync_notifications(db_session, org.id, "test")

        db_session.refresh(events[0])
        assert events[0].status == NotificationStatus.READ, "READ status should be preserved after resync"


# ========================================
# Test: Dashboard 2min includes alerts
# ========================================

class TestDashboard2MinAlerts:
    def test_alerts_in_2min(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        r = client.get("/api/dashboard/2min")
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data
        alerts = data["alerts"]
        assert alerts is not None
        assert alerts["new_critical"] >= 1
        assert alerts["total"] >= 1

    def test_top_alert_present(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        r = client.get("/api/dashboard/2min")
        data = r.json()
        alerts = data["alerts"]
        assert alerts["top_alert"] is not None
        assert "title" in alerts["top_alert"]
        assert "severity" in alerts["top_alert"]


# ========================================
# Test: Filter endpoints
# ========================================

class TestFilterEndpoints:
    def test_list_all(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        r = client.get("/api/notifications/list")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1

    def test_filter_severity(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        r = client.get("/api/notifications/list?severity=critical")
        assert r.status_code == 200
        for evt in r.json():
            assert evt["severity"] == "critical"

    def test_filter_source_type(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        r = client.get("/api/notifications/list?source_type=compliance")
        assert r.status_code == 200
        for evt in r.json():
            assert evt["source_type"] == "compliance"

    def test_summary(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        r = client.get("/api/notifications/summary")
        assert r.status_code == 200
        data = r.json()
        assert "by_severity" in data
        assert "by_status" in data
        assert data["total"] >= 1

    def test_batches(self, client, db_session):
        org, site = _seed_full_demo(db_session)
        sync_notifications(db_session, org.id, "test")

        r = client.get("/api/notifications/batches")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["created_count"] >= 1

    def test_empty_list(self, client, db_session):
        _create_org_site(db_session)
        db_session.commit()

        r = client.get("/api/notifications/list")
        assert r.status_code == 200
        assert r.json() == []


# ========================================
# Test: Sync API endpoint
# ========================================

class TestSyncEndpoint:
    def test_sync_via_api(self, client, db_session):
        org, site = _seed_full_demo(db_session)

        r = client.post("/api/notifications/sync")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["created"] >= 1

    def test_sync_returns_summary(self, client, db_session):
        org, site = _seed_full_demo(db_session)

        r = client.post("/api/notifications/sync")
        data = r.json()
        assert "new_critical" in data
        assert "by_severity" in data
        assert "total" in data


# ========================================
# Test: Preferences
# ========================================

class TestPreferences:
    def test_get_default_preferences(self, client, db_session):
        _create_org_site(db_session)
        db_session.commit()

        r = client.get("/api/notifications/preferences")
        assert r.status_code == 200
        data = r.json()
        assert data["enable_badges"] is True
        assert data["thresholds"]["critical_due_days"] == 30

    def test_put_preferences(self, client, db_session):
        _create_org_site(db_session)
        db_session.commit()

        r = client.put("/api/notifications/preferences", json={
            "enable_badges": False,
            "snooze_days": 7,
            "thresholds_json": json.dumps({"critical_due_days": 15, "warn_due_days": 45}),
        })
        assert r.status_code == 200
        assert r.json()["status"] == "updated"

        # Verify persistence
        r2 = client.get("/api/notifications/preferences")
        data = r2.json()
        assert data["enable_badges"] is False
        assert data["snooze_days"] == 7
        assert data["thresholds"]["critical_due_days"] == 15
