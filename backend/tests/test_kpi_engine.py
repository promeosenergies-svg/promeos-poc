"""
PROMEOS Electric Monitoring - Test KPI Engine
Tests for weekend/night ratios, hourly profiles, monthly breakdown.
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


def _make_week_readings(base_day=10, base_night=3, base_weekend=4):
    """Generate 1 week of hourly readings (Mon-Sun)."""
    # Start on a Monday
    start = datetime(2025, 1, 6, 0, 0)  # Monday
    readings = []
    for day in range(7):
        dt = start + timedelta(days=day)
        is_weekend = dt.weekday() >= 5
        for hour in range(24):
            ts = dt.replace(hour=hour)
            if is_weekend:
                value = base_weekend
            elif 8 <= hour <= 18:
                value = base_day
            else:
                value = base_night
            readings.append({"timestamp": ts, "value_kwh": float(value)})
    return readings


class TestWeekendRatio:
    def test_office_pattern_low_weekend(self, engine):
        readings = _make_week_readings(base_day=30, base_night=5, base_weekend=5)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["weekend_ratio"] < 0.5

    def test_commerce_pattern_high_weekend(self, engine):
        readings = _make_week_readings(base_day=20, base_night=15, base_weekend=18)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["weekend_ratio"] > 0.8

    def test_equal_consumption_ratio_1(self, engine):
        readings = _make_week_readings(base_day=10, base_night=10, base_weekend=10)
        kpis = engine.compute(readings, interval_minutes=60)
        assert abs(kpis["weekend_ratio"] - 1.0) < 0.01


class TestNightRatio:
    def test_night_ratio_with_night_consumption(self, engine):
        readings = _make_week_readings(base_day=20, base_night=20, base_weekend=20)
        kpis = engine.compute(readings, interval_minutes=60)
        # Night = 22:00-06:00 = 8h out of 24h = 33%
        assert 0.30 <= kpis["night_ratio"] <= 0.36

    def test_zero_night_low_ratio(self, engine):
        # Only consumption during 8-18
        start = datetime(2025, 1, 6, 0, 0)
        readings = []
        for day in range(7):
            dt = start + timedelta(days=day)
            for hour in range(24):
                ts = dt.replace(hour=hour)
                value = 20.0 if 8 <= hour <= 18 else 0.1
                readings.append({"timestamp": ts, "value_kwh": value})
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["night_ratio"] < 0.05


class TestHourlyProfile:
    def test_weekday_profile_24_hours(self, engine):
        readings = _make_week_readings()
        kpis = engine.compute(readings, interval_minutes=60)
        assert len(kpis["weekday_profile_kw"]) == 24
        assert len(kpis["weekend_profile_kw"]) == 24

    def test_weekday_profile_reflects_pattern(self, engine):
        readings = _make_week_readings(base_day=30, base_night=5, base_weekend=5)
        kpis = engine.compute(readings, interval_minutes=60)
        profile = kpis["weekday_profile_kw"]
        # Office hours should be higher
        assert profile[12] > profile[2]
        assert profile[10] > profile[3]

    def test_weekend_profile_flat(self, engine):
        readings = _make_week_readings(base_day=30, base_night=5, base_weekend=8)
        kpis = engine.compute(readings, interval_minutes=60)
        we_profile = kpis["weekend_profile_kw"]
        # Weekend should be roughly constant
        non_zero = [v for v in we_profile if v > 0]
        if non_zero:
            cv = (max(non_zero) - min(non_zero)) / (sum(non_zero) / len(non_zero))
            assert cv < 0.1  # Very flat


class TestMonthlyBreakdown:
    def test_monthly_keys(self, engine):
        # 90 days crossing 3 months
        start = datetime(2025, 1, 1)
        readings = [
            {"timestamp": start + timedelta(hours=i), "value_kwh": 10.0}
            for i in range(90 * 24)
        ]
        kpis = engine.compute(readings, interval_minutes=60)
        monthly = kpis["monthly_kwh"]
        assert "2025-01" in monthly
        assert "2025-02" in monthly
        assert "2025-03" in monthly

    def test_monthly_sums_match_total(self, engine):
        start = datetime(2025, 1, 1)
        readings = [
            {"timestamp": start + timedelta(hours=i), "value_kwh": 10.0}
            for i in range(48)
        ]
        kpis = engine.compute(readings, interval_minutes=60)
        monthly_sum = sum(kpis["monthly_kwh"].values())
        assert abs(monthly_sum - kpis["total_kwh"]) < 0.01


class TestBaseLoad:
    def test_pbase_is_p10(self, engine):
        # P10 should be close to the lowest values
        values = [5.0] * 80 + [50.0] * 20  # 80% at 5, 20% at 50
        start = datetime(2025, 1, 6)
        readings = [
            {"timestamp": start + timedelta(hours=i), "value_kwh": v}
            for i, v in enumerate(values)
        ]
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["pbase_kw"] == 5.0

    def test_pbase_night_from_night_hours(self, engine):
        # Night base should be computed from 00:00-05:00
        readings = _make_week_readings(base_day=30, base_night=5, base_weekend=5)
        kpis = engine.compute(readings, interval_minutes=60)
        assert kpis["pbase_night_kw"] <= kpis["pmean_kw"]


class TestKPICompleteness:
    def test_all_kpi_keys_present(self, engine):
        readings = _make_week_readings()
        kpis = engine.compute(readings, interval_minutes=60)
        expected_keys = [
            "pmax_kw", "p95_kw", "p99_kw", "pmean_kw", "pbase_kw", "pbase_night_kw",
            "load_factor", "peak_to_average", "weekend_ratio", "night_ratio",
            "total_kwh", "readings_count", "interval_minutes",
            "ramp_rate_max_kw_h", "weekday_profile_kw", "weekend_profile_kw",
            "monthly_kwh"
        ]
        for key in expected_keys:
            assert key in kpis, f"Missing KPI key: {key}"
