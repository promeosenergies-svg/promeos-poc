"""M2-5.8.A — Tests de `POST /api/auth/demo-login` (connexion démo pilote).

Couvre : garde DEMO_MODE (404 invisible en prod), émission du JWT, accès aux
endpoints V4 via le token (résolution du P0-1), idempotence, message explicite
si le compte n'est pas seedé, et le garde-fou de sécurité « le compte démo
n'est jamais authentifiable par mot de passe ».

Tests d'intégration : `TestClient(app)` + `SessionLocal` réelle (même pattern
que les autres `tests/test_*_api.py`). `DEMO_MODE` est une constante figée à
l'import dans `middleware.auth` — pilotée ici par `monkeypatch.setattr` sur
l'attribut de module (un `setenv` serait sans effet : la valeur est déjà lue).
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


def test_returns_404_when_demo_mode_disabled(client, demo_mode_off):
    """DEMO_MODE inactif → endpoint invisible (404, surtout pas 401/403)."""
    response = client.post("/api/auth/demo-login")
    assert response.status_code == 404


def test_returns_jwt_when_demo_mode_enabled(client, demo_mode_on, seeded_demo):
    """DEMO_MODE actif + compte seedé → 200 + JWT et métadonnées."""
    response = client.post("/api/auth/demo-login")
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["user_email"] == HELIOS_DEMO_USER_EMAIL
    assert data["organisation_id"] == 1
    assert data["expires_in"] == 8 * 3600


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
    assert first["user_email"] == second["user_email"]
    assert first["organisation_id"] == second["organisation_id"]


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
    donne accès — défense en profondeur contre un login deviné (« essayer
    `demo` comme mot de passe »).
    """
    response = client.post(
        "/api/auth/login",
        json={"email": HELIOS_DEMO_USER_EMAIL, "password": "demo"},
    )
    assert response.status_code == 401
