"""
PROMEOS — V28: Performance Budget Tests
Assert critical endpoint response times stay under budget.
Uses demo seed data for realistic load. In-memory SQLite.

Thresholds are configurable via env vars (see perf_config.py).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base
from database import get_db
from main import app
from perf_config import PERF_THRESHOLDS


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def seeded_client(db_session):
    """Client with demo data seeded once for all perf tests."""
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)

    # Seed demo data (org + sites + obligations + alertes)
    r = client.post("/api/demo/seed")
    assert r.status_code == 200, f"Demo seed failed: {r.text}"

    yield client
    app.dependency_overrides.clear()


def _timed_get(client, url, iterations=3):
    """Return best-of-N response time in ms. 1 warm-up call + N measured."""
    client.get(url)  # warm-up
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        r = client.get(url)
        elapsed = (time.perf_counter() - start) * 1000
        assert r.status_code == 200, f"{url} returned {r.status_code}"
        times.append(elapsed)
    return min(times)


class TestPerfBudget:
    """Assert critical endpoints respond within budget."""

    def test_cockpit_under_budget(self, seeded_client):
        """GET /api/cockpit must respond within budget."""
        ms = _timed_get(seeded_client, "/api/cockpit")
        threshold = PERF_THRESHOLDS["test_cockpit_ms"]
        assert ms < threshold, (
            f"GET /api/cockpit took {ms:.1f}ms, budget is {threshold}ms"
        )

    def test_dashboard_2min_under_budget(self, seeded_client):
        """GET /api/dashboard/2min must respond within budget."""
        ms = _timed_get(seeded_client, "/api/dashboard/2min")
        threshold = PERF_THRESHOLDS["test_dashboard_2min_ms"]
        assert ms < threshold, (
            f"GET /api/dashboard/2min took {ms:.1f}ms, budget is {threshold}ms"
        )

    def test_sites_list_under_budget(self, seeded_client):
        """GET /api/sites must respond within budget."""
        ms = _timed_get(seeded_client, "/api/sites")
        threshold = PERF_THRESHOLDS["test_sites_list_ms"]
        assert ms < threshold, (
            f"GET /api/sites took {ms:.1f}ms, budget is {threshold}ms"
        )
