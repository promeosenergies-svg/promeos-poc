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
