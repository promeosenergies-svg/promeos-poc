"""
Tests org-scoping cross-tenant strict pour routes Sol V1 Phase 4.

CRITIQUE : chaque route Sol doit garantir qu'une org ne peut pas accéder aux
données d'une autre org, même en connaissant correlation_id / token / etc.

Couvre aussi l'admin guard pour /api/sol/policy (require_platform_admin).

Sprint CX 2.5 hardening S2 : require_platform_admin NE bypass PAS DEMO_MODE.
Donc même en DEMO_MODE, /policy doit refuser sans JWT admin valide.
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

import sol.engines  # noqa: F401
from database import get_db
from main import app
from models import Base
from models.enums import UserRole
from models.iam import User, UserOrgRole
from models.organisation import Organisation


@pytest.fixture
def two_orgs_client():
    """TestClient avec 2 orgs distinctes + logs Sol pré-seedés par org."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    org_a = Organisation(nom="Org A", actif=True)
    org_b = Organisation(nom="Org B", actif=True)
    db.add_all([org_a, org_b])
    db.commit()
    db.refresh(org_a)
    db.refresh(org_b)

    user = User(
        email="cross-tenant@sol.local",
        hashed_password="x",
        nom="X",
        prenom="Y",
        actif=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(UserOrgRole(user_id=user.id, org_id=org_a.id, role=UserRole.DG_OWNER))
    db.commit()

    from services.demo_state import DemoState
    DemoState.set_demo_org(org_id=org_a.id, org_nom=org_a.nom)

    # Seed 1 SolActionLog pour org_a et 1 pour org_b
    from datetime import datetime, timezone
    from models.sol import SolActionLog

    for org in (org_a, org_b):
        db.add(
            SolActionLog(
                org_id=org.id,
                user_id=user.id,
                correlation_id=f"11111111-2222-3333-4444-{org.id:012d}",
                intent_kind="dummy_noop",
                action_phase="proposed",
                inputs_hash="a" * 64,
                plan_json={"org": org.nom},
            )
        )
    db.commit()

    def override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=False)
    yield client, db, org_a, org_b, user
    app.dependency_overrides.clear()
    db.close()
    engine.dispose()


# ─────────────────────────────────────────────────────────────────────────────
# /api/sol/propose — org_id auto depuis DemoState
# ─────────────────────────────────────────────────────────────────────────────


def test_propose_uses_org_from_demo_state(two_orgs_client):
    """En DEMO_MODE, propose résout org_id depuis DemoState (ici org_a)."""
    client, db, org_a, org_b, _ = two_orgs_client
    r = client.post("/api/sol/propose", json={"intent": "dummy_noop", "params": {}})
    assert r.status_code == 201

    # Le log ajouté doit être org_a, pas org_b
    from models.sol import SolActionLog
    new_logs = (
        db.query(SolActionLog)
        .filter(SolActionLog.intent_kind == "dummy_noop")
        .filter(SolActionLog.org_id == org_a.id)
        .filter(SolActionLog.action_phase == "proposed")
        .all()
    )
    assert len(new_logs) >= 2  # 1 seed + 1 juste créé


# ─────────────────────────────────────────────────────────────────────────────
# /api/sol/pending — isolation cross-tenant
# ─────────────────────────────────────────────────────────────────────────────


def test_pending_never_leaks_other_org(two_orgs_client):
    """GET /pending ne retourne que les pending de org_a (DemoState)."""
    client, db, org_a, org_b, user = two_orgs_client

    # Seed 1 pending pour org_a et 1 pour org_b
    from datetime import datetime, timedelta, timezone
    from models.sol import SolPendingAction

    for org, ct_suffix in ((org_a, "aaa"), (org_b, "bbb")):
        db.add(
            SolPendingAction(
                correlation_id=f"99999999-9999-9999-9999-{org.id:012d}",
                org_id=org.id,
                user_id=user.id,
                intent_kind="dummy_noop",
                plan_json={},
                scheduled_for=datetime.now(timezone.utc) + timedelta(minutes=15),
                cancellation_token=f"ct-{ct_suffix}-" + "x" * 20,
                status="waiting",
            )
        )
    db.commit()

    r = client.get("/api/sol/pending")
    assert r.status_code == 200
    body = r.json()
    # Tous les items retournés sont de org_a (via DemoState)
    assert body["total"] == 1
    assert body["items"][0]["correlation_id"].endswith(f"{org_a.id:012d}")


# ─────────────────────────────────────────────────────────────────────────────
# /api/sol/audit — isolation cross-tenant
# ─────────────────────────────────────────────────────────────────────────────


def test_audit_list_org_scoped(two_orgs_client):
    """GET /audit ne retourne que les logs de org_a."""
    client, db, org_a, org_b, _ = two_orgs_client
    r = client.get("/api/sol/audit")
    assert r.status_code == 200
    body = r.json()
    for item in body["items"]:
        assert not item["correlation_id"].endswith(f"{org_b.id:012d}"), (
            f"Cross-tenant leak: {item['correlation_id']}"
        )


def test_audit_csv_export_org_scoped(two_orgs_client):
    """GET /audit/export CSV ne contient que les logs de org_a."""
    client, db, org_a, org_b, _ = two_orgs_client
    r = client.get("/api/sol/audit/export")
    assert r.status_code == 200
    csv_body = r.text
    # correlation_id de org_b ne doit PAS apparaître
    assert f"{org_b.id:012d}" not in csv_body
    # Headers CSV présents
    assert "correlation_id" in csv_body


def test_audit_csv_injection_safe(two_orgs_client):
    """Valeurs suspectes (=, +, -, @) sont préfixées d'apostrophe pour bloquer
    l'évaluation de formules Excel/LibreOffice/Google Sheets."""
    client, db, org_a, org_b, user = two_orgs_client

    # Injecter un outcome_message commençant par "=" (formula)
    from models.sol import SolActionLog
    db.add(
        SolActionLog(
            org_id=org_a.id,
            user_id=user.id,
            correlation_id="injected0-aaaa-bbbb-cccc-000000000099",
            intent_kind="dummy_noop",
            action_phase="refused",
            inputs_hash="a" * 64,
            plan_json={},
            outcome_code="test",
            outcome_message="=IMPORTXML(1,2)",  # payload formula
        )
    )
    db.commit()

    r = client.get("/api/sol/audit/export")
    assert r.status_code == 200
    csv_body = r.text
    # Doit contenir la valeur préfixée d'apostrophe (neutralise formula)
    assert "'=IMPORTXML" in csv_body


# ─────────────────────────────────────────────────────────────────────────────
# /api/sol/policy — admin guard (require_platform_admin strict)
# ─────────────────────────────────────────────────────────────────────────────


def test_policy_get_requires_admin_jwt(two_orgs_client):
    """Sans JWT admin, /api/sol/policy retourne 401 même en DEMO_MODE."""
    client, _, _, _, _ = two_orgs_client
    r = client.get("/api/sol/policy")
    # require_platform_admin S2 : pas de bypass DEMO_MODE
    assert r.status_code in (401, 403)


def test_policy_put_requires_admin_jwt(two_orgs_client):
    """PUT /policy — même contrainte admin strict."""
    client, _, _, _, _ = two_orgs_client
    r = client.put(
        "/api/sol/policy",
        json={"confidence_threshold": 0.90, "grace_period_seconds": 600},
    )
    assert r.status_code in (401, 403)
