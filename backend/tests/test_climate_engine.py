"""
PROMEOS Electric Monitoring - Climate Engine Tests
Tests correlation, slope, balance point computation.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import math
from datetime import datetime, timedelta
from services.electric_monitoring.climate_engine import ClimateEngine


@pytest.fixture
def engine():
    return ClimateEngine()


def _make_correlated_data(days=60, base_kwh=200, heating_slope=8.0, cooling_slope=0.0):
    """Generate readings + weather with known heating/cooling correlation."""
    start = datetime(2025, 1, 1, 0, 0)
    readings = []
    weather = []

    for d in range(days):
        dt = start + timedelta(days=d)
        day_of_year = dt.timetuple().tm_yday
        # Sinusoidal temperature: cold in winter, warm in summer
        temp = 12.0 - 10.0 * math.cos(2 * math.pi * (day_of_year - 15) / 365)

        # Daily kWh = base + heating_slope * max(0, 15-T) + cooling_slope * max(0, T-22)
        daily_target = base_kwh + heating_slope * max(0, 15 - temp) + cooling_slope * max(0, temp - 22)

        # Distribute evenly across 24 hours
        hourly = daily_target / 24
        for h in range(24):
            ts = dt.replace(hour=h)
            readings.append({"timestamp": ts, "value_kwh": round(hourly, 2)})

        weather.append({
            "date": dt.date().isoformat(),
            "temp_avg_c": round(temp, 1),
        })

    return readings, weather


class TestClimateHeating:
    def test_detects_heating_slope(self, engine):
        readings, weather = _make_correlated_data(days=90, heating_slope=8.0)
        result = engine.compute(readings, weather)
        assert result["slope_kw_per_c"] > 2
        assert result["label"] == "heating_dominant"
        assert result["r_squared"] > 0.5

    def test_balance_point_reasonable(self, engine):
        readings, weather = _make_correlated_data(days=90, heating_slope=8.0)
        result = engine.compute(readings, weather)
        # Tb should be in 10-20 range
        assert result["balance_point_c"] is not None
        assert 8 <= result["balance_point_c"] <= 22

    def test_correlation_negative_for_heating(self, engine):
        readings, weather = _make_correlated_data(days=60, heating_slope=10.0)
        result = engine.compute(readings, weather)
        # Heating: more consumption when colder → negative correlation
        assert result["correlation_r"] is not None
        assert result["correlation_r"] < 0


class TestClimateCooling:
    def test_detects_cooling(self, engine):
        # Start in June for warm temps
        start = datetime(2025, 6, 1)
        readings = []
        weather = []
        for d in range(90):
            dt = start + timedelta(days=d)
            temp = 22 + 8 * math.sin(2 * math.pi * d / 90)  # 22-30 range
            daily = 200 + 6.0 * max(0, temp - 22)
            for h in range(24):
                readings.append({"timestamp": dt.replace(hour=h), "value_kwh": round(daily / 24, 2)})
            weather.append({"date": dt.date().isoformat(), "temp_avg_c": round(temp, 1)})

        result = engine.compute(readings, weather)
        assert result["n_points"] >= 10
        assert result["label"] in ("cooling_dominant", "mixed")


class TestClimateFlat:
    def test_flat_profile(self, engine):
        readings, weather = _make_correlated_data(days=60, heating_slope=0.0, cooling_slope=0.0)
        result = engine.compute(readings, weather)
        assert result["slope_kw_per_c"] < 1.5
        assert result["label"] == "flat"


class TestClimateEmpty:
    def test_empty_readings(self, engine):
        result = engine.compute([], [])
        assert result["n_points"] == 0
        assert result["correlation_r"] is None
        assert result["slope_kw_per_c"] is None

    def test_insufficient_data(self, engine):
        # Only 5 days — below threshold of 10
        readings, weather = _make_correlated_data(days=5, heating_slope=8.0)
        result = engine.compute(readings, weather)
        assert result["n_points"] < 10

    def test_no_weather(self, engine):
        readings, _ = _make_correlated_data(days=30)
        result = engine.compute(readings, [])
        assert result["n_points"] == 0


class TestClimateReasonCodes:
    """Ensure reason codes are present when analysis cannot run."""

    def test_no_meter_reason(self, engine):
        result = engine.compute([], [])
        assert result.get("reason") == "no_meter"

    def test_no_weather_reason(self, engine):
        readings, _ = _make_correlated_data(days=30)
        result = engine.compute(readings, [])
        assert result.get("reason") == "no_weather"

    def test_insufficient_readings_reason(self, engine):
        readings, weather = _make_correlated_data(days=5)
        result = engine.compute(readings, weather)
        assert result.get("reason") == "insufficient_readings"

    def test_no_reason_when_successful(self, engine):
        readings, weather = _make_correlated_data(days=60, heating_slope=8.0)
        result = engine.compute(readings, weather)
        assert "reason" not in result
        assert result["slope_kw_per_c"] is not None


class TestClimateScatter:
    def test_scatter_has_correct_shape(self, engine):
        readings, weather = _make_correlated_data(days=60, heating_slope=8.0)
        result = engine.compute(readings, weather)
        assert len(result["scatter"]) == result["n_points"]
        for pt in result["scatter"]:
            assert "T" in pt
            assert "kwh" in pt
            assert "predicted" in pt

    def test_fit_line_exists(self, engine):
        readings, weather = _make_correlated_data(days=60, heating_slope=8.0)
        result = engine.compute(readings, weather)
        assert len(result["fit_line"]) > 0
        for pt in result["fit_line"]:
            assert "T" in pt
            assert "predicted" in pt
