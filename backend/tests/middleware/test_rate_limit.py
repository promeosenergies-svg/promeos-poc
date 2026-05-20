"""M2-4.6 — Tests du rate limiting slowapi V4.

Chaque test utilise un `Limiter` FRAIS (storage in-memory isolé) → pas de
pollution de buckets entre tests. Le limiter global (`main_limiter.limiter`)
est `enabled=False` en environnement de test (cf. tests/conftest.py) — la
dernière classe le vérifie.
"""

import os

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from main_limiter import rate_limit_exceeded_handler, rate_limit_key
from services.iam_service import create_access_token


def _token(user_id: int) -> str:
    return create_access_token(user_id=user_id, org_id=1, role="energy_manager")


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def limited_client():
    """Mini-app avec un Limiter frais activé — endpoint /probe limité à 3/minute.

    Limiter dédié (storage isolé) → chaque test démarre avec des buckets vides.
    """
    fresh = Limiter(
        key_func=rate_limit_key,
        enabled=True,
        storage_uri="memory://",
    )
    app = FastAPI()
    app.state.limiter = fresh
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/probe")
    @fresh.limit("3/minute")
    async def probe(request: Request):
        return {"ok": True}

    return TestClient(app)


# ════════════════════════════════════════════════════════════════════
# Déclenchement du quota
# ════════════════════════════════════════════════════════════════════


class TestRateLimitTriggers:
    def test_under_limit_returns_200(self, limited_client):
        for _ in range(3):
            assert limited_client.get("/probe", headers=_h(_token(1))).status_code == 200

    def test_exceeding_limit_returns_429(self, limited_client):
        for _ in range(3):
            limited_client.get("/probe", headers=_h(_token(1)))
        assert limited_client.get("/probe", headers=_h(_token(1))).status_code == 429

    def test_429_response_follows_promeos_format(self, limited_client):
        for _ in range(3):
            limited_client.get("/probe", headers=_h(_token(1)))
        r = limited_client.get("/probe", headers=_h(_token(1)))
        assert r.status_code == 429
        detail = r.json()["detail"]
        assert detail["code"] == "RATE_LIMIT_EXCEEDED"
        assert isinstance(detail["retry_after"], int)
        assert "Retry-After" in r.headers


# ════════════════════════════════════════════════════════════════════
# Stratégie de clé (user_id, fallback IP)
# ════════════════════════════════════════════════════════════════════


class TestRateLimitScopeKey:
    def test_distinct_users_have_separate_quotas(self, limited_client):
        """🛡️ User A épuise son quota → User B intact (clé `user:<sub>`)."""
        for _ in range(3):
            limited_client.get("/probe", headers=_h(_token(201)))
        assert limited_client.get("/probe", headers=_h(_token(201))).status_code == 429
        # Autre user_id → bucket distinct, quota intact.
        assert limited_client.get("/probe", headers=_h(_token(202))).status_code == 200

    def test_anonymous_falls_back_to_ip(self, limited_client):
        """Sans JWT → clé `ip:<adresse>`. 3 OK puis 429 (même IP TestClient)."""
        for _ in range(3):
            assert limited_client.get("/probe").status_code == 200
        assert limited_client.get("/probe").status_code == 429

    def test_invalid_jwt_falls_back_to_ip_without_crash(self, limited_client):
        """JWT illisible → fallback IP silencieux, jamais de crash."""
        bad = {"Authorization": "Bearer not-a-real-jwt"}
        for i in range(4):
            r = limited_client.get("/probe", headers=bad)
            assert r.status_code == (200 if i < 3 else 429)


# ════════════════════════════════════════════════════════════════════
# Désactivation en environnement de test
# ════════════════════════════════════════════════════════════════════


class TestRateLimitDisabledInTests:
    def test_global_limiter_disabled_in_test_env(self):
        """Le limiter global est enabled=False en test → les 240+ tests V4 sûrs."""
        from main_limiter import limiter

        assert os.environ.get("PROMEOS_RATE_LIMIT_ENABLED") == "false"
        assert limiter.enabled is False
