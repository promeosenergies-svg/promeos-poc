"""
PROMEOS - Tests Sprint 10.1: Audit Report PDF
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models import (
    Base, Site, Organisation, EntiteJuridique, Portefeuille,
    ComplianceFinding, ConsumptionInsight, BillingInsight,
    ActionItem, ActionSyncBatch,
    ActionSourceType, ActionStatus, InsightStatus,
    TypeSite,
)
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


def _create_org_site(db_session, site_name="Site Test"):
    """Create org + entite + portefeuille + site."""
    org = Organisation(nom="Test Corp", type_client="bureau", actif=True)
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="Test Corp", siren="123456789")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="Principal")
    db_session.add(pf)
    db_session.flush()

    site = Site(
        portefeuille_id=pf.id,
        nom=site_name,
        type=TypeSite.BUREAU,
        surface_m2=2000,
        actif=True,
    )
    db_session.add(site)
    db_session.flush()
    return org, site


def _create_compliance_finding(db_session, site_id, rule_id="TEST_RULE", status="NOK",
                                severity="high", actions_json=None):
    f = ComplianceFinding(
        site_id=site_id,
        regulation="test_regulation",
        rule_id=rule_id,
        status=status,
        severity=severity,
        evidence="Test evidence for compliance",
        recommended_actions_json=actions_json or json.dumps(["Fix issue A", "Fix issue B"]),
        insight_status=InsightStatus.OPEN,
    )
    db_session.add(f)
    db_session.flush()
    return f


def _create_consumption_insight(db_session, site_id, loss_eur=5000):
    ins = ConsumptionInsight(
        site_id=site_id,
        type="hors_horaires",
        severity="medium",
        message="Consommation hors horaires detectee",
        estimated_loss_eur=loss_eur,
        recommended_actions_json=json.dumps([
            {"title": "Programmer arret CVC", "rationale": "CVC actif la nuit", "expected_gain_eur": 3000},
        ]),
    )
    db_session.add(ins)
    db_session.flush()
    return ins


def _create_billing_insight(db_session, site_id, loss_eur=2000):
    ins = BillingInsight(
        site_id=site_id,
        type="tarif_anomaly",
        severity="high",
        message="Ecart tarifaire detecte",
        estimated_loss_eur=loss_eur,
        recommended_actions_json=json.dumps(["Verifier le contrat"]),
        insight_status=InsightStatus.OPEN,
    )
    db_session.add(ins)
    db_session.flush()
    return ins


def _seed_full_demo(db_session):
    """Create a full set of demo data for report testing."""
    org, site = _create_org_site(db_session, "Site Demo Alpha")
    # Additional sites
    sites = [site]
    for name in ["Site Demo Beta", "Site Demo Gamma"]:
        pf_id = site.portefeuille_id
        s = Site(portefeuille_id=pf_id, nom=name, type=TypeSite.MAGASIN, surface_m2=3000, actif=True)
        db_session.add(s)
        db_session.flush()
        sites.append(s)

    # Compliance findings
    for s in sites:
        _create_compliance_finding(db_session, s.id, rule_id=f"RULE_{s.id}", severity="high")
        _create_compliance_finding(db_session, s.id, rule_id=f"RULE_OK_{s.id}", status="OK", severity="low")

    # Consumption insights
    for s in sites[:2]:
        _create_consumption_insight(db_session, s.id, loss_eur=5000 + s.id * 1000)

    # Billing insights
    for s in sites[:2]:
        _create_billing_insight(db_session, s.id, loss_eur=2000 + s.id * 500)

    # Sync actions
    from services.action_hub_service import sync_actions
    db_session.commit()
    sync_actions(db_session, org.id, triggered_by="test")

    return org, sites


# ========================================
# Test Audit JSON
# ========================================

class TestAuditJSON:
    def test_audit_json_returns_data(self, client, db_session):
        """GET /api/reports/audit.json should return structured data."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.json?org_id={org.id}")
        assert r.status_code == 200
        data = r.json()

        assert "organisation" in data
        assert data["organisation"]["nom"] == "Test Corp"
        assert "synthese" in data
        assert "compliance" in data
        assert "consumption" in data
        assert "billing" in data
        assert "actions" in data

    def test_audit_json_compliance_section(self, client, db_session):
        """Compliance section should have findings counts."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.json?org_id={org.id}")
        data = r.json()
        comp = data["compliance"]
        assert comp["total_findings"] > 0
        assert comp["nok"] > 0
        assert comp["ok"] > 0
        assert "top_findings" in comp

    def test_audit_json_consumption_section(self, client, db_session):
        """Consumption section should have insights and losses."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.json?org_id={org.id}")
        data = r.json()
        conso = data["consumption"]
        assert conso["total_insights"] > 0
        assert conso["total_loss_eur"] > 0

    def test_audit_json_actions_section(self, client, db_session):
        """Actions section should reflect synced actions."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.json?org_id={org.id}")
        data = r.json()
        act = data["actions"]
        assert act["total"] > 0
        assert act["open"] > 0
        assert "by_source" in act
        assert "top_actions" in act

    def test_audit_json_confidence(self, client, db_session):
        """Synthese should include a confidence flag."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.json?org_id={org.id}")
        data = r.json()
        assert data["synthese"]["confidence"] in ("low", "medium", "high")

    def test_audit_json_no_org(self, client, db_session):
        """Audit without data should return 400."""
        r = client.get("/api/reports/audit.json?org_id=99999")
        assert r.status_code == 400


# ========================================
# Test Audit PDF
# ========================================

class TestAuditPDF:
    def test_pdf_returns_bytes(self, client, db_session):
        """GET /api/reports/audit.pdf should return application/pdf."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.pdf?org_id={org.id}")
        assert r.status_code == 200
        assert "application/pdf" in r.headers["content-type"]
        # PDF starts with %PDF
        assert r.content[:5] == b"%PDF-"

    def test_pdf_has_content_disposition(self, client, db_session):
        """PDF response should have Content-Disposition header."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.pdf?org_id={org.id}")
        assert r.status_code == 200
        assert "content-disposition" in r.headers
        assert "audit_" in r.headers["content-disposition"]

    def test_pdf_multi_page(self, client, db_session):
        """Generated PDF should be multi-page (> 3 KB at least)."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        r = client.get(f"/api/reports/audit.pdf?org_id={org.id}")
        assert r.status_code == 200
        assert len(r.content) > 3000  # Multi-page PDF is always > 3KB

    def test_pdf_no_org(self, client, db_session):
        """PDF without org should return 400."""
        r = client.get("/api/reports/audit.pdf?org_id=99999")
        assert r.status_code == 400


# ========================================
# Test Build Report Data (service)
# ========================================

class TestBuildReportData:
    def test_build_data_empty_org(self, db_session):
        """build_audit_report_data with no org returns error."""
        from services.audit_report_service import build_audit_report_data
        data = build_audit_report_data(db_session, org_id=99999)
        assert "error" in data

    def test_build_data_with_data(self, db_session):
        """build_audit_report_data returns all sections."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        from services.audit_report_service import build_audit_report_data
        data = build_audit_report_data(db_session, org_id=org.id)
        assert "error" not in data
        assert data["organisation"]["total_sites"] > 0
        assert data["compliance"]["total_findings"] > 0
        assert data["actions"]["total"] > 0

    def test_render_pdf_produces_valid_pdf(self, db_session):
        """render_audit_pdf returns valid PDF bytes."""
        org, sites = _seed_full_demo(db_session)
        db_session.commit()

        from services.audit_report_service import build_audit_report_data, render_audit_pdf
        data = build_audit_report_data(db_session, org_id=org.id)
        pdf_bytes = render_audit_pdf(data)

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 1000

    def test_confidence_high(self, db_session):
        """Confidence should be high with sufficient data."""
        from services.audit_report_service import _compute_confidence
        assert _compute_confidence(10, 5, 5) == "high"

    def test_confidence_low(self, db_session):
        """Confidence should be low with little data."""
        from services.audit_report_service import _compute_confidence
        assert _compute_confidence(0, 0, 0) == "low"

    def test_confidence_medium(self, db_session):
        """Confidence should be medium with moderate data."""
        from services.audit_report_service import _compute_confidence
        assert _compute_confidence(10, 5, 0) == "medium"
