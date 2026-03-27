"""
Tests API decomposition prix — 5 endpoints.
"""

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
from services.market_tariff_loader import load_tariffs_from_yaml


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
    # Charger les tarifs pour que les endpoints fonctionnent
    load_tariffs_from_yaml(session)
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


class TestDecompositionCompute:
    def test_compute_default_c4(self, client):
        resp = client.get("/api/market/decomposition/compute?profile=C4&energy_price=70")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile"] == "C4"
        assert data["energy_eur_mwh"] == 70.0
        assert data["total_ttc_eur_mwh"] > 120
        assert data["total_ttc_eur_mwh"] < 250
        assert "turpe_eur_mwh" in data
        assert "warnings" in data

    def test_compute_c5(self, client):
        resp = client.get("/api/market/decomposition/compute?profile=C5&energy_price=70")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cspe_eur_mwh"] == 30.35  # C5 rate


class TestDecompositionStore:
    def test_store_creates_and_returns(self, client):
        resp = client.post("/api/market/decomposition/store?org_id=1&profile=C4&energy_price=70")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["total_ttc_eur_mwh"] > 0


class TestDecompositionLatest:
    def test_latest_no_data(self, client):
        resp = client.get("/api/market/decomposition/latest?org_id=999")
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_data"

    def test_latest_after_store(self, client):
        client.post("/api/market/decomposition/store?org_id=1&profile=C4&energy_price=70")
        resp = client.get("/api/market/decomposition/latest?org_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile"] == "C4"
        assert data["total_ttc_eur_mwh"] > 0


class TestDecompositionHistory:
    def test_history_empty(self, client):
        resp = client.get("/api/market/decomposition/history?org_id=999")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_history_after_multiple_stores(self, client):
        client.post("/api/market/decomposition/store?org_id=1&profile=C4&energy_price=70")
        client.post("/api/market/decomposition/store?org_id=1&profile=C5&energy_price=75")
        resp = client.get("/api/market/decomposition/history?org_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2


class TestDecompositionCompare:
    def test_compare_three_profiles(self, client):
        resp = client.get("/api/market/decomposition/compare?energy_price=70")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profiles"] == ["C5", "C4", "C2"]
        assert "C5" in data["decompositions"]
        assert "C4" in data["decompositions"]
        assert "C2" in data["decompositions"]

    def test_compare_c5_most_expensive(self, client):
        """C5 paye plus cher que C4 (CSPE 30.35 vs 26.58)."""
        resp = client.get("/api/market/decomposition/compare?energy_price=70")
        data = resp.json()
        s = data["summary"]
        assert s["C5"]["total_ttc_eur_mwh"] > s["C4"]["total_ttc_eur_mwh"]
        # C4 vs C2 : meme CSPE mais TURPE pondere different — pas d'ordre garanti
        assert abs(s["C4"]["total_ttc_eur_mwh"] - s["C2"]["total_ttc_eur_mwh"]) < 5
