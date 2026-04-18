"""
Tests routes Sol V1 Phase 4 — propose / preview / confirm / cancel / pending / stubs.

Pattern : TestClient FastAPI sur main.app avec DB in-memory SQLite override.
Couvre :
- Happy path propose → preview → confirm → cancel
- Stubs 501 ask + headline
- GET /pending org-scoped
- Gestion erreur correlation_id + code + message_fr
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("PROMEOS_JWT_SECRET", "test_only_not_for_production")
os.environ.setdefault("SECRET_KEY", "test_only_not_for_production")
os.environ.setdefault("SOL_SECRET_KEY", "test_only_not_for_production")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("PROMEOS_DEMO_MODE", "true")

import sol.engines  # noqa: F401 — register DummyEngine
from database import get_db
from main import app
from models import Base
from models.iam import User, UserOrgRole
from models.organisation import Organisation
from models.enums import UserRole


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures TestClient avec DB in-memory + override
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def sol_client():
    """TestClient avec DB in-memory + org+user seedés + DEMO_MODE."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    db = SessionLocal()
    org = Organisation(nom="Route Test Org", actif=True)
    db.add(org)
    db.commit()
    db.refresh(org)

    user = User(
        email="route-test@sol.local",
        hashed_password="x",
        nom="Route",
        prenom="Tester",
        actif=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Wire UserOrgRole pour que cx_logger membership check passe
    db.add(UserOrgRole(user_id=user.id, org_id=org.id, role=UserRole.DG_OWNER))
    db.commit()

    # DemoState pour resolve_org_id en DEMO_MODE
    from services.demo_state import DemoState
    DemoState.set_demo_org(org_id=org.id, org_nom=org.nom)

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client, db, org, user
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/propose
# ─────────────────────────────────────────────────────────────────────────────


def test_propose_dummy_noop_success(sol_client):
    client, db, org, user = sol_client
    r = client.post(
        "/api/sol/propose",
        json={"intent": "dummy_noop", "params": {"confidence": 0.94}},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "plan"
    assert body["plan"]["intent"] == "dummy_noop"
    assert body["plan"]["confidence"] == 0.94


def test_propose_dummy_noop_refuses(sol_client):
    client, db, org, user = sol_client
    r = client.post(
        "/api/sol/propose",
        json={"intent": "dummy_noop", "params": {"should_refuse": True}},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["type"] == "refused"
    assert body["refused"]["reason_code"] == "confidence_low"


def test_propose_unknown_intent_refuses(sol_client):
    client, db, org, user = sol_client
    r = client.post(
        "/api/sol/propose",
        json={"intent": "invoice_dispute", "params": {}},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["type"] == "refused"
    assert body["refused"]["reason_code"] == "unknown_intent"


def test_propose_missing_intent_422(sol_client):
    client, db, org, user = sol_client
    r = client.post("/api/sol/propose", json={"params": {}})
    assert r.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/sol/preview + POST /api/sol/confirm + POST /api/sol/cancel
# ─────────────────────────────────────────────────────────────────────────────


def _propose_and_get_correlation(client, intent="dummy_noop", params=None):
    r = client.post(
        "/api/sol/propose",
        json={"intent": intent, "params": params or {"confidence": 0.95}},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["type"] == "plan"
    return body["plan"]["correlation_id"]


def test_preview_emits_token(sol_client):
    client, db, org, user = sol_client
    correlation_id = _propose_and_get_correlation(client)

    r = client.post(
        "/api/sol/preview",
        json={
            "correlation_id": correlation_id,
            "intent": "dummy_noop",
            "params": {"confidence": 0.95},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["confirmation_token"]
    assert body["plan"]["correlation_id"] == correlation_id


def test_confirm_schedules_pending(sol_client):
    client, db, org, user = sol_client
    correlation_id = _propose_and_get_correlation(client)

    pv = client.post(
        "/api/sol/preview",
        json={
            "correlation_id": correlation_id,
            "intent": "dummy_noop",
            "params": {"confidence": 0.95},
        },
    ).json()

    r = client.post(
        "/api/sol/confirm",
        json={
            "correlation_id": correlation_id,
            "confirmation_token": pv["confirmation_token"],
            "intent": "dummy_noop",
            "params": {"confidence": 0.95},
        },
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["pending_action_id"] > 0
    assert body["cancellation_token"]


def test_confirm_invalid_token_401(sol_client):
    client, db, org, user = sol_client
    correlation_id = _propose_and_get_correlation(client)

    r = client.post(
        "/api/sol/confirm",
        json={
            "correlation_id": correlation_id,
            "confirmation_token": "invalid-token-xxx",
            "intent": "dummy_noop",
            "params": {"confidence": 0.95},
        },
    )
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "invalid_token"


def test_cancel_by_token(sol_client):
    client, db, org, user = sol_client
    # Full cycle : propose + preview + confirm + cancel
    correlation_id = _propose_and_get_correlation(client)
    pv = client.post(
        "/api/sol/preview",
        json={
            "correlation_id": correlation_id,
            "intent": "dummy_noop",
            "params": {"confidence": 0.95},
        },
    ).json()
    cf = client.post(
        "/api/sol/confirm",
        json={
            "correlation_id": correlation_id,
            "confirmation_token": pv["confirmation_token"],
            "intent": "dummy_noop",
            "params": {"confidence": 0.95},
        },
    ).json()

    r = client.post("/api/sol/cancel", json={"cancellation_token": cf["cancellation_token"]})
    assert r.status_code == 200, r.text
    assert r.json()["correlation_id"] == correlation_id


def test_cancel_unknown_token_404(sol_client):
    client, db, org, user = sol_client
    r = client.post("/api/sol/cancel", json={"cancellation_token": "ghost-token-of-sufficient-length-xxx"})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "pending_not_found"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/sol/pending
# ─────────────────────────────────────────────────────────────────────────────


def test_pending_list_empty(sol_client):
    client, db, org, user = sol_client
    r = client.get("/api/sol/pending")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


def test_pending_list_after_schedule(sol_client):
    client, db, org, user = sol_client
    correlation_id = _propose_and_get_correlation(client)
    pv = client.post(
        "/api/sol/preview",
        json={"correlation_id": correlation_id, "intent": "dummy_noop", "params": {"confidence": 0.95}},
    ).json()
    client.post(
        "/api/sol/confirm",
        json={
            "correlation_id": correlation_id,
            "confirmation_token": pv["confirmation_token"],
            "intent": "dummy_noop",
            "params": {"confidence": 0.95},
        },
    )

    r = client.get("/api/sol/pending")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["correlation_id"] == correlation_id
    assert body["items"][0]["status"] == "waiting"


# ─────────────────────────────────────────────────────────────────────────────
# Stubs /ask + /headline
# ─────────────────────────────────────────────────────────────────────────────


def test_ask_stub_501(sol_client):
    client, _, _, _ = sol_client
    r = client.post("/api/sol/ask", json={"question_fr": "Combien coûte Lyon ce mois ?"})
    assert r.status_code == 501
    assert r.json()["detail"]["code"] == "not_implemented_yet"


def test_headline_stub_501(sol_client):
    client, _, _, _ = sol_client
    r = client.post("/api/sol/headline", json={"template_key": "x", "context": {}})
    assert r.status_code == 501
