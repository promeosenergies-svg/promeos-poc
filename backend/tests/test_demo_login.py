"""M2-5.8.A / .bis — Tests de la connexion démo (`/api/auth/demo-login`).

Couvre : probe `available` (200 + flag), garde DEMO_MODE (404 invisible en
prod), format de réponse aligné sur `/api/auth/login` legacy, accès aux
endpoints V4 via le token (résolution du P0-1), idempotence, message explicite
si le compte n'est pas seedé, et le garde-fou « le compte démo n'est jamais
authentifiable par mot de passe ».

Tests d'intégration : `TestClient(app)` + `SessionLocal` réelle. `DEMO_MODE`
est une constante figée à l'import dans `middleware.auth` — pilotée ici par
`monkeypatch.setattr` sur l'attribut de module.
"""

import pytest
from fastapi.testclient import TestClient

from database import SessionLocal
from main import app
from models.iam import User
from seeds.use_case_a_seed import (
    HELIOS_DEMO_USER_EMAIL,
    seed_helios_demo_user,
    seed_use_case_a_actions,
)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def demo_mode_on(monkeypatch):
    """Active DEMO_MODE en patchant la constante de module (figée à l'import)."""
    monkeypatch.setattr("middleware.auth.DEMO_MODE", True)


@pytest.fixture
def demo_mode_off(monkeypatch):
    """Désactive DEMO_MODE (simule la production)."""
    monkeypatch.setattr("middleware.auth.DEMO_MODE", False)


@pytest.fixture
def seeded_demo():
    """Garantit le compte démo Marie Dupont + les 6 actions HELIOS (idempotent)."""
    db = SessionLocal()
    try:
        seed_use_case_a_actions(db)
    finally:
        db.close()


# ── Probe GET /api/auth/demo-login/available ──────────────────────────


def test_probe_available_true_when_demo_mode_on(client, demo_mode_on, seeded_demo):
    """Probe : {available: true} si DEMO_MODE actif ET compte démo seedé."""
    response = client.get("/api/auth/demo-login/available")
    assert response.status_code == 200
    assert response.json() == {"available": True}


def test_probe_available_false_when_demo_mode_off(client, demo_mode_off):
    """Probe : 200 + {available: false} quand DEMO_MODE est inactif (jamais 404)."""
    response = client.get("/api/auth/demo-login/available")
    assert response.status_code == 200
    assert response.json() == {"available": False}


def test_probe_available_false_when_user_not_seeded(client, demo_mode_on):
    """M2-5.9.bis — {available: false} si DEMO_MODE actif mais compte démo absent.

    La probe garantit la jouabilité réelle : le bouton de login démo ne doit
    s'afficher que si un clic aboutira (sinon il masquait un futur 500).
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == HELIOS_DEMO_USER_EMAIL).first()
        if user is not None:
            db.delete(user)
            db.commit()

        response = client.get("/api/auth/demo-login/available")
        assert response.status_code == 200
        assert response.json() == {"available": False}
    finally:
        seed_helios_demo_user(db)  # restaure le compte — leave-no-trace
        db.close()


# ── POST /api/auth/demo-login ─────────────────────────────────────────


def test_returns_404_when_demo_mode_disabled(client, demo_mode_off):
    """DEMO_MODE inactif → endpoint invisible (404, surtout pas 401/403)."""
    response = client.post("/api/auth/demo-login")
    assert response.status_code == 404


def test_returns_aligned_legacy_format_when_enabled(client, demo_mode_on, seeded_demo):
    """Réponse strictement alignée sur le schéma `/api/auth/login` legacy (Q3=A)."""
    response = client.post("/api/auth/demo-login")
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == HELIOS_DEMO_USER_EMAIL
    assert isinstance(data["user"]["id"], int)
    assert data["org"]["id"] == 1
    assert data["role"] == "energy_manager"
    # Clés legacy présentes (session complète, pas un payload tronqué).
    for key in ("orgs", "scopes", "permissions"):
        assert key in data


def test_jwt_allows_access_to_v4_items(client, demo_mode_on, seeded_demo):
    """Le JWT demo-login débloque les endpoints V4 — résolution directe du P0-1."""
    token = client.post("/api/auth/demo-login").json()["access_token"]
    response = client.get(
        "/api/v4/action-center/items",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 6  # les 6 actions HELIOS du seed Use Case A


def test_idempotent_returns_same_user(client, demo_mode_on, seeded_demo):
    """Body vide, appels répétés → même compte (tokens distincts tolérés)."""
    first = client.post("/api/auth/demo-login").json()
    second = client.post("/api/auth/demo-login").json()
    assert first["user"]["email"] == second["user"]["email"]
    assert first["org"]["id"] == second["org"]["id"]


def test_returns_500_with_hint_when_user_not_seeded(client, demo_mode_on):
    """Compte démo absent → 500 + code/hint explicites (puis restauration)."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == HELIOS_DEMO_USER_EMAIL).first()
        if user is not None:
            db.delete(user)  # cascade ORM → supprime aussi le UserOrgRole
            db.commit()

        response = client.post("/api/auth/demo-login")
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail["code"] == "DEMO_USER_NOT_SEEDED"
        assert "seed" in detail["hint"].lower()
    finally:
        seed_helios_demo_user(db)  # restaure le compte — leave-no-trace
        db.close()


def test_demo_user_cannot_login_with_password(client, seeded_demo):
    """🛡️ Le compte démo n'est JAMAIS authentifiable par mot de passe.

    Son `hashed_password` est un secret aléatoire jamais connu : `/api/auth/
    login` (email + password) ne peut pas le matcher. Seul `demo-login` y
    donne accès — défense en profondeur contre un login deviné.
    """
    response = client.post(
        "/api/auth/login",
        json={"email": HELIOS_DEMO_USER_EMAIL, "password": "demo"},
    )
    assert response.status_code == 401


def test_demo_login_rate_limited_after_quota(client, demo_mode_on, seeded_demo, monkeypatch):
    """🛡️ M2-5.9.bis — 6ᵉ appel en < 60 s → 429 (anti token-harvesting, CWE-307).

    `check_rate_limit` est neutralisé sous pytest (variable d'env
    `PYTEST_CURRENT_TEST`) ; on la retire le temps du test pour exercer la garde.
    """
    import middleware.rate_limit as rl

    rl._buckets.clear()
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    try:
        for _ in range(5):
            assert client.post("/api/auth/demo-login").status_code == 200
        assert client.post("/api/auth/demo-login").status_code == 429
    finally:
        rl._buckets.clear()
