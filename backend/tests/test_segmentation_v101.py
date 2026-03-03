"""
PROMEOS - Tests V101: Segmentation → Action Plan + Onboarding Pilote
Tests: enum, compute_next_best_step, next-step endpoint, action creation, V100 bug fixes.
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

from models import Base, Organisation, SegmentationProfile, ActionItem
from models.enums import Typologie, ActionSourceType, ActionStatus
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
# ActionSourceType — SEGMENTATION exists
# ========================================

class TestActionSourceTypeEnum:
    def test_segmentation_exists(self):
        assert ActionSourceType.SEGMENTATION.value == "segmentation"

    def test_no_breaking_change(self):
        """All pre-existing values still exist."""
        for val in ["compliance", "consumption", "billing", "purchase", "insight", "manual"]:
            assert ActionSourceType(val) is not None


# ========================================
# compute_next_best_step
# ========================================

class TestComputeNextBestStep:
    def test_low_confidence_returns_answer_questions(self, db_session):
        """When confidence < 50, step should be 'answer_questions'."""
        from services.segmentation_service import compute_next_best_step
        org = Organisation(nom="Test Org", type_client="bureau")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        # Create profile with low confidence
        profile = SegmentationProfile(
            organisation_id=org.id,
            typologie="tertiaire_prive",
            segment_label="Tertiaire Prive",
            confidence_score=30.0,
            derived_from="mix",
        )
        db_session.add(profile)
        db_session.commit()

        result = compute_next_best_step(db_session, org.id)
        assert result["key"] == "answer_questions"
        assert result["cta"]["type"] == "modal"

    def test_high_confidence_fallthrough(self, db_session):
        """When confidence >= 50 and no contracts/recon issues, fall through to recommendation."""
        from services.segmentation_service import compute_next_best_step
        org = Organisation(nom="High Conf Org", type_client="bureau")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        profile = SegmentationProfile(
            organisation_id=org.id,
            typologie="tertiaire_prive",
            segment_label="Tertiaire Prive",
            confidence_score=85.0,
            derived_from="mix",
            answers_json=json.dumps({"q_operat": "oui_a_jour", "q_bacs": "oui_conforme", "q_horaires": "bureau_standard"}),
        )
        db_session.add(profile)
        db_session.commit()

        result = compute_next_best_step(db_session, org.id)
        # Should fall through to a recommendation or default
        assert "key" in result
        assert "title" in result
        assert "cta" in result

    def test_required_fields(self, db_session):
        """Every next-best-step has all required fields."""
        from services.segmentation_service import compute_next_best_step
        org = Organisation(nom="Fields Test", type_client="collectivite")
        db_session.add(org)
        db_session.commit()
        db_session.refresh(org)

        result = compute_next_best_step(db_session, org.id)
        for field in ["key", "title", "why", "impact_label", "cta"]:
            assert field in result, f"Missing field: {field}"
        assert "type" in result["cta"]
        assert "label" in result["cta"]


# ========================================
# GET /api/segmentation/next-step
# ========================================

class TestNextStepEndpoint:
    def test_200_ok(self, client):
        _seed(client)
        resp = client.get("/api/segmentation/next-step")
        assert resp.status_code == 200

    def test_response_shape(self, client):
        _seed(client)
        data = client.get("/api/segmentation/next-step").json()
        assert "profile_summary" in data
        assert "next_best_step" in data
        assert "top_recommendations" in data

    def test_profile_summary_fields(self, client):
        _seed(client)
        data = client.get("/api/segmentation/next-step").json()
        ps = data["profile_summary"]
        for field in ["typologie", "segment_label", "confidence_score", "derived_from"]:
            assert field in ps, f"Missing profile_summary field: {field}"

    def test_portfolio_id_param(self, client):
        _seed(client)
        resp = client.get("/api/segmentation/next-step", params={"portfolio_id": 1})
        assert resp.status_code == 200


# ========================================
# POST /api/segmentation/actions/from-recommendation
# ========================================

class TestActionsFromRecommendation:
    def test_create_action(self, client):
        _seed(client)
        # First get recommendations to find a valid key
        profile = client.get("/api/segmentation/profile").json()
        recs = profile.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations for this profile")
        key = recs[0]["key"]

        resp = client.post(
            "/api/segmentation/actions/from-recommendation",
            json={"recommendation_key": key},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"
        assert "id" in data

    def test_idempotency(self, client):
        _seed(client)
        profile = client.get("/api/segmentation/profile").json()
        recs = profile.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        key = recs[0]["key"]

        resp1 = client.post("/api/segmentation/actions/from-recommendation", json={"recommendation_key": key})
        resp2 = client.post("/api/segmentation/actions/from-recommendation", json={"recommendation_key": key})
        assert resp1.json()["status"] == "created"
        assert resp2.json()["status"] == "existing"
        assert resp1.json()["id"] == resp2.json()["id"]

    def test_unknown_key_404(self, client):
        _seed(client)
        resp = client.post(
            "/api/segmentation/actions/from-recommendation",
            json={"recommendation_key": "nonexistent_key_xyz"},
        )
        assert resp.status_code == 404

    def test_response_fields(self, client):
        _seed(client)
        profile = client.get("/api/segmentation/profile").json()
        recs = profile.get("recommendations", [])
        if not recs:
            pytest.skip("No recommendations")
        key = recs[0]["key"]

        data = client.post(
            "/api/segmentation/actions/from-recommendation",
            json={"recommendation_key": key},
        ).json()
        for field in ["id", "title", "status", "message"]:
            assert field in data


# ========================================
# POST /api/segmentation/actions/from-next-step
# ========================================

class TestActionsFromNextStep:
    def test_create_action(self, client):
        _seed(client)
        resp = client.post(
            "/api/segmentation/actions/from-next-step",
            json={},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "created"

    def test_idempotency(self, client):
        _seed(client)
        resp1 = client.post("/api/segmentation/actions/from-next-step", json={})
        resp2 = client.post("/api/segmentation/actions/from-next-step", json={})
        assert resp1.json()["status"] == "created"
        assert resp2.json()["status"] == "existing"


# ========================================
# V100 Bug Fixes verification
# ========================================

class TestV100BugFixes:
    def test_post_answers_returns_missing_questions(self, client):
        """Bug #4: POST /answers now returns missing_questions."""
        _seed(client)
        resp = client.post(
            "/api/segmentation/answers",
            json={"answers": {"q_operat": "oui_a_jour"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "missing_questions" in data
        assert "recommendations" in data
        assert "has_profile" in data

    def test_get_recommendations_none_no_crash(self):
        """Bug #1: get_recommendations(None) should not crash."""
        from services.segmentation_service import get_recommendations
        result = get_recommendations(None)
        assert isinstance(result, list)
        assert len(result) > 0
