"""
PROMEOS - Tests for AI Agents
Tests the AI agent registry, stub mode, and status immutability rule
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, AiInsight, InsightType, Site, Organisation, TypeSite
from ai_layer.registry import run_agent
from ai_layer.client import AIClient


# ========================================
# Fixtures
# ========================================


@pytest.fixture
def db_session():
    """In-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Create minimal data for agents
    org = Organisation(id=1, nom="Test Org", type_client="retail", actif=True)
    session.add(org)
    session.flush()

    site = Site(id=1, nom="Test Site", type=TypeSite.BUREAU, surface_m2=1500, actif=True)
    session.add(site)
    session.commit()

    yield session
    session.close()


# ========================================
# Tests
# ========================================


def test_ai_client_stub_mode():
    """Test AI client defaults to stub mode without API key"""
    from unittest.mock import patch
    import ai_layer.client as _mod

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("AI_API_KEY", None)
        old_mod = _mod.AI_API_KEY
        _mod.AI_API_KEY = None
        try:
            client = AIClient()
            assert client.stub_mode is True
        finally:
            _mod.AI_API_KEY = old_mod


def test_ai_client_stub_response():
    """Test stub mode returns expected response format"""
    from unittest.mock import patch
    import ai_layer.client as _mod

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("AI_API_KEY", None)
        old_mod = _mod.AI_API_KEY
        _mod.AI_API_KEY = None
        try:
            client = AIClient()
            response = client.complete("system prompt", "user prompt")

            assert isinstance(response, str)
            assert "[AI Stub Mode]" in response or "stub" in response.lower()
        finally:
            _mod.AI_API_KEY = old_mod


def test_agent_creates_ai_insight(db_session):
    """Test that agents create AiInsight records"""
    from ai_layer.agents.regops_explainer import run

    # Run the agent
    insight = run(db_session, site_id=1)

    assert insight is not None
    assert isinstance(insight, AiInsight)
    assert insight.object_type == "site"
    assert insight.object_id == 1
    assert insight.insight_type == InsightType.EXPLAIN
    assert insight.content_json is not None


def test_ai_insight_structure(db_session):
    """Test AiInsight has required fields"""
    from ai_layer.agents.regops_explainer import run

    insight = run(db_session, site_id=1)

    # Parse content_json
    content = json.loads(insight.content_json)

    # Should have these fields per hard rule
    assert "brief" in content or "analysis" in content
    assert "sources_used" in content
    assert "needs_human_review" in content

    # AI version should be set
    assert insight.ai_version is not None


def test_ai_never_modifies_status(db_session):
    """HARD RULE: AI agents never modify compliance status"""
    from ai_layer.agents.regops_explainer import run

    # Get site before agent runs
    site_before = db_session.query(Site).filter(Site.id == 1).first()
    status_before = getattr(site_before, "statut_decret_tertiaire", None)

    # Run AI agent
    run(db_session, site_id=1)
    db_session.commit()

    # Get site after agent runs
    site_after = db_session.query(Site).filter(Site.id == 1).first()
    status_after = getattr(site_after, "statut_decret_tertiaire", None)

    # Status should be unchanged
    assert status_before == status_after

    # AI should only create AiInsight, not modify Site
    insights = db_session.query(AiInsight).all()
    assert len(insights) > 0


def test_recommendations_are_tagged(db_session):
    """Test that AI recommendations are properly tagged"""
    from ai_layer.agents.regops_recommender import run

    insight = run(db_session, site_id=1)
    content = json.loads(insight.content_json)

    # Recommendations should be separate from deterministic actions
    # In practice, is_ai_suggestion=True flag would be on Action objects
    # Here we just verify the insight is created
    assert insight.insight_type == InsightType.SUGGEST


def test_multiple_agents_coexist(db_session):
    """Test multiple agent types can create insights for same site"""
    from ai_layer.agents.regops_explainer import run as run_explainer
    from ai_layer.agents.data_quality_agent import run as run_quality

    # Run both agents
    insight1 = run_explainer(db_session, site_id=1)
    insight2 = run_quality(db_session, site_id=1)

    # Both should succeed
    assert insight1.insight_type == InsightType.EXPLAIN
    assert insight2.insight_type == InsightType.DATA_QUALITY

    # Both should be stored
    all_insights = db_session.query(AiInsight).filter(AiInsight.object_id == 1).all()
    assert len(all_insights) == 2


# ========================================
# Run Tests
# ========================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
