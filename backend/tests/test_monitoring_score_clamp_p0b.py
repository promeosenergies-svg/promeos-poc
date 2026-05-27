"""Test C1 Énergie P0b — Score Monitoring borné [0, 100].

Brief : si la logique de calcul est BE, le clamp doit s'y faire. Si un
snapshot legacy a un score 108 persisté avant le fix, la lecture clamp
defense-in-depth via _clamp_monitoring_score garantit que le payload reste
∈ [0, 100].
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routes.monitoring import _clamp_monitoring_score  # noqa: E402


class TestClampMonitoringScore:
    def test_score_above_100_becomes_100(self):
        assert _clamp_monitoring_score(108) == 100
        assert _clamp_monitoring_score(150.5) == 100
        assert _clamp_monitoring_score(1000) == 100

    def test_score_below_0_becomes_0(self):
        assert _clamp_monitoring_score(-5) == 0
        assert _clamp_monitoring_score(-100.7) == 0

    def test_score_in_range_preserved(self):
        assert _clamp_monitoring_score(0) == 0
        assert _clamp_monitoring_score(50) == 50
        assert _clamp_monitoring_score(100) == 100
        assert _clamp_monitoring_score(75.4) == 75
        assert _clamp_monitoring_score(75.6) == 76

    def test_none_stays_none(self):
        """None signifie 'pas de score disponible' — préservé tel quel
        pour ne pas mentir avec un faux 0."""
        assert _clamp_monitoring_score(None) is None

    def test_invalid_string_returns_0(self):
        """String non castable → fallback 0 défensif."""
        assert _clamp_monitoring_score("not-a-number") == 0
        assert _clamp_monitoring_score("") == 0
