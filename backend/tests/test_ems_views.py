"""
PROMEOS - EMS Saved Views CRUD Tests
10 tests covering create, read, update, delete, filtering and edge cases.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from main import app
from models import Base
from database import get_db


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    def _override():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    client = TestClient(app)
    yield client, session
    app.dependency_overrides.clear()
    session.close()


def _config(**kwargs):
    default = {
        "scope_type": "site", "scope_ids": [1],
        "date_from": "2025-01-01", "date_to": "2025-04-01",
        "granularity": "daily", "mode": "aggregate", "metric": "kwh",
        "show_weather": False, "show_quality": False,
    }
    default.update(kwargs)
    return json.dumps(default)


class TestSavedViews:

    def test_create_view_201(self, env):
        client, db = env
        r = client.post("/api/ems/views", params={
            "name": "Vue Test", "config_json": _config(), "user_id": 1,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Vue Test"
        assert "id" in data

    def test_get_view(self, env):
        client, db = env
        r = client.post("/api/ems/views", params={
            "name": "Vue A", "config_json": _config(),
        })
        view_id = r.json()["id"]

        r2 = client.get(f"/api/ems/views/{view_id}")
        assert r2.status_code == 200
        data = r2.json()
        assert data["name"] == "Vue A"
        assert json.loads(data["config_json"])["granularity"] == "daily"

    def test_list_views(self, env):
        client, db = env
        client.post("/api/ems/views", params={"name": "V1", "config_json": _config()})
        client.post("/api/ems/views", params={"name": "V2", "config_json": _config()})

        r = client.get("/api/ems/views")
        assert r.status_code == 200
        assert len(r.json()) >= 2

    def test_update_name(self, env):
        client, db = env
        r = client.post("/api/ems/views", params={
            "name": "Old Name", "config_json": _config(),
        })
        view_id = r.json()["id"]

        r2 = client.put(f"/api/ems/views/{view_id}", params={"name": "New Name"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    def test_update_config(self, env):
        client, db = env
        r = client.post("/api/ems/views", params={
            "name": "Config View", "config_json": _config(),
        })
        view_id = r.json()["id"]
        new_cfg = _config(granularity="monthly", show_weather=True)

        r2 = client.put(f"/api/ems/views/{view_id}", params={"config_json": new_cfg})
        assert r2.status_code == 200

        r3 = client.get(f"/api/ems/views/{view_id}")
        cfg = json.loads(r3.json()["config_json"])
        assert cfg["granularity"] == "monthly"
        assert cfg["show_weather"] is True

    def test_delete(self, env):
        client, db = env
        r = client.post("/api/ems/views", params={
            "name": "To Delete", "config_json": _config(),
        })
        view_id = r.json()["id"]

        r2 = client.delete(f"/api/ems/views/{view_id}")
        assert r2.status_code == 200
        assert r2.json()["deleted"] is True

        r3 = client.get(f"/api/ems/views/{view_id}")
        assert r3.status_code == 404

    def test_get_404(self, env):
        client, db = env
        r = client.get("/api/ems/views/9999")
        assert r.status_code == 404

    def test_delete_404(self, env):
        client, db = env
        r = client.delete("/api/ems/views/9999")
        assert r.status_code == 404

    def test_list_user_filter(self, env):
        client, db = env
        client.post("/api/ems/views", params={
            "name": "User1 View", "config_json": _config(), "user_id": 1,
        })
        client.post("/api/ems/views", params={
            "name": "User2 View", "config_json": _config(), "user_id": 2,
        })

        r = client.get("/api/ems/views", params={"user_id": 1})
        names = [v["name"] for v in r.json()]
        assert "User1 View" in names
        assert "User2 View" not in names

    def test_shared_view_visible(self, env):
        """Views with user_id=null are shared and visible to all users."""
        client, db = env
        # Create shared view (no user_id)
        client.post("/api/ems/views", params={
            "name": "Shared View", "config_json": _config(),
        })
        # Create user-specific view
        client.post("/api/ems/views", params={
            "name": "Private View", "config_json": _config(), "user_id": 5,
        })

        # User 5 should see both shared and own
        r = client.get("/api/ems/views", params={"user_id": 5})
        names = [v["name"] for v in r.json()]
        assert "Shared View" in names
        assert "Private View" in names
