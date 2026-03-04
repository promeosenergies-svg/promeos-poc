"""
PROMEOS — Tests Console Actions (V1)
CRUD, campaign_sites, timestamps, filtres, 404/422 propres.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app
from models import Base, Organisation
from database import get_db


@pytest.fixture
def client():
    """Client with isolated in-memory DB."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed a demo org + site so actions can reference them
    org = Organisation(id=1, nom="Test Corp")
    session.add(org)
    session.commit()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()


# ── CREATE ──────────────────────────────────────────────────────


class TestActionCreate:
    def test_create_minimal(self, client):
        r = client.post("/api/actions", json={"title": "Corriger anomalie conso"})
        assert r.status_code == 200
        data = r.json()
        # Note: response has {"status": "open", ...} because _serialize_action
        # overwrites the "created" status key with the action's workflow status
        assert data["status"] == "open"
        assert data["title"] == "Corriger anomalie conso"
        assert data["id"] is not None

    def test_create_with_all_fields(self, client):
        r = client.post(
            "/api/actions",
            json={
                "title": "Vérifier facture EDF",
                "source_type": "manual",
                "severity": "high",
                "priority": 2,
                "estimated_gain_eur": 5000.0,
                "due_date": "2026-06-30",
                "owner": "DAF",
                "notes": "Facture suspecte",
                "co2e_savings_est_kg": 120.5,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["estimated_gain_eur"] == 5000.0
        assert data["severity"] == "high"
        assert data["priority"] == 2
        assert data["owner"] == "DAF"
        assert data["co2e_savings_est_kg"] == 120.5

    def test_create_returns_timestamps(self, client):
        r = client.post("/api/actions", json={"title": "Action timestamped"})
        data = r.json()
        assert "created_at" in data
        assert data["created_at"] is not None
        assert "updated_at" in data
        assert data["updated_at"] is not None

    def test_create_with_campaign_sites(self, client):
        r = client.post(
            "/api/actions",
            json={
                "title": "Campagne multi-sites",
                "campaign_sites": [1, 2, 3],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["campaign_sites"] == [1, 2, 3]

    def test_create_campaign_sites_none(self, client):
        r = client.post("/api/actions", json={"title": "Action mono-site"})
        data = r.json()
        assert data["campaign_sites"] is None

    def test_create_idempotency(self, client):
        payload = {"title": "Idem action", "idempotency_key": "test-idem-001"}
        r1 = client.post("/api/actions", json=payload)
        assert r1.status_code == 200
        id1 = r1.json()["id"]
        # Second call with same key returns same action
        r2 = client.post("/api/actions", json=payload)
        assert r2.status_code == 200
        assert r2.json()["id"] == id1


# ── VALIDATION ──────────────────────────────────────────────────


class TestActionValidation:
    def test_create_empty_title_422(self, client):
        r = client.post("/api/actions", json={"title": ""})
        assert r.status_code == 422

    def test_create_whitespace_title_422(self, client):
        r = client.post("/api/actions", json={"title": "   "})
        assert r.status_code == 422

    def test_create_invalid_source_type_400(self, client):
        r = client.post(
            "/api/actions",
            json={
                "title": "Test",
                "source_type": "invalid_source",
            },
        )
        assert r.status_code == 400

    def test_create_invalid_priority_422(self, client):
        r = client.post(
            "/api/actions",
            json={
                "title": "Test",
                "priority": 99,
            },
        )
        assert r.status_code == 422  # Pydantic Field(ge=1, le=5) constraint

    def test_create_invalid_date_400(self, client):
        r = client.post(
            "/api/actions",
            json={
                "title": "Test",
                "due_date": "not-a-date",
            },
        )
        assert r.status_code == 400


# ── LIST + FILTERS ──────────────────────────────────────────────


class TestActionList:
    def test_list_empty(self, client):
        r = client.get("/api/actions/list")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_after_create(self, client):
        client.post("/api/actions", json={"title": "A1"})
        client.post("/api/actions", json={"title": "A2"})
        r = client.get("/api/actions/list")
        assert len(r.json()) == 2

    def test_list_filter_status(self, client):
        client.post("/api/actions", json={"title": "Open one"})
        r = client.get("/api/actions/list?status=open")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_list_filter_invalid_status_400(self, client):
        r = client.get("/api/actions/list?status=invalid_status")
        assert r.status_code == 400


# ── DETAIL ──────────────────────────────────────────────────────


class TestActionDetail:
    def test_detail_existing(self, client):
        r = client.post("/api/actions", json={"title": "Detail test"})
        aid = r.json()["id"]
        r2 = client.get(f"/api/actions/{aid}")
        assert r2.status_code == 200
        data = r2.json()
        assert data["title"] == "Detail test"
        assert "comments_count" in data
        assert "evidence_count" in data
        assert "events_count" in data
        assert "created_at" in data

    def test_detail_404(self, client):
        r = client.get("/api/actions/999999")
        assert r.status_code == 404


# ── PATCH ───────────────────────────────────────────────────────


class TestActionPatch:
    def test_patch_status(self, client):
        r = client.post("/api/actions", json={"title": "Patch me"})
        aid = r.json()["id"]
        r2 = client.patch(f"/api/actions/{aid}", json={"status": "in_progress"})
        assert r2.status_code == 200
        assert r2.json()["status"] == "in_progress"

    def test_patch_owner(self, client):
        r = client.post("/api/actions", json={"title": "Assign me"})
        aid = r.json()["id"]
        r2 = client.patch(f"/api/actions/{aid}", json={"owner": "Jean Dupont"})
        assert r2.status_code == 200
        assert r2.json()["owner"] == "Jean Dupont"

    def test_patch_invalid_status_400(self, client):
        r = client.post("/api/actions", json={"title": "Bad status"})
        aid = r.json()["id"]
        r2 = client.patch(f"/api/actions/{aid}", json={"status": "invalid"})
        assert r2.status_code == 400

    def test_patch_404(self, client):
        r = client.patch("/api/actions/999999", json={"status": "done"})
        assert r.status_code == 404


# ── SUMMARY ─────────────────────────────────────────────────────


class TestActionSummary:
    def test_summary_empty(self, client):
        r = client.get("/api/actions/summary")
        assert r.status_code == 200
        data = r.json()
        assert "counts" in data
        assert "by_source" in data
        assert data["counts"]["total"] == 0

    def test_summary_with_data(self, client):
        client.post("/api/actions", json={"title": "S1", "estimated_gain_eur": 1000})
        client.post("/api/actions", json={"title": "S2", "estimated_gain_eur": 2000})
        r = client.get("/api/actions/summary")
        data = r.json()
        assert data["counts"]["total"] == 2
        assert data["total_gain_eur"] == 3000.0


# ── COMMENTS ────────────────────────────────────────────────────


class TestActionComments:
    def test_add_and_list_comments(self, client):
        r = client.post("/api/actions", json={"title": "Commentable"})
        aid = r.json()["id"]

        # Add
        r2 = client.post(
            f"/api/actions/{aid}/comments",
            json={
                "author": "Amine",
                "body": "Premier commentaire",
            },
        )
        assert r2.status_code == 200
        assert r2.json()["body"] == "Premier commentaire"

        # List
        r3 = client.get(f"/api/actions/{aid}/comments")
        assert r3.status_code == 200
        assert len(r3.json()) == 1

    def test_comment_empty_body_422(self, client):
        r = client.post("/api/actions", json={"title": "No comment"})
        aid = r.json()["id"]
        r2 = client.post(
            f"/api/actions/{aid}/comments",
            json={
                "author": "X",
                "body": "",
            },
        )
        assert r2.status_code == 422


# ── EVENTS ──────────────────────────────────────────────────────


class TestActionEvents:
    def test_events_created_on_create(self, client):
        r = client.post("/api/actions", json={"title": "Evented"})
        aid = r.json()["id"]
        r2 = client.get(f"/api/actions/{aid}/events")
        assert r2.status_code == 200
        events = r2.json()
        assert len(events) >= 1
        assert events[0]["event_type"] == "created"

    def test_events_on_status_change(self, client):
        r = client.post("/api/actions", json={"title": "Status tracked"})
        aid = r.json()["id"]
        client.patch(f"/api/actions/{aid}", json={"status": "in_progress"})
        r2 = client.get(f"/api/actions/{aid}/events")
        types = [e["event_type"] for e in r2.json()]
        assert "status_change" in types


# ── EXPORT ──────────────────────────────────────────────────────


class TestActionExport:
    def test_export_csv_empty(self, client):
        r = client.get("/api/actions/export.csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers["content-type"]

    def test_export_csv_with_data(self, client):
        client.post("/api/actions", json={"title": "Export me"})
        r = client.get("/api/actions/export.csv")
        content = r.text
        assert "Export me" in content
