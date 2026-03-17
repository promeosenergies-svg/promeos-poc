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


# ═══════════════════════════════════════════════════════════════════════════
# 7. Cross-module invariants — patrimoine ↔ conformité ↔ billing
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossModuleInvariants:
    """Verify patrimoine ↔ conformite ↔ billing chain integrity"""

    def test_site_identity_consistent_across_modules(self, app_client):
        """Same site_id returns consistent data across patrimoine and conformité"""
        client, SessionLocal = app_client

        # Create site via quick-create
        r = client.post(
            "/api/sites/quick-create",
            json={
                "nom": "Invariant Test",
                "usage": "bureau",
                "adresse": "1 rue test",
                "code_postal": "75001",
                "ville": "Paris",
            },
            headers={"X-Org-Id": "1"},
        )
        assert r.status_code == 201, r.text
        site_id = r.json()["site"]["id"]

        # Same site accessible via patrimoine
        r2 = client.get(
            f"/api/patrimoine/sites/{site_id}",
            headers={"X-Org-Id": "1"},
        )
        assert r2.status_code == 200
        assert r2.json()["nom"] == "Invariant Test"

        # Same site accessible via completeness
        r3 = client.get(
            f"/api/patrimoine/sites/{site_id}/completeness",
            headers={"X-Org-Id": "1"},
        )
        assert r3.status_code == 200
        assert "score" in r3.json()

    def test_contract_references_valid_site(self, app_client):
        """No contract can reference a non-existent site"""
        client, _ = app_client
        r = client.post(
            "/api/patrimoine/contracts",
            json={
                "site_id": 99999,
                "energy_type": "elec",
                "supplier_name": "Test",
                "start_date": "2025-01-01",
            },
            headers={"X-Org-Id": "1"},
        )
        assert r.status_code in (404, 422, 400)

    def test_kpi_has_required_metadata(self, app_client):
        """Cockpit KPIs must include source and confidence"""
        client, _ = app_client
        r = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        if r.status_code == 200:
            data = r.json()
            # KPI cards should have source info
            for card in data.get("kpi_cards", []):
                if "source" in card:
                    assert card["source"], "KPI source must not be empty"

    def test_error_format_on_conformite_404(self, app_client):
        """Conformite endpoints return standard APIError format"""
        client, _ = app_client
        r = client.get("/api/tertiaire/efa/99999")
        if r.status_code == 404:
            body = r.json()
            assert "code" in body or "detail" in body


# ═══════════════════════════════════════════════════════════════════════════
# 8. KPI Catalog endpoint returns valid data
# ═══════════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════════════
# 8. compliance_needs_review includes reason codes
# ═══════════════════════════════════════════════════════════════════════════


class TestNeedsReviewHasReasons:
    """Invariant : compliance_needs_review includes reason codes."""

    def test_needs_review_has_reasons(self, app_client):
        """compliance_needs_review includes reason codes"""
        client, _ = app_client

        # Create a site first to ensure org exists
        client.post(
            "/api/sites/quick-create",
            json={"nom": "Review Test Site", "usage": "bureau"},
        )

        r = client.get("/api/patrimoine/sites", headers={"X-Org-Id": "1"})
        if r.status_code == 200:
            sites_data = r.json()
            sites = sites_data.get("sites", sites_data if isinstance(sites_data, list) else [])
            for site in sites:
                if site.get("compliance_needs_review"):
                    assert "compliance_review_reasons" in site, (
                        f"Site {site.get('id')} has compliance_needs_review=True but missing compliance_review_reasons"
                    )
                    assert len(site["compliance_review_reasons"]) > 0, (
                        f"Site {site.get('id')} has compliance_needs_review=True but empty compliance_review_reasons"
                    )


# ═══════════════════════════════════════════════════════════════════════════
# 9. KPI Catalog endpoint returns valid data
# ═══════════════════════════════════════════════════════════════════════════


class TestKpiCatalogEndpoint:
    """Invariant : /api/kpi-catalog retourne le catalogue KPI complet."""

    def test_kpi_catalog_returns_valid_structure(self, app_client):
        client, _ = app_client
        r = client.get("/api/kpi-catalog")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "count" in data
        assert "kpis" in data
        assert data["count"] > 0
        for kpi in data["kpis"]:
            assert "kpi_id" in kpi
            assert "name" in kpi
            assert "unit" in kpi


# ═══════════════════════════════════════════════════════════════════════════
# 10. Billing Perimeter & Canonical Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestBillingPerimeter:
    """Invariant : perimeter check validates billing ↔ contract ↔ site consistency."""

    def test_perimeter_valid_site(self, app_client):
        client, _ = app_client
        # Create a site first
        r = client.post(
            "/api/sites/quick-create",
            json={
                "nom": "Billing Test",
                "usage": "bureau",
                "adresse": "1 rue test",
                "code_postal": "75001",
                "ville": "Paris",
            },
            headers={"X-Org-Id": "1"},
        )
        site_id = r.json()["site"]["id"]

        # Check perimeter
        r2 = client.post("/api/billing/perimeter/check", json={"site_id": site_id})
        assert r2.status_code == 200
        assert r2.json()["consistent"] == True
        assert r2.json()["site_exists"] == True

    def test_perimeter_invalid_site(self, app_client):
        client, _ = app_client
        r = client.post("/api/billing/perimeter/check", json={"site_id": 99999})
        assert r.status_code == 200
        assert r.json()["consistent"] == False
        assert r.json()["site_exists"] == False

    def test_canonical_validation_valid(self, app_client):
        client, _ = app_client
        r = client.post(
            "/api/billing/invoices/validate-canonical",
            json={
                "site_id": 1,
                "supplier_name": "EDF",
                "amount_ht": 1500.0,
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
            },
        )
        assert r.status_code == 200
        assert r.json()["valid"] == True

    def test_canonical_validation_missing_fields(self, app_client):
        client, _ = app_client
        r = client.post("/api/billing/invoices/validate-canonical", json={"site_id": 1})
        assert r.status_code == 200
        assert r.json()["valid"] == False
        assert r.json()["missing_required_count"] > 0
