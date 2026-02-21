"""
PROMEOS - Tests Sprint 10: Action Hub V1
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

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    ComplianceFinding, ConsumptionInsight, BillingInsight,
    ActionItem, ActionSyncBatch,
    ActionSourceType, ActionStatus, InsightStatus,
    TypeSite,
)
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


def _create_compliance_finding(db_session, site_id, rule_id="TEST_RULE", status="NOK",
                                severity="high", actions_json=None):
    """Create a compliance finding."""
    f = ComplianceFinding(
        site_id=site_id,
        regulation="test_regulation",
        rule_id=rule_id,
        status=status,
        severity=severity,
        evidence="Test evidence",
        recommended_actions_json=actions_json or json.dumps(["Fix issue A", "Fix issue B"]),
        insight_status=InsightStatus.OPEN,
    )
    db_session.add(f)
    db_session.flush()
    return f


def _create_consumption_insight(db_session, site_id, loss_eur=5000):
    """Create a consumption insight with recommended actions."""
    ins = ConsumptionInsight(
        site_id=site_id,
        type="hors_horaires",
        severity="medium",
        message="Consommation hors horaires detectee",
        estimated_loss_eur=loss_eur,
        recommended_actions_json=json.dumps([
            {"title": "Programmer arret CVC", "rationale": "CVC actif la nuit", "expected_gain_eur": 3000},
        ]),
    )
    db_session.add(ins)
    db_session.flush()
    return ins


# ========================================
# Test Sync Idempotent
# ========================================

class TestSyncIdempotent:
    def test_double_sync_no_duplicates(self, client, db_session):
        """Two successive syncs should not create duplicates."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        r1 = client.post(f"/api/actions/sync?org_id={org.id}")
        assert r1.status_code == 200
        created_1 = r1.json()["created"]
        assert created_1 > 0

        r2 = client.post(f"/api/actions/sync?org_id={org.id}")
        assert r2.status_code == 200
        assert r2.json()["created"] == 0
        assert r2.json()["skipped"] == created_1

    def test_sync_creates_batch(self, client, db_session):
        """Each sync creates an ActionSyncBatch record."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        batches = db_session.query(ActionSyncBatch).all()
        assert len(batches) >= 1
        assert batches[0].org_id == org.id


# ========================================
# Test Preserve Workflow
# ========================================

class TestPreserveWorkflow:
    def test_patch_then_resync_preserves_status(self, client, db_session):
        """PATCH status/owner/notes, then resync -> must preserve them."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        actions = client.get(f"/api/actions/list?org_id={org.id}").json()
        assert len(actions) > 0
        action_id = actions[0]["id"]

        # PATCH
        r = client.patch(f"/api/actions/{action_id}", json={
            "status": "in_progress",
            "owner": "j.dupont@acme.fr",
            "notes": "Travaux en cours",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

        # Resync
        client.post(f"/api/actions/sync?org_id={org.id}")

        # Verify preserved
        item = db_session.query(ActionItem).filter(ActionItem.id == action_id).first()
        assert item.status == ActionStatus.IN_PROGRESS
        assert item.owner == "j.dupont@acme.fr"
        assert "Travaux en cours" in (item.notes or "")


# ========================================
# Test Priority
# ========================================

class TestPriority:
    def test_priority_range(self, client, db_session):
        """All action priorities must be between 1 and 5."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id, severity="critical")
        _create_compliance_finding(db_session, site.id, rule_id="RULE_2", severity="low")
        _create_consumption_insight(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        actions = client.get(f"/api/actions/list?org_id={org.id}").json()
        for a in actions:
            assert 1 <= a["priority"] <= 5

    def test_critical_has_high_priority(self, client, db_session):
        """Critical severity should produce priority 1 or 2."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id, severity="critical")
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        actions = client.get(f"/api/actions/list?org_id={org.id}").json()
        critical_actions = [a for a in actions if a["severity"] == "critical"]
        for a in critical_actions:
            assert a["priority"] <= 2


# ========================================
# Test Export CSV
# ========================================

class TestExportCSV:
    def test_export_returns_csv(self, client, db_session):
        """Export endpoint returns text/csv with header + rows."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        r = client.get(f"/api/actions/export.csv?org_id={org.id}")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]
        lines = r.text.strip().split("\n")
        assert len(lines) >= 2  # header + at least 1 data row
        assert "id" in lines[0]
        assert "titre" in lines[0]


# ========================================
# Test Dashboard 2min ActionHub
# ========================================

class TestDashboard2MinActionHub:
    def test_action_hub_in_dashboard(self, client, db_session):
        """Dashboard 2min should include action_hub field when actions exist."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        r = client.get("/api/dashboard/2min")
        assert r.status_code == 200
        data = r.json()
        assert "action_hub" in data
        hub = data["action_hub"]
        assert hub is not None
        assert "action_stats" in hub
        assert hub["action_stats"]["total"] > 0

    def test_action_hub_has_top_action(self, client, db_session):
        """action_hub.top_action should be present with expected fields."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        r = client.get("/api/dashboard/2min")
        data = r.json()
        top = data["action_hub"]["top_action"]
        assert top is not None
        assert "texte" in top
        assert "priorite" in top


# ========================================
# Test Patch Workflow
# ========================================

class TestPatchWorkflow:
    def test_patch_status(self, client, db_session):
        """PATCH /api/actions/{id} with valid status."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")
        actions = client.get(f"/api/actions/list?org_id={org.id}").json()
        aid = actions[0]["id"]

        r = client.patch(f"/api/actions/{aid}", json={"status": "done"})
        assert r.status_code == 200
        assert r.json()["status"] == "done"

    def test_patch_invalid_status(self, client, db_session):
        """PATCH with invalid status should return 400."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")
        actions = client.get(f"/api/actions/list?org_id={org.id}").json()
        aid = actions[0]["id"]

        r = client.patch(f"/api/actions/{aid}", json={"status": "invalid_status"})
        assert r.status_code == 400

    def test_patch_404(self, client, db_session):
        """PATCH non-existent action should return 404."""
        org, _ = _create_org_site(db_session)
        db_session.commit()

        r = client.patch("/api/actions/99999", json={"status": "done"})
        assert r.status_code == 404

    def test_patch_priority(self, client, db_session):
        """PATCH priority update."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")
        actions = client.get(f"/api/actions/list?org_id={org.id}").json()
        aid = actions[0]["id"]

        r = client.patch(f"/api/actions/{aid}", json={"priority": 1})
        assert r.status_code == 200
        assert r.json()["priority"] == 1


# ========================================
# Test Filter Endpoints
# ========================================

class TestFilterEndpoints:
    def test_filter_by_source_type(self, client, db_session):
        """Filter list by source_type=compliance."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        _create_consumption_insight(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        r = client.get(f"/api/actions/list?org_id={org.id}&source_type=compliance")
        assert r.status_code == 200
        data = r.json()
        assert all(a["source_type"] == "compliance" for a in data)

    def test_filter_by_status(self, client, db_session):
        """Filter list by status=open."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        r = client.get(f"/api/actions/list?org_id={org.id}&status=open")
        assert r.status_code == 200
        assert all(a["status"] == "open" for a in r.json())

    def test_summary_counts(self, client, db_session):
        """Summary should have counts and by_source."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        r = client.get(f"/api/actions/summary?org_id={org.id}")
        assert r.status_code == 200
        data = r.json()
        assert "counts" in data
        assert data["counts"]["total"] > 0
        assert "by_source" in data
        assert "compliance" in data["by_source"]

    def test_batches_list(self, client, db_session):
        """Batches endpoint returns sync history."""
        org, site = _create_org_site(db_session)
        _create_compliance_finding(db_session, site.id)
        db_session.commit()

        client.post(f"/api/actions/sync?org_id={org.id}")

        r = client.get(f"/api/actions/batches?org_id={org.id}")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert data[0]["created_count"] > 0

    def test_empty_list(self, client, db_session):
        """List with no actions returns empty array."""
        org, _ = _create_org_site(db_session)
        db_session.commit()

        r = client.get(f"/api/actions/list?org_id={org.id}")
        assert r.status_code == 200
        assert r.json() == []


# ========================================
# Test Direct Create (POST /api/actions)
# ========================================

class TestDirectCreate:
    def test_create_manual_action(self, client, db_session):
        """POST /api/actions with source_type=manual creates an action."""
        org, site = _create_org_site(db_session)
        db_session.commit()

        r = client.post("/api/actions", json={
            "org_id": org.id,
            "site_id": site.id,
            "source_type": "manual",
            "title": "Planifier audit energetique",
            "severity": "medium",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "open"  # action workflow status (from _serialize_action)
        assert data["title"] == "Planifier audit energetique"
        assert data["source_type"] == "manual"
        assert data["site_id"] == site.id
        assert 1 <= data["priority"] <= 5

    def test_create_insight_action(self, client, db_session):
        """POST /api/actions with source_type=insight + source_id."""
        org, site = _create_org_site(db_session)
        db_session.commit()

        r = client.post("/api/actions", json={
            "org_id": org.id,
            "site_id": site.id,
            "source_type": "insight",
            "source_id": "insight_42",
            "title": "Reduire consommation hors horaires",
            "severity": "high",
            "estimated_gain_eur": 12000,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["source_type"] == "insight"
        assert data["source_id"] == "insight_42"
        assert data["estimated_gain_eur"] == 12000

    def test_reject_empty_title(self, client, db_session):
        """POST /api/actions with empty title returns 422."""
        org, _ = _create_org_site(db_session)
        db_session.commit()

        r = client.post("/api/actions", json={
            "org_id": org.id,
            "source_type": "manual",
            "title": "",
        })
        assert r.status_code == 422

    def test_reject_invalid_source_type(self, client, db_session):
        """POST /api/actions with source_type=compliance returns 400."""
        org, _ = _create_org_site(db_session)
        db_session.commit()

        r = client.post("/api/actions", json={
            "org_id": org.id,
            "source_type": "compliance",
            "title": "Test action",
        })
        assert r.status_code == 400
        assert "manual" in r.json()["detail"] or "insight" in r.json()["detail"]

    def test_auto_compute_priority(self, client, db_session):
        """Priority auto-computed when omitted, using severity + gain."""
        org, _ = _create_org_site(db_session)
        db_session.commit()

        r = client.post("/api/actions", json={
            "org_id": org.id,
            "source_type": "manual",
            "title": "Action critique urgente",
            "severity": "critical",
            "estimated_gain_eur": 20000,
        })
        assert r.status_code == 200
        # critical + high gain -> priority should be 1
        assert r.json()["priority"] == 1

    def test_created_appears_in_list(self, client, db_session):
        """Manually created action appears in GET /api/actions/list."""
        org, site = _create_org_site(db_session)
        db_session.commit()

        client.post("/api/actions", json={
            "org_id": org.id,
            "site_id": site.id,
            "source_type": "manual",
            "title": "Action visible dans la liste",
        })

        r = client.get(f"/api/actions/list?org_id={org.id}")
        assert r.status_code == 200
        titles = [a["title"] for a in r.json()]
        assert "Action visible dans la liste" in titles

    def test_sync_does_not_close_manual_actions(self, client, db_session):
        """Sync auto-close must NOT affect manual/insight actions."""
        org, site = _create_org_site(db_session)
        db_session.commit()

        # Create a manual action
        r = client.post("/api/actions", json={
            "org_id": org.id,
            "site_id": site.id,
            "source_type": "manual",
            "title": "Action manuelle a preserver",
        })
        assert r.status_code == 200
        manual_id = r.json()["id"]

        # Run sync (no compliance/billing sources => would close everything without guard)
        client.post(f"/api/actions/sync?org_id={org.id}")

        # Manual action must still be OPEN
        item = db_session.query(ActionItem).filter(ActionItem.id == manual_id).first()
        assert item is not None
        assert item.status == ActionStatus.OPEN
