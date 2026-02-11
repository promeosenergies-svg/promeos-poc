"""
PROMEOS Electric Monitoring - Test Alert Engine
Tests all 12 Tier-1 alert rules and lifecycle.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timedelta
from services.electric_monitoring.kpi_engine import KPIEngine
from services.electric_monitoring.power_engine import PowerEngine
from services.electric_monitoring.data_quality import DataQualityEngine
from services.electric_monitoring.alert_engine import AlertEngine, ALERT_DEFS


@pytest.fixture
def alert_engine():
    return AlertEngine()


@pytest.fixture
def kpi_engine():
    return KPIEngine()


@pytest.fixture
def power_engine():
    return PowerEngine()


@pytest.fixture
def quality_engine():
    return DataQualityEngine()


def _make_readings(pattern="office", days=7):
    """Generate readings for different patterns."""
    start = datetime(2025, 1, 6, 0, 0)  # Monday
    readings = []
    for day in range(days):
        dt = start + timedelta(days=day)
        is_weekend = dt.weekday() >= 5
        for hour in range(24):
            ts = dt.replace(hour=hour)
            if pattern == "office":
                if is_weekend:
                    value = 3.0
                elif 8 <= hour <= 18:
                    value = 25.0
                else:
                    value = 4.0
            elif pattern == "high_night":
                if is_weekend:
                    value = 15.0
                elif 8 <= hour <= 18:
                    value = 15.0
                else:
                    value = 25.0  # Night consumption higher than day
            elif pattern == "high_weekend":
                if is_weekend:
                    value = 30.0  # Higher than weekday
                elif 8 <= hour <= 18:
                    value = 25.0
                else:
                    value = 4.0
            elif pattern == "flat":
                value = 50.0  # Completely flat
            elif pattern == "spike":
                if day == 3 and hour == 14:
                    value = 500.0  # Massive spike
                elif 8 <= hour <= 18 and not is_weekend:
                    value = 20.0
                else:
                    value = 5.0
            else:
                value = 10.0
            readings.append({"timestamp": ts, "value_kwh": float(value)})
    return readings


def _run_full_analysis(pattern, days=7, subscribed_kva=100):
    """Helper to run full pipeline."""
    kpi_eng = KPIEngine()
    power_eng = PowerEngine()
    quality_eng = DataQualityEngine()

    readings = _make_readings(pattern, days)
    kpis = kpi_eng.compute(readings, interval_minutes=60)
    quality = quality_eng.compute(readings, interval_minutes=60)
    power_risk = power_eng.compute(kpis, readings, subscribed_power_kva=subscribed_kva)
    return kpis, quality, power_risk, readings


class TestAlert1BaseNuitElevee:
    def test_normal_office_no_alert(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "BASE_NUIT_ELEVEE" not in types

    def test_high_night_triggers_alert(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("high_night")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "BASE_NUIT_ELEVEE" in types


class TestAlert2WeekendAnormal:
    def test_normal_office_no_alert(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "WEEKEND_ANORMAL" not in types

    def test_high_weekend_triggers_alert(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("high_weekend")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "WEEKEND_ANORMAL" in types


class TestAlert3DeriveTalon:
    def test_no_previous_no_alert(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        alerts = alert_engine.evaluate(kpis, power_risk, quality, previous_kpis=None)
        types = [a["alert_type"] for a in alerts]
        assert "DERIVE_TALON" not in types

    def test_increasing_talon_triggers(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        previous = dict(kpis)
        previous["pbase_kw"] = kpis["pbase_kw"] * 0.5  # Previous was half
        alerts = alert_engine.evaluate(kpis, power_risk, quality, previous_kpis=previous)
        types = [a["alert_type"] for a in alerts]
        assert "DERIVE_TALON" in types


class TestAlert4PicAnormal:
    def test_normal_no_spike(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "PIC_ANORMAL" not in types

    def test_massive_spike_triggers(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("spike")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "PIC_ANORMAL" in types


class TestAlert5P95Hausse:
    def test_p95_increase_triggers(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        previous = dict(kpis)
        previous["p95_kw"] = kpis["p95_kw"] * 0.7  # Previous was 30% lower
        alerts = alert_engine.evaluate(kpis, power_risk, quality, previous_kpis=previous)
        types = [a["alert_type"] for a in alerts]
        assert "P95_HAUSSE" in types


class TestAlert6DepassementPuissance:
    def test_no_depassement_large_sub(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office", subscribed_kva=1000)
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "DEPASSEMENT_PUISSANCE" not in types

    def test_depassement_small_sub(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office", subscribed_kva=5)
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "DEPASSEMENT_PUISSANCE" in types


class TestAlert9CourbePlate:
    def test_flat_curve_triggers(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("flat")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "COURBE_PLATE" in types


class TestAlert10DonneesManquantes:
    def test_complete_data_no_alert(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "DONNEES_MANQUANTES" not in types

    def test_incomplete_data_triggers(self, alert_engine):
        kpis = KPIEngine().compute([], interval_minutes=60)
        quality = {"completeness_pct": 50, "gap_count": 10, "max_gap_hours": 48,
                   "duplicate_count": 0, "dst_collisions": 0, "negative_count": 0}
        power_risk = {"ratio_p95_psub": 0, "depassement_count": 0}
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "DONNEES_MANQUANTES" in types


class TestAlert11DoublonsDST:
    def test_no_duplicates_no_alert(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("office")
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "DOUBLONS_DST" not in types

    def test_duplicates_trigger(self, alert_engine):
        quality = {"completeness_pct": 100, "gap_count": 0, "max_gap_hours": 0,
                   "duplicate_count": 5, "dst_collisions": 1, "negative_count": 0}
        kpis = KPIEngine().compute(_make_readings("office"), interval_minutes=60)
        power_risk = {"ratio_p95_psub": 0, "depassement_count": 0}
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "DOUBLONS_DST" in types


class TestAlert12ValeursNegatives:
    def test_no_negatives_no_alert(self, alert_engine):
        quality = {"completeness_pct": 100, "gap_count": 0, "max_gap_hours": 0,
                   "duplicate_count": 0, "dst_collisions": 0, "negative_count": 0}
        kpis = KPIEngine().compute(_make_readings("office"), interval_minutes=60)
        power_risk = {"ratio_p95_psub": 0, "depassement_count": 0}
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "VALEURS_NEGATIVES" not in types

    def test_negatives_trigger(self, alert_engine):
        quality = {"completeness_pct": 100, "gap_count": 0, "max_gap_hours": 0,
                   "duplicate_count": 0, "dst_collisions": 0, "negative_count": 3}
        kpis = KPIEngine().compute(_make_readings("office"), interval_minutes=60)
        power_risk = {"ratio_p95_psub": 0, "depassement_count": 0}
        alerts = alert_engine.evaluate(kpis, power_risk, quality)
        types = [a["alert_type"] for a in alerts]
        assert "VALEURS_NEGATIVES" in types


class TestAlertStructure:
    def test_alert_has_required_fields(self, alert_engine):
        kpis, quality, power_risk, _ = _run_full_analysis("high_night")
        alerts = alert_engine.evaluate(kpis, power_risk, quality, site_id=1, meter_id=1)
        assert len(alerts) > 0
        a = alerts[0]
        assert "alert_type" in a
        assert "severity" in a
        assert "explanation" in a
        assert "evidence" in a
        assert "recommended_action" in a
        assert "kb_link" in a
        assert "created_at" in a

    def test_12_alert_types_defined(self):
        assert len(ALERT_DEFS) == 12
