"""
PROMEOS Electric Monitoring - Integration Test
Tests the full orchestrator pipeline (standalone mode, no DB).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from services.electric_monitoring.monitoring_orchestrator import MonitoringOrchestrator
from services.electric_monitoring.kpi_engine import KPIEngine
from services.electric_monitoring.power_engine import PowerEngine
from services.electric_monitoring.data_quality import DataQualityEngine
from services.electric_monitoring.alert_engine import AlertEngine


def _make_office_readings(days=30):
    """Generate realistic office readings."""
    start = datetime(2025, 1, 6, 0, 0)
    readings = []
    import random

    random.seed(42)
    for day in range(days):
        dt = start + timedelta(days=day)
        is_weekend = dt.weekday() >= 5
        for hour in range(24):
            ts = dt.replace(hour=hour)
            if is_weekend:
                value = 3.0 + random.uniform(-0.5, 0.5)
            elif 8 <= hour <= 18:
                value = 25.0 + random.uniform(-3, 3)
            elif 7 <= hour <= 7 or 19 <= hour <= 20:
                value = 12.0 + random.uniform(-2, 2)
            else:
                value = 4.0 + random.uniform(-0.5, 0.5)
            readings.append({"timestamp": ts, "value_kwh": max(0.1, round(value, 2))})
    return readings


def _make_anomalous_readings(days=30):
    """Generate readings with embedded anomalies."""
    start = datetime(2025, 1, 6, 0, 0)
    readings = []
    import random

    random.seed(99)
    for day in range(days):
        dt = start + timedelta(days=day)
        is_weekend = dt.weekday() >= 5

        # Data gap on days 15-16
        if 15 <= day <= 16:
            continue

        for hour in range(24):
            ts = dt.replace(hour=hour)
            if is_weekend:
                value = 20.0  # High weekend
            elif 8 <= hour <= 18:
                value = 25.0
            else:
                value = 18.0  # High night base

            # Negative value
            if day == 10 and hour == 3:
                value = -5.0

            # Power spike
            if day == 20 and hour == 14:
                value = 200.0

            readings.append({"timestamp": ts, "value_kwh": round(value, 2)})
    return readings


class TestOrchestratorStandalone:
    def test_empty_readings(self):
        orch = MonitoringOrchestrator()
        result = orch.run_standalone([])
        assert result["kpis"] == {}
        assert result["alerts"] == []

    def test_office_pattern(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(30)
        result = orch.run_standalone(readings, subscribed_power_kva=100)
        assert "kpis" in result
        assert "data_quality" in result
        assert "power_risk" in result
        assert "alerts" in result
        assert result["readings_count"] == len(readings)

    def test_kpis_populated(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(7)
        result = orch.run_standalone(readings)
        kpis = result["kpis"]
        assert kpis["pmax_kw"] > 0
        assert kpis["p95_kw"] > 0
        assert kpis["pmean_kw"] > 0
        assert kpis["total_kwh"] > 0
        assert 0 < kpis["load_factor"] < 1

    def test_quality_score_clean_data(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(7)
        result = orch.run_standalone(readings)
        quality = result["data_quality"]
        assert quality["quality_score"] >= 80
        assert quality["quality_level"] in ("excellent", "good")

    def test_risk_score_safe(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(7)
        result = orch.run_standalone(readings, subscribed_power_kva=200)
        risk = result["power_risk"]
        assert risk["risk_score"] < 50
        assert risk["depassement_count"] == 0


class TestAnomalousData:
    def test_anomalous_triggers_alerts(self):
        orch = MonitoringOrchestrator()
        readings = _make_anomalous_readings(30)
        result = orch.run_standalone(readings, subscribed_power_kva=50)
        alerts = result["alerts"]
        alert_types = [a["alert_type"] for a in alerts]
        # Should detect at least some of these
        assert len(alerts) >= 2
        # Data gap -> DONNEES_MANQUANTES
        assert "DONNEES_MANQUANTES" in alert_types or result["data_quality"]["completeness_pct"] < 95
        # Negative values
        assert "VALEURS_NEGATIVES" in alert_types
        # High weekend
        assert "WEEKEND_ANORMAL" in alert_types

    def test_depassement_with_low_sub(self):
        orch = MonitoringOrchestrator()
        readings = _make_anomalous_readings(30)
        result = orch.run_standalone(readings, subscribed_power_kva=30)
        risk = result["power_risk"]
        assert risk["depassement_count"] > 0
        alert_types = [a["alert_type"] for a in result["alerts"]]
        assert "DEPASSEMENT_PUISSANCE" in alert_types

    def test_quality_score_degraded(self):
        orch = MonitoringOrchestrator()
        readings = _make_anomalous_readings(30)
        result = orch.run_standalone(readings)
        quality = result["data_quality"]
        assert quality["negative_count"] >= 1
        assert quality["gap_count"] >= 1


class TestTrendAlerts:
    def test_p95_hausse_detected(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(7)
        current_kpis = orch.kpi_engine.compute(readings)

        # Simulate previous period with lower P95
        previous_kpis = dict(current_kpis)
        previous_kpis["p95_kw"] = current_kpis["p95_kw"] * 0.6

        result = orch.run_standalone(readings, previous_kpis=previous_kpis)
        alert_types = [a["alert_type"] for a in result["alerts"]]
        assert "P95_HAUSSE" in alert_types

    def test_derive_talon_detected(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(7)
        current_kpis = orch.kpi_engine.compute(readings)

        previous_kpis = dict(current_kpis)
        previous_kpis["pbase_kw"] = current_kpis["pbase_kw"] * 0.5

        result = orch.run_standalone(readings, previous_kpis=previous_kpis)
        alert_types = [a["alert_type"] for a in result["alerts"]]
        assert "DERIVE_TALON" in alert_types


class TestPowerEngine:
    def test_high_risk_low_subscription(self):
        eng = PowerEngine()
        kpi_eng = KPIEngine()
        readings = _make_office_readings(7)
        kpis = kpi_eng.compute(readings)
        result = eng.compute(kpis, readings, subscribed_power_kva=5)
        assert result["risk_score"] > 50
        assert result["depassement_count"] > 0

    def test_low_risk_high_subscription(self):
        eng = PowerEngine()
        kpi_eng = KPIEngine()
        readings = _make_office_readings(7)
        kpis = kpi_eng.compute(readings)
        result = eng.compute(kpis, readings, subscribed_power_kva=500)
        assert result["risk_score"] < 30
        assert result["depassement_count"] == 0


class TestDemoProfilePlausibility:
    """Ensure demo profiles produce realistic KPIs."""

    def _make_profile_readings(self, profile_name, days=14):
        """Simulate demo readings using USAGE_PROFILES config."""
        import random, math
        from routes.monitoring import USAGE_PROFILES

        profile = USAGE_PROFILES[profile_name]
        start = datetime(2025, 6, 1, 0, 0)
        readings = []
        random.seed(42)
        peak_start, peak_end = profile["peak_h"]
        for day in range(days):
            dt = start + timedelta(days=day)
            is_weekend = dt.weekday() >= 5
            for hour in range(24):
                ts = dt.replace(hour=hour)
                if is_weekend:
                    base = profile["weekend"]
                elif peak_start <= hour <= peak_end:
                    base = profile["peak"]
                else:
                    base = profile["night"]
                base *= random.uniform(0.9, 1.1)
                value = max(0.1, round(base, 2))
                readings.append({"timestamp": ts, "value_kwh": value})
        return readings

    @pytest.mark.parametrize("profile", ["office", "hotel", "retail", "warehouse"])
    def test_all_profiles_produce_valid_kpis(self, profile):
        readings = self._make_profile_readings(profile)
        eng = KPIEngine()
        kpis = eng.compute(readings)
        assert kpis["pmax_kw"] > 0
        assert 0 < kpis["load_factor"] < 1
        assert kpis["total_kwh"] > 0
        # Guard: no absurd peak (< 500 kW for these profiles)
        assert kpis["pmax_kw"] < 500

    def test_office_low_weekend(self):
        readings = self._make_profile_readings("office")
        eng = KPIEngine()
        kpis = eng.compute(readings)
        assert kpis["weekend_ratio"] < 0.5  # Office should have low WE

    def test_hotel_high_weekend(self):
        readings = self._make_profile_readings("hotel")
        eng = KPIEngine()
        kpis = eng.compute(readings)
        assert kpis["weekend_ratio"] > 0.5  # Hotel open on weekends

    def test_profiles_have_labels(self):
        from routes.monitoring import USAGE_PROFILES

        for name, p in USAGE_PROFILES.items():
            assert "label" in p, f"Missing label for profile {name}"
            assert "psub_kva" in p, f"Missing psub_kva for profile {name}"

    def test_empty_input(self):
        eng = PowerEngine()
        result = eng.compute({}, [], subscribed_power_kva=100)
        assert result["risk_score"] == 0


class TestEndToEndPipeline:
    def test_full_pipeline_returns_all_sections(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(14)
        result = orch.run_standalone(readings, subscribed_power_kva=100)

        assert "kpis" in result
        assert "data_quality" in result
        assert "power_risk" in result
        assert "alerts" in result
        assert "alert_count" in result
        assert result["alert_count"] == len(result["alerts"])

    def test_pipeline_with_previous_kpis(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(14)
        previous_kpis = {"pbase_kw": 1.0, "p95_kw": 5.0, "weekday_profile_kw": [1.0] * 24}
        result = orch.run_standalone(readings, previous_kpis=previous_kpis)
        assert result["alert_count"] >= 1

    def test_alert_count_matches(self):
        orch = MonitoringOrchestrator()
        readings = _make_anomalous_readings(30)
        result = orch.run_standalone(readings, subscribed_power_kva=30)
        assert result["alert_count"] == len(result["alerts"])
        assert result["alert_count"] >= 3  # Multiple anomalies embedded


class TestClimateIntegration:
    def test_pipeline_with_weather(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(30)
        start = datetime(2025, 1, 6)
        weather = []
        for d in range(30):
            dt = start + timedelta(days=d)
            temp = 5 + 10 * (d / 30)
            weather.append({"date": dt.date().isoformat(), "temp_avg_c": round(temp, 1)})
        result = orch.run_standalone(readings, weather_data=weather)
        assert "climate" in result
        assert result["climate"]["n_points"] > 0

    def test_pipeline_without_weather(self):
        orch = MonitoringOrchestrator()
        readings = _make_office_readings(7)
        result = orch.run_standalone(readings)
        assert "climate" in result
        assert result["climate"]["n_points"] <= 7

    def test_climate_key_always_present(self):
        orch = MonitoringOrchestrator()
        result = orch.run_standalone([])
        assert "climate" in result
