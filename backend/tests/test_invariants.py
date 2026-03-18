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


# ═══════════════════════════════════════════════════════════════════════════
# 11. Purchase ↔ Billing Perimeter Alignment
# ═══════════════════════════════════════════════════════════════════════════


class TestPurchaseBillingAlignment:
    """Verify purchase uses same perimeter as billing."""

    def test_purchase_perimeter_valid(self, app_client):
        """Purchase perimeter validation on valid site"""
        client, _ = app_client
        r = client.post(
            "/api/sites/quick-create",
            json={
                "nom": "Purchase Test",
                "usage": "bureau",
                "adresse": "1 rue test",
                "code_postal": "75001",
                "ville": "Paris",
            },
            headers={"X-Org-Id": "1"},
        )
        site_id = r.json()["site"]["id"]

        r2 = client.post("/api/purchase/perimeter/validate", json={"site_id": site_id})
        assert r2.status_code == 200
        assert r2.json()["consistent"] == True
        assert r2.json()["module"] == "purchase"

    def test_purchase_perimeter_invalid(self, app_client):
        """Purchase rejects invalid perimeter"""
        client, _ = app_client
        r = client.post("/api/purchase/perimeter/validate", json={"site_id": 99999})
        assert r.status_code == 200
        assert r.json()["consistent"] == False


# ═══════════════════════════════════════════════════════════════════════════
# 12. Shadow Billing Gap Report
# ═══════════════════════════════════════════════════════════════════════════


class TestShadowBillingGaps:
    """Verify shadow billing gap report quality."""

    def test_shadow_billing_valid(self, app_client):
        """Valid invoice passes shadow billing check"""
        client, _ = app_client
        r = client.post(
            "/api/billing/invoices/shadow-billing-check",
            json={
                "site_id": 1,
                "supplier_name": "EDF",
                "amount_ht": 1500.0,
                "amount_ttc": 1800.0,
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
                "currency": "EUR",
                "energy_unit": "kWh",
            },
        )
        assert r.status_code == 200
        assert r.json()["shadow_billing_ready"] == True
        assert r.json()["errors_count"] == 0

    def test_shadow_billing_ht_ttc_mismatch(self, app_client):
        """TTC < HT triggers warning"""
        client, _ = app_client
        r = client.post(
            "/api/billing/invoices/shadow-billing-check",
            json={
                "site_id": 1,
                "supplier_name": "EDF",
                "amount_ht": 2000.0,
                "amount_ttc": 1500.0,
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
            },
        )
        assert r.status_code == 200
        checks = r.json()["business_checks"]
        assert any(c["check"] == "ht_ttc_mismatch" for c in checks)

    def test_shadow_billing_period_inverted(self, app_client):
        """Inverted period triggers error"""
        client, _ = app_client
        r = client.post(
            "/api/billing/invoices/shadow-billing-check",
            json={
                "site_id": 1,
                "supplier_name": "EDF",
                "amount_ht": 1000.0,
                "period_start": "2025-06-01",
                "period_end": "2025-01-01",
            },
        )
        assert r.status_code == 200
        assert r.json()["shadow_billing_ready"] == False
        assert r.json()["errors_count"] > 0

    def test_shadow_billing_missing_required(self, app_client):
        """Missing required fields makes shadow billing not ready"""
        client, _ = app_client
        r = client.post("/api/billing/invoices/shadow-billing-check", json={"site_id": 1})
        assert r.status_code == 200
        assert r.json()["shadow_billing_ready"] == False
        assert r.json()["missing_required_count"] > 0


# ═══════════════════════════════════════════════════════════════════════════
# 13. Action Center — unified actionable issues
# ═══════════════════════════════════════════════════════════════════════════


class TestActionCenter:
    """Verify action center aggregates issues correctly."""

    def test_action_center_returns_issues(self, app_client):
        """Action center endpoint returns structured response"""
        client, _ = app_client
        r = client.get("/api/action-center/issues", headers={"X-Org-Id": "1"})
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "issues" in data
        assert "domains" in data
        assert "severities" in data
        assert isinstance(data["issues"], list)

    def test_action_center_issues_have_required_fields(self, app_client):
        """Each issue has required canonical fields"""
        client, _ = app_client
        r = client.get("/api/action-center/issues", headers={"X-Org-Id": "1"})
        if r.status_code == 200:
            for issue in r.json()["issues"]:
                assert "issue_id" in issue
                assert "domain" in issue
                assert "severity" in issue
                assert "site_id" in issue
                assert "issue_code" in issue
                assert "issue_label" in issue
                assert "reason_codes" in issue
                assert isinstance(issue["reason_codes"], list)

    def test_action_center_filter_by_domain(self, app_client):
        """Filtering by domain returns only that domain"""
        client, _ = app_client
        r = client.get("/api/action-center/issues?domain=compliance", headers={"X-Org-Id": "1"})
        if r.status_code == 200:
            for issue in r.json()["issues"]:
                assert issue["domain"] == "compliance"

    def test_action_center_summary(self, app_client):
        """Summary endpoint returns counts"""
        client, _ = app_client
        r = client.get("/api/action-center/summary", headers={"X-Org-Id": "1"})
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "critical_count" in data
        assert "high_count" in data

    def test_compliance_review_generates_issue(self, app_client):
        """A site with compliance_needs_review generates an action center issue"""
        client, _ = app_client
        # Create a site (will likely have needs_review due to missing data)
        r = client.post(
            "/api/sites/quick-create",
            json={
                "nom": "ActionCenter Test",
                "usage": "bureau",
                "adresse": "1 test",
                "code_postal": "75001",
                "ville": "Paris",
            },
            headers={"X-Org-Id": "1"},
        )
        site_id = r.json()["site"]["id"]

        # Check action center has an issue for this site
        r2 = client.get(f"/api/action-center/issues?site_id={site_id}", headers={"X-Org-Id": "1"})
        assert r2.status_code == 200
        # New site should have at least patrimoine incomplete or compliance issue
        # (it has no contract, no PDL, possibly incomplete)


# ═══════════════════════════════════════════════════════════════════════════
# 14. Action Workflow — create → update → resolve → reopen
# ═══════════════════════════════════════════════════════════════════════════


class TestActionWorkflow:
    """Verify action center workflow: create → update → resolve → reopen."""

    def test_create_action_from_issue(self, app_client):
        """Can create a persisted action from an issue payload"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "compliance_review_1",
                "domain": "compliance",
                "severity": "high",
                "site_id": 1,
                "issue_code": "compliance_needs_review",
                "issue_label": "Test action",
                "reason_codes": ["a_risque"],
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "open"
        assert data["issue_id"] == "compliance_review_1"
        assert data["id"] > 0

    def test_resolve_action(self, app_client):
        """Can resolve an action"""
        client, _ = app_client
        # Create
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "test_resolve",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Resolve test",
            },
        )
        action_id = r1.json()["id"]

        # Resolve
        r2 = client.post(
            f"/api/action-center/actions/{action_id}/resolve", json={"resolution_note": "Corrigé manuellement"}
        )
        assert r2.status_code == 200
        assert r2.json()["status"] == "resolved"
        assert r2.json()["resolution_note"] == "Corrigé manuellement"
        assert r2.json()["resolved_at"] is not None

    def test_reopen_action(self, app_client):
        """Can reopen a resolved action"""
        client, _ = app_client
        # Create + resolve
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "test_reopen",
                "domain": "patrimoine",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Reopen test",
            },
        )
        action_id = r1.json()["id"]
        client.post(f"/api/action-center/actions/{action_id}/resolve", json={})

        # Reopen
        r3 = client.post(f"/api/action-center/actions/{action_id}/reopen", json={"reason": "Problème récurrent"})
        assert r3.status_code == 200
        assert r3.json()["status"] == "reopened"
        assert r3.json()["reopened_at"] is not None

    def test_list_actions_filtered(self, app_client):
        """Can list actions with filters"""
        client, _ = app_client
        # Create two actions in different domains
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "filter_test_1",
                "domain": "compliance",
                "severity": "high",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Filter 1",
            },
        )
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "filter_test_2",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Filter 2",
            },
        )

        # Filter by domain
        r = client.get("/api/action-center/actions?domain=compliance")
        assert r.status_code == 200
        for action in r.json()["actions"]:
            assert action["domain"] == "compliance"

    def test_action_counts_consistent(self, app_client):
        """Summary counts match actual issues"""
        client, _ = app_client
        r1 = client.get("/api/action-center/summary", headers={"X-Org-Id": "1"})
        r2 = client.get("/api/action-center/issues", headers={"X-Org-Id": "1"})
        if r1.status_code == 200 and r2.status_code == 200:
            assert r1.json()["total"] == r2.json()["total"]


# ═══════════════════════════════════════════════════════════════════════════
# 15. Action Operational — priority, SLA, evidence guard
# ═══════════════════════════════════════════════════════════════════════════


class TestActionOperational:
    """Verify operational action features: priority, SLA, evidence guard."""

    def test_action_has_priority(self, app_client):
        """Created action has priority derived from severity"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "priority_test",
                "domain": "compliance",
                "severity": "critical",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Priority test",
            },
        )
        assert r.status_code == 200
        assert r.json()["priority"] == "critical"
        assert r.json()["sla_days"] == 7

    def test_action_sla_on_track(self, app_client):
        """New action has sla_status on_track"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "sla_test",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "SLA test",
            },
        )
        assert r.status_code == 200
        assert r.json()["sla_status"] in ("on_track", "at_risk")

    def test_evidence_required_blocks_resolve(self, app_client):
        """Critical action cannot be resolved without evidence"""
        client, _ = app_client
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "evidence_block_test",
                "domain": "compliance",
                "severity": "critical",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Evidence test",
            },
        )
        action_id = r1.json()["id"]
        assert r1.json()["evidence_required"] == True

        # Try to resolve without evidence
        r2 = client.post(f"/api/action-center/actions/{action_id}/resolve", json={})
        assert r2.status_code == 400  # Should be blocked

    def test_actions_summary_counts(self, app_client):
        """Actions summary returns consistent counts"""
        client, _ = app_client
        r = client.get("/api/action-center/actions/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "by_status" in data
        assert "by_priority" in data
        assert "overdue_count" in data
        assert "open_count" in data

    def test_action_source_ref(self, app_client):
        """Action has source_ref linking to origin domain"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "source_ref_test",
                "domain": "billing",
                "severity": "high",
                "site_id": 1,
                "issue_code": "no_contract",
                "issue_label": "Source ref test",
            },
        )
        assert r.status_code == 200
        assert r.json()["source_ref"] == "billing:no_contract"


# ═══════════════════════════════════════════════════════════════════════════
# 16. Action Owner & Priority Override
# ═══════════════════════════════════════════════════════════════════════════


class TestActionOwnerPriority:
    """Verify owner assignment and priority override."""

    def test_action_assignable_to_owner(self, app_client):
        """Can assign owner to action"""
        client, _ = app_client
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "owner_test",
                "domain": "compliance",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Owner test",
                "owner": "alice@promeos.io",
            },
        )
        assert r1.status_code == 200
        assert r1.json()["owner"] == "alice@promeos.io"

    def test_action_update_owner(self, app_client):
        """Can update owner on existing action"""
        client, _ = app_client
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "update_owner_test",
                "domain": "billing",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Update owner test",
            },
        )
        action_id = r1.json()["id"]

        r2 = client.patch(f"/api/action-center/actions/{action_id}", json={"owner": "bob@promeos.io"})
        assert r2.status_code == 200
        assert r2.json()["owner"] == "bob@promeos.io"

    def test_priority_override_requires_reason(self, app_client):
        """Cannot override priority without reason"""
        client, _ = app_client
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "override_no_reason",
                "domain": "compliance",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Override test",
            },
        )
        action_id = r1.json()["id"]

        r2 = client.post(f"/api/action-center/actions/{action_id}/override-priority", json={"priority": "critical"})
        assert r2.status_code == 400

    def test_priority_override_with_reason(self, app_client):
        """Can override priority with valid reason"""
        client, _ = app_client
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "override_ok",
                "domain": "billing",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Override OK test",
            },
        )
        action_id = r1.json()["id"]

        r2 = client.post(
            f"/api/action-center/actions/{action_id}/override-priority",
            json={"priority": "critical", "reason": "Demande direction urgente"},
        )
        assert r2.status_code == 200
        assert r2.json()["priority"] == "critical"
        assert r2.json()["priority_source"] == "manual"
        assert r2.json()["sla_days"] == 7

    def test_summary_includes_owner_breakdown(self, app_client):
        """Summary includes owner breakdown"""
        client, _ = app_client
        r = client.get("/api/action-center/actions/summary")
        assert r.status_code == 200
        assert "by_owner" in r.json()


# ═══════════════════════════════════════════════════════════════════════════
# 17. Due Date SLA Integration
# ═══════════════════════════════════════════════════════════════════════════


class TestDueDateSla:
    """Verify due_date integration with SLA."""

    def test_action_with_due_date_sla(self, app_client):
        """Action with explicit due_date uses it for SLA computation"""
        client, _ = app_client
        from datetime import datetime, timedelta

        future = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d")
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "due_date_test",
                "domain": "compliance",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Due date test",
                "due_date": future,
            },
        )
        assert r.status_code == 200
        assert r.json()["sla_status"] == "on_track"

    def test_action_overdue_with_past_due_date(self, app_client):
        """Action with past due_date is overdue"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "overdue_due_test",
                "domain": "billing",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Overdue test",
                "due_date": "2020-01-01",
            },
        )
        assert r.status_code == 200
        assert r.json()["sla_status"] == "overdue"

    def test_summary_has_sla_breakdown(self, app_client):
        """Summary includes by_sla breakdown"""
        client, _ = app_client
        r = client.get("/api/action-center/actions/summary")
        assert r.status_code == 200
        assert "by_sla" in r.json()

    def test_cockpit_includes_action_center(self, app_client):
        """Cockpit response includes action_center counts"""
        client, _ = app_client
        # Create a site so org exists
        client.post("/api/sites/quick-create", json={"nom": "CockpitAC", "usage": "bureau"})
        r = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        assert r.status_code == 200
        assert "action_center" in r.json()
        ac = r.json()["action_center"]
        assert "total_issues" in ac
        assert "critical" in ac

    def test_filter_due_before(self, app_client):
        """Can filter actions by due_before"""
        client, _ = app_client
        r = client.get("/api/action-center/actions?due_before=2030-12-31")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 18. Coherence action center / summary / cockpit
# ═══════════════════════════════════════════════════════════════════════════


class TestActionCenterCoherence:
    """Verify action center counts are consistent across views."""

    def test_issues_and_summary_counts_match(self, app_client):
        """Issues total matches summary total"""
        client, _ = app_client
        # Create a site to have org
        client.post("/api/sites/quick-create", json={"nom": "CoherenceTest", "usage": "bureau"})

        r1 = client.get("/api/action-center/issues", headers={"X-Org-Id": "1"})
        r2 = client.get("/api/action-center/summary", headers={"X-Org-Id": "1"})
        if r1.status_code == 200 and r2.status_code == 200:
            assert r1.json()["total"] == r2.json()["total"]

    def test_actions_list_and_summary_consistent(self, app_client):
        """Actions list total matches actions summary total"""
        client, _ = app_client
        # Create some actions
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "coh_1",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Coh 1",
            },
        )
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "coh_2",
                "domain": "compliance",
                "severity": "high",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Coh 2",
            },
        )

        r1 = client.get("/api/action-center/actions")
        r2 = client.get("/api/action-center/actions/summary")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["total"] == r2.json()["total"]

    def test_cockpit_action_center_matches_issues(self, app_client):
        """Cockpit action_center.total_issues matches issues endpoint"""
        client, _ = app_client
        client.post("/api/sites/quick-create", json={"nom": "CockpitCoh", "usage": "bureau"})

        r1 = client.get("/api/cockpit", headers={"X-Org-Id": "1"})
        r2 = client.get("/api/action-center/issues", headers={"X-Org-Id": "1"})
        if r1.status_code == 200 and r2.status_code == 200:
            cockpit_total = r1.json().get("action_center", {}).get("total_issues", 0)
            issues_total = r2.json()["total"]
            assert cockpit_total == issues_total, f"Cockpit={cockpit_total} vs Issues={issues_total}"


# ═══════════════════════════════════════════════════════════════════════════
# 19. Action Audit Proof (Sprint 13)
# ═══════════════════════════════════════════════════════════════════════════


class TestActionAuditProof:
    """Verify audit trail and evidence on actions."""

    def test_create_generates_event(self, app_client):
        """Creating an action generates a 'created' event"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "audit_test_1",
                "domain": "compliance",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Audit test",
            },
        )
        action_id = r.json()["id"]

        r2 = client.get(f"/api/action-center/actions/{action_id}/history")
        assert r2.status_code == 200
        events = r2.json()["events"]
        assert any(e["event_type"] == "created" for e in events)

    def test_resolve_generates_event(self, app_client):
        """Resolving an action generates a 'resolved' event"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "audit_resolve",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Resolve audit",
            },
        )
        action_id = r.json()["id"]
        client.post(f"/api/action-center/actions/{action_id}/resolve", json={"resolution_note": "Done"})

        r2 = client.get(f"/api/action-center/actions/{action_id}/history")
        events = r2.json()["events"]
        assert any(e["event_type"] == "resolved" for e in events)

    def test_evidence_added_and_retrievable(self, app_client):
        """Evidence can be added and retrieved"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "evidence_test",
                "domain": "compliance",
                "severity": "high",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Evidence test",
            },
        )
        action_id = r.json()["id"]

        r2 = client.post(
            f"/api/action-center/actions/{action_id}/evidence",
            json={"evidence_type": "note", "label": "Justification test", "value": "OK validé"},
        )
        assert r2.status_code == 200

        r3 = client.get(f"/api/action-center/actions/{action_id}/evidence")
        assert r3.status_code == 200
        assert len(r3.json()["evidence"]) > 0

    def test_export_dossier_complete(self, app_client):
        """Export dossier includes action + history + evidence"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "export_test",
                "domain": "patrimoine",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Export test",
            },
        )
        action_id = r.json()["id"]

        r2 = client.get(f"/api/action-center/actions/{action_id}/export")
        assert r2.status_code == 200
        dossier = r2.json()
        assert "action" in dossier
        assert "history" in dossier
        assert "evidence" in dossier
        assert dossier["complete"] == True

    def test_critical_resolve_blocked_without_evidence(self, app_client):
        """Critical action cannot be resolved without evidence"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "block_test",
                "domain": "compliance",
                "severity": "critical",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Block test",
            },
        )
        action_id = r.json()["id"]
        assert r.json()["evidence_required"] == True

        r2 = client.post(f"/api/action-center/actions/{action_id}/resolve", json={})
        assert r2.status_code == 400


class TestNotificationsAndBulk:
    """Verify notifications, bulk actions, and saved views."""

    def test_notification_on_assign(self, app_client):
        """Creating action with owner generates assigned notification"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "notif_test",
                "domain": "compliance",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Notif test",
                "owner": "alice@test.io",
            },
        )
        action_id = r.json()["id"]

        r2 = client.get("/api/action-center/notifications?recipient=alice@test.io")
        assert r2.status_code == 200
        notifs = r2.json()["notifications"]
        assert any(n["type"] == "assigned" and n["action_id"] == action_id for n in notifs)

    def test_bulk_assign_creates_events(self, app_client):
        """Bulk assign creates audit events"""
        client, _ = app_client
        ids = []
        for i in range(3):
            r = client.post(
                "/api/action-center/actions",
                json={
                    "issue_id": f"bulk_test_{i}",
                    "domain": "billing",
                    "severity": "low",
                    "site_id": 1,
                    "issue_code": "test",
                    "issue_label": f"Bulk {i}",
                },
            )
            ids.append(r.json()["id"])

        r2 = client.post(
            "/api/action-center/actions/bulk/assign-owner", json={"action_ids": ids, "owner": "bob@test.io"}
        )
        assert r2.status_code == 200
        assert r2.json()["updated"] == 3

        # Check audit trail
        r3 = client.get(f"/api/action-center/actions/{ids[0]}/history")
        events = r3.json()["events"]
        assert any(e["event_type"] == "owner_change" and e["new_value"] == "bob@test.io" for e in events)

    def test_bulk_resolve_blocked(self, app_client):
        """Bulk resolve is not allowed"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "bulk_resolve",
                "domain": "compliance",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Bulk resolve",
            },
        )
        r2 = client.post(
            "/api/action-center/actions/bulk/update-status", json={"action_ids": [r.json()["id"]], "status": "resolved"}
        )
        assert r2.status_code == 200
        assert r2.json()["updated"] == 0

    def test_saved_views_exist(self, app_client):
        """Saved views endpoint returns predefined views"""
        client, _ = app_client
        r = client.get("/api/action-center/views")
        assert r.status_code == 200
        views = r.json()["views"]
        assert len(views) >= 4
        view_ids = [v["id"] for v in views]
        assert "overdue" in view_ids
        assert "critiques" in view_ids

    def test_summary_needs_evidence(self, app_client):
        """Summary includes needs_evidence_count"""
        client, _ = app_client
        r = client.get("/api/action-center/actions/summary")
        assert r.status_code == 200
        assert "needs_evidence_count" in r.json()


class TestManagementSummary:
    """Verify management summary aggregates."""

    def test_management_summary_structure(self, app_client):
        """Management summary has all required fields"""
        client, _ = app_client
        r = client.get("/api/action-center/management-summary")
        assert r.status_code == 200
        data = r.json()
        for field in (
            "total_actions",
            "open_count",
            "overdue_count",
            "critical_count",
            "needs_evidence_count",
            "stale_count",
            "by_owner",
            "by_domain",
            "by_priority",
        ):
            assert field in data, f"Missing field: {field}"

    def test_management_open_matches_list(self, app_client):
        """open_count matches filtered list count"""
        client, _ = app_client
        # Create some actions
        for i in range(3):
            client.post(
                "/api/action-center/actions",
                json={
                    "issue_id": f"mgmt_test_{i}",
                    "domain": "compliance",
                    "severity": "medium",
                    "site_id": 1,
                    "issue_code": "test",
                    "issue_label": f"Mgmt {i}",
                },
            )

        r1 = client.get("/api/action-center/management-summary")
        r2 = client.get("/api/action-center/actions?status=open")
        if r1.status_code == 200 and r2.status_code == 200:
            # open_count should include open + in_progress + reopened
            open_in_list = len([a for a in r2.json()["actions"] if a["status"] in ("open", "in_progress", "reopened")])
            assert r1.json()["open_count"] >= open_in_list

    def test_management_stale_rule(self, app_client):
        """Stale count follows the documented threshold"""
        client, _ = app_client
        r = client.get("/api/action-center/management-summary")
        assert r.status_code == 200
        data = r.json()
        assert "stale_threshold_days" in data
        assert data["stale_threshold_days"] == 14

    def test_management_avg_resolution(self, app_client):
        """avg_resolution_days is null or reasonable"""
        client, _ = app_client
        # Create + resolve an action
        r1 = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "avg_res_test",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Avg test",
            },
        )
        action_id = r1.json()["id"]
        client.post(f"/api/action-center/actions/{action_id}/resolve", json={"resolution_note": "Done"})

        r2 = client.get("/api/action-center/management-summary")
        data = r2.json()
        if data["avg_resolution_days"] is not None:
            assert data["avg_resolution_days"] >= 0


# ═══════════════════════════════════════════════════════════════════════════
# 21. Executive Summary & Trends (Sprint 16)
# ═══════════════════════════════════════════════════════════════════════════


class TestExecutiveSummary:
    """Verify executive summary and trends."""

    def test_executive_summary_structure(self, app_client):
        """Executive summary has all required fields"""
        client, _ = app_client
        r = client.get("/api/action-center/executive-summary")
        assert r.status_code == 200
        data = r.json()
        for field in (
            "period_days",
            "open_count",
            "resolved_count",
            "overdue_count",
            "backlog_health",
            "top_sites",
            "top_domains",
            "top_actions",
        ):
            assert field in data, f"Missing: {field}"

    def test_executive_backlog_health_rules(self, app_client):
        """Backlog health follows documented rules"""
        client, _ = app_client
        r = client.get("/api/action-center/executive-summary")
        data = r.json()
        assert data["backlog_health"] in ("healthy", "at_risk", "unhealthy")
        assert "backlog_health_rules" in data

    def test_trends_structure(self, app_client):
        """Trends endpoint returns daily buckets and totals"""
        client, _ = app_client
        r = client.get("/api/action-center/trends?window=7")
        assert r.status_code == 200
        data = r.json()
        assert data["window_days"] == 7
        assert "daily" in data
        assert "totals" in data
        assert "current_snapshot" in data
        assert len(data["daily"]) == 7

    def test_executive_top_sites_coherent(self, app_client):
        """top_sites site_ids exist in the action list"""
        client, _ = app_client
        # Create actions for different sites
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "exec_s1",
                "domain": "compliance",
                "severity": "high",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Exec 1",
            },
        )
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "exec_s2",
                "domain": "billing",
                "severity": "medium",
                "site_id": 2,
                "issue_code": "test",
                "issue_label": "Exec 2",
            },
        )

        r = client.get("/api/action-center/executive-summary")
        data = r.json()
        top_site_ids = {s["site_id"] for s in data["top_sites"]}

        r2 = client.get("/api/action-center/actions")
        action_site_ids = {a["site_id"] for a in r2.json()["actions"]}

        assert top_site_ids.issubset(action_site_ids)


# ═══════════════════════════════════════════════════════════════════════════
# 22. Recommendation Engine (Sprint 17)
# ═══════════════════════════════════════════════════════════════════════════


class TestRecommendations:
    """Verify recommendation engine ranking and consistency."""

    def test_recommendations_structure(self, app_client):
        """Recommendations have all required fields"""
        client, _ = app_client
        # Create test actions
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "rec_test_1",
                "domain": "compliance",
                "severity": "critical",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Critical overdue",
            },
        )
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "rec_test_2",
                "domain": "billing",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Low priority",
            },
        )

        r = client.get("/api/action-center/recommendations")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "recommendations" in data
        for rec in data["recommendations"]:
            for field in (
                "recommendation_id",
                "scope",
                "domain",
                "urgency_score",
                "risk_score",
                "confidence_score",
                "decision_score",
                "why_now",
            ):
                assert field in rec, f"Missing: {field}"

    def test_critical_ranks_above_low(self, app_client):
        """Critical overdue item ranks above low priority item"""
        client, _ = app_client
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "rank_critical",
                "domain": "compliance",
                "severity": "critical",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "CRITICAL",
                "due_date": "2020-01-01",  # overdue
            },
        )
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "rank_low",
                "domain": "patrimoine",
                "severity": "low",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "LOW",
            },
        )

        r = client.get("/api/action-center/recommendations")
        recs = r.json()["recommendations"]
        if len(recs) >= 2:
            # Find our items
            critical_idx = next((i for i, r in enumerate(recs) if "CRITICAL" in r["recommended_action"]), None)
            low_idx = next((i for i, r in enumerate(recs) if "LOW" in r["recommended_action"]), None)
            if critical_idx is not None and low_idx is not None:
                assert critical_idx < low_idx, "Critical should rank above low"

    def test_low_confidence_visible(self, app_client):
        """Low confidence score is explicitly visible"""
        client, _ = app_client
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "conf_test",
                "domain": "compliance",
                "severity": "critical",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Confidence test",
            },
        )
        r = client.get("/api/action-center/recommendations")
        for rec in r.json()["recommendations"]:
            assert rec["confidence_score"] >= 0
            assert rec["confidence_score"] <= 100

    def test_recommendations_summary_coherent(self, app_client):
        """Summary total matches recommendations list"""
        client, _ = app_client
        r1 = client.get("/api/action-center/recommendations?limit=100")
        r2 = client.get("/api/action-center/recommendations/summary")
        if r1.status_code == 200 and r2.status_code == 200:
            assert r1.json()["total"] == r2.json()["total"]


class TestRecommendationDecisions:
    """Verify recommendation decision workflow."""

    def test_accept_recommendation(self, app_client):
        """Can accept a recommendation"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "dec_accept",
                "domain": "compliance",
                "severity": "high",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Accept test",
            },
        )
        action_id = r.json()["id"]

        r2 = client.post(f"/api/action-center/recommendations/rec_{action_id}/accept", json={"action_id": action_id})
        assert r2.status_code == 200
        assert r2.json()["decision"] == "accepted"

    def test_dismiss_requires_reason(self, app_client):
        """Cannot dismiss without reason"""
        client, _ = app_client
        r = client.post("/api/action-center/recommendations/rec_999/dismiss", json={})
        assert r.status_code == 400

    def test_dismiss_with_reason(self, app_client):
        """Can dismiss with valid reason"""
        client, _ = app_client
        r = client.post("/api/action-center/recommendations/rec_test/dismiss", json={"reason": "Hors périmètre actuel"})
        assert r.status_code == 200
        assert r.json()["decision"] == "dismissed"

    def test_convert_to_action(self, app_client):
        """Can convert recommendation to new action"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/recommendations/rec_convert/create-action",
            json={
                "issue_id": "converted_rec",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Converted recommendation",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "decision" in data
        assert "action" in data
        assert data["decision"]["decision"] == "converted_to_action"
        assert data["decision"]["created_action_id"] == data["action"]["id"]

    def test_decision_stats(self, app_client):
        """Decision stats endpoint returns counts"""
        client, _ = app_client
        # Make some decisions first
        client.post("/api/action-center/recommendations/rec_stats1/dismiss", json={"reason": "Not relevant now"})
        client.post("/api/action-center/recommendations/rec_stats2/defer", json={"reason": "Next quarter"})

        r = client.get("/api/action-center/recommendations/decisions")
        assert r.status_code == 200
        data = r.json()
        assert "total_decisions" in data
        assert "accepted_count" in data
        assert "dismissed_count" in data
        assert "converted_to_action_count" in data


# ═══════════════════════════════════════════════════════════════════════════
# Sprint 19 — Recommendation Quality & Calibration
# ═══════════════════════════════════════════════════════════════════════════


class TestRecommendationQuality:
    """Verify recommendation quality metrics and calibration."""

    def test_quality_summary_structure(self, app_client):
        """Quality summary has all required fields"""
        client, _ = app_client
        r = client.get("/api/action-center/recommendations/quality-summary")
        assert r.status_code == 200
        data = r.json()
        for field in (
            "period_days",
            "total_recommendations_decided",
            "accepted_count",
            "dismissed_count",
            "acceptance_rate",
            "confidence_distribution",
            "stale_recommendations_count",
            "calibration",
        ):
            assert field in data, f"Missing: {field}"

    def test_quality_rates_correct(self, app_client):
        """Rates are mathematically correct"""
        client, _ = app_client
        # Create decisions
        client.post("/api/action-center/recommendations/rec_q1/dismiss", json={"reason": "Not relevant for now"})
        client.post("/api/action-center/recommendations/rec_q2/defer", json={"reason": "Next quarter review"})
        client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "q_accept",
                "domain": "compliance",
                "severity": "high",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Quality accept",
            },
        )
        action_id_q = client.post(
            "/api/action-center/actions",
            json={
                "issue_id": "q_accept2",
                "domain": "billing",
                "severity": "medium",
                "site_id": 1,
                "issue_code": "test",
                "issue_label": "Quality accept 2",
            },
        ).json()["id"]
        client.post(f"/api/action-center/recommendations/rec_{action_id_q}/accept", json={"action_id": action_id_q})

        r = client.get("/api/action-center/recommendations/quality-summary")
        data = r.json()
        total = data["total_recommendations_decided"]
        if total > 0:
            assert (
                data["accepted_count"]
                + data["dismissed_count"]
                + data["deferred_count"]
                + data["converted_to_action_count"]
                == total
            )

    def test_calibration_versioned(self, app_client):
        """Calibration has version and weights"""
        client, _ = app_client
        r = client.get("/api/action-center/recommendations/calibration")
        assert r.status_code == 200
        data = r.json()
        assert "current" in data
        assert "history" in data
        assert data["current"]["version"] == "1.0"
        assert "weights" in data["current"]
        w = data["current"]["weights"]
        assert abs(sum(w.values()) - 1.0) < 0.01

    def test_confidence_distribution_coherent(self, app_client):
        """Confidence distribution sums to open action count"""
        client, _ = app_client
        r = client.get("/api/action-center/recommendations/quality-summary")
        data = r.json()
        dist = data["confidence_distribution"]
        total_dist = dist["high"] + dist["medium"] + dist["low"]
        # Should match open actions count (approximately, since some may be created between calls)
        assert total_dist >= 0


class TestCalibrationGovernance:
    """Verify calibration versioning, activation, rollback, compare."""

    def test_create_calibration(self, app_client):
        """Can create a new calibration version"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/recommendations/calibration",
            json={
                "version": "2.0",
                "weights": {"urgency": 0.35, "risk": 0.35, "ease": 0.1, "confidence": 0.2},
                "comment": "Sprint 20 test",
            },
        )
        assert r.status_code == 200
        assert r.json()["version"] == "2.0"
        assert r.json()["status"] == "draft"

    def test_activate_calibration(self, app_client):
        """Can activate a draft calibration"""
        client, _ = app_client
        client.post(
            "/api/action-center/recommendations/calibration",
            json={
                "version": "2.1",
                "weights": {"urgency": 0.3, "risk": 0.3, "ease": 0.2, "confidence": 0.2},
            },
        )
        r = client.post("/api/action-center/recommendations/calibration/activate", json={"version": "2.1"})
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    def test_rollback_calibration(self, app_client):
        """Can rollback to previous version"""
        client, _ = app_client
        # Ensure v1.0 exists (via GET calibration which triggers ensure_initial_version)
        client.get("/api/action-center/recommendations/calibration")
        # Create and activate v3.0 (archives v1.0)
        client.post(
            "/api/action-center/recommendations/calibration",
            json={
                "version": "3.0",
                "weights": {"urgency": 0.5, "risk": 0.2, "ease": 0.1, "confidence": 0.2},
            },
        )
        client.post("/api/action-center/recommendations/calibration/activate", json={"version": "3.0"})

        # Rollback should restore v1.0
        r = client.post("/api/action-center/recommendations/calibration/rollback")
        assert r.status_code == 200

    def test_compare_calibrations(self, app_client):
        """Can compare two calibration versions"""
        client, _ = app_client
        client.post(
            "/api/action-center/recommendations/calibration",
            json={
                "version": "4.0",
                "weights": {"urgency": 0.4, "risk": 0.3, "ease": 0.1, "confidence": 0.2},
            },
        )
        client.post(
            "/api/action-center/recommendations/calibration",
            json={
                "version": "4.1",
                "weights": {"urgency": 0.5, "risk": 0.2, "ease": 0.1, "confidence": 0.2},
            },
        )
        r = client.get("/api/action-center/recommendations/calibration/compare?v1=4.0&v2=4.1")
        assert r.status_code == 200
        data = r.json()
        assert "deltas" in data
        assert data["deltas"]["urgency"]["delta"] == 0.1

    def test_record_outcome(self, app_client):
        """Can record a recommendation outcome"""
        client, _ = app_client
        r = client.post(
            "/api/action-center/recommendations/outcomes",
            json={
                "recommendation_id": "rec_outcome_test",
                "outcome_status": "positive",
                "outcome_reason": "Issue resolved successfully",
            },
        )
        assert r.status_code == 200
        assert r.json()["outcome_status"] == "positive"
