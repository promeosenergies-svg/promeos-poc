"""
PROMEOS - Tests Sprint 11: IAM ULTIMATE (Users / Roles / Scopes)
~32 tests covering: user CRUD, login, JWT, role permissions, scope hierarchy,
scope filtering, last-owner protection, prestataire expiry, switch org, admin endpoints.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    User, UserOrgRole, UserScope, AuditLog,
    UserRole, ScopeLevel, TypeSite,
)
from database import get_db
from main import app
from services.iam_service import (
    hash_password, verify_password,
    create_access_token, decode_token,
    check_permission, get_permissions_for_role,
    get_scoped_site_ids, get_accessible_entity_ids,
    can, log_audit,
    create_user, assign_role, assign_scope, remove_role, soft_delete_user,
)


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def db_session():
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
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _create_org_hierarchy(db_session):
    """Create org + 2 entites + 2 portefeuilles + 4 sites."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()

    ej1 = EntiteJuridique(organisation_id=org.id, nom="Entite IDF", siren="111111111")
    ej2 = EntiteJuridique(organisation_id=org.id, nom="Entite Sud", siren="222222222")
    db_session.add_all([ej1, ej2])
    db_session.flush()

    pf1 = Portefeuille(entite_juridique_id=ej1.id, nom="PF IDF")
    pf2 = Portefeuille(entite_juridique_id=ej2.id, nom="PF Sud")
    db_session.add_all([pf1, pf2])
    db_session.flush()

    sites = []
    for i, (pf, name) in enumerate([
        (pf1, "Site IDF-A"), (pf1, "Site IDF-B"),
        (pf2, "Site Sud-A"), (pf2, "Site Sud-B"),
    ]):
        site = Site(
            portefeuille_id=pf.id, nom=name,
            type=TypeSite.BUREAU, surface_m2=1000, actif=True,
        )
        db_session.add(site)
        sites.append(site)

    db_session.flush()
    return org, ej1, ej2, pf1, pf2, sites


def _create_user_with_role(db_session, org, email, role, scope_level, scope_id, expires_at=None):
    """Helper: create user + role + scope."""
    user = create_user(db_session, email=email, password="test123", nom="Test", prenom="User")
    uor = assign_role(db_session, user.id, org.id, role)
    assign_scope(db_session, uor.id, scope_level, scope_id, expires_at=expires_at)
    db_session.flush()
    return user, uor


def _login(client, email, password="test123"):
    """Helper: login and return response data."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    return res


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ========================================
# TestUserCRUD
# ========================================

class TestUserCRUD:
    def test_create_user(self, db_session):
        user = create_user(db_session, "alice@test.com", "secret", "Alice", "Dupont")
        db_session.commit()
        assert user.id is not None
        assert user.email == "alice@test.com"
        assert user.actif is True
        assert verify_password("secret", user.hashed_password)

    def test_soft_delete(self, db_session):
        user = create_user(db_session, "bob@test.com", "secret", "Bob", "Martin")
        db_session.commit()
        result = soft_delete_user(db_session, user.id)
        db_session.commit()
        assert result is True
        refreshed = db_session.query(User).filter(User.id == user.id).first()
        assert refreshed.actif is False

    def test_duplicate_email_rejected(self, db_session):
        create_user(db_session, "dup@test.com", "secret", "A", "B")
        db_session.commit()
        with pytest.raises(Exception):
            create_user(db_session, "dup@test.com", "secret2", "C", "D")
            db_session.commit()


# ========================================
# TestLogin
# ========================================

class TestLogin:
    def test_login_ok(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "login@test.com", UserRole.ENERGY_MANAGER, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "login@test.com")
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "login@test.com"
        assert data["role"] == "energy_manager"
        assert "permissions" in data

    def test_wrong_password_401(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "wrong@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "wrong@test.com", "badpassword")
        assert res.status_code == 401

    def test_inactive_user_401(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        user, _ = _create_user_with_role(db_session, org, "inactive@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        user.actif = False
        db_session.commit()

        res = _login(client, "inactive@test.com")
        assert res.status_code == 401

    def test_unknown_email_401(self, client, db_session):
        res = _login(client, "nobody@test.com")
        assert res.status_code == 401


# ========================================
# TestJWT
# ========================================

class TestJWT:
    def test_token_valid(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "jwt@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "jwt@test.com")
        token = res.json()["access_token"]

        me = client.get("/api/auth/me", headers=_auth_header(token))
        assert me.status_code == 200
        assert me.json()["user"]["email"] == "jwt@test.com"

    def test_token_expired_401(self, client, db_session):
        token = create_access_token(user_id=999, org_id=1, role="dg_owner",
                                     expires_delta=timedelta(seconds=-10))
        me = client.get("/api/auth/me", headers=_auth_header(token))
        assert me.status_code == 401

    def test_token_tampered_401(self, client, db_session):
        me = client.get("/api/auth/me", headers=_auth_header("tampered.jwt.token"))
        assert me.status_code == 401


# ========================================
# TestRolePermissions
# ========================================

class TestRolePermissions:
    def test_dg_sees_all(self):
        assert check_permission(UserRole.DG_OWNER, "view", "cockpit") is True
        assert check_permission(UserRole.DG_OWNER, "edit", "patrimoine") is True
        assert check_permission(UserRole.DG_OWNER, "admin") is True
        assert check_permission(UserRole.DG_OWNER, "export") is True

    def test_resp_site_limited(self):
        assert check_permission(UserRole.RESP_SITE, "view", "patrimoine") is True
        assert check_permission(UserRole.RESP_SITE, "view", "billing") is False
        assert check_permission(UserRole.RESP_SITE, "admin") is False

    def test_auditeur_readonly(self):
        assert check_permission(UserRole.AUDITEUR, "view", "cockpit") is True
        assert check_permission(UserRole.AUDITEUR, "edit", "cockpit") is False
        assert check_permission(UserRole.AUDITEUR, "export") is True
        assert check_permission(UserRole.AUDITEUR, "admin") is False

    def test_prestataire_no_edit(self):
        assert check_permission(UserRole.PRESTATAIRE, "view", "patrimoine") is True
        assert check_permission(UserRole.PRESTATAIRE, "edit", "patrimoine") is False
        assert check_permission(UserRole.PRESTATAIRE, "admin") is False
        assert check_permission(UserRole.PRESTATAIRE, "export") is False


# ========================================
# TestScopeHierarchy
# ========================================

class TestScopeHierarchy:
    def test_org_scope_all_sites(self, db_session):
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "org@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        site_ids = get_scoped_site_ids(db_session, uor)
        assert len(site_ids) == 4

    def test_entite_scope_entite_sites(self, db_session):
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "entite@test.com", UserRole.RESP_IMMOBILIER, ScopeLevel.ENTITE, ej1.id)
        db_session.commit()

        site_ids = get_scoped_site_ids(db_session, uor)
        assert len(site_ids) == 2
        # Should only have IDF sites
        assert sites[0].id in site_ids
        assert sites[1].id in site_ids
        assert sites[2].id not in site_ids

    def test_site_scope_one_site(self, db_session):
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "site@test.com", UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id)
        db_session.commit()

        site_ids = get_scoped_site_ids(db_session, uor)
        assert site_ids == [sites[0].id]

    def test_no_scope_no_access(self, db_session):
        org, *_ = _create_org_hierarchy(db_session)
        user = create_user(db_session, "noscope@test.com", "test123", "No", "Scope")
        uor = assign_role(db_session, user.id, org.id, UserRole.AUDITEUR)
        # No scope assigned → deny-by-default
        db_session.commit()

        site_ids = get_scoped_site_ids(db_session, uor)
        assert site_ids == []


# ========================================
# TestScopeFiltering (API level)
# ========================================

class TestScopeFiltering:
    def test_sites_filtered_by_scope(self, client, db_session):
        """User with SITE scope should only see that site via GET /api/sites."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(
            db_session, org, "filter@test.com",
            UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id,
        )
        db_session.commit()

        res = _login(client, "filter@test.com")
        token = res.json()["access_token"]

        sites_res = client.get("/api/sites", headers=_auth_header(token))
        assert sites_res.status_code == 200
        data = sites_res.json()
        assert data["total"] == 1
        assert data["sites"][0]["id"] == sites[0].id

    def test_sites_unfiltered_without_auth(self, client, db_session):
        """Without auth (demo mode), all sites should be visible."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        db_session.commit()

        sites_res = client.get("/api/sites")
        assert sites_res.status_code == 200
        assert sites_res.json()["total"] == 4

    def test_dashboard_filtered_by_org(self, client, db_session):
        """User with ORG scope should get dashboard for their org."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(
            db_session, org, "dash@test.com",
            UserRole.DG_OWNER, ScopeLevel.ORG, org.id,
        )
        db_session.commit()

        res = _login(client, "dash@test.com")
        token = res.json()["access_token"]

        # Dashboard endpoint — should work with auth
        dash_res = client.get("/api/dashboard/2min", headers=_auth_header(token))
        assert dash_res.status_code == 200


# ========================================
# TestLastOwnerProtection
# ========================================

class TestLastOwnerProtection:
    def test_cannot_remove_last_dg(self, db_session):
        org, *_ = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "lastdg@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        result = remove_role(db_session, user.id, org.id)
        assert result is False  # Protected

    def test_can_remove_if_two_dgs(self, db_session):
        org, *_ = _create_org_hierarchy(db_session)
        user1, _ = _create_user_with_role(db_session, org, "dg1@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        user2, _ = _create_user_with_role(db_session, org, "dg2@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        result = remove_role(db_session, user1.id, org.id)
        assert result is True


# ========================================
# TestPrestataire
# ========================================

class TestPrestataire:
    def test_access_before_expiry(self, db_session):
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        expires = datetime.now(timezone.utc) + timedelta(days=30)
        user, uor = _create_user_with_role(
            db_session, org, "presta@test.com",
            UserRole.PRESTATAIRE, ScopeLevel.SITE, sites[0].id, expires_at=expires,
        )
        db_session.commit()

        site_ids = get_scoped_site_ids(db_session, uor)
        assert sites[0].id in site_ids

    def test_access_denied_after_expiry(self, db_session):
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        user, uor = _create_user_with_role(
            db_session, org, "expired@test.com",
            UserRole.PRESTATAIRE, ScopeLevel.SITE, sites[0].id, expires_at=expired,
        )
        db_session.commit()

        site_ids = get_scoped_site_ids(db_session, uor)
        assert site_ids == []


# ========================================
# TestSwitchOrg
# ========================================

class TestSwitchOrg:
    def test_switch_org_ok(self, client, db_session):
        org1, *_ = _create_org_hierarchy(db_session)
        org2 = Organisation(nom="Other Corp", type_client="retail", actif=True)
        db_session.add(org2)
        db_session.flush()

        user = create_user(db_session, "multi@test.com", "test123", "Multi", "Org")
        uor1 = assign_role(db_session, user.id, org1.id, UserRole.DG_OWNER)
        assign_scope(db_session, uor1.id, ScopeLevel.ORG, org1.id)
        uor2 = assign_role(db_session, user.id, org2.id, UserRole.AUDITEUR)
        assign_scope(db_session, uor2.id, ScopeLevel.ORG, org2.id)
        db_session.commit()

        res = _login(client, "multi@test.com")
        token = res.json()["access_token"]

        switch_res = client.post(
            "/api/auth/switch-org",
            json={"org_id": org2.id},
            headers=_auth_header(token),
        )
        assert switch_res.status_code == 200
        new_data = switch_res.json()
        assert new_data["org"]["id"] == org2.id
        assert new_data["role"] == "auditeur"

    def test_switch_to_unauthorized_org_403(self, client, db_session):
        org1, *_ = _create_org_hierarchy(db_session)
        org2 = Organisation(nom="Forbidden Corp", type_client="retail", actif=True)
        db_session.add(org2)
        db_session.flush()

        user, uor = _create_user_with_role(db_session, org1, "single@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org1.id)
        db_session.commit()

        res = _login(client, "single@test.com")
        token = res.json()["access_token"]

        switch_res = client.post(
            "/api/auth/switch-org",
            json={"org_id": org2.id},
            headers=_auth_header(token),
        )
        assert switch_res.status_code == 403


# ========================================
# TestAdminEndpoints
# ========================================

class TestAdminEndpoints:
    def _admin_login(self, client, db_session):
        """Create admin user and return token."""
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "admin@test.com", UserRole.DSI_ADMIN, ScopeLevel.ORG, org.id)
        db_session.commit()
        res = _login(client, "admin@test.com")
        return res.json()["access_token"], org

    def test_list_users(self, client, db_session):
        token, org = self._admin_login(client, db_session)
        res = client.get("/api/admin/users", headers=_auth_header(token))
        assert res.status_code == 200
        assert isinstance(res.json(), list)
        assert len(res.json()) >= 1

    def test_create_user(self, client, db_session):
        token, org = self._admin_login(client, db_session)
        res = client.post(
            "/api/admin/users",
            json={
                "email": "new@test.com",
                "password": "newpass",
                "nom": "New",
                "prenom": "User",
                "role": "auditeur",
                "scopes": [{"level": "org", "id": org.id}],
            },
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "created"
        assert "user_id" in data

    def test_patch_user(self, client, db_session):
        token, org = self._admin_login(client, db_session)
        # Create a user to patch
        user = create_user(db_session, "patch@test.com", "pass", "Old", "Name")
        assign_role(db_session, user.id, org.id, UserRole.AUDITEUR)
        db_session.commit()

        res = client.patch(
            f"/api/admin/users/{user.id}",
            json={"nom": "NewNom", "prenom": "NewPrenom"},
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        assert res.json()["status"] == "updated"

    def test_change_role(self, client, db_session):
        token, org = self._admin_login(client, db_session)
        user = create_user(db_session, "role@test.com", "pass", "Role", "Change")
        assign_role(db_session, user.id, org.id, UserRole.AUDITEUR)
        db_session.commit()

        res = client.put(
            f"/api/admin/users/{user.id}/role",
            json={"role": "energy_manager"},
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        assert res.json()["role"] == "energy_manager"

    def test_set_scopes(self, client, db_session):
        token, org = self._admin_login(client, db_session)
        user = create_user(db_session, "scope@test.com", "pass", "Scope", "Set")
        uor = assign_role(db_session, user.id, org.id, UserRole.RESP_SITE)
        db_session.commit()

        # Get first site
        sites = db_session.query(Site).all()
        site_id = sites[0].id if sites else 1

        res = client.put(
            f"/api/admin/users/{user.id}/scopes",
            json={"scopes": [{"level": "site", "id": site_id}]},
            headers=_auth_header(token),
        )
        assert res.status_code == 200
        assert res.json()["scopes_count"] == 1


# ========================================
# TestPasswordChange
# ========================================

class TestPasswordChange:
    def test_change_password_ok(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "pwd@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "pwd@test.com")
        token = res.json()["access_token"]

        change = client.put(
            "/api/auth/password",
            json={"current_password": "test123", "new_password": "newpass456"},
            headers=_auth_header(token),
        )
        assert change.status_code == 200

        # Verify new password works
        res2 = _login(client, "pwd@test.com", "newpass456")
        assert res2.status_code == 200

    def test_change_password_wrong_current(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "pwdfail@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "pwdfail@test.com")
        token = res.json()["access_token"]

        change = client.put(
            "/api/auth/password",
            json={"current_password": "wrong", "new_password": "newpass456"},
            headers=_auth_header(token),
        )
        assert change.status_code == 400


# ========================================
# TestPermissionsMatrix
# ========================================

class TestPermissionsMatrix:
    def test_get_permissions_for_role(self):
        perms = get_permissions_for_role(UserRole.DAF)
        assert isinstance(perms["view"], list)
        assert "cockpit" in perms["view"]
        assert "billing" in perms["view"]
        assert perms["export"] is True
        assert perms["admin"] is False

    def test_admin_roles_list(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "roles@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "roles@test.com")
        token = res.json()["access_token"]

        roles_res = client.get("/api/admin/roles", headers=_auth_header(token))
        assert roles_res.status_code == 200
        data = roles_res.json()
        assert len(data) == 11  # 11 roles


# ========================================
# TestRefreshToken
# ========================================

class TestRefreshToken:
    def test_refresh_ok(self, client, db_session):
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "refresh@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "refresh@test.com")
        token = res.json()["access_token"]

        refresh = client.post("/api/auth/refresh", headers=_auth_header(token))
        assert refresh.status_code == 200
        assert "access_token" in refresh.json()


# ========================================
# TestCan — can() authorization engine
# ========================================

class TestCan:
    def test_can_dg_view_org(self, db_session):
        """DG_OWNER with ORG scope can view org-level resource."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "can1@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        result = can(db_session, user.id, "view", scope_type="org", scope_id=org.id)
        assert result["allowed"] is True
        assert result["reason"] == "Authorized"
        assert len(result["matched_assignments"]) >= 1

    def test_can_dg_view_site_through_org(self, db_session):
        """DG_OWNER with ORG scope can view any site in that org (hierarchy)."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "can2@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        result = can(db_session, user.id, "view", scope_type="site", scope_id=sites[0].id)
        assert result["allowed"] is True

    def test_can_resp_site_deny_other_site(self, db_session):
        """RESP_SITE with SITE scope on site[0] cannot view site[2]."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "can3@test.com", UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id)
        db_session.commit()

        result = can(db_session, user.id, "view", scope_type="site", scope_id=sites[2].id)
        assert result["allowed"] is False
        assert "deny" in result["reason"].lower() or "no matching" in result["reason"].lower()

    def test_can_entite_scope_covers_child_sites(self, db_session):
        """RESP_IMMOBILIER with ENTITE scope sees sites in that entite."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "can4@test.com", UserRole.RESP_IMMOBILIER, ScopeLevel.ENTITE, ej1.id)
        db_session.commit()

        # Site in ej1 → allowed
        result = can(db_session, user.id, "view", scope_type="site", scope_id=sites[0].id)
        assert result["allowed"] is True

        # Site in ej2 → denied
        result2 = can(db_session, user.id, "view", scope_type="site", scope_id=sites[2].id)
        assert result2["allowed"] is False

    def test_can_inactive_user_denied(self, db_session):
        """Inactive user is always denied."""
        org, *_ = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "can5@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        user.actif = False
        db_session.commit()

        result = can(db_session, user.id, "view")
        assert result["allowed"] is False
        assert "inactive" in result["reason"].lower()

    def test_can_no_role_denied(self, db_session):
        """User with no role is denied."""
        org, *_ = _create_org_hierarchy(db_session)
        user = create_user(db_session, "can6@test.com", "test123", "No", "Role")
        db_session.commit()

        result = can(db_session, user.id, "view")
        assert result["allowed"] is False
        assert "no role" in result["reason"].lower()

    def test_can_role_level_no_scope_required(self, db_session):
        """can() without scope_type checks role permission only."""
        org, *_ = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "can7@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        db_session.commit()

        # Auditeur can view
        result = can(db_session, user.id, "view", module="cockpit")
        assert result["allowed"] is True

        # Auditeur cannot edit
        result2 = can(db_session, user.id, "edit", module="cockpit")
        assert result2["allowed"] is False


# ========================================
# TestGetAccessibleEntityIds
# ========================================

class TestGetAccessibleEntityIds:
    def test_org_scope_all_entities(self, db_session):
        """ORG scope → all entites of the org."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "eid1@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        ids = get_accessible_entity_ids(db_session, uor)
        assert set(ids) == {ej1.id, ej2.id}

    def test_entite_scope_one_entity(self, db_session):
        """ENTITE scope → just that entite."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "eid2@test.com", UserRole.RESP_IMMOBILIER, ScopeLevel.ENTITE, ej1.id)
        db_session.commit()

        ids = get_accessible_entity_ids(db_session, uor)
        assert ids == [ej1.id]

    def test_site_scope_resolves_entity(self, db_session):
        """SITE scope → resolves to parent entite."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(db_session, org, "eid3@test.com", UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id)
        db_session.commit()

        ids = get_accessible_entity_ids(db_session, uor)
        assert ej1.id in ids


# ========================================
# TestAuditLog
# ========================================

class TestAuditLog:
    def test_audit_log_created_on_login(self, client, db_session):
        """Login creates an audit log entry."""
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "audit1@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        db_session.commit()

        _login(client, "audit1@test.com")

        logs = db_session.query(AuditLog).filter(AuditLog.action == "login").all()
        assert len(logs) >= 1

    def test_audit_log_created_on_user_create(self, client, db_session):
        """Creating a user via admin API generates audit log entry."""
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "auditadm@test.com", UserRole.DSI_ADMIN, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "auditadm@test.com")
        token = res.json()["access_token"]

        client.post(
            "/api/admin/users",
            json={
                "email": "newaudit@test.com", "password": "pass",
                "nom": "Audit", "prenom": "Test", "role": "auditeur",
            },
            headers=_auth_header(token),
        )

        logs = db_session.query(AuditLog).filter(AuditLog.action == "create_user").all()
        assert len(logs) >= 1

    def test_log_audit_function(self, db_session):
        """log_audit() creates an entry in the database."""
        log_audit(db_session, user_id=None, action="test_action", resource_type="test", resource_id="42", detail={"key": "val"})
        db_session.commit()

        entry = db_session.query(AuditLog).filter(AuditLog.action == "test_action").first()
        assert entry is not None
        assert entry.resource_id == "42"
        assert '"key"' in entry.detail_json

    def test_audit_api_list(self, client, db_session):
        """GET /api/auth/audit returns entries (admin only)."""
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "auditapi@test.com", UserRole.DG_OWNER, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "auditapi@test.com")
        token = res.json()["access_token"]

        # Create some audit entries
        log_audit(db_session, user_id=None, action="test_api", resource_type="test")
        db_session.commit()

        audit_res = client.get("/api/auth/audit", headers=_auth_header(token))
        assert audit_res.status_code == 200
        data = audit_res.json()
        assert "total" in data
        assert "entries" in data
        assert data["total"] >= 1


# ========================================
# TestScopeFiltering403
# ========================================

class TestScopeFiltering403:
    def test_prestataire_no_edit_403(self, client, db_session):
        """Prestataire cannot edit — role check blocks edit permission."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(
            db_session, org, "presta403@test.com",
            UserRole.PRESTATAIRE, ScopeLevel.SITE, sites[0].id,
        )
        db_session.commit()

        result = can(db_session, user.id, "edit", scope_type="site", scope_id=sites[0].id)
        assert result["allowed"] is False

    def test_resp_site_sees_only_assigned_sites_via_api(self, client, db_session):
        """Resp_site logged in should only see their assigned site via /api/sites."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(
            db_session, org, "scope403@test.com",
            UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id,
        )
        db_session.commit()

        res = _login(client, "scope403@test.com")
        token = res.json()["access_token"]

        sites_res = client.get("/api/sites", headers=_auth_header(token))
        assert sites_res.status_code == 200
        data = sites_res.json()
        assert data["total"] == 1
        assert data["sites"][0]["id"] == sites[0].id

    def test_admin_endpoint_403_for_non_admin(self, client, db_session):
        """Non-admin role gets 403 on admin endpoints."""
        org, *_, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "nonadm@test.com", UserRole.AUDITEUR, ScopeLevel.ORG, org.id)
        db_session.commit()

        res = _login(client, "nonadm@test.com")
        token = res.json()["access_token"]

        users_res = client.get("/api/admin/users", headers=_auth_header(token))
        assert users_res.status_code == 403


# ========================================
# TestAntiLeak — scope hardening Sprint 12
# ========================================

class TestAntiLeak:
    """Verify detail/export endpoints respect scope filtering (Sprint 12)."""

    def test_site_detail_403_out_of_scope(self, client, db_session):
        """GET /api/sites/{id} returns 403 for a site not in user's scope."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        # User with SITE scope on site[0]
        user, uor = _create_user_with_role(
            db_session, org, "leak1@test.com",
            UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id,
        )
        db_session.commit()

        res = _login(client, "leak1@test.com")
        token = res.json()["access_token"]

        # Own site → 200
        own = client.get(f"/api/sites/{sites[0].id}", headers=_auth_header(token))
        assert own.status_code == 200

        # Other site → 403
        other = client.get(f"/api/sites/{sites[2].id}", headers=_auth_header(token))
        assert other.status_code == 403

    def test_site_stats_403_out_of_scope(self, client, db_session):
        """GET /api/sites/{id}/stats returns 403 for out-of-scope site."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(
            db_session, org, "leak2@test.com",
            UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id,
        )
        db_session.commit()

        res = _login(client, "leak2@test.com")
        token = res.json()["access_token"]

        stats = client.get(f"/api/sites/{sites[2].id}/stats", headers=_auth_header(token))
        assert stats.status_code == 403

    def test_actions_export_scoped(self, client, db_session):
        """GET /api/actions/export.csv should only include scoped actions."""
        from models import ActionItem, ActionStatus, ActionSourceType
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(
            db_session, org, "leak3@test.com",
            UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id,
        )
        # Create actions on different sites
        for i, site in enumerate(sites):
            a = ActionItem(
                org_id=org.id, site_id=site.id,
                source_type=ActionSourceType.COMPLIANCE,
                source_id=f"test-{i}", source_key=f"leak-{i}",
                title=f"Action-{site.nom}",
                status=ActionStatus.OPEN, priority=3,
            )
            db_session.add(a)
        db_session.commit()

        res = _login(client, "leak3@test.com")
        token = res.json()["access_token"]

        export = client.get("/api/actions/export.csv", headers=_auth_header(token))
        assert export.status_code == 200
        content = export.text
        # Should only contain action for site[0], not site[2]
        assert sites[0].nom in content
        assert sites[2].nom not in content

    def test_notifications_scoped(self, client, db_session):
        """GET /api/notifications/list should filter by user's site scope."""
        from models import (
            NotificationEvent, NotificationSeverity,
            NotificationStatus, NotificationSourceType,
        )
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        user, uor = _create_user_with_role(
            db_session, org, "leak4@test.com",
            UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id,
        )
        # Create notifications on different sites
        for site in sites:
            n = NotificationEvent(
                org_id=org.id, site_id=site.id,
                source_type=NotificationSourceType.COMPLIANCE,
                severity=NotificationSeverity.WARN,
                status=NotificationStatus.NEW,
                title=f"Notif-{site.nom}",
                message=f"Test for {site.nom}",
            )
            db_session.add(n)
        db_session.commit()

        res = _login(client, "leak4@test.com")
        token = res.json()["access_token"]

        notifs = client.get("/api/notifications/list", headers=_auth_header(token))
        assert notifs.status_code == 200
        data = notifs.json()
        # Should only contain notifications for site[0]
        titles = [n["title"] for n in data]
        assert any(sites[0].nom in t for t in titles)
        assert not any(sites[2].nom in t for t in titles)

    def test_demo_mode_no_auth_sees_all_sites(self, client, db_session):
        """Without auth (demo mode), all sites should be visible."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        db_session.commit()

        sites_res = client.get("/api/sites")
        assert sites_res.status_code == 200
        assert sites_res.json()["total"] == 4

    def test_effective_access_endpoint(self, client, db_session):
        """GET /api/admin/users/{id}/effective-access returns resolved sites."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        # Admin user
        admin_user, _ = _create_user_with_role(
            db_session, org, "effadm@test.com",
            UserRole.DSI_ADMIN, ScopeLevel.ORG, org.id,
        )
        # Target user with SITE scope
        target_user, _ = _create_user_with_role(
            db_session, org, "efftarget@test.com",
            UserRole.RESP_SITE, ScopeLevel.SITE, sites[0].id,
        )
        db_session.commit()

        res = _login(client, "effadm@test.com")
        token = res.json()["access_token"]

        eff = client.get(f"/api/admin/users/{target_user.id}/effective-access", headers=_auth_header(token))
        assert eff.status_code == 200
        data = eff.json()
        assert data["total_sites"] == 1
        assert data["sites"][0]["id"] == sites[0].id
        assert data["role"] == "resp_site"

    def test_audit_on_scope_change(self, client, db_session):
        """Changing scopes via admin API creates an audit log entry."""
        org, ej1, ej2, pf1, pf2, sites = _create_org_hierarchy(db_session)
        _create_user_with_role(db_session, org, "audsc@test.com", UserRole.DSI_ADMIN, ScopeLevel.ORG, org.id)
        target = create_user(db_session, "sctarget@test.com", "pass", "Sc", "Target")
        assign_role(db_session, target.id, org.id, UserRole.RESP_SITE)
        db_session.commit()

        res = _login(client, "audsc@test.com")
        token = res.json()["access_token"]

        client.put(
            f"/api/admin/users/{target.id}/scopes",
            json={"scopes": [{"level": "site", "id": sites[0].id}]},
            headers=_auth_header(token),
        )

        logs = db_session.query(AuditLog).filter(AuditLog.action == "set_scopes").all()
        assert len(logs) >= 1
