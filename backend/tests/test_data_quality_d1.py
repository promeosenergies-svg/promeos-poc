"""
PROMEOS — D.1 Data Quality Score (4 dimensions)
Tests for compute_site_data_quality, compute_portfolio_data_quality, grade helper, endpoints.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from services.data_quality_service import (
    _grade,
    DQ_GRADES,
    DQ_WEIGHTS,
    compute_site_data_quality,
    compute_portfolio_data_quality,
)


# ── Grade helper ────────────────────────────────────────────────────────────

class TestGrade:
    def test_grade_A(self):
        assert _grade(85) == "A"
        assert _grade(100) == "A"

    def test_grade_B(self):
        assert _grade(70) == "B"
        assert _grade(84.9) == "B"

    def test_grade_C(self):
        assert _grade(50) == "C"
        assert _grade(69.9) == "C"

    def test_grade_D(self):
        assert _grade(30) == "D"
        assert _grade(49.9) == "D"

    def test_grade_F(self):
        assert _grade(0) == "F"
        assert _grade(29.9) == "F"


# ── Weights ─────────────────────────────────────────────────────────────────

class TestWeights:
    def test_weights_sum_to_1(self):
        assert abs(sum(DQ_WEIGHTS.values()) - 1.0) < 0.001

    def test_completeness_is_heaviest(self):
        assert DQ_WEIGHTS["completeness"] >= max(
            DQ_WEIGHTS["freshness"], DQ_WEIGHTS["accuracy"], DQ_WEIGHTS["consistency"]
        )


# ── compute_site_data_quality ───────────────────────────────────────────────

class TestComputeSiteDataQuality:
    """Tests with mocked dimension functions to isolate score aggregation."""

    def _mock_dims(self, completeness=80, freshness=80, accuracy=80, consistency=80):
        """Patch the 4 dimension functions to return fixed scores."""
        return {
            "_dim_completeness": {"score": completeness, "weight": DQ_WEIGHTS["completeness"], "detail": "mock", "recommendation": None if completeness >= 70 else "fix completeness"},
            "_dim_freshness": {"score": freshness, "weight": DQ_WEIGHTS["freshness"], "detail": "mock", "recommendation": None if freshness >= 70 else "fix freshness"},
            "_dim_accuracy": {"score": accuracy, "weight": DQ_WEIGHTS["accuracy"], "detail": "mock", "recommendation": None if accuracy >= 70 else "fix accuracy"},
            "_dim_consistency": {"score": consistency, "weight": DQ_WEIGHTS["consistency"], "detail": "mock", "recommendation": None if consistency >= 70 else "fix consistency"},
        }

    @patch("services.data_quality_service._dim_consistency")
    @patch("services.data_quality_service._dim_accuracy")
    @patch("services.data_quality_service._dim_freshness")
    @patch("services.data_quality_service._dim_completeness")
    def test_perfect_score(self, mock_comp, mock_fresh, mock_acc, mock_cons):
        mocks = self._mock_dims(100, 100, 100, 100)
        mock_comp.return_value = mocks["_dim_completeness"]
        mock_fresh.return_value = mocks["_dim_freshness"]
        mock_acc.return_value = mocks["_dim_accuracy"]
        mock_cons.return_value = mocks["_dim_consistency"]

        db = MagicMock()
        result = compute_site_data_quality(db, 1, date(2025, 6, 1))

        assert result["score"] == 100.0
        assert result["grade"] == "A"
        assert result["site_id"] == 1
        assert "dimensions" in result
        assert len(result["recommendations"]) == 0

    @patch("services.data_quality_service._dim_consistency")
    @patch("services.data_quality_service._dim_accuracy")
    @patch("services.data_quality_service._dim_freshness")
    @patch("services.data_quality_service._dim_completeness")
    def test_low_completeness_lowers_score(self, mock_comp, mock_fresh, mock_acc, mock_cons):
        mocks = self._mock_dims(completeness=20, freshness=80, accuracy=80, consistency=80)
        mock_comp.return_value = mocks["_dim_completeness"]
        mock_fresh.return_value = mocks["_dim_freshness"]
        mock_acc.return_value = mocks["_dim_accuracy"]
        mock_cons.return_value = mocks["_dim_consistency"]

        db = MagicMock()
        result = compute_site_data_quality(db, 1, date(2025, 6, 1))

        # 20*0.35 + 80*0.25 + 80*0.25 + 80*0.15 = 7 + 20 + 20 + 12 = 59
        assert result["score"] == 59.0
        assert result["grade"] == "C"

    @patch("services.data_quality_service._dim_consistency")
    @patch("services.data_quality_service._dim_accuracy")
    @patch("services.data_quality_service._dim_freshness")
    @patch("services.data_quality_service._dim_completeness")
    def test_zero_all_gives_F(self, mock_comp, mock_fresh, mock_acc, mock_cons):
        mocks = self._mock_dims(0, 0, 0, 0)
        mock_comp.return_value = mocks["_dim_completeness"]
        mock_fresh.return_value = mocks["_dim_freshness"]
        mock_acc.return_value = mocks["_dim_accuracy"]
        mock_cons.return_value = mocks["_dim_consistency"]

        db = MagicMock()
        result = compute_site_data_quality(db, 1, date(2025, 6, 1))

        assert result["score"] == 0.0
        assert result["grade"] == "F"

    @patch("services.data_quality_service._dim_consistency")
    @patch("services.data_quality_service._dim_accuracy")
    @patch("services.data_quality_service._dim_freshness")
    @patch("services.data_quality_service._dim_completeness")
    def test_recommendations_for_low_dims(self, mock_comp, mock_fresh, mock_acc, mock_cons):
        mocks = self._mock_dims(completeness=30, freshness=40, accuracy=90, consistency=90)
        mock_comp.return_value = mocks["_dim_completeness"]
        mock_fresh.return_value = mocks["_dim_freshness"]
        mock_acc.return_value = mocks["_dim_accuracy"]
        mock_cons.return_value = mocks["_dim_consistency"]

        db = MagicMock()
        result = compute_site_data_quality(db, 1, date(2025, 6, 1))

        # completeness and freshness are < 70 → 2 recommendations
        assert len(result["recommendations"]) == 2
        assert all("message" in r for r in result["recommendations"])
        assert all("priority" in r for r in result["recommendations"])

    @patch("services.data_quality_service._dim_consistency")
    @patch("services.data_quality_service._dim_accuracy")
    @patch("services.data_quality_service._dim_freshness")
    @patch("services.data_quality_service._dim_completeness")
    def test_result_has_computed_at(self, mock_comp, mock_fresh, mock_acc, mock_cons):
        mocks = self._mock_dims()
        mock_comp.return_value = mocks["_dim_completeness"]
        mock_fresh.return_value = mocks["_dim_freshness"]
        mock_acc.return_value = mocks["_dim_accuracy"]
        mock_cons.return_value = mocks["_dim_consistency"]

        db = MagicMock()
        result = compute_site_data_quality(db, 1, date(2025, 6, 1))

        assert "computed_at" in result
        assert isinstance(result["computed_at"], str)

    @patch("services.data_quality_service._dim_consistency")
    @patch("services.data_quality_service._dim_accuracy")
    @patch("services.data_quality_service._dim_freshness")
    @patch("services.data_quality_service._dim_completeness")
    def test_dimensions_dict_has_all_4(self, mock_comp, mock_fresh, mock_acc, mock_cons):
        mocks = self._mock_dims()
        mock_comp.return_value = mocks["_dim_completeness"]
        mock_fresh.return_value = mocks["_dim_freshness"]
        mock_acc.return_value = mocks["_dim_accuracy"]
        mock_cons.return_value = mocks["_dim_consistency"]

        db = MagicMock()
        result = compute_site_data_quality(db, 1, date(2025, 6, 1))

        dims = result["dimensions"]
        assert "completeness" in dims
        assert "freshness" in dims
        assert "accuracy" in dims
        assert "consistency" in dims

    @patch("services.data_quality_service._dim_consistency")
    @patch("services.data_quality_service._dim_accuracy")
    @patch("services.data_quality_service._dim_freshness")
    @patch("services.data_quality_service._dim_completeness")
    def test_score_capped_at_100(self, mock_comp, mock_fresh, mock_acc, mock_cons):
        # Even with impossibly high dimension scores, global should cap at 100
        mocks = self._mock_dims(120, 120, 120, 120)
        mock_comp.return_value = mocks["_dim_completeness"]
        mock_fresh.return_value = mocks["_dim_freshness"]
        mock_acc.return_value = mocks["_dim_accuracy"]
        mock_cons.return_value = mocks["_dim_consistency"]

        db = MagicMock()
        result = compute_site_data_quality(db, 1, date(2025, 6, 1))

        assert result["score"] <= 100.0


# ── compute_portfolio_data_quality ──────────────────────────────────────────

class TestPortfolioDataQuality:
    @patch("services.data_quality_service.compute_site_data_quality")
    def test_avg_score_computed(self, mock_site_dq):
        mock_site_dq.side_effect = [
            {"site_id": 1, "score": 80, "grade": "B", "dimensions": {}, "recommendations": [], "computed_at": "t"},
            {"site_id": 2, "score": 60, "grade": "C", "dimensions": {}, "recommendations": [], "computed_at": "t"},
        ]

        db = MagicMock()
        # Mock the query chain for site_ids
        db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [
            (1,), (2,)
        ]

        result = compute_portfolio_data_quality(db, 1, date(2025, 6, 1))

        assert result["avg_score"] == 70.0
        assert result["grade"] == "B"
        assert result["org_id"] == 1
        assert len(result["sites"]) == 2

    @patch("services.data_quality_service.compute_site_data_quality")
    def test_grade_distribution(self, mock_site_dq):
        mock_site_dq.side_effect = [
            {"site_id": 1, "score": 90, "grade": "A", "dimensions": {}, "recommendations": [], "computed_at": "t"},
            {"site_id": 2, "score": 75, "grade": "B", "dimensions": {}, "recommendations": [], "computed_at": "t"},
            {"site_id": 3, "score": 20, "grade": "F", "dimensions": {}, "recommendations": [], "computed_at": "t"},
        ]

        db = MagicMock()
        db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [
            (1,), (2,), (3,)
        ]

        result = compute_portfolio_data_quality(db, 1, date(2025, 6, 1))

        assert result["grade_distribution"]["A"] == 1
        assert result["grade_distribution"]["B"] == 1
        assert result["grade_distribution"]["F"] == 1

    @patch("services.data_quality_service.compute_site_data_quality")
    def test_worst_sites_max_3(self, mock_site_dq):
        sites_data = [
            {"site_id": i, "score": i * 10, "grade": "F", "dimensions": {}, "recommendations": [], "computed_at": "t"}
            for i in range(1, 6)
        ]
        mock_site_dq.side_effect = sites_data

        db = MagicMock()
        db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [
            (i,) for i in range(1, 6)
        ]

        result = compute_portfolio_data_quality(db, 1, date(2025, 6, 1))

        assert len(result["worst_sites"]) == 3
        # Worst first (lowest score)
        assert result["worst_sites"][0]["score"] <= result["worst_sites"][1]["score"]

    @patch("services.data_quality_service.compute_site_data_quality")
    def test_empty_org(self, mock_site_dq):
        db = MagicMock()
        db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []

        result = compute_portfolio_data_quality(db, 1, date(2025, 6, 1))

        assert result["avg_score"] == 0
        assert result["grade"] == "F"
        assert len(result["sites"]) == 0


# ── API Endpoints ───────────────────────────────────────────────────────────

class TestEndpoints:
    """Source-level checks: verify routes are registered with expected paths."""

    def test_site_endpoint_exists(self):
        from routes.data_quality import router
        paths = [r.path for r in router.routes]
        assert any("/site/{site_id}" in p for p in paths), f"Missing /site/{{site_id}} in {paths}"

    def test_portfolio_endpoint_exists(self):
        from routes.data_quality import router
        paths = [r.path for r in router.routes]
        assert any("/portfolio" in p for p in paths), f"Missing /portfolio in {paths}"

    def test_site_endpoint_is_get(self):
        from routes.data_quality import router
        for r in router.routes:
            if hasattr(r, "path") and "/site/{site_id}" in r.path:
                assert "GET" in r.methods
