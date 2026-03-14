"""
PROMEOS - Tests Sprint 3: Segmentation B2B
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

from models import Base, Organisation, SegmentationProfile
from models.enums import Typologie
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
    """Helper: create org via demo seed."""
    return client.post("/api/demo/seed").json()


# ========================================
# Enum Typologie
# ========================================


class TestTypologieEnum:
    def test_all_values_exist(self):
        expected = [
            "tertiaire_prive",
            "tertiaire_public",
            "industrie",
            "commerce_retail",
            "copropriete_syndic",
            "bailleur_social",
            "collectivite",
            "hotellerie_restauration",
            "sante_medico_social",
            "enseignement",
            "mixte",
        ]
        for val in expected:
            assert Typologie(val) is not None

    def test_count(self):
        assert len(Typologie) == 11


# ========================================
# SegmentationProfile model
# ========================================


class TestSegmentationProfileModel:
    def test_create_profile(self, db_session):
        org = Organisation(nom="Test Org", type_client="bureau", actif=True)
        db_session.add(org)
        db_session.flush()

        profile = SegmentationProfile(
            organisation_id=org.id,
            typologie=Typologie.TERTIAIRE_PRIVE.value,
            confidence_score=50.0,
        )
        db_session.add(profile)
        db_session.commit()

        assert profile.id is not None
        assert profile.typologie == "tertiaire_prive"
        assert profile.confidence_score == 50.0

    def test_profile_with_answers(self, db_session):
        org = Organisation(nom="Test Org 2", type_client="hotel", actif=True)
        db_session.add(org)
        db_session.flush()

        answers = {"q_travaux": "oui", "q_gtb": "non"}
        profile = SegmentationProfile(
            organisation_id=org.id,
            typologie=Typologie.HOTELLERIE_RESTAURATION.value,
            confidence_score=60.0,
            answers_json=json.dumps(answers),
            reasons_json=json.dumps(["Type client hotel"]),
        )
        db_session.add(profile)
        db_session.commit()

        loaded = json.loads(profile.answers_json)
        assert loaded["q_travaux"] == "oui"
        assert len(json.loads(profile.reasons_json)) == 1


# ========================================
# GET /api/segmentation/questions
# ========================================


class TestSegmentationQuestions:
    def test_list_questions(self, client):
        r = client.get("/api/segmentation/questions")
        assert r.status_code == 200
        data = r.json()
        assert "questions" in data
        assert data["total"] == 8

    def test_question_structure(self, client):
        data = client.get("/api/segmentation/questions").json()
        q = data["questions"][0]
        assert "id" in q
        assert "text" in q
        assert "type" in q
        assert "options" in q
        assert len(q["options"]) >= 2

    def test_all_questions_have_ids(self, client):
        data = client.get("/api/segmentation/questions").json()
        ids = [q["id"] for q in data["questions"]]
        assert len(ids) == len(set(ids))  # unique
        expected_ids = [
            "q_travaux",
            "q_gtb",
            "q_bacs",
            "q_operat",
            # q_cee masque (hidden=True) — non retourne par get_questions
            "q_horaires",
            "q_chauffage",
            "q_irve",
        ]
        for eid in expected_ids:
            assert eid in ids


# ========================================
# GET /api/segmentation/profile
# ========================================


class TestSegmentationProfile:
    def test_no_org_returns_no_profile(self, client):
        # V57: resolve_org_id returns 403 when no org resolvable
        from services.demo_state import DemoState

        DemoState.clear_demo_org()
        r = client.get("/api/segmentation/profile")
        assert r.status_code in (200, 403)

    def test_with_org_returns_profile(self, client):
        _seed(client)
        r = client.get("/api/segmentation/profile")
        assert r.status_code == 200
        data = r.json()
        assert data["has_profile"] is True
        assert data["typologie"] is not None
        assert data["confidence_score"] > 0

    def test_profile_has_organisation(self, client):
        _seed(client)
        data = client.get("/api/segmentation/profile").json()
        assert "organisation" in data
        assert data["organisation"]["nom"] == "Demo PROMEOS"

    def test_profile_has_reasons(self, client):
        _seed(client)
        data = client.get("/api/segmentation/profile").json()
        assert isinstance(data["reasons"], list)
        assert len(data["reasons"]) >= 1

    def test_profile_idempotent(self, client):
        _seed(client)
        d1 = client.get("/api/segmentation/profile").json()
        d2 = client.get("/api/segmentation/profile").json()
        assert d1["typologie"] == d2["typologie"]
        assert d1["confidence_score"] == d2["confidence_score"]


# ========================================
# POST /api/segmentation/answers
# ========================================


class TestSegmentationAnswers:
    def test_submit_without_org(self, client):
        # V57: resolve_org_id returns 403 when no org resolvable
        from services.demo_state import DemoState

        DemoState.clear_demo_org()
        r = client.post(
            "/api/segmentation/answers",
            json={
                "answers": {"q_travaux": "oui"},
            },
        )
        assert r.status_code in (400, 403)

    def test_submit_answers(self, client):
        _seed(client)
        r = client.post(
            "/api/segmentation/answers",
            json={
                "answers": {"q_travaux": "oui", "q_gtb": "non"},
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["answers_count"] == 2
        assert data["typologie"] is not None
        assert data["confidence_score"] > 0

    def test_answers_boost_confidence(self, client):
        _seed(client)
        # Get baseline
        baseline = client.get("/api/segmentation/profile").json()
        base_score = baseline["confidence_score"]

        # Submit answers
        client.post(
            "/api/segmentation/answers",
            json={
                "answers": {
                    "q_travaux": "oui",
                    "q_gtb": "oui_centralisee",
                    "q_bacs": "oui_conforme",
                    "q_operat": "oui_a_jour",
                },
            },
        )
        updated = client.get("/api/segmentation/profile").json()
        assert updated["confidence_score"] > base_score

    def test_answers_merge(self, client):
        _seed(client)
        # First batch
        client.post(
            "/api/segmentation/answers",
            json={
                "answers": {"q_travaux": "oui"},
            },
        )
        # Second batch
        r = client.post(
            "/api/segmentation/answers",
            json={
                "answers": {"q_gtb": "non"},
            },
        )
        data = r.json()
        assert data["answers_count"] == 2  # merged

    def test_answers_all_8_questions(self, client):
        _seed(client)
        all_answers = {
            "q_travaux": "oui",
            "q_gtb": "oui_centralisee",
            "q_bacs": "oui_conforme",
            "q_operat": "oui_a_jour",
            "q_cee": "oui",
            "q_horaires": "bureau_standard",
            "q_chauffage": "gaz",
            "q_irve": "non",
        }
        r = client.post(
            "/api/segmentation/answers",
            json={
                "answers": all_answers,
            },
        )
        data = r.json()
        assert data["answers_count"] == 8
        assert data["confidence_score"] >= 50  # baseline + 8*2.5 = +20


# ========================================
# Service: detect_typologie
# ========================================


class TestDetectTypologie:
    def test_detect_from_type_client_bureau(self, db_session):
        from services.segmentation_service import detect_typologie

        org = Organisation(nom="Bureau Corp", type_client="bureau", actif=True)
        db_session.add(org)
        db_session.commit()

        result = detect_typologie(db_session, org.id)
        assert result["typologie"] == Typologie.TERTIAIRE_PRIVE

    def test_detect_from_type_client_hotel(self, db_session):
        from services.segmentation_service import detect_typologie

        org = Organisation(nom="Hotel Group", type_client="hotel", actif=True)
        db_session.add(org)
        db_session.commit()

        result = detect_typologie(db_session, org.id)
        assert result["typologie"] == Typologie.HOTELLERIE_RESTAURATION

    def test_detect_from_type_client_collectivite(self, db_session):
        from services.segmentation_service import detect_typologie

        org = Organisation(nom="Mairie X", type_client="collectivite", actif=True)
        db_session.add(org)
        db_session.commit()

        result = detect_typologie(db_session, org.id)
        assert result["typologie"] == Typologie.COLLECTIVITE

    def test_detect_unknown_defaults_tertiaire(self, db_session):
        from services.segmentation_service import detect_typologie

        org = Organisation(nom="Unknown", type_client=None, actif=True)
        db_session.add(org)
        db_session.commit()

        result = detect_typologie(db_session, org.id)
        assert result["typologie"] == Typologie.TERTIAIRE_PRIVE
        assert result["confidence_score"] <= 30

    def test_detect_nonexistent_org(self, db_session):
        from services.segmentation_service import detect_typologie

        result = detect_typologie(db_session, 9999)
        assert result["typologie"] == Typologie.TERTIAIRE_PRIVE
        assert result["confidence_score"] == 0.0

    def test_confidence_increases_with_signals(self, db_session):
        from services.segmentation_service import detect_typologie
        from models import EntiteJuridique

        org = Organisation(nom="Industrie SA", type_client="usine", actif=True, siren="123456789")
        db_session.add(org)
        db_session.flush()

        entite = EntiteJuridique(
            organisation_id=org.id,
            nom="Industrie SA",
            siren="123456789",
            naf_code="25.11Z",
        )
        db_session.add(entite)
        db_session.commit()

        result = detect_typologie(db_session, org.id)
        # Both heuristic + NAF converge on industrie → higher confidence
        assert result["confidence_score"] >= 50
        assert len(result["reasons"]) >= 2
