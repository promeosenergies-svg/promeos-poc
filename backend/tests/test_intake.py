"""
PROMEOS - Tests DIAMANT: Smart Intake
~20 tests covering: question generation, prefill, apply answers, demo autofill,
inheritance (override resolution), before/after diff, PDF extraction, API endpoints.
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
    Base, Site, Organisation, EntiteJuridique, Portefeuille, Batiment, Evidence,
    IntakeSession, IntakeAnswer, IntakeFieldOverride,
    IntakeSessionStatus, IntakeMode, IntakeSource,
    TypeSite, TypeEvidence, StatutEvidence, OperatStatus, ParkingType,
)
from database import get_db
from main import app
from services.intake_engine import (
    generate_questions, prefill_from_existing, resolve_overrides,
    compute_before_after, extract_from_pdf_text,
    QUESTION_BANK, DEMO_DEFAULTS, MAX_QUESTIONS,
)
from services.intake_service import (
    create_session, submit_answer, compute_diff, apply_answers,
    demo_autofill, complete_session, get_session_detail,
    purge_demo_sessions,
)


# ========================================
# Fixtures
# ========================================

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


def _create_empty_site(db_session, **overrides):
    """Create a site with all regulatory fields NULL (maximum questions)."""
    defaults = dict(
        nom="Site Vide",
        type=TypeSite.BUREAU,
        adresse="1 rue Vide",
        code_postal="75001",
        ville="Paris",
        region="IDF",
        surface_m2=None,
        nombre_employes=None,
        tertiaire_area_m2=None,
        parking_area_m2=None,
        roof_area_m2=None,
        parking_type=None,
        operat_status=None,
        annual_kwh_total=None,
        is_multi_occupied=None,
        naf_code=None,
    )
    defaults.update(overrides)
    site = Site(**defaults)
    db_session.add(site)
    db_session.flush()
    return site


def _create_full_site(db_session):
    """Create a site with all regulatory fields filled (zero questions)."""
    site = Site(
        nom="Site Complet",
        type=TypeSite.BUREAU,
        adresse="10 rue Pleine",
        code_postal="75002",
        ville="Paris",
        region="IDF",
        surface_m2=3000.0,
        nombre_employes=150,
        tertiaire_area_m2=2500.0,
        parking_area_m2=2000.0,
        roof_area_m2=800.0,
        parking_type=ParkingType.OUTDOOR,
        operat_status=OperatStatus.SUBMITTED,
        annual_kwh_total=200000.0,
        is_multi_occupied=False,
        naf_code="7010A",
    )
    db_session.add(site)
    db_session.flush()

    # Add batiment with CVC
    bat = Batiment(
        site_id=site.id,
        nom="Bat Principal",
        surface_m2=2500.0,
        cvc_power_kw=180.0,
    )
    db_session.add(bat)

    # Add BACS evidences
    db_session.add(Evidence(
        site_id=site.id,
        type=TypeEvidence.ATTESTATION_BACS,
        statut=StatutEvidence.VALIDE,
        note="Test attestation",
    ))
    db_session.add(Evidence(
        site_id=site.id,
        type=TypeEvidence.DEROGATION_BACS,
        statut=StatutEvidence.VALIDE,
        note="Test derogation",
    ))
    db_session.flush()
    return site


def _create_org_hierarchy(db_session):
    """Create org > entity > portefeuille hierarchy, return (org, entity, pf)."""
    org = Organisation(nom="Org Test", type_client="bureau", actif=True, siren="111222333")
    db_session.add(org)
    db_session.flush()

    ej = EntiteJuridique(organisation_id=org.id, nom="EJ Test", siren="111222333")
    db_session.add(ej)
    db_session.flush()

    pf = Portefeuille(entite_juridique_id=ej.id, nom="PF Test", description="Test")
    db_session.add(pf)
    db_session.flush()

    return org, ej, pf


# ========================================
# TestQuestionGeneration (4 tests)
# ========================================

class TestQuestionGeneration:
    def test_full_null_site_gets_max_questions(self, db_session):
        """Site with all null fields -> generates MAX_QUESTIONS (8) questions."""
        site = _create_empty_site(db_session)
        questions = generate_questions(db_session, site.id)
        assert len(questions) == MAX_QUESTIONS
        assert all("field_path" in q for q in questions)
        assert all("question" in q for q in questions)

    def test_partial_data_fewer_questions(self, db_session):
        """Site with many fields filled -> fewer questions."""
        site = _create_empty_site(
            db_session,
            tertiaire_area_m2=2000.0,
            surface_m2=3000.0,
            parking_area_m2=1800.0,
            roof_area_m2=600.0,
            annual_kwh_total=180000.0,
            nombre_employes=80,
        )
        questions = generate_questions(db_session, site.id)
        field_paths = [q["field_path"] for q in questions]
        assert "site.tertiaire_area_m2" not in field_paths
        assert "site.surface_m2" not in field_paths
        assert "site.parking_area_m2" not in field_paths
        assert len(questions) <= MAX_QUESTIONS

    def test_all_data_no_questions(self, db_session):
        """Fully filled site -> 0 questions."""
        site = _create_full_site(db_session)
        questions = generate_questions(db_session, site.id)
        assert len(questions) == 0

    def test_blocking_first_ordering(self, db_session):
        """Critical/high severity questions come before medium/low."""
        site = _create_empty_site(db_session)
        questions = generate_questions(db_session, site.id)
        severities = [q["severity"] for q in questions]
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        values = [severity_order[s] for s in severities]
        # Should be sorted descending
        assert values == sorted(values, reverse=True)


# ========================================
# TestPrefill (3 tests)
# ========================================

class TestPrefill:
    def test_prefill_surface_to_tertiaire(self, db_session):
        """surface_m2 suggests tertiaire_area_m2 for tertiaire site."""
        site = _create_empty_site(db_session, surface_m2=3000.0)
        prefills = prefill_from_existing(db_session, site.id)
        assert "site.tertiaire_area_m2" in prefills
        assert prefills["site.tertiaire_area_m2"] == 3000.0

    def test_prefill_cvc_from_surface(self, db_session):
        """surface_m2 + type -> estimated cvc_power_kw."""
        site = _create_empty_site(db_session, surface_m2=2000.0)
        prefills = prefill_from_existing(db_session, site.id)
        assert "batiment.cvc_power_kw" in prefills
        assert prefills["batiment.cvc_power_kw"] > 0

    def test_no_prefill_when_data_exists(self, db_session):
        """No prefill for fields already filled."""
        site = _create_empty_site(db_session, surface_m2=3000.0, tertiaire_area_m2=2500.0)
        prefills = prefill_from_existing(db_session, site.id)
        # tertiaire_area_m2 is already filled, so no prefill
        assert "site.tertiaire_area_m2" not in prefills


# ========================================
# TestApplyAnswers (4 tests)
# ========================================

class TestApplyAnswers:
    def test_apply_site_field(self, db_session):
        """Submit tertiaire_area_m2=2000, apply -> site updated."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.WIZARD)
        submit_answer(db_session, session.id, "site.tertiaire_area_m2", 2000.0, IntakeSource.USER)
        result = apply_answers(db_session, session.id)
        db_session.refresh(site)
        assert site.tertiaire_area_m2 == 2000.0
        assert result["fields_applied"] >= 1

    def test_apply_batiment_field(self, db_session):
        """Submit cvc_power_kw=150, apply -> batiment created/updated."""
        site = _create_empty_site(db_session, surface_m2=2000.0)
        session = create_session(db_session, site.id, mode=IntakeMode.WIZARD)
        submit_answer(db_session, session.id, "batiment.cvc_power_kw", 150.0, IntakeSource.USER)
        result = apply_answers(db_session, session.id)
        bat = db_session.query(Batiment).filter(Batiment.site_id == site.id).first()
        assert bat is not None
        assert bat.cvc_power_kw == 150.0
        assert result["fields_applied"] >= 1

    def test_apply_triggers_score_update(self, db_session):
        """After apply, session has score_after set."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.WIZARD)
        submit_answer(db_session, session.id, "site.tertiaire_area_m2", 2500.0, IntakeSource.USER)
        submit_answer(db_session, session.id, "site.operat_status", "submitted", IntakeSource.USER)
        result = apply_answers(db_session, session.id)
        assert result["score_after"] is not None
        assert "delta" in result

    def test_before_after_diff(self, db_session):
        """compute_diff returns correct score delta."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.WIZARD)
        submit_answer(db_session, session.id, "site.tertiaire_area_m2", 2500.0, IntakeSource.USER)
        diff = compute_diff(db_session, session.id)
        assert "score_before" in diff
        assert "score_after" in diff
        assert diff["answers_count"] >= 1


# ========================================
# TestDemoAutofill (3 tests)
# ========================================

class TestDemoAutofill:
    def test_autofill_creates_answers(self, db_session):
        """demo_autofill creates IntakeAnswer records with source=SYSTEM_DEMO."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.DEMO)
        result = demo_autofill(db_session, session.id)
        assert result["answers_created"] > 0
        answers = db_session.query(IntakeAnswer).filter(
            IntakeAnswer.session_id == session.id
        ).all()
        assert len(answers) > 0
        assert all(a.source == IntakeSource.SYSTEM_DEMO for a in answers)

    def test_autofill_applies_and_updates_score(self, db_session):
        """After autofill, session score_after is set."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.DEMO)
        result = demo_autofill(db_session, session.id)
        assert result["score_after"] is not None
        assert result["score_before"] is not None

    def test_purge_demo(self, db_session):
        """purge_demo_sessions removes sessions, count returned."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.DEMO)
        demo_autofill(db_session, session.id)
        complete_session(db_session, session.id)
        db_session.commit()
        count = purge_demo_sessions(db_session)
        db_session.commit()
        assert count >= 1
        remaining = db_session.query(IntakeSession).filter(
            IntakeSession.mode == IntakeMode.DEMO
        ).count()
        assert remaining == 0


# ========================================
# TestInheritance (3 tests)
# ========================================

class TestInheritance:
    def test_org_override_provides_default(self, db_session):
        """IntakeFieldOverride at ORG level -> resolve_overrides returns it."""
        org, ej, pf = _create_org_hierarchy(db_session)
        site = _create_empty_site(db_session)
        site.portefeuille_id = pf.id
        db_session.flush()

        db_session.add(IntakeFieldOverride(
            scope_type="org",
            scope_id=org.id,
            field_path="site.tertiaire_area_m2",
            value_json=json.dumps(5000.0),
            source="bulk",
        ))
        db_session.flush()

        overrides = resolve_overrides(db_session, site.id)
        assert "site.tertiaire_area_m2" in overrides
        assert overrides["site.tertiaire_area_m2"]["value"] == 5000.0
        assert overrides["site.tertiaire_area_m2"]["scope_type"] == "org"

    def test_entity_overrides_org(self, db_session):
        """Both ORG and ENTITY override -> ENTITY wins."""
        org, ej, pf = _create_org_hierarchy(db_session)
        site = _create_empty_site(db_session)
        site.portefeuille_id = pf.id
        db_session.flush()

        # ORG override
        db_session.add(IntakeFieldOverride(
            scope_type="org",
            scope_id=org.id,
            field_path="site.parking_area_m2",
            value_json=json.dumps(3000.0),
            source="bulk",
        ))
        # ENTITY override (should win)
        db_session.add(IntakeFieldOverride(
            scope_type="entity",
            scope_id=ej.id,
            field_path="site.parking_area_m2",
            value_json=json.dumps(2000.0),
            source="bulk",
        ))
        db_session.flush()

        overrides = resolve_overrides(db_session, site.id)
        assert overrides["site.parking_area_m2"]["value"] == 2000.0
        assert overrides["site.parking_area_m2"]["scope_type"] == "entity"

    def test_site_overrides_all(self, db_session):
        """All 3 levels -> SITE level wins."""
        org, ej, pf = _create_org_hierarchy(db_session)
        site = _create_empty_site(db_session)
        site.portefeuille_id = pf.id
        db_session.flush()

        # ORG
        db_session.add(IntakeFieldOverride(
            scope_type="org", scope_id=org.id,
            field_path="site.roof_area_m2", value_json=json.dumps(1000.0), source="bulk",
        ))
        # ENTITY
        db_session.add(IntakeFieldOverride(
            scope_type="entity", scope_id=ej.id,
            field_path="site.roof_area_m2", value_json=json.dumps(800.0), source="bulk",
        ))
        # SITE (should win)
        db_session.add(IntakeFieldOverride(
            scope_type="site", scope_id=site.id,
            field_path="site.roof_area_m2", value_json=json.dumps(600.0), source="bulk",
        ))
        db_session.flush()

        overrides = resolve_overrides(db_session, site.id)
        assert overrides["site.roof_area_m2"]["value"] == 600.0
        assert overrides["site.roof_area_m2"]["scope_type"] == "site"


# ========================================
# TestBeforeAfter (2 tests)
# ========================================

class TestBeforeAfter:
    def test_compute_before_after_empty_site(self, db_session):
        """Empty site has many UNKNOWNs, proposed answers resolve some."""
        site = _create_empty_site(db_session)
        diff = compute_before_after(db_session, site.id, {})
        assert diff["unknowns_before"] > 0
        assert diff["score_before"] is not None

    def test_compute_proposed_improves_score(self, db_session):
        """Proposing answers should resolve UNKNOWNs and potentially improve score."""
        site = _create_empty_site(db_session)
        proposed = {
            "site.tertiaire_area_m2": 2500.0,
            "site.operat_status": "submitted",
            "site.annual_kwh_total": 185000.0,
        }
        diff = compute_before_after(db_session, site.id, proposed)
        assert diff["unknowns_after"] < diff["unknowns_before"]
        assert diff["unknowns_resolved"] > 0


# ========================================
# TestPDFExtraction (1 test)
# ========================================

class TestPDFExtraction:
    def test_extract_from_pdf_text(self):
        """Regex patterns extract fields from PDF text."""
        text = """
        Societe ACME SARL - SIRET 12345678901234
        Code NAF: 7010A
        Surface totale: 2 500 m2
        Puissance CVC: 180,5 kW
        Consommation annuelle: 195000 kWh
        """
        results = extract_from_pdf_text(text)
        assert results.get("site.surface_m2") == 2500.0
        assert results.get("site.siret") == "12345678901234"
        assert results.get("site.naf_code") == "7010A"
        assert results.get("batiment.cvc_power_kw") == 180.5
        assert results.get("site.annual_kwh_total") == 195000.0


# ========================================
# TestSessionLifecycle (2 tests)
# ========================================

class TestSessionLifecycle:
    def test_create_and_complete_session(self, db_session):
        """Create session -> submit -> complete."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.WIZARD)
        assert session.status == IntakeSessionStatus.IN_PROGRESS
        assert session.score_before is not None

        submit_answer(db_session, session.id, "site.tertiaire_area_m2", 2000.0)
        apply_answers(db_session, session.id)
        completed = complete_session(db_session, session.id)
        assert completed.status == IntakeSessionStatus.COMPLETED
        assert completed.completed_at is not None

    def test_get_session_detail(self, db_session):
        """get_session_detail returns full session with answers."""
        site = _create_empty_site(db_session)
        session = create_session(db_session, site.id, mode=IntakeMode.WIZARD)
        submit_answer(db_session, session.id, "site.tertiaire_area_m2", 2500.0)
        db_session.flush()

        detail = get_session_detail(db_session, session.id)
        assert detail["session"]["id"] == session.id
        assert detail["session"]["status"] == "in_progress"
        assert len(detail["answers"]) == 1
        assert detail["answers"][0]["field_path"] == "site.tertiaire_area_m2"


# ========================================
# TestIntakeAPI (3 tests)
# ========================================

class TestIntakeAPI:
    def test_get_questions_endpoint(self, client, db_session):
        """GET /api/intake/{site_id}/questions returns question list."""
        site = _create_empty_site(db_session)
        db_session.commit()
        resp = client.get(f"/api/intake/{site.id}/questions")
        assert resp.status_code == 200
        data = resp.json()
        assert "questions" in data
        assert data["questions_count"] > 0
        assert data["session_id"] is not None

    def test_post_answer_endpoint(self, client, db_session):
        """POST /api/intake/{site_id}/answers returns answer + diff preview."""
        site = _create_empty_site(db_session)
        db_session.commit()
        # First get questions to create a session
        client.get(f"/api/intake/{site.id}/questions")
        # Then post an answer
        resp = client.post(f"/api/intake/{site.id}/answers", json={
            "field_path": "site.tertiaire_area_m2",
            "value": 2000.0,
            "source": "user",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["field_path"] == "site.tertiaire_area_m2"
        assert "diff_preview" in data

    def test_complete_flow_endpoint(self, client, db_session):
        """Full flow: questions -> answer -> complete."""
        site = _create_empty_site(db_session)
        db_session.commit()
        # Get questions
        q_resp = client.get(f"/api/intake/{site.id}/questions")
        assert q_resp.status_code == 200
        # Submit answer
        a_resp = client.post(f"/api/intake/{site.id}/answers", json={
            "field_path": "site.tertiaire_area_m2",
            "value": 2500.0,
        })
        assert a_resp.status_code == 200
        # Complete
        c_resp = client.post(f"/api/intake/{site.id}/complete")
        assert c_resp.status_code == 200
        data = c_resp.json()
        assert "score_before" in data
        assert "score_after" in data
        assert data["fields_applied"] >= 1
