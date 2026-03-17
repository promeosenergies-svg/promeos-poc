"""
PROMEOS — Tests d'invariants metier.
Verifie les contrats fondamentaux de l'API :
- Quick-create => batiment auto
- Soft-delete => exclusion des listes
- Contrat => site_id valide
- Erreurs => format APIError standard
- EFA => site_id valide (pas d'orphelins)
- Completeness => structure valide
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import Base, Site, Batiment, not_deleted


@pytest.fixture
def app_client():
    """TestClient with in-memory DB — meme pattern que test_quick_create_site.py."""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)

    from main import app
    from database import get_db

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    os.environ["DEMO_MODE"] = "true"

    client = TestClient(app, raise_server_exceptions=False)
    yield client, SessionLocal

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Quick-create toujours auto-cree un batiment
# ═══════════════════════════════════════════════════════════════════════════


class TestSiteCreatedHasBuilding:
    """Invariant : quick-create site => batiment auto-cree."""

    def test_site_created_has_building(self, app_client):
        client, SessionLocal = app_client
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": "Bureau Invariant", "usage": "bureau"},
        )
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "created"

        # Le batiment auto-provisionne doit exister
        assert data["auto_provisioned"]["batiment_id"] is not None
        batiment_id = data["auto_provisioned"]["batiment_id"]

        # Verification en base
        db = SessionLocal()
        bat = db.query(Batiment).filter(Batiment.id == batiment_id).first()
        assert bat is not None, "Le batiment auto-cree doit exister en base"
        assert bat.site_id == data["site"]["id"]
        db.close()


# ═══════════════════════════════════════════════════════════════════════════
# 2. Un site soft-delete est exclu des requetes de listing
# ═══════════════════════════════════════════════════════════════════════════


class TestSoftDeletedSiteExcludedFromQueries:
    """Invariant : un site archive (deleted_at != NULL) ne doit pas apparaitre dans list_sites."""

    def test_soft_deleted_site_excluded_from_queries(self, app_client):
        client, SessionLocal = app_client

        # Creer 2 sites
        resp1 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Site Actif"},
        )
        assert resp1.status_code == 201
        site_actif_id = resp1.json()["site"]["id"]

        resp2 = client.post(
            "/api/sites/quick-create",
            json={"nom": "Site Archive"},
        )
        assert resp2.status_code == 201
        site_archive_id = resp2.json()["site"]["id"]

        # Soft-delete le 2eme site
        db = SessionLocal()
        from datetime import datetime, timezone

        site_to_delete = db.query(Site).filter(Site.id == site_archive_id).first()
        site_to_delete.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.close()

        # Lister les sites patrimoine => seul le site actif doit apparaitre
        resp_list = client.get("/api/sites")
        assert resp_list.status_code == 200
        sites = resp_list.json().get("sites", resp_list.json().get("data", []))

        site_ids = [s["id"] for s in sites]
        assert site_actif_id in site_ids, "Le site actif doit etre dans la liste"
        assert site_archive_id not in site_ids, "Le site archive ne doit PAS etre dans la liste"


# ═══════════════════════════════════════════════════════════════════════════
# 3. Creation contrat avec site_id invalide => erreur
# ═══════════════════════════════════════════════════════════════════════════


class TestContractRequiresValidSite:
    """Invariant : creer un contrat avec un site_id inexistant retourne une erreur."""

    def test_contract_requires_valid_site(self, app_client):
        client, _ = app_client

        # Creer un site d'abord pour avoir une org valide
        resp_site = client.post(
            "/api/sites/quick-create",
            json={"nom": "Site Test Contrat"},
        )
        assert resp_site.status_code == 201

        # Tenter de creer un contrat avec un site_id inexistant
        resp = client.post(
            "/api/patrimoine/contracts",
            json={
                "site_id": 99999,
                "energy_type": "elec",
                "supplier_name": "EDF",
                "start_date": "2024-01-01",
            },
        )
        # Doit echouer (404 site non trouve)
        assert resp.status_code in (404, 403, 400), f"Expected error, got {resp.status_code}: {resp.text}"


# ═══════════════════════════════════════════════════════════════════════════
# 4. Format APIError standard pour les erreurs
# ═══════════════════════════════════════════════════════════════════════════


class TestAPIErrorFormat:
    """Invariant : les erreurs HTTP renvoient le format APIError standard."""

    def test_api_error_format_404(self, app_client):
        client, _ = app_client

        # Appeler un endpoint inexistant ou avec un ID invalide
        resp = client.get("/api/patrimoine/sites/999999/completeness")
        assert resp.status_code in (404, 403, 500)

        data = resp.json()
        # Doit contenir les champs APIError standard
        assert "code" in data, f"La reponse d'erreur doit contenir 'code'. Got: {data}"
        assert "message" in data, f"La reponse d'erreur doit contenir 'message'. Got: {data}"
        assert "correlation_id" in data, f"La reponse d'erreur doit contenir 'correlation_id'. Got: {data}"

    def test_api_error_format_validation(self, app_client):
        client, _ = app_client

        # Envoyer un payload invalide (nom vide)
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": ""},
        )
        assert resp.status_code == 422

        data = resp.json()
        assert "code" in data, f"La reponse de validation doit contenir 'code'. Got: {data}"
        assert data["code"] == "VALIDATION_ERROR"
        assert "correlation_id" in data


# ═══════════════════════════════════════════════════════════════════════════
# 5. Pas d'EFA orpheline sans site valide
# ═══════════════════════════════════════════════════════════════════════════


class TestNoOrphanEfaWithoutSite:
    """Invariant : toutes les EFA avec site_id non-null doivent referencer un site existant."""

    def test_no_orphan_efa_without_site(self, app_client):
        client, SessionLocal = app_client

        db = SessionLocal()
        try:
            from models import TertiaireEfa

            # Verifier qu'il n'y a pas d'EFA orphelines (site_id pointe vers un site inexistant)
            efas_with_site = db.query(TertiaireEfa).filter(TertiaireEfa.site_id.isnot(None)).all()

            for efa in efas_with_site:
                site = db.query(Site).filter(Site.id == efa.site_id).first()
                assert site is not None, (
                    f"EFA {efa.id} (nom={efa.nom}) reference site_id={efa.site_id} "
                    f"qui n'existe pas en base — orphelin detecte"
                )
        finally:
            db.close()


# ═══════════════════════════════════════════════════════════════════════════
# 6. Endpoint completeness retourne une structure valide
# ═══════════════════════════════════════════════════════════════════════════


class TestCompletenessEndpointReturnsValidStructure:
    """Invariant : /completeness retourne score, missing, filled."""

    def test_completeness_endpoint_returns_valid_structure(self, app_client):
        client, _ = app_client

        # Creer un site
        resp = client.post(
            "/api/sites/quick-create",
            json={"nom": "Site Completeness Test", "usage": "bureau"},
        )
        assert resp.status_code == 201
        site_id = resp.json()["site"]["id"]

        # Appeler le endpoint completeness
        resp_comp = client.get(f"/api/patrimoine/sites/{site_id}/completeness")
        assert resp_comp.status_code == 200, resp_comp.text

        data = resp_comp.json()

        # Champs obligatoires de la structure completeness
        assert "score" in data, f"Completeness doit contenir 'score'. Got: {list(data.keys())}"
        assert "missing" in data, f"Completeness doit contenir 'missing'. Got: {list(data.keys())}"
        assert "filled" in data, f"Completeness doit contenir 'filled'. Got: {list(data.keys())}"
        assert "total" in data, f"Completeness doit contenir 'total'. Got: {list(data.keys())}"
        assert "checks" in data, f"Completeness doit contenir 'checks'. Got: {list(data.keys())}"

        # Validations de type
        assert isinstance(data["score"], int), f"score doit etre un int, got {type(data['score'])}"
        assert 0 <= data["score"] <= 100, f"score doit etre entre 0 et 100, got {data['score']}"
        assert isinstance(data["missing"], list), f"missing doit etre une liste"
        assert isinstance(data["filled"], int), f"filled doit etre un int"
        assert isinstance(data["total"], int), f"total doit etre un int"
        assert data["filled"] + len(data["missing"]) == data["total"], "filled + len(missing) == total"
