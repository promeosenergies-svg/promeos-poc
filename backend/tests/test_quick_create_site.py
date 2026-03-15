"""
PROMEOS — Tests Quick-Create Site (Sprint 1 Patrimoine).
Covers: auto-hiérarchie, anti-doublons, provision auto.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Organisation, EntiteJuridique, Portefeuille, Site, Batiment, not_deleted


@pytest.fixture
def app_client():
    """TestClient with in-memory DB."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    # Patch get_db
    from main import app
    from database import get_db

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Set DEMO_MODE for scope resolution
    os.environ["DEMO_MODE"] = "true"

    client = TestClient(app)
    yield client, SessionLocal

    app.dependency_overrides.clear()


class TestQuickCreateNoOrg:
    """Quick-create quand aucune org n'existe → auto-création complète."""

    def test_creates_site_and_hierarchy(self, app_client):
        client, SessionLocal = app_client
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "usage": "bureau"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "created"
        assert data["site"]["nom"] == "Bureau Lyon"
        assert data["site"]["usage"] == "bureau"

        # Vérifier auto-création hiérarchie
        assert "organisation" in data["auto_created"]
        assert "entite_juridique" in data["auto_created"]
        assert "portefeuille" in data["auto_created"]

    def test_auto_provisions_batiment(self, app_client):
        client, SessionLocal = app_client
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": "Usine Dijon", "usage": "usine", "surface_m2": 5000},
        )
        data = resp.json()
        assert data["auto_provisioned"]["batiment_id"] is not None
        assert data["auto_provisioned"]["cvc_power_kw"] > 0

    def test_auto_creates_obligations(self, app_client):
        client, SessionLocal = app_client
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Paris", "usage": "bureau", "surface_m2": 2000},
        )
        data = resp.json()
        # Bureau 2000 m² → décret tertiaire applicable
        assert data["auto_provisioned"]["obligations"] >= 1


class TestQuickCreateWithOrg:
    """Quick-create quand une org existe déjà."""

    def test_reuses_existing_org(self, app_client):
        client, SessionLocal = app_client
        # Créer d'abord un site (crée l'org auto)
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Site 1"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        # Deuxième site → réutilise l'org
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Site 2"},
            headers={"X-Org-Id": str(org_id)},
        )
        data2 = resp2.json()
        assert data2["status"] == "created"
        assert data2["auto_created"] == {}  # rien auto-créé


class TestQuickCreateDuplicateDetection:
    """Anti-doublons par nom + code_postal."""

    def test_detects_duplicate(self, app_client):
        client, SessionLocal = app_client
        # Créer un premier site
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001", "ville": "Lyon"},
        )
        assert resp1.json()["status"] == "created"

        org_id = resp1.json()["auto_created"]["organisation"]

        # Même nom + même CP → doublon
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001"},
            headers={"X-Org-Id": str(org_id)},
        )
        data2 = resp2.json()
        assert data2["status"] == "duplicate_detected"
        assert "existe" in data2["message"].lower() or "existe" in data2["message"]

    def test_different_cp_no_duplicate(self, app_client):
        client, SessionLocal = app_client
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        # Même nom mais CP différent → pas de doublon
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "75001"},
            headers={"X-Org-Id": str(org_id)},
        )
        assert resp2.json()["status"] == "created"

    def test_no_cp_no_duplicate_check(self, app_client):
        client, SessionLocal = app_client
        # Sans CP → pas de vérification doublon
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon"},
            headers={"X-Org-Id": str(org_id)},
        )
        assert resp2.json()["status"] == "created"


class TestQuickCreateMinimalPayload:
    """Le minimum absolu : juste un nom."""

    def test_nom_only(self, app_client):
        client, _ = app_client
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": "Mon site"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "created"
        assert data["site"]["nom"] == "Mon site"
        # Usage par défaut = bureau
        assert data["site"]["usage"] == "bureau"

    def test_empty_nom_rejected(self, app_client):
        client, _ = app_client
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": ""},
        )
        assert resp.status_code == 422  # Validation error
