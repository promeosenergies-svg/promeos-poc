"""
PROMEOS - Tests Sprint V5.0: Action CRUD + Auto-Events + Idempotency
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
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    ActionItem, ActionSourceType, ActionStatus,
    ActionEvent, ActionComment, ActionEvidence,
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
    site = Site(portefeuille_id=pf.id, nom="Site Test", type=TypeSite.BUREAU, surface_m2=1000, actif=True)
    db.add(site)
    db.flush()
    db.commit()
    return org, site


def _create_action_via_api(client, site_id=None, title="Test action", **kwargs):
    payload = {"title": title, "source_type": "manual"}
    if site_id:
        payload["site_id"] = site_id
    payload.update(kwargs)
    resp = client.post("/api/actions", json=payload)
    return resp


# ========================================
# Comments CRUD
# ========================================

class TestCommentsCRUD:
    def test_add_and_list_comments(self, db, client):
        """POST + GET comments work."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        # Add two comments
        r1 = client.post(f"/api/actions/{action_id}/comments", json={
            "author": "J. Dupont",
            "body": "Premier commentaire",
        })
        assert r1.status_code == 200
        assert r1.json()["author"] == "J. Dupont"
        assert r1.json()["body"] == "Premier commentaire"

        r2 = client.post(f"/api/actions/{action_id}/comments", json={
            "author": "A. Martin",
            "body": "Deuxieme commentaire",
        })
        assert r2.status_code == 200

        # List
        r3 = client.get(f"/api/actions/{action_id}/comments")
        assert r3.status_code == 200
        comments = r3.json()
        assert len(comments) == 2
        assert comments[0]["author"] == "J. Dupont"

    def test_reject_empty_comment_body(self, db, client):
        """Empty body is rejected."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        r = client.post(f"/api/actions/{action_id}/comments", json={
            "author": "Test",
            "body": "   ",
        })
        assert r.status_code == 422

    def test_comment_on_nonexistent_action(self, db, client):
        """Comment on nonexistent action returns 404."""
        _create_org_site(db)
        r = client.post("/api/actions/99999/comments", json={
            "author": "Test",
            "body": "Should fail",
        })
        assert r.status_code == 404


# ========================================
# Evidence CRUD
# ========================================

class TestEvidenceCRUD:
    def test_add_and_list_evidence(self, db, client):
        """POST + GET evidence work."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        r1 = client.post(f"/api/actions/{action_id}/evidence", json={
            "label": "Rapport audit",
            "file_url": "https://docs.example.com/audit.pdf",
            "mime_type": "application/pdf",
            "uploaded_by": "J. Dupont",
        })
        assert r1.status_code == 200
        assert r1.json()["label"] == "Rapport audit"

        # List
        r2 = client.get(f"/api/actions/{action_id}/evidence")
        assert r2.status_code == 200
        assert len(r2.json()) == 1

    def test_reject_empty_evidence_label(self, db, client):
        """Empty label is rejected."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        r = client.post(f"/api/actions/{action_id}/evidence", json={
            "label": "  ",
        })
        assert r.status_code == 422


# ========================================
# Events (audit trail)
# ========================================

class TestAutoEvents:
    def test_auto_event_on_create(self, db, client):
        """Creating an action generates a 'created' event."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        r = client.get(f"/api/actions/{action_id}/events")
        assert r.status_code == 200
        events = r.json()
        assert len(events) >= 1
        assert events[0]["event_type"] == "created"

    def test_auto_event_on_status_change(self, db, client):
        """PATCH status generates a 'status_change' event."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        client.patch(f"/api/actions/{action_id}", json={"status": "in_progress"})

        r = client.get(f"/api/actions/{action_id}/events")
        events = r.json()
        status_events = [e for e in events if e["event_type"] == "status_change"]
        assert len(status_events) == 1
        assert status_events[0]["old_value"] == "open"
        assert status_events[0]["new_value"] == "in_progress"

    def test_auto_event_on_comment(self, db, client):
        """Adding a comment generates a 'commented' event."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        client.post(f"/api/actions/{action_id}/comments", json={
            "author": "Test",
            "body": "Hello",
        })

        r = client.get(f"/api/actions/{action_id}/events")
        events = r.json()
        comment_events = [e for e in events if e["event_type"] == "commented"]
        assert len(comment_events) == 1
        assert comment_events[0]["actor"] == "Test"

    def test_auto_event_on_evidence(self, db, client):
        """Adding evidence generates an 'evidence_added' event."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        client.post(f"/api/actions/{action_id}/evidence", json={
            "label": "Photo chantier",
            "uploaded_by": "J. Dupont",
        })

        r = client.get(f"/api/actions/{action_id}/events")
        events = r.json()
        evidence_events = [e for e in events if e["event_type"] == "evidence_added"]
        assert len(evidence_events) == 1

    def test_closed_at_set_on_done(self, db, client):
        """Setting status to 'done' sets closed_at."""
        org, site = _create_org_site(db)
        resp = _create_action_via_api(client, site.id)
        action_id = resp.json()["id"]

        r = client.patch(f"/api/actions/{action_id}", json={"status": "done"})
        assert r.status_code == 200
        assert r.json()["closed_at"] is not None


# ========================================
# Idempotency + Collision Detection
# ========================================

class TestIdempotency:
    def test_idempotency_key_returns_existing(self, db, client):
        """Same idempotency_key returns existing action instead of creating duplicate."""
        org, site = _create_org_site(db)

        r1 = _create_action_via_api(client, site.id, title="Unique action", idempotency_key="idem_123")
        assert r1.status_code == 200
        # Note: _serialize_action overwrites "status" key with action's workflow status
        assert r1.json()["title"] == "Unique action"
        id1 = r1.json()["id"]

        r2 = _create_action_via_api(client, site.id, title="Different title", idempotency_key="idem_123")
        assert r2.status_code == 200
        # Second call returns existing action (same id, original title)
        assert r2.json()["id"] == id1
        assert r2.json()["title"] == "Unique action"  # original title, not new one

    def test_no_idempotency_key_creates_new(self, db, client):
        """Without idempotency_key, always creates a new action."""
        org, site = _create_org_site(db)

        r1 = _create_action_via_api(client, site.id, title="Action 1")
        r2 = _create_action_via_api(client, site.id, title="Action 2")
        assert r1.json()["id"] != r2.json()["id"]

    def test_collision_detection_warning(self, db, client):
        """Creating action with same title + site within 24h returns warning."""
        org, site = _create_org_site(db)

        r1 = _create_action_via_api(client, site.id, title="Declarer OPERAT", source_id="src_1")
        assert r1.status_code == 200
        id1 = r1.json()["id"]

        r2 = _create_action_via_api(client, site.id, title="Declarer OPERAT", source_id="src_2")
        assert r2.status_code == 200
        # Still created (warning, not block) — new id
        assert r2.json()["id"] != id1
        assert r2.json().get("warning") == "similar_action_exists"
        assert r2.json().get("similar_id") == id1
