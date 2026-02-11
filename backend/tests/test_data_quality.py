"""
PROMEOS Electric Monitoring - Test Data Quality Engine
Tests for gap detection, duplicates, DST, negatives, completeness.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from services.electric_monitoring.data_quality import DataQualityEngine


@pytest.fixture
def engine():
    return DataQualityEngine()


def _make_readings(count=24, interval_minutes=60, start=None, value=10.0):
    """Generate uniform readings."""
    if start is None:
        start = datetime(2025, 1, 1, 0, 0)
    return [
        {"timestamp": start + timedelta(minutes=i * interval_minutes), "value_kwh": value}
        for i in range(count)
    ]


class TestCompleteness:
    def test_perfect_completeness(self, engine):
        readings = _make_readings(24)
        result = engine.compute(readings, interval_minutes=60)
        assert result["completeness_pct"] >= 99
        assert result["quality_score"] >= 90

    def test_half_completeness(self, engine):
        start = datetime(2025, 1, 1)
        # Only 12 readings for a 24-hour period
        readings = _make_readings(12, start=start)
        result = engine.compute(
            readings, interval_minutes=60,
            period_start=start,
            period_end=start + timedelta(hours=23)
        )
        assert result["completeness_pct"] < 60

    def test_empty_readings(self, engine):
        result = engine.compute([])
        assert result["quality_score"] == 0
        assert result["quality_level"] == "poor"


class TestGapDetection:
    def test_no_gaps(self, engine):
        readings = _make_readings(24)
        result = engine.compute(readings, interval_minutes=60)
        assert result["gap_count"] == 0

    def test_single_gap(self, engine):
        start = datetime(2025, 1, 1)
        readings = _make_readings(10, start=start)
        # Add gap: skip 5 hours
        readings += _make_readings(10, start=start + timedelta(hours=15))
        result = engine.compute(readings, interval_minutes=60)
        assert result["gap_count"] >= 1
        assert result["max_gap_hours"] >= 4.0

    def test_multiple_gaps(self, engine):
        start = datetime(2025, 1, 1)
        readings = []
        # 3 chunks with 2 gaps
        for offset in [0, 10, 20]:
            readings += _make_readings(5, start=start + timedelta(hours=offset))
        result = engine.compute(readings, interval_minutes=60)
        assert result["gap_count"] >= 2

    def test_gap_list_populated(self, engine):
        start = datetime(2025, 1, 1)
        readings = _make_readings(5, start=start)
        readings += _make_readings(5, start=start + timedelta(hours=12))
        result = engine.compute(readings, interval_minutes=60)
        assert len(result["gaps"]) >= 1
        assert "start" in result["gaps"][0]
        assert "duration_hours" in result["gaps"][0]


class TestDuplicates:
    def test_no_duplicates(self, engine):
        readings = _make_readings(24)
        result = engine.compute(readings, interval_minutes=60)
        assert result["duplicate_count"] == 0

    def test_with_duplicates(self, engine):
        readings = _make_readings(24)
        # Add 3 duplicates (same timestamp)
        readings.append({"timestamp": readings[0]["timestamp"], "value_kwh": 10.0})
        readings.append({"timestamp": readings[1]["timestamp"], "value_kwh": 10.0})
        readings.append({"timestamp": readings[2]["timestamp"], "value_kwh": 10.0})
        result = engine.compute(readings, interval_minutes=60)
        assert result["duplicate_count"] == 3

    def test_duplicates_lower_score(self, engine):
        clean = _make_readings(100)
        dirty = list(clean)
        for i in range(10):
            dirty.append({"timestamp": clean[i]["timestamp"], "value_kwh": 10.0})
        clean_result = engine.compute(clean, interval_minutes=60)
        dirty_result = engine.compute(dirty, interval_minutes=60)
        assert dirty_result["quality_score"] <= clean_result["quality_score"]


class TestNegativeValues:
    def test_no_negatives(self, engine):
        readings = _make_readings(24, value=10.0)
        result = engine.compute(readings, interval_minutes=60)
        assert result["negative_count"] == 0

    def test_with_negatives(self, engine):
        readings = _make_readings(24, value=10.0)
        readings[5]["value_kwh"] = -5.0
        readings[10]["value_kwh"] = -2.0
        result = engine.compute(readings, interval_minutes=60)
        assert result["negative_count"] == 2

    def test_negatives_trigger_issue(self, engine):
        readings = _make_readings(24, value=10.0)
        readings[5]["value_kwh"] = -5.0
        result = engine.compute(readings, interval_minutes=60)
        neg_issues = [i for i in result["issues"] if i["type"] == "negative_values"]
        assert len(neg_issues) == 1


class TestOutliers:
    def test_no_outliers_uniform(self, engine):
        readings = _make_readings(100, value=10.0)
        result = engine.compute(readings, interval_minutes=60)
        assert result["outlier_count"] == 0

    def test_extreme_outlier_detected(self, engine):
        readings = _make_readings(100, value=10.0)
        readings[50]["value_kwh"] = 1000.0  # Extreme outlier
        result = engine.compute(readings, interval_minutes=60)
        assert result["outlier_count"] >= 1


class TestQualityLevel:
    def test_excellent_quality(self, engine):
        readings = _make_readings(100, value=10.0)
        result = engine.compute(readings, interval_minutes=60)
        assert result["quality_level"] == "excellent"

    def test_poor_quality_with_issues(self, engine):
        start = datetime(2025, 1, 1)
        readings = _make_readings(10, start=start, value=10.0)
        # Many negatives
        for r in readings[:5]:
            r["value_kwh"] = -1.0
        result = engine.compute(
            readings, interval_minutes=60,
            period_start=start,
            period_end=start + timedelta(hours=100)
        )
        assert result["quality_level"] in ("poor", "fair")


class TestScoreDetails:
    def test_details_present(self, engine):
        readings = _make_readings(24)
        result = engine.compute(readings, interval_minutes=60)
        details = result["details"]
        assert "score_completeness" in details
        assert "score_gaps" in details
        assert "score_duplicates" in details
        assert "score_negatives" in details
        assert "score_outliers" in details
