"""
PROMEOS Electric Monitoring - Test Power Calculations
Tests for P = E / (interval/60), percentile, load factor, peak-to-average.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from services.electric_monitoring.kpi_engine import KPIEngine


@pytest.fixture
def engine():
    return KPIEngine()


def _make_readings(values, start=None, interval_minutes=60):
    """Helper to create readings from a list of kWh values."""
    if start is None:
        start = datetime(2025, 1, 1, 0, 0)
    return [
        {"timestamp": start + timedelta(minutes=i * interval_minutes), "value_kwh": v}
        for i, v in enumerate(values)
    ]


class TestPowerFromEnergy:
    """P(kW) = E(kWh) / (interval_minutes / 60)"""

    def test_hourly_1kwh_is_1kw(self, engine):
        readings = _make_readings([1.0])
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["pmax_kw"] == 1.0

    def test_hourly_10kwh_is_10kw(self, engine):
        readings = _make_readings([10.0])
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["pmax_kw"] == 10.0

    def test_30min_5kwh_is_10kw(self, engine):
        readings = _make_readings([5.0], interval_minutes=30)
        kpis = engine.compute(readings, interval_minutes=30)
        assert kpis["pmax_kw"] == 10.0

    def test_15min_2_5kwh_is_10kw(self, engine):
        readings = _make_readings([2.5], interval_minutes=15)
        kpis = engine.compute(readings, interval_minutes=15)
        assert kpis["pmax_kw"] == 10.0


class TestPercentile:
    """Pure Python percentile calculation."""

    def test_p95_of_100_values(self, engine):
        values = list(range(1, 101))  # 1 to 100
        p95 = engine._percentile(values, 95)
        assert 94 <= p95 <= 96

    def test_p10_of_100_values(self, engine):
        values = list(range(1, 101))
        p10 = engine._percentile(values, 10)
        assert 9 <= p10 <= 11

    def test_p50_is_median(self, engine):
        values = [1, 2, 3, 4, 5]
        p50 = engine._percentile(values, 50)
        assert p50 == 3.0

    def test_empty_returns_zero(self, engine):
        assert engine._percentile([], 95) == 0.0

    def test_single_value(self, engine):
        assert engine._percentile([42.0], 50) == 42.0

    def test_unsorted_input(self, engine):
        values = [5, 1, 3, 2, 4]
        p50 = engine._percentile(values, 50)
        assert p50 == 3.0


class TestLoadFactor:
    """Load factor = E_total / (Pmax * total_hours)"""

    def test_flat_curve_load_factor_1(self, engine):
        # All readings same value => load factor = 1.0
        readings = _make_readings([10.0] * 24)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["load_factor"] == 1.0

    def test_variable_curve_load_factor_less_than_1(self, engine):
        # Mix of high and low => load factor < 1
        values = [5.0] * 12 + [20.0] * 12
        readings = _make_readings(values)
        kpis = engine.compute(readings, interval_minutes=60)
        assert 0 < kpis["load_factor"] < 1.0

    def test_single_spike_low_load_factor(self, engine):
        values = [1.0] * 23 + [100.0]
        readings = _make_readings(values)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["load_factor"] < 0.2


class TestPeakToAverage:
    """Peak-to-average = Pmax / Pmean"""

    def test_flat_curve_pta_1(self, engine):
        readings = _make_readings([10.0] * 24)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["peak_to_average"] == 1.0

    def test_spike_high_pta(self, engine):
        values = [1.0] * 23 + [100.0]
        readings = _make_readings(values)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["peak_to_average"] > 5.0


class TestRampRate:
    """Ramp rate: max delta P between consecutive readings."""

    def test_constant_zero_ramp(self, engine):
        readings = _make_readings([10.0] * 24)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["ramp_rate_max_kw_h"] == 0.0

    def test_step_change_ramp(self, engine):
        values = [10.0] * 12 + [50.0] * 12
        readings = _make_readings(values)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["ramp_rate_max_kw_h"] == 40.0


class TestEmptyInput:
    def test_empty_readings(self, engine):
        kpis = engine.compute([], interval_minutes=60)
        assert kpis["pmax_kw"] == 0
        assert kpis["total_kwh"] == 0
        assert kpis["readings_count"] == 0
