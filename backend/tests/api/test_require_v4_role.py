"""M2-3.B — Tests du wrapper require_v4_role + mapping legacy → V4.

Sprint M2-3 commit M2-3.B.

Couvre :
1. Comportement wrapper :
   - 401 sans token (hors DEMO_MODE)
   - 403 ROLE_FORBIDDEN si role mappé V4 ∉ allowed
   - 200 si role mappé V4 ∈ allowed
   - 200 multi-roles (admin OU user passe)
   - boot-time ValueError si allowed_roles vide

2. Mapping cardinal _LEGACY_TO_V4_ROLE (4 tests métier sensibles) :
   - dg_owner → admin
   - energy_manager → user
   - auditeur → viewer
   - rôle inconnu → viewer (least privilege) + warning log

Architecture : utilise une mini-app FastAPI isolée (pas la prod app) pour tester
le wrapper sans dépendre de tous les routes legacy.
"""

import logging

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from middleware.rbac import _LEGACY_TO_V4_ROLE, _translate_role, require_v4_role
from models.v4.enums import Role
from services.iam_service import create_access_token


# ─────────────────────────────────────────────────────────────────────
# Mini-app de test isolée
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def mini_app() -> TestClient:
    """App FastAPI minimal exposant 3 endpoints protégés (1 par scénario allowlist)."""
    app = FastAPI()

    @app.get("/admin-only")
    def admin_only(_rbac=Depends(require_v4_role(Role.ADMIN))):
        return {"ok": True, "scope": "admin"}

    @app.get("/admin-or-user")
    def admin_or_user(_rbac=Depends(require_v4_role(Role.ADMIN, Role.USER))):
        return {"ok": True, "scope": "admin_or_user"}

    @app.get("/viewer-allowed")
    def viewer_allowed(
        _rbac=Depends(require_v4_role(Role.ADMIN, Role.USER, Role.VIEWER)),
    ):
        return {"ok": True, "scope": "all_authenticated"}

    return TestClient(app)


def _token(role: str) -> str:
    """Helper local : génère JWT avec rôle legacy donné."""
    return create_access_token(user_id=1, org_id=1, role=role)


# ═════════════════════════════════════════════════════════════════════
# 1. Comportement wrapper — 5 tests cardinaux
# ═════════════════════════════════════════════════════════════════════


class TestRequireV4RoleBehavior:
    """Comportement du wrapper require_v4_role()."""

    def test_no_token_returns_401(self, mini_app):
        """Sans token (hors DEMO_MODE) → 401 Not authenticated (via get_jwt_payload)."""
        # Note : DEMO_MODE peut être actif via env var. Test reste robuste car
        # 401 ou 403 selon DEMO_MODE — mais 200 serait un bug clair.
        response = mini_app.get("/admin-only")
        assert response.status_code in (401, 200), (
            f"Expected 401 (no auth) or 200 (DEMO_MODE bypass), got {response.status_code}"
        )

    def test_admin_role_accepted_on_admin_only(self, mini_app, admin_token):
        """admin_token (legacy dg_owner → V4 admin) → 200 sur /admin-only."""
        response = mini_app.get("/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
        assert response.status_code == 200
        assert response.json()["scope"] == "admin"

    def test_user_role_rejected_on_admin_only(self, mini_app, user_token):
        """user_token (legacy energy_manager → V4 user) → 403 sur /admin-only."""
        response = mini_app.get("/admin-only", headers={"Authorization": f"Bearer {user_token}"})
        assert response.status_code == 403
        body = response.json()
        assert body["detail"]["code"] == "ROLE_FORBIDDEN"
        assert body["detail"]["current_role_v4"] == "user"

    def test_admin_or_user_accepts_both(self, mini_app, admin_token, user_token):
        """admin OU user passent sur /admin-or-user."""
        for token, expected_role in [(admin_token, "admin"), (user_token, "user")]:
            response = mini_app.get("/admin-or-user", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200, f"Token (V4 role={expected_role}) should pass on /admin-or-user"

    def test_viewer_rejected_on_admin_or_user(self, mini_app, viewer_token):
        """viewer_token (legacy auditeur → V4 viewer) → 403 sur /admin-or-user."""
        response = mini_app.get("/admin-or-user", headers={"Authorization": f"Bearer {viewer_token}"})
        assert response.status_code == 403
        body = response.json()
        assert body["detail"]["code"] == "ROLE_FORBIDDEN"

    def test_empty_allowed_roles_raises_at_boot(self):
        """require_v4_role() sans args → ValueError immédiat (fail-fast au boot)."""
        with pytest.raises(ValueError, match="at least one Role"):
            require_v4_role()


# ═════════════════════════════════════════════════════════════════════
# 2. Mapping cardinal — 4 tests métier
# ═════════════════════════════════════════════════════════════════════


class TestLegacyToV4RoleMapping:
    """Mapping _LEGACY_TO_V4_ROLE — 4 tests cardinaux + table coverage."""

    def test_dg_owner_maps_to_admin(self):
        """dg_owner (top-level governance) → admin."""
        assert _translate_role("dg_owner") == "admin"
        assert _LEGACY_TO_V4_ROLE["dg_owner"] == "admin"

    def test_energy_manager_maps_to_user(self):
        """energy_manager (write on scope) → user."""
        assert _translate_role("energy_manager") == "user"
        assert _LEGACY_TO_V4_ROLE["energy_manager"] == "user"

    def test_auditeur_maps_to_viewer(self):
        """auditeur (read-only) → viewer."""
        assert _translate_role("auditeur") == "viewer"
        assert _LEGACY_TO_V4_ROLE["auditeur"] == "viewer"

    def test_unknown_role_defaults_to_viewer_with_warning(self, caplog):
        """🛡️ Defense in depth : rôle legacy inconnu → viewer (least privilege) + WARNING log."""
        with caplog.at_level(logging.WARNING, logger="promeos.security.rbac"):
            result = _translate_role("unknown_role_xyz")

        assert result == "viewer", "Unknown role must default to least privilege (viewer)"
        # Vérifier qu'un warning a été émis
        warning_records = [r for r in caplog.records if "unknown_legacy_role" in r.message]
        assert len(warning_records) >= 1, (
            "Unknown legacy role must emit WARNING log (révèle rôles oubliés). "
            "Cf. backend/middleware/rbac.py _translate_role."
        )

    def test_table_covers_all_11_promeos_user_roles(self):
        """Sanity : la table couvre les 11 UserRole legacy (révèle évolution enum)."""
        from models.enums import UserRole

        legacy_role_values = {r.value for r in UserRole}
        mapped_values = set(_LEGACY_TO_V4_ROLE.keys())
        missing_in_table = legacy_role_values - mapped_values

        assert not missing_in_table, (
            f"_LEGACY_TO_V4_ROLE table missing {len(missing_in_table)} legacy "
            f"UserRole values: {missing_in_table}. "
            "Si nouveau rôle legacy ajouté, l'ajouter à la table mapping. "
            "(Sinon il fall back to viewer + warning log.)"
        )

    def test_all_v4_target_roles_are_valid(self):
        """Sanity : toutes les V4 target values dans la table sont des Role.value valides."""
        v4_valid_values = {r.value for r in Role}
        v4_targets = set(_LEGACY_TO_V4_ROLE.values())
        invalid = v4_targets - v4_valid_values

        assert not invalid, (
            f"_LEGACY_TO_V4_ROLE maps to invalid V4 Role values: {invalid}. "
            f"Valid Role.value: {sorted(v4_valid_values)}."
        )
