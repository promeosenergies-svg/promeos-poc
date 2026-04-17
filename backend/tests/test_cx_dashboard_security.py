"""
Sprint CX 2.5 hardening S2 — Tests sécurité /api/admin/cx-dashboard/*

Vérifie que les 4 endpoints admin CX refusent l'accès non-authentifié ou
non-admin, MÊME en DEMO_MODE. `require_platform_admin` ne doit jamais
bypasser la vérification.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from models import Base
from database import get_db


ADMIN_ENDPOINTS = [
    "/api/admin/cx-dashboard",
    "/api/admin/cx-dashboard/t2v",
    "/api/admin/cx-dashboard/iar",
    "/api/admin/cx-dashboard/wau-mau",
]


@pytest.fixture
def client_no_auth_override():
    """Client sans override auth — teste le vrai require_platform_admin."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    # Pas d'override de require_platform_admin → teste la vraie sécurité
    yield TestClient(app)
    app.dependency_overrides.clear()
    session.close()


class TestS2NoTokenRejected:
    """S2 : sans token, retour 401 même en DEMO_MODE."""

    @pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
    def test_endpoint_without_token_returns_401(self, client_no_auth_override, endpoint):
        r = client_no_auth_override.get(endpoint)
        assert r.status_code == 401
        body = r.json()
        msg = body.get("message") or body.get("detail", "")
        assert "Authentification requise" in msg


class TestS2InvalidTokenRejected:
    """S2 : token invalide → 401."""

    @pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
    def test_endpoint_with_invalid_token_returns_401(self, client_no_auth_override, endpoint):
        r = client_no_auth_override.get(
            endpoint, headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert r.status_code == 401


class TestS2ValidNonAdminRoleRejected:
    """S2 : token valide mais rôle non-admin (ex: ENERGY_MANAGER) → 403."""

    @pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
    def test_endpoint_with_non_admin_role_returns_403(self, client_no_auth_override, endpoint):
        # Créer un token valide pour un rôle non-admin
        from services.iam_service import create_access_token

        token = create_access_token(user_id=1, org_id=1, role="energy_manager")
        r = client_no_auth_override.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403
        body = r.json()
        msg = (body.get("message") or body.get("detail", "")).lower()
        assert "administration plateforme" in msg or "admin" in msg


class TestS2DgOwnerAccepted:
    """S2 : DG_OWNER → 200."""

    @pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
    def test_endpoint_with_dg_owner_returns_200(self, client_no_auth_override, endpoint):
        from services.iam_service import create_access_token

        token = create_access_token(user_id=1, org_id=1, role="dg_owner")
        r = client_no_auth_override.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200


class TestS2DsiAdminAccepted:
    """S2 : DSI_ADMIN → 200."""

    @pytest.mark.parametrize("endpoint", ADMIN_ENDPOINTS)
    def test_endpoint_with_dsi_admin_returns_200(self, client_no_auth_override, endpoint):
        from services.iam_service import create_access_token

        token = create_access_token(user_id=1, org_id=1, role="dsi_admin")
        r = client_no_auth_override.get(endpoint, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
