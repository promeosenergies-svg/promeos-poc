"""Conftest local backend/tests/api/ — Sprint M2-3.

Override l'autouse parent `_ensure_seeded` (qui exige DB HELIOS réelle)
pour les tests API qui ne touchent pas la DB métier.

Sprint M2-3.B : ajoute fixtures JWT (admin/user/viewer tokens) pour tests
RBAC wrapper `require_v4_role`. Les rôles legacy (dg_owner, energy_manager,
auditeur) sont émis dans le JWT — le mapping V4 (`backend/middleware/rbac.py`)
fait le pont vers les Role enum V4.

Cohérent pattern Sprint M2-2 backend/tests/unit/conftest.py.
"""

import os

import pytest

# Sprint M2-3.B : JWT_SECRET requis pour create_access_token. Tests doivent
# pouvoir tourner standalone (sans .env présent). Fallback test-safe.
os.environ.setdefault("PROMEOS_JWT_SECRET", "m2_3_b_test_secret_do_not_use_prod")

from services.iam_service import create_access_token  # noqa: E402

# M2-4.3 : importe les models V4 au niveau module → enregistre les 8 tables V4
# dans `Base.metadata` AVANT que la fixture `app_client` (conftest racine) ne
# fasse `create_all`. Sans ça, le 1er test V4 d'un process tourne sur une DB
# in-memory sans les tables V4 (app_client crée les tables puis importe `main`).
from models.v4.action_blockers import ActionBlocker  # noqa: E402, F401
from models.v4.action_center_items import ActionCenterItem  # noqa: E402, F401
from models.v4.action_event_log import ActionEventLog  # noqa: E402, F401
from models.v4.action_links import ActionLink  # noqa: E402, F401
from models.v4.evidences import Evidence  # noqa: E402, F401


@pytest.fixture(scope="module", autouse=True)
def _ensure_seeded():
    """Override le parent conftest._ensure_seeded — tests API standalone."""
    return  # no-op


# ─────────────────────────────────────────────────────────────────────
# Sprint M2-3.B — JWT fixtures pour tests RBAC wrapper
# ─────────────────────────────────────────────────────────────────────
# Émet des JWT signés avec des rôles legacy PROMEOS (dg_owner, energy_manager,
# auditeur). Le mapping V4 (rbac._LEGACY_TO_V4_ROLE) traduit en admin/user/viewer.
# Cela teste la chaîne complète : JWT issuance → decode → mapping → enforcement.


def _make_token(role: str, user_id: int = 1, org_id: int = 1) -> str:
    """Helper : génère un JWT signé avec rôle legacy donné."""
    return create_access_token(user_id=user_id, org_id=org_id, role=role)


@pytest.fixture
def admin_token() -> str:
    """JWT avec role legacy 'dg_owner' → mappé V4 'admin'."""
    return _make_token(role="dg_owner")


@pytest.fixture
def user_token() -> str:
    """JWT avec role legacy 'energy_manager' → mappé V4 'user'."""
    return _make_token(role="energy_manager")


@pytest.fixture
def viewer_token() -> str:
    """JWT avec role legacy 'auditeur' → mappé V4 'viewer'."""
    return _make_token(role="auditeur")


@pytest.fixture
def unknown_role_token() -> str:
    """JWT avec role legacy non mappé → fallback V4 'viewer' + warning log."""
    return _make_token(role="unknown_role_xyz")


# ─────────────────────────────────────────────────────────────────────
# M2-4.2 — JWT scopés par org (tests d'isolation cross-org endpoints V4)
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def user_token_org_1() -> str:
    """JWT energy_manager (→ V4 user) scopé org 1."""
    return _make_token(role="energy_manager", org_id=1)


@pytest.fixture
def user_token_org_2() -> str:
    """JWT energy_manager (→ V4 user) scopé org 2 — isolation cross-org."""
    return _make_token(role="energy_manager", org_id=2)


# ─────────────────────────────────────────────────────────────────────
# M2-4.3 — client + fixtures de seed pour les endpoints sous-ressources
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def client(app_client):
    """TestClient déballé du tuple (client, SessionLocal) de `app_client`."""
    return app_client[0]


@pytest.fixture
def seeded_item(app_client) -> str:
    """1 ActionCenterItem (org 1) sans sous-ressource. Retourne son id (str)."""
    from uuid import uuid4

    _, session_local = app_client
    item_id = uuid4()
    db = session_local()
    try:
        db.add(
            ActionCenterItem(
                id=item_id,
                organisation_id=1,
                kind="anomaly",
                title="Parent item M2-4.3",
                priority_bracket="P2",
                priority_score=50.0,
            )
        )
        db.commit()
    finally:
        db.close()
    return str(item_id)


@pytest.fixture
def seeded_item_with_subs(app_client) -> str:
    """ActionCenterItem (org 1) + 3 events + 3 evidences + 2 blockers + 2 links.

    Timestamps espacés d'1 min → tests de tri DESC déterministes (anti-flaky).
    Retourne l'id de l'item parent (str).
    """
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    _, session_local = app_client
    item_id = uuid4()
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    db = session_local()
    try:
        db.add(
            ActionCenterItem(
                id=item_id,
                organisation_id=1,
                kind="anomaly",
                title="Parent avec sous-ressources",
                priority_bracket="P2",
                priority_score=50.0,
            )
        )
        for i, event_type in enumerate(("created", "state_changed", "owner_changed")):
            db.add(
                ActionEventLog(
                    id=uuid4(),
                    organisation_id=1,
                    action_item_id=item_id,
                    event_type=event_type,
                    occurred_at=base + timedelta(minutes=i),
                    actor_type="system",
                    actor_id=None,
                    event_payload={"schema_version": "v1"},
                    correlation_id=uuid4(),
                )
            )
        for i in range(3):
            db.add(
                Evidence(
                    id=uuid4(),
                    organisation_id=1,
                    action_item_id=item_id,
                    mime_type="application/pdf",
                    file_size_bytes=1024 + i,
                    storage_uri=f"fs://test/ev{i}.pdf",
                    original_filename=f"ev{i}.pdf",
                    uploaded_at=base + timedelta(minutes=i),
                    uploaded_by=uuid4(),
                )
            )
        for i, blocker_type in enumerate(("waiting_evidence", "waiting_budget")):
            db.add(
                ActionBlocker(
                    id=uuid4(),
                    organisation_id=1,
                    item_id=item_id,
                    blocker_type=blocker_type,
                    added_at=base + timedelta(minutes=i),
                )
            )
        for i, (link_type, target_module, relation) in enumerate(
            (
                ("anomaly_caused_by_invoice", "billing", "caused_by"),
                ("action_references_site", "patrimoine", "references"),
            )
        ):
            db.add(
                ActionLink(
                    id=uuid4(),
                    organisation_id=1,
                    item_id=item_id,
                    link_type=link_type,
                    target_module=target_module,
                    target_id=uuid4(),
                    relation=relation,
                    created_at=base + timedelta(minutes=i),
                )
            )
        db.commit()
    finally:
        db.close()
    return str(item_id)
