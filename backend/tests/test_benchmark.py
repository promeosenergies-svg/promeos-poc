"""
PROMEOS - Tests for benchmark utility and endpoint
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.electric_monitoring.benchmark import compute_percentiles, compute_rank, build_benchmark


class TestComputePercentiles:
    def test_basic_5_values(self):
        p = compute_percentiles([1, 2, 3, 4, 5])
        assert p["p50"] == 3.0
        assert p["p25"] == 2.0
        assert p["p75"] == 4.0

    def test_single_value(self):
        p = compute_percentiles([10])
        assert p["p50"] == 10.0

    def test_empty(self):
        p = compute_percentiles([])
        assert p["p50"] == 0

    def test_even_count(self):
        p = compute_percentiles([1, 2, 3, 4])
        assert p["p50"] == 2.5

    def test_unsorted_input(self):
        p = compute_percentiles([5, 3, 1, 4, 2])
        assert p["p50"] == 3.0


class TestComputeRank:
    def test_middle_value(self):
        r = compute_rank(3, [1, 2, 3, 4, 5])
        assert 40 <= r <= 60

    def test_lowest(self):
        r = compute_rank(1, [1, 2, 3, 4, 5])
        assert r <= 20

    def test_highest(self):
        r = compute_rank(5, [1, 2, 3, 4, 5])
        assert r >= 80

    def test_empty_values(self):
        assert compute_rank(5, []) == 50


class TestBuildBenchmark:
    def test_basic(self):
        target = {"pbase_kw": 5.0, "off_hours_ratio": 0.3}
        peers = [
            {"pbase_kw": 3.0, "off_hours_ratio": 0.15},
            {"pbase_kw": 6.0, "off_hours_ratio": 0.25},
            {"pbase_kw": 10.0, "off_hours_ratio": 0.40},
        ]
        result = build_benchmark(target, peers, ["pbase_kw", "off_hours_ratio"])
        assert result["pbase_kw"] is not None
        assert result["pbase_kw"]["value"] == 5.0
        assert "percentile" in result["pbase_kw"]
        assert "p25" in result["pbase_kw"]

    def test_insufficient_peers(self):
        target = {"pbase_kw": 5.0}
        peers = [{"pbase_kw": 3.0}]
        result = build_benchmark(target, peers, ["pbase_kw"])
        assert result["pbase_kw"] is None

    def test_missing_target_kpi(self):
        target = {"pbase_kw": None}
        peers = [{"pbase_kw": 3.0}, {"pbase_kw": 6.0}, {"pbase_kw": 10.0}]
        result = build_benchmark(target, peers, ["pbase_kw"])
        assert result["pbase_kw"] is None
