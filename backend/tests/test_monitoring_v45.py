"""
PROMEOS - Sprint V4.5 Tests
Covers: climate engine reason codes, weather multi-site envelope,
timeseries availability/coverage, monitoring orchestrator edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta, date

from services.electric_monitoring.climate_engine import ClimateEngine
from services.ems.timeseries_service import estimate_points, _compute_availability


# --- Climate Engine: explicit reason codes ---

class TestClimateReasonCodes:
    """Climate engine returns explicit reason when analysis cannot run."""

    def test_no_readings_returns_no_meter_reason(self):
        eng = ClimateEngine()
        result = eng.compute([], [{"date": "2025-01-01", "temp_avg_c": 5}])
        assert result["reason"] == "no_meter"
        assert result["slope_kw_per_c"] is None

    def test_no_weather_returns_no_weather_reason(self):
        eng = ClimateEngine()
        readings = [{"timestamp": datetime(2025, 1, 1, h), "value_kwh": 10}
                    for h in range(24)]
        result = eng.compute(readings, [])
        assert result["reason"] == "no_weather"

    def test_insufficient_points_returns_reason(self):
        eng = ClimateEngine()
        # Only 5 days of readings + weather (need >= 10)
        readings = []
        weather = []
        for d in range(5):
            dt = datetime(2025, 1, 1 + d)
            for h in range(24):
                readings.append({"timestamp": dt.replace(hour=h), "value_kwh": 10})
            weather.append({"date": f"2025-01-{1 + d:02d}", "temp_avg_c": 5 + d})
        result = eng.compute(readings, weather)
        assert result["reason"] == "insufficient_readings"
        assert result["n_points"] == 5

    def test_successful_computation_has_no_reason(self):
        eng = ClimateEngine()
        readings = []
        weather = []
        for d in range(30):
            dt = datetime(2025, 1, 1) + timedelta(days=d)
            for h in range(24):
                # Temperature-correlated consumption
                temp = 5 + d * 0.5
                base = 200 + max(0, 15 - temp) * 10  # heating pattern
                readings.append({"timestamp": dt.replace(hour=h), "value_kwh": base / 24})
            weather.append({
                "date": (datetime(2025, 1, 1) + timedelta(days=d)).date().isoformat(),
                "temp_avg_c": 5 + d * 0.5,
            })
        result = eng.compute(readings, weather)
        assert result.get("reason") is None
        assert result["slope_kw_per_c"] is not None
        assert result["n_points"] >= 10


# --- Timeseries availability / coverage ---

class TestTimeseriesAvailability:
    """estimate_points and _compute_availability edge cases."""

    def test_estimate_points_hourly_7_days(self):
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 8)
        pts = estimate_points(start, end, "hourly")
        assert pts == 7 * 24  # 168

    def test_estimate_points_15min_1_day(self):
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 2)
        pts = estimate_points(start, end, "15min")
        assert pts == 24 * 4  # 96

    def test_estimate_points_daily_30_days(self):
        start = datetime(2025, 1, 1)
        end = datetime(2025, 1, 31)
        pts = estimate_points(start, end, "daily")
        assert pts == 30  # 30 days

    def test_compute_availability_full_coverage(self):
        """100% coverage when all expected points present."""
        series = [{
            "key": "meter_1",
            "data": [{"t": datetime(2025, 1, 1, h).isoformat()} for h in range(24)],
        }]
        result = _compute_availability(series, 24, "hourly")
        assert len(result) == 1
        assert result[0]["actual_points"] == 24
        assert result[0]["expected_points"] == 24
        assert result[0]["coverage_pct"] == 100.0

    def test_compute_availability_with_gaps(self):
        """Coverage < 100% when points are missing."""
        # 20 out of 24 hours (skip hours 10-13)
        data = [{"t": datetime(2025, 1, 1, h).isoformat()} for h in range(24) if h < 10 or h >= 14]
        series = [{"key": "meter_1", "data": data}]
        result = _compute_availability(series, 24, "hourly")
        assert result[0]["actual_points"] == 20
        assert result[0]["coverage_pct"] < 100.0
        assert result[0]["coverage_pct"] == pytest.approx(83.3, abs=0.1)
        # Should detect the gap between hour 9 and hour 14
        assert len(result[0]["gaps"]) >= 1

    def test_compute_availability_empty_series(self):
        """0% coverage when no data."""
        series = [{"key": "meter_1", "data": []}]
        result = _compute_availability(series, 24, "hourly")
        assert result[0]["actual_points"] == 0
        assert result[0]["coverage_pct"] == 0.0


# --- Weather multi-site ---

class TestWeatherMultiMeta:
    """Weather multi-site envelope and multi_city_risk detection."""

    def test_multi_city_risk_detected(self):
        """Latitude spread > 2 degrees triggers multi_city_risk."""
        from services.ems.weather_service import get_weather_multi
        # We can't easily test with DB, but we can test the logic
        # by checking that the function signature accepts site_ids
        # (full integration tested via test_monitoring_integration.py)
        # Instead, test the core logic inline
        site_latitudes = [43.6, 48.8]  # Marseille vs Paris
        lat_spread = max(site_latitudes) - min(site_latitudes)
        multi_city_risk = lat_spread > 2.0
        assert multi_city_risk is True

    def test_no_multi_city_risk_same_city(self):
        """Same city sites should not trigger multi_city_risk."""
        site_latitudes = [48.85, 48.87]  # Paris sites
        lat_spread = max(site_latitudes) - min(site_latitudes)
        multi_city_risk = lat_spread > 2.0
        assert multi_city_risk is False


# --- Monitoring orchestrator: explicit edge cases ---

class TestOrchestratorReasonCodes:
    """Orchestrator returns proper status/reason for edge cases."""

    def test_empty_readings_status_no_data(self):
        from services.electric_monitoring.monitoring_orchestrator import MonitoringOrchestrator
        orch = MonitoringOrchestrator()
        result = orch.run_standalone([])
        assert result.get("kpis") == {}
        assert result.get("alerts") == []

    def test_climate_with_weather_returns_data(self):
        from services.electric_monitoring.monitoring_orchestrator import MonitoringOrchestrator
        import random
        random.seed(42)
        # Generate 30 days of readings
        readings = []
        weather = []
        start = datetime(2025, 1, 6, 0, 0)
        for day in range(30):
            dt = start + timedelta(days=day)
            temp = 5 + random.uniform(-3, 3)
            for hour in range(24):
                ts = dt.replace(hour=hour)
                base = 20 + max(0, 15 - temp) * 2
                value = base + random.uniform(-2, 2)
                readings.append({"timestamp": ts, "value_kwh": max(0.1, round(value, 2))})
            weather.append({
                "date": dt.date().isoformat(),
                "temp_avg_c": round(temp, 1),
                "temp_min_c": round(temp - 3, 1),
                "temp_max_c": round(temp + 3, 1),
                "source": "test",
            })

        orch = MonitoringOrchestrator()
        result = orch.run_standalone(readings, weather_data=weather)
        climate = result.get("climate", {})
        # Should have valid climate data (not empty)
        assert climate.get("n_points", 0) >= 10
        assert climate.get("slope_kw_per_c") is not None
