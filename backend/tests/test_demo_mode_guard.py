"""
PROMEOS — Test DEMO_MODE org fallback guard.

Covers:
  1) DEMO_MODE=true  → resolve_org_id falls back to first active org (no 401)
  2) DEMO_MODE=false → resolve_org_id raises 401 when auth=None and no header
  3) org_id_override bypasses header/fallback (for routes with query param)
  4) Auth takes priority over override and header
  5) DEMO_MODE default is false (secure-by-default)
  6) No inline _resolve_org_id remain in hardened routes
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inspect
import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def db():
    """In-memory SQLite with a single active Organisation."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    org = Organisation(
        nom="TestCorp",
        siren="123456789",
        actif=True,
    )
    session.add(org)
    session.commit()

    yield session
    session.close()


def _make_request(org_id_header=None):
    """Build a mock FastAPI Request with optional X-Org-Id header."""
    req = MagicMock()
    headers = {}
    if org_id_header is not None:
        headers["X-Org-Id"] = str(org_id_header)
    req.headers = headers
    return req


@dataclass
class _FakeAuth:
    org_id: int


# ========================================
# Tests — core resolve_org_id behaviour
# ========================================


class TestDemoModeAllowsFallback:
    """DEMO_MODE=true → auth=None without header → fallback to DB org."""

    @patch("services.scope_utils.DEMO_MODE", True)
    @patch("services.demo_state.DemoState.get_demo_org_id", return_value=None)
    def test_demo_mode_allows_fallback(self, _mock_demo, db):
        """resolve_org_id returns the first active org when DEMO_MODE=true."""
        from services.scope_utils import resolve_org_id

        request = _make_request()  # no X-Org-Id header
        auth = None  # no authentication

        org_id = resolve_org_id(request, auth, db)

        # Should fall back to the Organisation created in fixture
        org = db.query(Organisation).filter(Organisation.actif == True).first()
        assert org_id == org.id


class TestNonDemoModeRejectsFallback:
    """DEMO_MODE=false → auth=None without header → 401."""

    @patch("services.scope_utils.DEMO_MODE", False)
    def test_non_demo_mode_rejects_fallback(self, db):
        """resolve_org_id raises 401 when DEMO_MODE=false and no auth/header."""
        from services.scope_utils import resolve_org_id

        request = _make_request()  # no X-Org-Id header
        auth = None  # no authentication

        with pytest.raises(HTTPException) as exc_info:
            resolve_org_id(request, auth, db)

        assert exc_info.value.status_code == 401
        assert "DEMO_MODE" in exc_info.value.detail


class TestOrgIdOverride:
    """org_id_override param (for routes using query params instead of header)."""

    @patch("services.scope_utils.DEMO_MODE", False)
    def test_override_bypasses_fallback(self, db):
        """Explicit org_id_override resolves without needing auth or header."""
        from services.scope_utils import resolve_org_id

        request = _make_request()  # no header
        org = db.query(Organisation).first()

        result = resolve_org_id(request, None, db, org_id_override=org.id)
        assert result == org.id

    @patch("services.scope_utils.DEMO_MODE", False)
    def test_auth_takes_priority_over_override(self, db):
        """Auth org_id wins over org_id_override."""
        from services.scope_utils import resolve_org_id

        request = _make_request()
        auth = _FakeAuth(org_id=999)

        result = resolve_org_id(request, auth, db, org_id_override=888)
        assert result == 999  # auth wins


class TestDemoModeDefault:
    """DEMO_MODE defaults to false (secure-by-default)."""

    def test_demo_mode_code_default_is_false(self):
        """Source code default for PROMEOS_DEMO_MODE is 'false' (secure-by-default)."""
        import inspect
        import middleware.auth as mod

        src = inspect.getsource(mod)
        # The env var default must be "false" — not "true"
        assert 'get("PROMEOS_DEMO_MODE", "false")' in src


# ========================================
# Tests — no inline resolvers in hardened routes
# ========================================


class TestNoInlineResolvers:
    """Ensure hardened routes delegate to centralized resolve_org_id."""

    def test_actions_no_inline_resolver(self):
        """actions.py has no insecure _resolve_org_id with Organisation.first()."""
        import routes.actions as mod

        src = inspect.getsource(mod)
        assert "Organisation).first()" not in src

    def test_notifications_no_inline_resolver(self):
        """notifications.py has no insecure _resolve_org_id with Organisation.first()."""
        import routes.notifications as mod

        src = inspect.getsource(mod)
        assert "Organisation).first()" not in src

    def test_reports_no_inline_resolver(self):
        """reports.py has no insecure _resolve_org_id with Organisation.first()."""
        import routes.reports as mod

        src = inspect.getsource(mod)
        assert "Organisation).first()" not in src

    def test_cockpit_no_inline_resolver(self):
        """cockpit.py has no header-only _get_org_id helper."""
        import routes.cockpit as mod

        src = inspect.getsource(mod)
        assert "def _get_org_id(" not in src

    def test_dashboard_no_inline_resolver(self):
        """dashboard_2min.py has no header-only _get_org_id_from_header helper."""
        import routes.dashboard_2min as mod

        src = inspect.getsource(mod)
        assert "def _get_org_id_from_header(" not in src

    def test_sites_no_inline_resolver(self):
        """sites.py has no header-only _get_org_id_from_request helper."""
        import routes.sites as mod

        src = inspect.getsource(mod)
        assert "def _get_org_id_from_request(" not in src
