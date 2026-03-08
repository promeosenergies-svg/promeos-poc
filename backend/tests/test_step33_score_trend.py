"""
Step 33 — Score trend sparkline : tests unitaires.
Model ComplianceScoreHistory + service compliance_score_trend + seed.
"""

import pytest
from datetime import date


class TestComplianceScoreHistoryModel:
    """ComplianceScoreHistory model exists with required columns."""

    def test_import(self):
        from models.compliance_score_history import ComplianceScoreHistory

        assert ComplianceScoreHistory.__tablename__ == "compliance_score_history"

    def test_columns(self):
        from models.compliance_score_history import ComplianceScoreHistory

        cols = {c.name for c in ComplianceScoreHistory.__table__.columns}
        assert "site_id" in cols
        assert "org_id" in cols
        assert "month_key" in cols
        assert "score" in cols
        assert "grade" in cols

    def test_unique_constraint(self):
        from models.compliance_score_history import ComplianceScoreHistory

        constraints = ComplianceScoreHistory.__table__.constraints
        uq_names = [c.name for c in constraints if hasattr(c, "name") and c.name]
        assert any("uq_site_month" in (n or "") for n in uq_names)

    def test_registered_in_init(self):
        import models

        assert hasattr(models, "ComplianceScoreHistory")


class TestScoreTrendService:
    """compliance_score_trend service functions."""

    def test_import_get_score_trend(self):
        from services.compliance_score_trend import get_score_trend

        assert callable(get_score_trend)

    def test_import_snapshot(self):
        from services.compliance_score_trend import snapshot_monthly_scores

        assert callable(snapshot_monthly_scores)

    def test_grade_function(self):
        from services.compliance_score_trend import _score_to_grade

        assert _score_to_grade(85) == "A"
        assert _score_to_grade(65) == "B"
        assert _score_to_grade(45) == "C"
        assert _score_to_grade(25) == "D"
        assert _score_to_grade(10) == "F"


class TestSeedScoreHistory:
    """gen_score_history seed module."""

    def test_import(self):
        from services.demo_seed.gen_score_history import seed_score_history

        assert callable(seed_score_history)

    def test_progressions_defined(self):
        from services.demo_seed.gen_score_history import _PROGRESSIONS

        assert "paris" in _PROGRESSIONS
        assert "lyon" in _PROGRESSIONS
        assert len(_PROGRESSIONS["paris"]) == 6

    def test_grade_helper(self):
        from services.demo_seed.gen_score_history import _grade

        assert _grade(80) == "A"
        assert _grade(60) == "B"
        assert _grade(40) == "C"
        assert _grade(20) == "D"
        assert _grade(10) == "F"


class TestScoreTrendEndpoint:
    """GET /api/compliance/score-trend route exists."""

    def test_route_registered(self):
        from routes.compliance import router

        paths = [r.path for r in router.routes]
        assert "/score-trend" in paths or any("/score-trend" in p for p in paths)
