"""
PROMEOS — V29 Test: /api/actions/list multi-status filter
Validates that comma-separated status values are correctly handled.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, ActionItem, TypeSite
from models.enums import ActionStatus, ActionSourceType
from database import get_db
from main import app


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def seeded_client(db_session):
    """Seed org + 4 actions with different statuses, return TestClient."""
    org = Organisation(nom="TestOrg", type_client="retail", actif=True)
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    statuses = [ActionStatus.OPEN, ActionStatus.IN_PROGRESS, ActionStatus.DONE, ActionStatus.BLOCKED]
    for i, st in enumerate(statuses):
        action = ActionItem(
            org_id=org.id,
            source_type=ActionSourceType.MANUAL,
            source_id=f"test_{i}",
            source_key=f"key_{i}",
            title=f"Action {st.value}",
            status=st,
            priority=2,
        )
        db_session.add(action)
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    yield client, org.id
    app.dependency_overrides.clear()


# ── Tests ───────────────────────────────────────────────────────────────────


class TestActionsMultiStatus:
    """V29: Comma-separated status filter on /api/actions/list."""

    def test_single_status_filter(self, seeded_client):
        client, org_id = seeded_client
        resp = client.get(f"/api/actions/list?org_id={org_id}&status=open")
        assert resp.status_code == 200
        data = resp.json()
        actions = data if isinstance(data, list) else data.get("actions", [])
        assert all(a["status"] == "open" for a in actions)
        assert len(actions) == 1

    def test_multi_status_comma_separated(self, seeded_client):
        """The main bug fix: ?status=open,in_progress should return both."""
        client, org_id = seeded_client
        resp = client.get(f"/api/actions/list?org_id={org_id}&status=open,in_progress")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        actions = data if isinstance(data, list) else data.get("actions", [])
        statuses = {a["status"] for a in actions}
        assert statuses == {"open", "in_progress"}
        assert len(actions) == 2

    def test_multi_status_three_values(self, seeded_client):
        client, org_id = seeded_client
        resp = client.get(f"/api/actions/list?org_id={org_id}&status=open,in_progress,done")
        assert resp.status_code == 200
        data = resp.json()
        actions = data if isinstance(data, list) else data.get("actions", [])
        statuses = {a["status"] for a in actions}
        assert statuses == {"open", "in_progress", "done"}
        assert len(actions) == 3

    def test_invalid_status_still_400(self, seeded_client):
        """Invalid enum value should still return 400."""
        client, org_id = seeded_client
        resp = client.get(f"/api/actions/list?org_id={org_id}&status=bogus")
        assert resp.status_code == 400

    def test_mixed_valid_invalid_status_400(self, seeded_client):
        """If any value in the comma list is invalid, return 400."""
        client, org_id = seeded_client
        resp = client.get(f"/api/actions/list?org_id={org_id}&status=open,backlog")
        assert resp.status_code == 400

    def test_no_status_returns_all(self, seeded_client):
        """No status filter returns all actions."""
        client, org_id = seeded_client
        resp = client.get(f"/api/actions/list?org_id={org_id}")
        assert resp.status_code == 200
        data = resp.json()
        actions = data if isinstance(data, list) else data.get("actions", [])
        assert len(actions) == 4

    def test_whitespace_handling(self, seeded_client):
        """Spaces around commas should be tolerated."""
        client, org_id = seeded_client
        resp = client.get(f"/api/actions/list?org_id={org_id}&status=open, in_progress")
        assert resp.status_code == 200
        data = resp.json()
        actions = data if isinstance(data, list) else data.get("actions", [])
        assert len(actions) == 2
