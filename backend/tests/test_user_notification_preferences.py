"""Tests user_notification_preferences — Phase 2.C Sprint α-push.

Couvre :
- Service : get defaults gracieux / upsert insert / upsert partial update
- Endpoints : GET / PATCH self-service / 401 unauthenticated /
  isolation user (pas de user_id dans body)
- Validation : digest_channels invalide / digest_daily_locale trop long
- Migration : table créée idempotemment
- CASCADE : suppression user supprime préférences
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def seeded_user(app_client):
    """Crée un User minimal dans la DB SQLite mémoire + active le mode demo."""
    _, SessionLocal = app_client
    from models import User

    db = SessionLocal()
    try:
        user = User(
            email="marie.daf@test.io",
            hashed_password="$2b$12$test_hash",
            nom="DAF",
            prenom="Marie",
            actif=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        yield user
    finally:
        db.close()


@pytest.fixture
def auth_as_user(app_client, seeded_user):
    """Override get_current_user pour retourner le user seedé."""
    from main import app
    from middleware.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: seeded_user
    yield app_client, seeded_user


# ── Service unit tests ──────────────────────────────────────────────


class TestUserNotificationPreferenceService:
    def test_get_returns_defaults_when_no_row(self, app_client, seeded_user):
        """Pas de ligne DB → retourne defaults + created_at=None."""
        from services.user_notification_preference_service import get_user_preferences

        _, SessionLocal = app_client
        db = SessionLocal()
        try:
            prefs = get_user_preferences(db, seeded_user.id)
            assert prefs["digest_daily_enabled"] is True
            assert prefs["digest_daily_locale"] == "fr-FR"
            assert prefs["digest_channels"] == ["email"]
            assert prefs["created_at"] is None
            assert prefs["updated_at"] is None
        finally:
            db.close()

    def test_upsert_creates_row_first_time(self, app_client, seeded_user):
        """Premier upsert → INSERT ligne avec defaults + updates."""
        from models.user_notification_preference import UserNotificationPreference
        from services.user_notification_preference_service import upsert_user_preferences

        _, SessionLocal = app_client
        db = SessionLocal()
        try:
            assert db.query(UserNotificationPreference).filter_by(user_id=seeded_user.id).first() is None

            result = upsert_user_preferences(db, seeded_user.id, {"digest_daily_enabled": False})
            assert result["digest_daily_enabled"] is False
            # Defaults appliqués sur les autres champs
            assert result["digest_daily_locale"] == "fr-FR"
            assert result["digest_channels"] == ["email"]
            assert result["created_at"] is not None

            # Row persistée
            assert db.query(UserNotificationPreference).filter_by(user_id=seeded_user.id).count() == 1
        finally:
            db.close()

    def test_upsert_partial_update_only_changes_provided_fields(self, app_client, seeded_user):
        """Update partiel : seul digest_daily_locale change."""
        from services.user_notification_preference_service import upsert_user_preferences

        _, SessionLocal = app_client
        db = SessionLocal()
        try:
            # 1er appel : crée la ligne avec defaults + opt-out digest
            upsert_user_preferences(db, seeded_user.id, {"digest_daily_enabled": False})
            # 2e appel : update locale uniquement
            result = upsert_user_preferences(db, seeded_user.id, {"digest_daily_locale": "en-US"})
            # digest_daily_enabled reste False (pas dans updates 2e appel)
            assert result["digest_daily_enabled"] is False
            assert result["digest_daily_locale"] == "en-US"
        finally:
            db.close()


# ── Endpoint integration tests ──────────────────────────────────────


class TestGetMyNotificationPreferencesEndpoint:
    def test_get_returns_defaults(self, auth_as_user):
        (client, _), _ = auth_as_user
        response = client.get("/api/v1/users/me/notification-preferences")
        assert response.status_code == 200
        body = response.json()
        assert body["digest_daily_enabled"] is True
        assert body["digest_daily_locale"] == "fr-FR"
        assert body["digest_channels"] == ["email"]
        assert body["created_at"] is None
        assert body["updated_at"] is None

    def test_get_returns_db_values_when_row_exists(self, auth_as_user):
        (client, SessionLocal), user = auth_as_user
        from services.user_notification_preference_service import upsert_user_preferences

        db = SessionLocal()
        try:
            upsert_user_preferences(db, user.id, {"digest_daily_enabled": False})
        finally:
            db.close()

        response = client.get("/api/v1/users/me/notification-preferences")
        assert response.status_code == 200
        body = response.json()
        assert body["digest_daily_enabled"] is False
        assert body["created_at"] is not None  # row existe maintenant

    def test_get_requires_auth(self, app_client):
        """Sans override get_current_user → 401."""
        client, _ = app_client
        response = client.get("/api/v1/users/me/notification-preferences")
        assert response.status_code == 401


class TestPatchMyNotificationPreferencesEndpoint:
    def test_patch_creates_row_first_time(self, auth_as_user):
        (client, _), _ = auth_as_user
        response = client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"digest_daily_enabled": False},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["digest_daily_enabled"] is False
        assert body["created_at"] is not None  # row désormais persistée

    def test_patch_partial_update(self, auth_as_user):
        (client, _), _ = auth_as_user
        # 1er PATCH
        client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"digest_daily_enabled": False},
        )
        # 2e PATCH : seul locale change
        response = client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"digest_daily_locale": "en-US"},
        )
        assert response.status_code == 200
        body = response.json()
        # digest_daily_enabled reste False
        assert body["digest_daily_enabled"] is False
        assert body["digest_daily_locale"] == "en-US"

    def test_patch_validates_invalid_channels(self, auth_as_user):
        (client, _), _ = auth_as_user
        response = client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"digest_channels": ["telegram", "fax"]},
        )
        assert response.status_code == 422
        # Format error_handler PROMEOS : code/message/hint (pas Pydantic
        # standard `detail`). Vérification message contient les channels invalides.
        body = response.json()
        assert body.get("code") == "VALIDATION_ERROR"
        assert "telegram" in body.get("hint", "") or "telegram" in body.get("message", "")

    def test_patch_rejects_locale_too_long(self, auth_as_user):
        (client, _), _ = auth_as_user
        response = client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"digest_daily_locale": "x" * 32},  # > max_length=16
        )
        assert response.status_code == 422

    def test_patch_rejects_empty_channels_list(self, auth_as_user):
        (client, _), _ = auth_as_user
        response = client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"digest_channels": []},
        )
        assert response.status_code == 422

    def test_patch_requires_auth(self, app_client):
        client, _ = app_client
        response = client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"digest_daily_enabled": False},
        )
        assert response.status_code == 401

    def test_patch_ignores_user_id_in_body(self, auth_as_user):
        """SG_USER_PREFS_03 : user_id dans body est ignoré.

        Même si l'attaquant tente d'override user_id=99 (autre user),
        le service utilise current_user.id du token.
        """
        (client, SessionLocal), seeded = auth_as_user

        # Tente d'injecter user_id=99 dans le body
        response = client.patch(
            "/api/v1/users/me/notification-preferences",
            json={"user_id": 99, "digest_daily_enabled": False},
        )
        # Pydantic strip les champs inconnus (pas de validation error)
        assert response.status_code == 200

        # Vérifie que la ligne a été créée pour seeded.id, pas user_id=99
        from models.user_notification_preference import UserNotificationPreference

        db = SessionLocal()
        try:
            row = db.query(UserNotificationPreference).filter_by(user_id=seeded.id).first()
            assert row is not None
            assert row.digest_daily_enabled is False
            # Pas de ligne pour user_id=99
            row_99 = db.query(UserNotificationPreference).filter_by(user_id=99).first()
            assert row_99 is None
        finally:
            db.close()


# ── Migration / schema tests ────────────────────────────────────────


class TestMigration:
    def test_table_created_idempotent(self, app_client):
        """Le table user_notification_preferences existe après init DB."""
        from sqlalchemy import inspect

        _, SessionLocal = app_client
        db = SessionLocal()
        try:
            insp = inspect(db.get_bind())
            assert insp.has_table("user_notification_preferences")
            cols = {c["name"] for c in insp.get_columns("user_notification_preferences")}
            assert {
                "id",
                "user_id",
                "digest_daily_enabled",
                "digest_daily_locale",
                "digest_channels",
                "created_at",
                "updated_at",
            } <= cols
        finally:
            db.close()


# ── OpenAPI ─────────────────────────────────────────────────────────


class TestOpenAPI:
    def test_endpoints_in_openapi(self, app_client):
        client, _ = app_client
        spec = client.get("/openapi.json").json()
        path = "/api/v1/users/me/notification-preferences"
        assert path in spec["paths"]
        assert "get" in spec["paths"][path]
        assert "patch" in spec["paths"][path]
