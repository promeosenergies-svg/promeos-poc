"""
PROMEOS Electric Monitoring - Orchestrator
Pipeline: readings -> KPIs -> quality -> power risk -> alerts -> snapshot + persist

Usage:
    orchestrator = MonitoringOrchestrator(db)
    result = orchestrator.run(site_id=1, meter_id=1)
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from .kpi_engine import KPIEngine
from .power_engine import PowerEngine
from .data_quality import DataQualityEngine
from .alert_engine import AlertEngine
from .climate_engine import ClimateEngine


ENGINE_VERSION = "monitoring_v1.0"


class MonitoringOrchestrator:
    """Orchestrate full monitoring analysis pipeline."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.kpi_engine = KPIEngine()
        self.power_engine = PowerEngine()
        self.quality_engine = DataQualityEngine()
        self.alert_engine = AlertEngine()
        self.climate_engine = ClimateEngine()

    def run(self, site_id: int, meter_id: Optional[int] = None,
            days: int = 90, interval_minutes: int = 60,
            persist: bool = True) -> Dict[str, Any]:
        """
        Run the full monitoring pipeline.

        Args:
            site_id: target site
            meter_id: specific meter (None = all meters for site)
            days: lookback period
            interval_minutes: expected reading interval
            persist: whether to save snapshot + alerts to DB

        Returns:
            dict with kpis, power_risk, data_quality, alerts, snapshot_id
        """
        from models import Meter, MeterReading, MonitoringSnapshot, MonitoringAlert, AlertStatus, AlertSeverity, Site

        if not self.db:
            raise RuntimeError("DB session required for orchestrator.run()")

        # Determine meters
        if meter_id:
            meters = self.db.query(Meter).filter_by(id=meter_id, site_id=site_id).all()
        else:
            meters = self.db.query(Meter).filter_by(site_id=site_id).all()

        if not meters:
            return {"error": f"No meters found for site {site_id}", "kpis": {}, "alerts": []}

        # Get site for subscribed power
        site = self.db.query(Site).filter_by(id=site_id).first()

        results = []
        for meter in meters:
            result = self._run_for_meter(meter, site, days, interval_minutes, persist)
            results.append(result)

        # Aggregate if multiple meters
        if len(results) == 1:
            return results[0]

        return {
            "site_id": site_id,
            "meters_analyzed": len(results),
            "results": results,
            "total_alerts": sum(r.get("alert_count", 0) for r in results),
        }

    def _run_for_meter(self, meter, site, days: int,
                       interval_minutes: int, persist: bool) -> Dict[str, Any]:
        """Run pipeline for a single meter."""
        from models import MeterReading, MonitoringSnapshot, MonitoringAlert, AlertStatus, AlertSeverity

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        period_start = now - timedelta(days=days)
        period_end = now

        # 1. Fetch readings — filter by frequency (prefer finest: 15min > hourly)
        #    Exclude MONTHLY/DAILY readings that would corrupt power calculations
        from models import FrequencyType
        best_freq = None
        for freq in [FrequencyType.MIN_15, FrequencyType.HOURLY]:
            count = self.db.query(MeterReading).filter(
                MeterReading.meter_id == meter.id,
                MeterReading.frequency == freq,
                MeterReading.timestamp >= period_start,
                MeterReading.timestamp <= period_end,
            ).count()
            if count >= 48:  # at least 2 days of data
                best_freq = freq
                break

        freq_filter = [best_freq] if best_freq else [FrequencyType.MIN_15, FrequencyType.HOURLY]
        readings_orm = self.db.query(MeterReading).filter(
            MeterReading.meter_id == meter.id,
            MeterReading.frequency.in_(freq_filter),
            MeterReading.timestamp >= period_start,
            MeterReading.timestamp <= period_end,
        ).order_by(MeterReading.timestamp).all()

        # Auto-detect interval from best frequency
        if best_freq == FrequencyType.MIN_15:
            interval_minutes = 15
        elif best_freq == FrequencyType.HOURLY:
            interval_minutes = 60

        readings = [
            {"timestamp": r.timestamp, "value_kwh": r.value_kwh}
            for r in readings_orm
        ]

        if not readings:
            return {
                "meter_id": meter.id,
                "meter_code": meter.meter_id,
                "status": "no_data",
                "kpis": {},
                "climate": {},
                "alerts": [],
            }

        # 1b. Fetch weather data for climate analysis
        weather_data = []
        if self.db:
            try:
                from services.ems.weather_service import get_weather
                weather_data = get_weather(
                    self.db, meter.site_id,
                    period_start.date(), period_end.date()
                )
            except Exception:
                weather_data = []

        # 1c. Fetch operating schedule for off-hours KPI
        schedule = None
        if self.db:
            try:
                from models import SiteOperatingSchedule
                sched = self.db.query(SiteOperatingSchedule).filter_by(
                    site_id=meter.site_id
                ).first()
                if sched:
                    schedule = {
                        "open_days": sched.open_days,
                        "open_time": sched.open_time,
                        "close_time": sched.close_time,
                        "is_24_7": sched.is_24_7,
                    }
            except Exception:
                schedule = None

        # 2. Compute KPIs (with schedule for off-hours)
        kpis = self.kpi_engine.compute(readings, interval_minutes, schedule=schedule)

        # 3. Data quality
        quality = self.quality_engine.compute(
            readings, interval_minutes,
            period_start=period_start, period_end=period_end
        )

        # 4. Power risk
        sub_power = meter.subscribed_power_kva or 0
        power_risk = self.power_engine.compute(
            kpis, readings,
            subscribed_power_kva=sub_power,
            interval_minutes=interval_minutes
        )

        # 4b. Climate analysis
        climate = self.climate_engine.compute(readings, weather_data, interval_minutes)

        # 5. Get previous period KPIs for trend alerts
        previous_kpis = self._get_previous_kpis(meter.id, period_start, days)

        # 6. Generate alerts
        alerts = self.alert_engine.evaluate(
            kpis, power_risk, quality,
            previous_kpis=previous_kpis,
            site_id=meter.site_id,
            meter_id=meter.id
        )

        # 6b. Climate alerts
        climate_alerts = self.alert_engine.evaluate_climate(
            climate, site_id=meter.site_id, meter_id=meter.id
        )
        alerts.extend(climate_alerts)

        snapshot_id = None

        # 7. Persist
        if persist:
            snapshot_id = self._persist_snapshot(
                meter, period_start, period_end, kpis, quality, power_risk
            )
            self._persist_alerts(alerts, snapshot_id)

        return {
            "meter_id": meter.id,
            "meter_code": meter.meter_id,
            "site_id": meter.site_id,
            "period": f"{period_start.date()} - {period_end.date()}",
            "readings_count": len(readings),
            "kpis": kpis,
            "data_quality": quality,
            "power_risk": power_risk,
            "climate": climate,
            "alerts": alerts,
            "alert_count": len(alerts),
            "snapshot_id": snapshot_id,
        }

    def _get_previous_kpis(self, meter_id: int, current_start: datetime,
                           days: int) -> Optional[Dict]:
        """Fetch KPIs from the previous equivalent period."""
        from models import MonitoringSnapshot

        prev_end = current_start
        prev_start = current_start - timedelta(days=days)

        prev_snapshot = self.db.query(MonitoringSnapshot).filter(
            MonitoringSnapshot.meter_id == meter_id,
            MonitoringSnapshot.period_start >= prev_start,
            MonitoringSnapshot.period_end <= prev_end
        ).order_by(MonitoringSnapshot.created_at.desc()).first()

        if prev_snapshot and prev_snapshot.kpis_json:
            return prev_snapshot.kpis_json
        return None

    def _persist_snapshot(self, meter, period_start, period_end,
                          kpis, quality, power_risk) -> int:
        """Save monitoring snapshot to DB."""
        from models import MonitoringSnapshot

        snapshot = MonitoringSnapshot(
            site_id=meter.site_id,
            meter_id=meter.id,
            period_start=period_start,
            period_end=period_end,
            kpis_json=kpis,
            data_quality_score=quality.get("quality_score", 0),
            risk_power_score=power_risk.get("risk_score", 0),
            data_quality_details_json=quality,
            risk_power_details_json=power_risk,
            engine_version=ENGINE_VERSION,
        )
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot.id

    def _persist_alerts(self, alerts: List[Dict], snapshot_id: int):
        """Save monitoring alerts to DB."""
        from models import MonitoringAlert, AlertStatus, AlertSeverity

        severity_map = {
            "info": AlertSeverity.INFO,
            "warning": AlertSeverity.WARNING,
            "high": AlertSeverity.HIGH,
            "critical": AlertSeverity.CRITICAL,
        }

        for a in alerts:
            alert = MonitoringAlert(
                site_id=a.get("site_id"),
                meter_id=a.get("meter_id"),
                alert_type=a["alert_type"],
                severity=severity_map.get(a.get("severity", "warning"), AlertSeverity.WARNING),
                explanation=a["explanation"],
                evidence_json=a.get("evidence"),
                recommended_action=a.get("recommended_action"),
                estimated_impact_kwh=a.get("estimated_impact_kwh"),
                estimated_impact_eur=a.get("estimated_impact_eur"),
                kb_link_json=a.get("kb_link"),
                status=AlertStatus.OPEN,
                snapshot_id=snapshot_id,
            )
            self.db.add(alert)

        self.db.commit()

    def run_standalone(self, readings: List[Dict[str, Any]],
                       interval_minutes: int = 60,
                       subscribed_power_kva: float = 0,
                       previous_kpis: Optional[Dict] = None,
                       weather_data: Optional[List[Dict]] = None,
                       schedule: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Run pipeline without DB (for testing / stateless use).

        Args:
            readings: list of {timestamp, value_kwh}
            interval_minutes: step size
            subscribed_power_kva: subscribed power
            previous_kpis: previous period KPIs for trend comparison
            weather_data: optional daily weather for climate analysis
            schedule: optional operating schedule for off-hours KPI

        Returns:
            full analysis result dict
        """
        if not readings:
            return {"kpis": {}, "data_quality": {}, "power_risk": {}, "climate": {}, "alerts": []}

        kpis = self.kpi_engine.compute(readings, interval_minutes, schedule=schedule)
        quality = self.quality_engine.compute(readings, interval_minutes)
        power_risk = self.power_engine.compute(
            kpis, readings,
            subscribed_power_kva=subscribed_power_kva,
            interval_minutes=interval_minutes
        )
        climate = self.climate_engine.compute(
            readings, weather_data or [], interval_minutes
        )
        alerts = self.alert_engine.evaluate(
            kpis, power_risk, quality,
            previous_kpis=previous_kpis
        )
        climate_alerts = self.alert_engine.evaluate_climate(climate)
        alerts.extend(climate_alerts)

        return {
            "readings_count": len(readings),
            "kpis": kpis,
            "data_quality": quality,
            "power_risk": power_risk,
            "climate": climate,
            "alerts": alerts,
            "alert_count": len(alerts),
        }
