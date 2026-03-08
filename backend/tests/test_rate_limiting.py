"""
Tests — Rate limiting middleware (Playbook 1.3).
"""

import os
import time
import pytest
from middleware.rate_limit import check_rate_limit, _buckets

pytestmark = pytest.mark.fast


class FakeClient:
    host = "127.0.0.1"


class FakeRequest:
    def __init__(self, ip="127.0.0.1"):
        self.client = FakeClient()
        self.client.host = ip


@pytest.fixture(autouse=True)
def clear_buckets():
    """Clear rate limit buckets between tests."""
    _buckets.clear()
    yield
    _buckets.clear()


@pytest.fixture(autouse=True)
def disable_pytest_skip(monkeypatch):
    """Patch os.environ so PYTEST_CURRENT_TEST is hidden from rate limiter."""
    import middleware.rate_limit as rl_mod

    monkeypatch.setattr(
        rl_mod.os.environ,
        "get",
        lambda key, default=None: None if key == "PYTEST_CURRENT_TEST" else os.environ.get(key, default),
    )


class TestRateLimiting:
    def test_allows_under_limit(self):
        """Requests under limit should pass."""
        req = FakeRequest()
        for _ in range(5):
            check_rate_limit(req, key_prefix="test_ok", max_requests=5, window_seconds=60)

    def test_blocks_over_limit(self):
        """Request over limit should raise 429."""
        from fastapi import HTTPException

        req = FakeRequest()
        for _ in range(5):
            check_rate_limit(req, key_prefix="test_block", max_requests=5, window_seconds=60)

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(req, key_prefix="test_block", max_requests=5, window_seconds=60)

        assert exc_info.value.status_code == 429
        assert "Trop de requêtes" in exc_info.value.detail

    def test_different_ips_independent(self):
        """Different IPs should have independent limits."""
        req1 = FakeRequest(ip="1.1.1.1")
        req2 = FakeRequest(ip="2.2.2.2")

        for _ in range(5):
            check_rate_limit(req1, key_prefix="test_ip", max_requests=5, window_seconds=60)

        # req2 should still work
        check_rate_limit(req2, key_prefix="test_ip", max_requests=5, window_seconds=60)

    def test_different_prefixes_independent(self):
        """Different key prefixes should have independent limits."""
        req = FakeRequest()
        for _ in range(3):
            check_rate_limit(req, key_prefix="prefix_a", max_requests=3, window_seconds=60)

        # Different prefix should still work
        check_rate_limit(req, key_prefix="prefix_b", max_requests=3, window_seconds=60)

    def test_retry_after_header(self):
        """429 response should include Retry-After."""
        from fastapi import HTTPException

        req = FakeRequest()
        for _ in range(2):
            check_rate_limit(req, key_prefix="test_retry", max_requests=2, window_seconds=30)

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(req, key_prefix="test_retry", max_requests=2, window_seconds=30)

        assert "Retry-After" in (exc_info.value.headers or {})

    def test_login_limit_specific(self):
        """Login endpoint should enforce its specific limit."""
        from fastapi import HTTPException

        req = FakeRequest()
        for _ in range(5):
            check_rate_limit(req, key_prefix="login", max_requests=5, window_seconds=60)

        with pytest.raises(HTTPException) as exc_info:
            check_rate_limit(req, key_prefix="login", max_requests=5, window_seconds=60)

        assert exc_info.value.status_code == 429
