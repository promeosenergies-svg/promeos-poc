"""
Tests — CORS configuration (Playbook 1.3).
Source-guard: verify CORS setup in main.py.
"""
import inspect
import re
import os
import pytest

pytestmark = pytest.mark.fast


def _read_main_source():
    main_path = os.path.join(os.path.dirname(__file__), "..", "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        return f.read()


class TestCORSConfig:
    def test_cors_middleware_present(self):
        """main.py should configure CORSMiddleware."""
        src = _read_main_source()
        assert "CORSMiddleware" in src

    def test_demo_mode_wildcard(self):
        """In DEMO_MODE, CORS origins should be wildcard ['*']."""
        src = _read_main_source()
        assert '_CORS_ORIGINS = ["*"]' in src or "_CORS_ORIGINS = ['*']" in src

    def test_production_uses_env_var(self):
        """In production mode, CORS reads PROMEOS_CORS_ORIGINS from env."""
        src = _read_main_source()
        assert "PROMEOS_CORS_ORIGINS" in src

    def test_localhost_defaults(self):
        """Default CORS includes localhost:5173 and localhost:3000."""
        src = _read_main_source()
        assert "localhost:5173" in src
        assert "localhost:3000" in src

    def test_expose_headers(self):
        """CORS should expose X-Request-Id and X-Response-Time."""
        src = _read_main_source()
        assert "X-Request-Id" in src
        assert "X-Response-Time" in src


class TestRateLimitConfig:
    def test_login_rate_limited(self):
        """auth.py should rate-limit login endpoint."""
        auth_path = os.path.join(os.path.dirname(__file__), "..", "routes", "auth.py")
        with open(auth_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "check_rate_limit" in src
        assert 'key_prefix="login"' in src

    def test_reset_db_rate_limited(self):
        """dev_tools.py should rate-limit reset_db endpoint."""
        dt_path = os.path.join(os.path.dirname(__file__), "..", "routes", "dev_tools.py")
        with open(dt_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "check_rate_limit" in src
        assert 'key_prefix="reset_db"' in src

    def test_billing_import_rate_limited(self):
        """billing.py should rate-limit import endpoints."""
        billing_path = os.path.join(os.path.dirname(__file__), "..", "routes", "billing.py")
        with open(billing_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "check_rate_limit" in src
        assert 'key_prefix="billing_import"' in src

    def test_rate_limit_message_french(self):
        """Rate limit 429 message should be in French."""
        rl_path = os.path.join(os.path.dirname(__file__), "..", "middleware", "rate_limit.py")
        with open(rl_path, "r", encoding="utf-8") as f:
            src = f.read()
        assert "Trop de requêtes" in src
