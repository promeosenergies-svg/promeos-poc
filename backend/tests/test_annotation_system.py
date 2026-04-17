"""
Tests Annotation System -- Phase 3 + Phase 4.
Couvre: Annotation model, AnnotatorProfile, 4 agents stubs.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(scope="module", autouse=True)
def ensure_demo_data():
    """Override conftest autouse fixture -- annotation tests don't need demo seed."""
    pass


class TestAnnotationModelImport:
    def test_import_annotation(self):
        from models.annotation import Annotation

        assert hasattr(Annotation, "__tablename__")
        assert Annotation.__tablename__ == "annotations"

    def test_import_annotator_profile(self):
        from models.annotation import AnnotatorProfile

        assert hasattr(AnnotatorProfile, "__tablename__")
        assert AnnotatorProfile.__tablename__ == "annotator_profiles"

    def test_annotation_columns(self):
        from models.annotation import Annotation

        cols = {c.name for c in Annotation.__table__.columns}
        required = {
            "id",
            "object_type",
            "object_id",
            "label",
            "confidence",
            "annotator_type",
            "annotator_id",
            "org_id",
            "needs_review",
        }
        assert required.issubset(cols), f"Missing columns: {required - cols}"

    def test_annotator_profile_columns(self):
        from models.annotation import AnnotatorProfile

        cols = {c.name for c in AnnotatorProfile.__table__.columns}
        required = {"id", "annotator_id", "annotator_type", "org_id", "trust_weight"}
        assert required.issubset(cols), f"Missing columns: {required - cols}"

    def test_annotation_in_models_init(self):
        from models import Annotation, AnnotatorProfile

        assert Annotation.__tablename__ == "annotations"
        assert AnnotatorProfile.__tablename__ == "annotator_profiles"


class TestAnnotationAgentsImport:
    def test_import_profiler_agent(self):
        from services.annotation_agents import ProfilerAgent

        agent = ProfilerAgent()
        assert hasattr(agent, "run")

    def test_import_router_agent(self):
        from services.annotation_agents import RouterAgent

        agent = RouterAgent()
        assert hasattr(agent, "route")

    def test_import_auto_annotator(self):
        from services.annotation_agents import AutoAnnotator

        agent = AutoAnnotator()
        assert hasattr(agent, "annotate")
        assert agent.CONFIDENCE_THRESHOLD == 0.85

    def test_import_feedback_digest(self):
        from services.annotation_agents import FeedbackDigestAgent

        agent = FeedbackDigestAgent()
        assert hasattr(agent, "run")
        assert agent.FP_THRESHOLD_REVIEW == 0.60

    def test_router_escalation_rules(self):
        from services.annotation_agents import RouterAgent

        router = RouterAgent()
        assert len(router.ESCALATION_RULES) == 3
        # Test HIGH compliance escalation
        assert router.ESCALATION_RULES[0]({"severity": "HIGH", "domain": "compliance"})
        assert not router.ESCALATION_RULES[0]({"severity": "LOW", "domain": "compliance"})
        # Test financial escalation
        assert router.ESCALATION_RULES[1]({"financial_impact_eur": 10000})
        assert not router.ESCALATION_RULES[1]({"financial_impact_eur": 1000})

    def test_auto_annotator_threshold(self):
        from services.annotation_agents import AutoAnnotator

        auto = AutoAnnotator()
        # Below threshold should return None (we can't test DB without session)
        assert auto.CONFIDENCE_THRESHOLD == 0.85


class TestPatchEndpoint:
    def test_resolution_enum(self):
        from routes.ai_route import AiInsightResolution

        assert AiInsightResolution.VALIDATED.value == "validated"
        assert AiInsightResolution.DISMISSED.value == "dismissed"
        assert AiInsightResolution.CORRECTED.value == "corrected"

    def test_resolve_body_model(self):
        from routes.ai_route import ResolveInsightBody, AiInsightResolution

        body = ResolveInsightBody(
            resolution=AiInsightResolution.VALIDATED,
            correction_note="OK",
        )
        assert body.resolution == AiInsightResolution.VALIDATED

    def test_patch_route_exists(self):
        from routes.ai_route import router

        patch_routes = [r for r in router.routes if hasattr(r, "methods") and "PATCH" in r.methods]
        assert len(patch_routes) == 1
        assert "insight" in patch_routes[0].path


class TestSeedAnnotations:
    def test_helios_ground_truth_data(self):
        from scripts.seed_annotations_helios import HELIOS_GROUND_TRUTH

        assert len(HELIOS_GROUND_TRUTH) == 5
        # All should be confirmed_anomaly
        for _, _, _, label in HELIOS_GROUND_TRUTH:
            assert label == "confirmed_anomaly"
