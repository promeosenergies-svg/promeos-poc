"""Tests endpoint POST /api/v1/digest/dispatch — Phase 2.D Sprint α-push.

Couvre :
- 200 admin auth + délégation pure
- 401 sans token
- 403 sans rôle platform admin
- Body dry_run + user_filter passés au service
- Default body (vide) → DispatchRequest()
- Schema response (DigestRunSummary)
- OpenAPI inclut POST /digest/dispatch
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def admin_payload():
    return {"sub": "1", "org_id": 1, "role": "DG_OWNER"}


@pytest.fixture
def with_admin(app_client, admin_payload):
    from main import app
    from middleware.auth import require_platform_admin

    app.dependency_overrides[require_platform_admin] = lambda: admin_payload
    yield app_client


class TestDigestDispatchEndpoint:
    def test_returns_200_with_admin(self, with_admin, monkeypatch):
        from services.digest_service import DigestRunSummary

        monkeypatch.setattr(
            "routes.digest.dispatch_daily_digest",
            lambda db, dry_run, user_filter: DigestRunSummary(
                sent=2, skipped_no_events=1, dry_run=dry_run, correlation_id="abc12345"
            ),
        )

        client, _ = with_admin
        response = client.post("/api/v1/digest/dispatch", json={})
        assert response.status_code == 200
        body = response.json()
        assert body["sent"] == 2
        assert body["skipped_no_events"] == 1
        assert body["dry_run"] is False
        assert body["correlation_id"] == "abc12345"

    def test_returns_401_without_auth(self, app_client):
        client, _ = app_client
        response = client.post("/api/v1/digest/dispatch", json={})
        assert response.status_code == 401

    def test_returns_403_without_platform_admin_role(self, app_client):
        from fastapi import HTTPException
        from main import app
        from middleware.auth import require_platform_admin

        app.dependency_overrides[require_platform_admin] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="forbidden")
        )

        try:
            client, _ = app_client
            response = client.post("/api/v1/digest/dispatch", json={})
            assert response.status_code == 403
        finally:
            app.dependency_overrides.clear()

    def test_dry_run_passed_to_service(self, with_admin, monkeypatch):
        from services.digest_service import DigestRunSummary

        captured = {}

        def _spy(db, dry_run, user_filter):
            captured["dry_run"] = dry_run
            captured["user_filter"] = user_filter
            return DigestRunSummary(dry_run=dry_run, correlation_id="cid")

        monkeypatch.setattr("routes.digest.dispatch_daily_digest", _spy)

        client, _ = with_admin
        client.post(
            "/api/v1/digest/dispatch",
            json={"dry_run": True, "user_filter": [1, 2, 3]},
        )
        assert captured["dry_run"] is True
        assert captured["user_filter"] == [1, 2, 3]

    def test_default_body_is_empty_dispatch_request(self, with_admin, monkeypatch):
        """POST avec body absent ou {} → DispatchRequest() defaults."""
        from services.digest_service import DigestRunSummary

        captured = {}

        def _spy(db, dry_run, user_filter):
            captured["dry_run"] = dry_run
            captured["user_filter"] = user_filter
            return DigestRunSummary(correlation_id="cid")

        monkeypatch.setattr("routes.digest.dispatch_daily_digest", _spy)

        client, _ = with_admin
        # Body vide
        client.post("/api/v1/digest/dispatch", json={})
        assert captured["dry_run"] is False
        assert captured["user_filter"] is None

    def test_response_schema(self, with_admin, monkeypatch):
        from services.digest_service import DigestRunSummary

        monkeypatch.setattr(
            "routes.digest.dispatch_daily_digest",
            lambda db, dry_run, user_filter: DigestRunSummary(sent=5, failed=1, dry_run=False, correlation_id="x"),
        )
        client, _ = with_admin
        body = client.post("/api/v1/digest/dispatch", json={}).json()
        for key in ("sent", "skipped_no_opt_in", "skipped_no_events", "failed", "dry_run", "correlation_id"):
            assert key in body
        assert isinstance(body["sent"], int)

    def test_endpoint_in_openapi(self, app_client):
        client, _ = app_client
        spec = client.get("/openapi.json").json()
        assert "/api/v1/digest/dispatch" in spec["paths"]
        assert "post" in spec["paths"]["/api/v1/digest/dispatch"]
