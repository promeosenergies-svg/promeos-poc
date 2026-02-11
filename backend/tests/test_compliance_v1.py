"""
PROMEOS - Tests Sprint 4: Compliance V1 (rules engine + findings + endpoints)
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
    Base, Site, Batiment, Obligation, Evidence, ComplianceFinding,
    Organisation, EntiteJuridique, Portefeuille,
    TypeSite, TypeObligation, StatutConformite,
    TypeEvidence, StatutEvidence, OperatStatus, ParkingType,
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


def _seed(client):
    """Create org via demo seed."""
    return client.post("/api/demo/seed").json()


def _create_org_site(db_session, type_site=TypeSite.BUREAU, surface=2000,
                     operat_status=None, cvc_kw=100):
    """Helper: create org + entite + portefeuille + site + batiment."""
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
        nom="Site Test",
        type=type_site,
        surface_m2=surface,
        tertiaire_area_m2=surface if type_site == TypeSite.BUREAU else None,
        operat_status=operat_status,
        actif=True,
    )
    db_session.add(site)
    db_session.flush()

    bat = Batiment(site_id=site.id, nom="Bat principal", surface_m2=surface, cvc_power_kw=cvc_kw)
    db_session.add(bat)
    db_session.flush()

    db_session.commit()
    return org, site, bat


# ========================================
# YAML Rule Packs
# ========================================

class TestYamlRulePacks:
    def test_load_all_packs(self):
        from services.compliance_rules import load_all_packs
        packs = load_all_packs()
        assert len(packs) == 3
        regs = [p["regulation"] for p in packs]
        assert "decret_tertiaire_operat" in regs
        assert "bacs" in regs
        assert "aper" in regs

    def test_decret_tertiaire_pack_structure(self):
        from services.compliance_rules import _load_pack
        pack = _load_pack("decret_tertiaire_operat_v1.yaml")
        assert pack["version"] == "1.0"
        assert len(pack["rules"]) == 5
        rule_ids = [r["id"] for r in pack["rules"]]
        assert "DT_SCOPE" in rule_ids
        assert "DT_OPERAT" in rule_ids

    def test_bacs_pack_structure(self):
        from services.compliance_rules import _load_pack
        pack = _load_pack("decret_bacs_v1.yaml")
        assert len(pack["rules"]) == 5
        assert "thresholds" in pack
        assert pack["thresholds"]["high_power_kw"] == 290

    def test_aper_pack_structure(self):
        from services.compliance_rules import _load_pack
        pack = _load_pack("loi_aper_v1.yaml")
        assert len(pack["rules"]) == 3

    def test_rules_endpoint(self, client):
        r = client.get("/api/compliance/rules")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 3
        assert data[0]["rules_count"] >= 3


# ========================================
# ComplianceFinding model
# ========================================

class TestComplianceFindingModel:
    def test_create_finding(self, db_session):
        org, site, bat = _create_org_site(db_session)

        cf = ComplianceFinding(
            site_id=site.id,
            regulation="bacs",
            rule_id="BACS_POWER",
            status="NOK",
            severity="high",
            evidence="CVC > 290 kW sans attestation",
        )
        db_session.add(cf)
        db_session.commit()

        assert cf.id is not None
        assert cf.status == "NOK"

    def test_finding_with_actions(self, db_session):
        org, site, bat = _create_org_site(db_session)

        actions = ["Installer GTB/GTC", "Obtenir attestation"]
        cf = ComplianceFinding(
            site_id=site.id,
            regulation="bacs",
            rule_id="BACS_HIGH_DEADLINE",
            status="NOK",
            severity="critical",
            recommended_actions_json=json.dumps(actions),
        )
        db_session.add(cf)
        db_session.commit()

        loaded = json.loads(cf.recommended_actions_json)
        assert len(loaded) == 2


# ========================================
# evaluate_site service
# ========================================

class TestEvaluateSite:
    def test_evaluate_bureau_2000m2(self, db_session):
        """Bureau 2000m2 with CVC 100kW → DT in scope, BACS in scope."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(db_session, surface=2000, cvc_kw=100)

        findings = evaluate_site(db_session, site.id)
        assert len(findings) > 0

        # Should have DT findings (in scope, 2000 > 1000)
        dt_findings = [f for f in findings if f.regulation == "decret_tertiaire_operat"]
        assert len(dt_findings) >= 2  # DT_SCOPE + DT_OPERAT + ...

        # BACS findings (100 kW > 70)
        bacs_findings = [f for f in findings if f.regulation == "bacs"]
        assert len(bacs_findings) >= 2

    def test_evaluate_small_site_out_of_scope(self, db_session):
        """Small site 500m2, CVC 30kW → both DT and BACS out of scope."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(db_session, surface=500, cvc_kw=30)
        site.tertiaire_area_m2 = 500
        db_session.commit()

        findings = evaluate_site(db_session, site.id)

        dt_findings = [f for f in findings if f.regulation == "decret_tertiaire_operat"]
        assert any(f.status == "OUT_OF_SCOPE" for f in dt_findings)

        bacs_findings = [f for f in findings if f.regulation == "bacs"]
        assert any(f.status == "OUT_OF_SCOPE" for f in bacs_findings)

    def test_evaluate_operat_submitted(self, db_session):
        """Site with OPERAT submitted → DT_OPERAT should be OK."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(
            db_session, surface=2000, cvc_kw=100,
            operat_status=OperatStatus.SUBMITTED,
        )

        findings = evaluate_site(db_session, site.id)
        operat = [f for f in findings if f.rule_id == "DT_OPERAT"]
        assert len(operat) == 1
        assert operat[0].status == "OK"

    def test_evaluate_operat_not_started(self, db_session):
        """Site with OPERAT not started → DT_OPERAT should be NOK."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(
            db_session, surface=2000, cvc_kw=100,
            operat_status=OperatStatus.NOT_STARTED,
        )

        findings = evaluate_site(db_session, site.id)
        operat = [f for f in findings if f.rule_id == "DT_OPERAT"]
        assert len(operat) == 1
        assert operat[0].status == "NOK"
        assert operat[0].severity == "critical"

    def test_evaluate_bacs_high_power(self, db_session):
        """CVC 400kW without attestation → BACS_HIGH_DEADLINE NOK critical."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(db_session, surface=3000, cvc_kw=400)

        findings = evaluate_site(db_session, site.id)
        high = [f for f in findings if f.rule_id == "BACS_HIGH_DEADLINE"]
        assert len(high) == 1
        assert high[0].status == "NOK"
        assert high[0].severity == "critical"

    def test_evaluate_bacs_with_attestation(self, db_session):
        """CVC 400kW with valid attestation → BACS OK."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(db_session, surface=3000, cvc_kw=400)

        # Add BACS attestation evidence
        ev = Evidence(
            site_id=site.id,
            type=TypeEvidence.ATTESTATION_BACS,
            statut=StatutEvidence.VALIDE,
        )
        db_session.add(ev)
        db_session.commit()

        findings = evaluate_site(db_session, site.id)
        high = [f for f in findings if f.rule_id == "BACS_HIGH_DEADLINE"]
        assert len(high) == 1
        assert high[0].status == "OK"

    def test_unknown_to_nok_after_data(self, db_session):
        """Site with no tertiaire_area → UNKNOWN, then set area → NOK or OK."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(db_session, surface=2000, cvc_kw=100)
        site.tertiaire_area_m2 = None
        db_session.commit()

        # First eval: UNKNOWN
        findings1 = evaluate_site(db_session, site.id)
        dt_scope = [f for f in findings1 if f.rule_id == "DT_SCOPE"]
        assert dt_scope[0].status == "UNKNOWN"

        # Set tertiaire area
        site.tertiaire_area_m2 = 2000
        db_session.commit()

        # Re-eval: now in scope
        findings2 = evaluate_site(db_session, site.id)
        dt_scope2 = [f for f in findings2 if f.rule_id == "DT_SCOPE"]
        assert dt_scope2[0].status == "OK"

    def test_findings_replaced_on_reevaluation(self, db_session):
        """Re-evaluation replaces previous findings."""
        from services.compliance_rules import evaluate_site
        org, site, bat = _create_org_site(db_session, surface=2000, cvc_kw=100)

        f1 = evaluate_site(db_session, site.id)
        count1 = db_session.query(ComplianceFinding).filter(
            ComplianceFinding.site_id == site.id
        ).count()

        f2 = evaluate_site(db_session, site.id)
        count2 = db_session.query(ComplianceFinding).filter(
            ComplianceFinding.site_id == site.id
        ).count()

        assert count1 == count2  # Replaced, not appended


# ========================================
# API Endpoints
# ========================================

class TestComplianceEndpoints:
    def test_summary_no_org(self, client):
        r = client.get("/api/compliance/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_sites"] == 0

    def test_summary_with_seed(self, client):
        _seed(client)
        # Recompute rules first
        client.post("/api/compliance/recompute-rules")
        r = client.get("/api/compliance/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_sites"] == 3
        assert "findings_by_regulation" in data

    def test_sites_no_org(self, client):
        r = client.get("/api/compliance/sites")
        assert r.status_code == 200
        assert r.json() == []

    def test_sites_with_seed(self, client):
        _seed(client)
        client.post("/api/compliance/recompute-rules")
        r = client.get("/api/compliance/sites")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        assert "findings" in data[0]

    def test_sites_filter_regulation(self, client):
        _seed(client)
        client.post("/api/compliance/recompute-rules")
        r = client.get("/api/compliance/sites", params={"regulation": "bacs"})
        assert r.status_code == 200
        data = r.json()
        for site in data:
            for f in site["findings"]:
                assert f["regulation"] == "bacs"

    def test_sites_filter_status_nok(self, client):
        _seed(client)
        client.post("/api/compliance/recompute-rules")
        r = client.get("/api/compliance/sites", params={"status": "NOK"})
        assert r.status_code == 200
        data = r.json()
        for site in data:
            for f in site["findings"]:
                assert f["status"] == "NOK"

    def test_recompute_rules(self, client):
        _seed(client)
        r = client.post("/api/compliance/recompute-rules")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["sites_evaluated"] == 3
        assert data["total_findings"] > 0

    def test_recompute_rules_no_org(self, client):
        r = client.post("/api/compliance/recompute-rules")
        assert r.status_code == 400

    def test_rules_list(self, client):
        r = client.get("/api/compliance/rules")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 3
        reg_names = [d["regulation"] for d in data]
        assert "decret_tertiaire_operat" in reg_names
        assert "bacs" in reg_names
        assert "aper" in reg_names


# ========================================
# Dashboard 2min integration
# ========================================

class TestDashboard2MinFindings:
    def test_findings_summary_present(self, client):
        _seed(client)
        client.post("/api/compliance/recompute-rules")
        r = client.get("/api/dashboard/2min")
        assert r.status_code == 200
        data = r.json()
        assert data["findings_summary"] is not None
        assert "total" in data["findings_summary"]
        assert "nok" in data["findings_summary"]

    def test_action_1_from_findings(self, client):
        _seed(client)
        client.post("/api/compliance/recompute-rules")
        data = client.get("/api/dashboard/2min").json()
        a1 = data["action_1"]
        assert a1 is not None
        assert a1["texte"]


# ========================================
# Auto-trigger on site creation
# ========================================

class TestAutoTrigger:
    def test_site_creation_triggers_evaluation(self, client):
        _seed(client)
        r = client.post("/api/sites", json={
            "nom": "Bureau Lyon",
            "type": "bureau",
            "surface_m2": 3000,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["findings_count"] > 0
