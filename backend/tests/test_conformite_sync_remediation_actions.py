"""
PROMEOS — Conformité P1 2026-05-23 : endpoint sync remediation actions.

`POST /api/conformite/sync-remediation-actions` — ferme la boucle
CadreApplicable DATA_MISSING → ActionCenterItem.

Vérifie :
- DATA_MISSING DT.SURFACE → 1 action créée
- Replay identique → 0 nouvelle action (idempotent par signature)
- NOT_APPLICABLE → 0 action jamais (by design service P0-5)
- Event log `created` avec payload `source=regulatory_rule` écrit
- Headers Idempotency-Key validé UUID v4
- Message FR en cas d'erreur
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # noqa: E402
from main import app  # noqa: E402
from models import (  # noqa: E402
    Base,
    EntiteJuridique,
    Organisation,
    Portefeuille,
    Site,
    TypeSite,
)
from models.v4.action_center_items import ActionCenterItem  # noqa: E402
from models.v4.enums import Domain, Kind, LifecycleState  # noqa: E402


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def client(db):
    """TestClient avec contexte org bypass JWT.

    Le middleware V4 `populate_org_context` requiert un JWT valide. En test on
    override la dependency pour lire `X-Org-Id` directement depuis le header
    de la requête et faire `set_org_context()` manuellement (yield/finally
    propre, pas de fuite cross-test).

    `require_v4_role` est aussi overridé pour bypass le RBAC en test.
    """
    from middleware.org_context import (
        populate_org_context,
        reset_org_context,
        set_org_context,
    )

    async def _override_populate_org_context(request: Request):
        """Lit X-Org-Id, set le ContextVar pour la durée de la requête."""
        org_id_header = request.headers.get("X-Org-Id")
        token = None
        if org_id_header:
            try:
                token = set_org_context(int(org_id_header))
            except (TypeError, ValueError):
                pass
        try:
            yield
        finally:
            if token is not None:
                reset_org_context(token)

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[populate_org_context] = _override_populate_org_context

    # Bypass RBAC require_v4_role (closures `_role_checker`) — override par scan
    # des dépendances de la route cible.
    for route in app.routes:
        if not hasattr(route, "dependant") or route.dependant is None:
            continue
        for dep in route.dependant.dependencies:
            if dep.call and getattr(dep.call, "__name__", "") == "_role_checker":
                app.dependency_overrides[dep.call] = lambda: {"sub": 1, "role": "user"}

    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_org_with_dt_data_missing(db):
    """Crée Org + EJ + PF + Site sans tertiaire_area_m2 → DT.DATA_MISSING.SURFACE."""
    org = Organisation(nom="Org P1", siren="111111111", type_client="bureau", actif=True)
    db.add(org)
    db.flush()
    ej = EntiteJuridique(organisation_id=org.id, nom="EJ", siren="111111111")
    db.add(ej)
    db.flush()
    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF")
    db.add(pf)
    db.flush()
    site = Site(
        portefeuille_id=pf.id,
        nom="Site Sync",
        type=TypeSite.BUREAU,
        adresse="x",
        code_postal="75001",
        ville="Paris",
        surface_m2=None,
        tertiaire_area_m2=None,
        actif=True,
    )
    db.add(site)
    db.commit()
    return org, site


def _headers(org_id, idempotency_key=None):
    h = {"X-Org-Id": str(org_id)}
    if idempotency_key:
        h["Idempotency-Key"] = idempotency_key
    return h


# ─── Création nominale ──────────────────────────────────────────────────────


def test_data_missing_dt_surface_creates_action(client, db):
    """DT.DATA_MISSING.SURFACE → 1 ActionCenterItem créé."""
    org, _ = _seed_org_with_dt_data_missing(db)
    response = client.post(
        "/api/conformite/sync-remediation-actions",
        headers=_headers(org.id),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["created"] >= 1
    # Vérifier en DB qu'au moins 1 ActionCenterItem existe avec kind=evidence_request + domain=conformite
    items = (
        db.query(ActionCenterItem)
        .filter(
            ActionCenterItem.organisation_id == org.id,
            ActionCenterItem.kind == Kind.EVIDENCE_REQUEST.value,
            ActionCenterItem.domain == Domain.CONFORMITE.value,
        )
        .all()
    )
    assert len(items) >= 1
    # Vérifier qu'au moins un porte le titre DT
    dt_items = [i for i in items if "Décret Tertiaire" in i.title]
    assert len(dt_items) >= 1


# ─── Idempotency : replay identique ─────────────────────────────────────────


def test_replay_does_not_duplicate(client, db):
    """2 appels successifs sans changement → 2e n'ajoute aucun ActionCenterItem."""
    org, _ = _seed_org_with_dt_data_missing(db)
    r1 = client.post("/api/conformite/sync-remediation-actions", headers=_headers(org.id))
    assert r1.status_code == 200
    count_after_1 = db.query(ActionCenterItem).filter(ActionCenterItem.organisation_id == org.id).count()

    r2 = client.post("/api/conformite/sync-remediation-actions", headers=_headers(org.id))
    assert r2.status_code == 200
    count_after_2 = db.query(ActionCenterItem).filter(ActionCenterItem.organisation_id == org.id).count()

    assert count_after_2 == count_after_1
    body2 = r2.json()
    assert body2["summary"]["created"] == 0
    assert body2["summary"]["skipped_existing"] >= 1


# ─── NOT_APPLICABLE : zéro action jamais ────────────────────────────────────


def test_not_applicable_never_creates_action(client, db):
    """Site avec toutes données présentes → 0 DATA_MISSING → 0 action créée."""
    org, site = _seed_org_with_dt_data_missing(db)
    # Compléter le site → plus de DT.DATA_MISSING.SURFACE
    site.surface_m2 = 1500
    site.tertiaire_area_m2 = 1500
    site.usage_principal = "BUREAUX"
    db.commit()

    response = client.post("/api/conformite/sync-remediation-actions", headers=_headers(org.id))
    assert response.status_code == 200
    body = response.json()
    # Aucun item ne doit être créé avec rule_code=DT pour ce site
    dt_items = (
        db.query(ActionCenterItem)
        .filter(
            ActionCenterItem.organisation_id == org.id,
            ActionCenterItem.kind == Kind.EVIDENCE_REQUEST.value,
        )
        .all()
    )
    dt_surface_items = [i for i in dt_items if "Surface tertiaire" in (i.title or "")]
    assert dt_surface_items == [], "Aucun item DT.SURFACE ne doit être créé quand les données sont complètes"


# ─── Audit event log ────────────────────────────────────────────────────────


def test_event_log_created_with_source_marker(client, db):
    """Chaque création écrit un event `created` avec payload `source=regulatory_rule`."""
    from models.v4.action_event_log import ActionEventLog

    org, _ = _seed_org_with_dt_data_missing(db)
    response = client.post("/api/conformite/sync-remediation-actions", headers=_headers(org.id))
    assert response.status_code == 200

    # Au moins un event `created` avec source=regulatory_rule
    events = db.query(ActionEventLog).filter(ActionEventLog.event_type == "created").all()
    regulatory_events = [e for e in events if (e.event_payload or {}).get("source") == "regulatory_rule"]
    assert len(regulatory_events) >= 1
    payload = regulatory_events[0].event_payload
    assert payload["rule_code"] == "DT"
    assert payload["reason_code"] == "DT.DATA_MISSING.SURFACE"
    assert payload["scope_level"] == "site"
    assert payload["remediation_field"] == "site.tertiaire_area_m2"


# ─── Idempotency-Key validation ─────────────────────────────────────────────


def test_invalid_idempotency_key_returns_400(client, db):
    """Header Idempotency-Key non-UUID → 400 avec message FR."""
    org, _ = _seed_org_with_dt_data_missing(db)
    response = client.post(
        "/api/conformite/sync-remediation-actions",
        headers=_headers(org.id, idempotency_key="not-a-uuid"),
    )
    assert response.status_code == 400
    detail = response.json().get("detail") or response.json()
    assert detail.get("code") == "IDEMPOTENCY_KEY_INVALID"
    assert "UUID" in detail.get("message", "")


def test_valid_idempotency_key_accepted(client, db):
    """Header Idempotency-Key UUID v4 valide → 200 sans erreur."""
    org, _ = _seed_org_with_dt_data_missing(db)
    response = client.post(
        "/api/conformite/sync-remediation-actions",
        headers=_headers(org.id, idempotency_key=str(uuid.uuid4())),
    )
    assert response.status_code == 200


# ─── Resolved items : pas re-créés ──────────────────────────────────────────


def test_closed_item_not_recreated(client, db):
    """Si l'utilisateur a clôturé un item, un 2e sync ne le recrée pas."""
    org, _ = _seed_org_with_dt_data_missing(db)
    # 1er sync : crée les items
    r1 = client.post("/api/conformite/sync-remediation-actions", headers=_headers(org.id))
    assert r1.status_code == 200
    created_ids = [c["id"] for c in r1.json()["created"]]
    assert len(created_ids) >= 1

    # Clôturer manuellement le 1er item
    from datetime import datetime, timezone

    item = db.query(ActionCenterItem).filter(ActionCenterItem.id == uuid.UUID(created_ids[0])).first()
    item.lifecycle_state = LifecycleState.CLOSED.value
    item.closure_reason = "resolved"
    item.closed_at = datetime.now(timezone.utc)
    db.commit()

    # 2e sync : ne doit PAS recréer l'item clos
    initial_count = db.query(ActionCenterItem).filter(ActionCenterItem.organisation_id == org.id).count()
    r2 = client.post("/api/conformite/sync-remediation-actions", headers=_headers(org.id))
    assert r2.status_code == 200
    final_count = db.query(ActionCenterItem).filter(ActionCenterItem.organisation_id == org.id).count()
    assert final_count == initial_count, "Un item clos ne doit pas être re-créé"

    body2 = r2.json()
    assert body2["summary"]["skipped_resolved"] >= 1
