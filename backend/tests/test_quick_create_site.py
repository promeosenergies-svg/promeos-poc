"""
PROMEOS — Tests Quick-Create Site (Sprint 1 Patrimoine).
Covers: auto-hiérarchie, anti-doublons, provision auto.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


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
    """Anti-doublons 2 niveaux : exact (nom+CP) et similaire (nom+ville)."""

    def test_exact_duplicate_nom_cp(self, app_client):
        client, SessionLocal = app_client
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001", "ville": "Lyon"},
        )
        assert resp1.json()["status"] == "created"
        org_id = resp1.json()["auto_created"]["organisation"]

        # Même nom + même CP → doublon exact
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001", "ville": "Lyon"},
            headers={"X-Org-Id": str(org_id)},
        )
        data2 = resp2.json()
        assert data2["status"] == "duplicate_detected"
        assert data2["level"] == "exact"

    def test_case_insensitive_detection(self, app_client):
        client, _ = app_client
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001", "ville": "Lyon"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        # Casse différente → détecté quand même
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "bureau lyon", "code_postal": "69001", "ville": "lyon"},
            headers={"X-Org-Id": str(org_id)},
        )
        assert resp2.json()["status"] == "duplicate_detected"

    def test_similar_duplicate_nom_ville(self, app_client):
        client, _ = app_client
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001", "ville": "Lyon"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        # Même nom + même ville mais CP différent → similaire
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69009", "ville": "Lyon"},
            headers={"X-Org-Id": str(org_id)},
        )
        data2 = resp2.json()
        assert data2["status"] == "duplicate_detected"
        assert data2["level"] == "similar"

    def test_different_cp_different_ville_no_duplicate(self, app_client):
        client, _ = app_client
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau", "code_postal": "69001", "ville": "Lyon"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        # Même nom mais ville différente → pas de doublon
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau", "code_postal": "75001", "ville": "Paris"},
            headers={"X-Org-Id": str(org_id)},
        )
        assert resp2.json()["status"] == "created"

    def test_skip_duplicate_check_forces_creation(self, app_client):
        client, _ = app_client
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Lyon", "code_postal": "69001", "ville": "Lyon"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        # Doublon exact mais skip_duplicate_check=true → créé quand même
        resp2 = client.post(
            "/api/sites/quick-create",
            json={
                "nom": "Bureau Lyon",
                "code_postal": "69001",
                "ville": "Lyon",
                "skip_duplicate_check": True,
            },
            headers={"X-Org-Id": str(org_id)},
        )
        assert resp2.json()["status"] == "created"

    def test_no_location_no_duplicate_check(self, app_client):
        client, _ = app_client
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau"},
        )
        org_id = resp1.json()["auto_created"]["organisation"]

        # Sans CP ni ville → pas de vérification
        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau"},
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
