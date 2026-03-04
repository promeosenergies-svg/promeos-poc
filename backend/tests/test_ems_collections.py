"""
PROMEOS - EMS Collections CRUD Tests
12 tests covering create, list, update, delete, favorite, site_ids, edge cases.
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest

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


class TestCollectionsCRUD:
    def test_create_collection_201(self, env):
        client, db = env
        r = client.post(
            "/api/ems/collections",
            params={
                "name": "Bureaux IDF",
                "site_ids": "1,2,3",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Bureaux IDF"
        assert data["site_ids"] == [1, 2, 3]
        assert "id" in data

    def test_list_empty(self, env):
        client, db = env
        r = client.get("/api/ems/collections")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_after_create(self, env):
        client, db = env
        client.post("/api/ems/collections", params={"name": "C1", "site_ids": "1"})
        client.post("/api/ems/collections", params={"name": "C2", "site_ids": "2,3"})

        r = client.get("/api/ems/collections")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 2
        names = {c["name"] for c in data}
        assert names == {"C1", "C2"}

    def test_create_with_scope_type(self, env):
        client, db = env
        r = client.post(
            "/api/ems/collections",
            params={
                "name": "Portfolio",
                "site_ids": "1,2",
                "scope_type": "portfolio",
            },
        )
        assert r.status_code == 201
        # Verify via list
        cols = client.get("/api/ems/collections").json()
        assert cols[0]["scope_type"] == "portfolio"

    def test_create_favorite(self, env):
        client, db = env
        r = client.post(
            "/api/ems/collections",
            params={
                "name": "Favoris",
                "site_ids": "1",
                "is_favorite": True,
            },
        )
        assert r.status_code == 201

        cols = client.get("/api/ems/collections").json()
        assert cols[0]["is_favorite"] is True

    def test_favorite_sorted_first(self, env):
        """Favorites should appear before non-favorites in listing."""
        client, db = env
        client.post(
            "/api/ems/collections",
            params={
                "name": "Normal",
                "site_ids": "1",
                "is_favorite": False,
            },
        )
        client.post(
            "/api/ems/collections",
            params={
                "name": "Star",
                "site_ids": "2",
                "is_favorite": True,
            },
        )

        cols = client.get("/api/ems/collections").json()
        assert cols[0]["name"] == "Star"
        assert cols[1]["name"] == "Normal"

    def test_update_name(self, env):
        client, db = env
        r = client.post(
            "/api/ems/collections",
            params={
                "name": "Old",
                "site_ids": "1,2",
            },
        )
        col_id = r.json()["id"]

        r2 = client.put(f"/api/ems/collections/{col_id}", params={"name": "New Name"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    def test_update_site_ids(self, env):
        client, db = env
        r = client.post(
            "/api/ems/collections",
            params={
                "name": "Sites",
                "site_ids": "1,2,3",
            },
        )
        col_id = r.json()["id"]

        client.put(f"/api/ems/collections/{col_id}", params={"site_ids": "4,5"})

        cols = client.get("/api/ems/collections").json()
        updated = [c for c in cols if c["id"] == col_id][0]
        assert updated["site_ids"] == [4, 5]

    def test_update_favorite_flag(self, env):
        client, db = env
        r = client.post(
            "/api/ems/collections",
            params={
                "name": "Toggle",
                "site_ids": "1",
            },
        )
        col_id = r.json()["id"]

        client.put(f"/api/ems/collections/{col_id}", params={"is_favorite": True})
        cols = client.get("/api/ems/collections").json()
        assert cols[0]["is_favorite"] is True

    def test_delete(self, env):
        client, db = env
        r = client.post(
            "/api/ems/collections",
            params={
                "name": "To Delete",
                "site_ids": "1",
            },
        )
        col_id = r.json()["id"]

        r2 = client.delete(f"/api/ems/collections/{col_id}")
        assert r2.status_code == 200
        assert r2.json()["deleted"] is True

        cols = client.get("/api/ems/collections").json()
        assert len(cols) == 0

    def test_delete_404(self, env):
        client, db = env
        r = client.delete("/api/ems/collections/9999")
        assert r.status_code == 404

    def test_update_404(self, env):
        client, db = env
        r = client.put("/api/ems/collections/9999", params={"name": "Nope"})
        assert r.status_code == 404
