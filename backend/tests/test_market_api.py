"""Tests routes API Market Data V2."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from database import get_db
from main import app


@pytest.fixture
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


@pytest.fixture
def client(db_session):
    def _override():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestMarketAPI:

    def test_spot_latest_empty(self, client):
        resp = client.get("/api/market/spot/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") == "no_data" or "price_eur_mwh" in data

    def test_spot_history(self, client):
        resp = client.get("/api/market/spot/history?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert "prices" in data
        assert data["period_days"] == 7

    def test_spot_stats(self, client):
        resp = client.get("/api/market/spot/stats?days=30")
        assert resp.status_code == 200
        data = resp.json()
        assert "zone" in data
        assert "avg_eur_mwh" in data

    def test_forwards(self, client):
        resp = client.get("/api/market/forwards?product=BASELOAD")
        assert resp.status_code == 200
        data = resp.json()
        assert "curves" in data

    def test_tariffs_current(self, client):
        resp = client.get("/api/market/tariffs/current?profile=C4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile"] == "C4"

    def test_tariffs_reload(self, client):
        resp = client.post("/api/market/tariffs/reload")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_freshness(self, client):
        resp = client.get("/api/market/freshness")
        assert resp.status_code == 200
