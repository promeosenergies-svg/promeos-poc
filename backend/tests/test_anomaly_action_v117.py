"""
PROMEOS - Tests V117: Anomaly ↔ Action Link, Dismiss, Statuses
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base,
    Site,
    Organisation,
    EntiteJuridique,
    Portefeuille,
    ActionItem,
    ActionSourceType,
    ActionStatus,
    AnomalyActionLink,
    AnomalyDismissal,
    DismissReason,
    TypeSite,
)
from database import get_db
from main import app


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


def _create_org_site(db):
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="123456789")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="P1")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id, nom="Site Test", type=TypeSite.BUREAU, surface_m2=1000, actif=True
    )
    db.add(site)
    db.flush()
    db.commit()
    return org, site


# ========================================
# POST /api/actions/anomaly-links
# ========================================


class TestAnomalyLinks:
    def test_create_action_from_anomaly(self, client, db):
        org, site = _create_org_site(db)
        resp = client.post(
            "/api/actions/anomaly-links",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "MISSING_SURFACE",
                "site_id": site.id,
                "title": "Corriger surface manquante",
                "severity": "high",
            },
            headers={"X-Org-Id": str(org.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["action"]["title"] == "Corriger surface manquante"
        assert data["link_id"] is not None

    def test_link_to_existing_action(self, client, db):
        org, site = _create_org_site(db)
        # Create action first
        action = ActionItem(
            org_id=org.id,
            site_id=site.id,
            source_type=ActionSourceType.MANUAL,
            source_id="manual_test",
            source_key="manual:test:1",
            title="Action existante",
            status=ActionStatus.OPEN,
        )
        db.add(action)
        db.commit()

        resp = client.post(
            "/api/actions/anomaly-links",
            json={
                "anomaly_source": "billing",
                "anomaly_ref": "shadow_gap_42",
                "site_id": site.id,
                "action_id": action.id,
                "link_reason": "Ecart facturation lie",
            },
            headers={"X-Org-Id": str(org.id)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert data["action"]["id"] == action.id

    def test_idempotency_dedup(self, client, db):
        """Same idempotency_key returns existing action without creating duplicate."""
        org, site = _create_org_site(db)
        idem_key = "anomaly:patrimoine:MISSING_SURFACE:1"

        # First call
        resp1 = client.post(
            "/api/actions/anomaly-links",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "MISSING_SURFACE",
                "site_id": site.id,
                "title": "Fix surface",
                "idempotency_key": idem_key,
            },
            headers={"X-Org-Id": str(org.id)},
        )
        assert resp1.status_code == 200
        action_id = resp1.json()["action"]["id"]

        # Second call with same key
        resp2 = client.post(
            "/api/actions/anomaly-links",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "MISSING_SURFACE",
                "site_id": site.id,
                "title": "Fix surface (retry)",
                "idempotency_key": idem_key,
            },
            headers={"X-Org-Id": str(org.id)},
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "existing"
        assert resp2.json()["action"]["id"] == action_id

    def test_link_creates_event(self, client, db):
        org, site = _create_org_site(db)
        resp = client.post(
            "/api/actions/anomaly-links",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "LOW_SURFACE",
                "site_id": site.id,
                "title": "Verifier surface",
            },
            headers={"X-Org-Id": str(org.id)},
        )
        action_id = resp.json()["action"]["id"]
        # Fetch events sub-resource
        events_resp = client.get(
            f"/api/actions/{action_id}/events",
            headers={"X-Org-Id": str(org.id)},
        )
        assert events_resp.status_code == 200
        event_types = [e["event_type"] for e in events_resp.json()]
        assert "created" in event_types
        assert "anomaly_linked" in event_types


# ========================================
# POST /api/actions/anomaly-dismiss
# ========================================


class TestAnomalyDismiss:
    def test_dismiss_with_valid_reason(self, client, db):
        _create_org_site(db)
        resp = client.post(
            "/api/actions/anomaly-dismiss",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "MISSING_SURFACE",
                "site_id": 1,
                "reason_code": "false_positive",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

    def test_dismiss_invalid_reason_rejected(self, client, db):
        _create_org_site(db)
        resp = client.post(
            "/api/actions/anomaly-dismiss",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "MISSING_SURFACE",
                "site_id": 1,
                "reason_code": "invalid_reason",
            },
        )
        assert resp.status_code == 422

    def test_dismiss_idempotent_upsert(self, client, db):
        _create_org_site(db)
        payload = {
            "anomaly_source": "billing",
            "anomaly_ref": "shadow_gap_99",
            "site_id": 1,
            "reason_code": "known_issue",
            "reason_text": "Deja traite",
        }
        resp1 = client.post("/api/actions/anomaly-dismiss", json=payload)
        assert resp1.json()["status"] == "created"
        dismiss_id = resp1.json()["id"]

        # Second call updates
        payload["reason_code"] = "out_of_scope"
        resp2 = client.post("/api/actions/anomaly-dismiss", json=payload)
        assert resp2.json()["status"] == "updated"
        assert resp2.json()["id"] == dismiss_id

    def test_all_dismiss_reasons_accepted(self, client, db):
        _create_org_site(db)
        for reason in ["false_positive", "known_issue", "out_of_scope", "duplicate", "other"]:
            resp = client.post(
                "/api/actions/anomaly-dismiss",
                json={
                    "anomaly_source": "patrimoine",
                    "anomaly_ref": f"TEST_{reason}",
                    "site_id": 1,
                    "reason_code": reason,
                },
            )
            assert resp.status_code == 200, f"Failed for reason: {reason}"


# ========================================
# POST /api/actions/anomaly-statuses
# ========================================


class TestAnomalyStatuses:
    def test_open_status_by_default(self, client, db):
        _create_org_site(db)
        resp = client.post(
            "/api/actions/anomaly-statuses",
            json={
                "anomalies": [
                    {"anomaly_source": "patrimoine", "anomaly_ref": "MISSING_SURFACE", "site_id": 1}
                ]
            },
        )
        assert resp.status_code == 200
        statuses = resp.json()["statuses"]
        assert len(statuses) == 1
        assert statuses[0]["status"] == "open"
        assert statuses[0]["linked_actions"] == []
        assert statuses[0]["dismissal"] is None

    def test_linked_status_after_link(self, client, db):
        org, site = _create_org_site(db)
        # Create link
        client.post(
            "/api/actions/anomaly-links",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "LOW_SURFACE",
                "site_id": site.id,
                "title": "Fix it",
            },
            headers={"X-Org-Id": str(org.id)},
        )
        # Check status
        resp = client.post(
            "/api/actions/anomaly-statuses",
            json={
                "anomalies": [
                    {"anomaly_source": "patrimoine", "anomaly_ref": "LOW_SURFACE", "site_id": site.id}
                ]
            },
        )
        statuses = resp.json()["statuses"]
        assert statuses[0]["status"] == "linked"
        assert len(statuses[0]["linked_actions"]) == 1

    def test_dismissed_status_after_dismiss(self, client, db):
        _create_org_site(db)
        client.post(
            "/api/actions/anomaly-dismiss",
            json={
                "anomaly_source": "patrimoine",
                "anomaly_ref": "MISSING_SURFACE",
                "site_id": 1,
                "reason_code": "false_positive",
            },
        )
        resp = client.post(
            "/api/actions/anomaly-statuses",
            json={
                "anomalies": [
                    {"anomaly_source": "patrimoine", "anomaly_ref": "MISSING_SURFACE", "site_id": 1}
                ]
            },
        )
        statuses = resp.json()["statuses"]
        assert statuses[0]["status"] == "dismissed"
        assert statuses[0]["dismissal"]["reason_code"] == "false_positive"

    def test_batch_multiple_anomalies(self, client, db):
        _create_org_site(db)
        resp = client.post(
            "/api/actions/anomaly-statuses",
            json={
                "anomalies": [
                    {"anomaly_source": "patrimoine", "anomaly_ref": "A1", "site_id": 1},
                    {"anomaly_source": "billing", "anomaly_ref": "A2", "site_id": 1},
                    {"anomaly_source": "patrimoine", "anomaly_ref": "A3", "site_id": 1},
                ]
            },
        )
        assert resp.status_code == 200
        assert len(resp.json()["statuses"]) == 3
