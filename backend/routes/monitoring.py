"""
PROMEOS - Routes API Monitoring (Electric Consumption Mastery)
6 endpoints for KPIs, analysis, snapshots, alerts lifecycle.
"""
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from models import (
    Site, Meter, MeterReading, MonitoringSnapshot, MonitoringAlert,
    AlertStatus, AlertSeverity, FrequencyType, SiteOperatingSchedule
)
from models.energy_models import EnergyVector

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])


# --- Pydantic models ---

class MonitoringRunRequest(BaseModel):
    site_id: int
    meter_id: Optional[int] = None
    days: int = 90
    interval_minutes: int = 60


class AlertAckRequest(BaseModel):
    acknowledged_by: str = "user"


class AlertResolveRequest(BaseModel):
    resolved_by: str = "user"
    resolution_note: Optional[str] = None


# --- 1. GET /api/monitoring/kpis ---

@router.get("/kpis")
def get_monitoring_kpis(
    site_id: int = Query(...),
    meter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get latest monitoring KPIs for a site/meter."""
    if auth and auth.site_ids is not None and site_id not in auth.site_ids:
        raise HTTPException(status_code=403, detail="Site not in auth scope")
    query = db.query(MonitoringSnapshot).filter_by(site_id=site_id)
    if meter_id:
        query = query.filter_by(meter_id=meter_id)

    snapshot = query.order_by(MonitoringSnapshot.created_at.desc()).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No monitoring snapshot found. Run analysis first.")

    # Compute climate analysis on-the-fly
    climate_data = {}
    try:
        from services.ems.weather_service import get_weather
        from services.electric_monitoring import ClimateEngine
        # Resolve meter: prefer snapshot's meter, fallback to any active meter on site
        meter_obj = None
        if snapshot.meter_id:
            meter_obj = db.query(Meter).filter_by(id=snapshot.meter_id).first()
        if not meter_obj:
            meter_obj = db.query(Meter).filter_by(site_id=site_id, is_active=True).first()
        if not meter_obj:
            climate_data = {"reason": "no_meter", "scatter": [], "fit_line": []}
        else:
            weather = get_weather(db, site_id, snapshot.period_start.date(), snapshot.period_end.date())
            if not weather:
                climate_data = {"reason": "no_weather", "scatter": [], "fit_line": []}
            else:
                # Filter by frequency: prefer 15-min > hourly (exclude monthly/daily)
                _best_freq = None
                for _freq in [FrequencyType.MIN_15, FrequencyType.HOURLY]:
                    _cnt = db.query(MeterReading).filter(
                        MeterReading.meter_id == meter_obj.id,
                        MeterReading.frequency == _freq,
                        MeterReading.timestamp >= snapshot.period_start,
                        MeterReading.timestamp <= snapshot.period_end,
                    ).count()
                    if _cnt >= 48:
                        _best_freq = _freq
                        break
                _freq_filter = [_best_freq] if _best_freq else [FrequencyType.MIN_15, FrequencyType.HOURLY]
                readings_orm = db.query(MeterReading).filter(
                    MeterReading.meter_id == meter_obj.id,
                    MeterReading.frequency.in_(_freq_filter),
                    MeterReading.timestamp >= snapshot.period_start,
                    MeterReading.timestamp <= snapshot.period_end,
                ).order_by(MeterReading.timestamp).all()
                if len(readings_orm) < 240:
                    climate_data = {"reason": "insufficient_readings", "scatter": [], "fit_line": [],
                                    "n_readings": len(readings_orm)}
                else:
                    readings = [{"timestamp": r.timestamp, "value_kwh": r.value_kwh} for r in readings_orm]
                    climate_data = ClimateEngine().compute(readings, weather)
    except Exception as e:
        climate_data = {"reason": "computation_error", "scatter": [], "fit_line": [],
                        "error_detail": str(e)[:200]}

    # Fetch operating schedule for display
    schedule_data = None
    try:
        sched = db.query(SiteOperatingSchedule).filter_by(site_id=site_id).first()
        if sched:
            schedule_data = {
                "open_days": sched.open_days,
                "open_time": sched.open_time,
                "close_time": sched.close_time,
                "is_24_7": sched.is_24_7,
                "timezone": sched.timezone,
            }
    except Exception:
        pass

    # Compute EUR impact via ImpactModel
    impact_data = {}
    try:
        from services.impact_model import resolve_price, compute_off_hours_eur, compute_power_overrun_eur
        from dataclasses import asdict
        price_info = resolve_price(db, site_id)
        impact_data["price"] = asdict(price_info)

        kpis = snapshot.kpis_json or {}
        period_days = max(1, (snapshot.period_end.date() - snapshot.period_start.date()).days)

        # Off-hours impact
        off_hours_kwh = kpis.get("off_hours_kwh", 0) or 0
        off_hours_result = compute_off_hours_eur(off_hours_kwh, period_days, price_info)
        impact_data["off_hours"] = asdict(off_hours_result)

        # Power overrun impact
        p95_kw = kpis.get("p95_kw", 0) or 0
        psub_kva = kpis.get("puissance_souscrite_kva") or kpis.get("psub_kva")
        power_result = compute_power_overrun_eur(p95_kw, psub_kva, price_info)
        impact_data["power_overrun"] = asdict(power_result)
    except Exception as e:
        impact_data["error"] = str(e)[:200]

    # Compute CO2e emissions
    emissions_data = {}
    try:
        from services.emissions_service import compute_emissions_summary
        emissions_data = compute_emissions_summary(
            db, site_id, snapshot.kpis_json or {}
        )
    except Exception as e:
        emissions_data = {"error": str(e)[:200]}

    return {
        "snapshot_id": snapshot.id,
        "site_id": snapshot.site_id,
        "meter_id": snapshot.meter_id,
        "period": f"{snapshot.period_start.date()} - {snapshot.period_end.date()}",
        "kpis": snapshot.kpis_json or {},
        "data_quality_score": snapshot.data_quality_score,
        "risk_power_score": snapshot.risk_power_score,
        "data_quality_details": snapshot.data_quality_details_json or {},
        "risk_power_details": snapshot.risk_power_details_json or {},
        "climate": climate_data,
        "schedule": schedule_data,
        "impact": impact_data,
        "emissions": emissions_data,
        "engine_version": snapshot.engine_version,
        "created_at": snapshot.created_at.isoformat(),
    }


# --- 1b. GET /api/monitoring/kpis/compare ---

@router.get("/kpis/compare")
def get_monitoring_kpis_compare(
    site_id: int = Query(...),
    mode: str = Query("previous", description="previous|n-1|custom"),
    custom_start: Optional[str] = None,
    custom_end: Optional[str] = None,
    meter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get comparison KPIs for a site. Modes: previous period, N-1, or custom dates."""
    if auth and auth.site_ids is not None and site_id not in auth.site_ids:
        raise HTTPException(status_code=403, detail="Site not in auth scope")

    # Get current snapshot first
    current_q = db.query(MonitoringSnapshot).filter_by(site_id=site_id)
    if meter_id:
        current_q = current_q.filter_by(meter_id=meter_id)
    current = current_q.order_by(MonitoringSnapshot.created_at.desc()).first()
    if not current:
        return {"compare": None, "reason": "no_current_snapshot"}

    compare_snapshot = None

    if mode == "previous":
        # Find snapshot whose period_end < current.period_start
        compare_snapshot = (
            db.query(MonitoringSnapshot)
            .filter(
                MonitoringSnapshot.site_id == site_id,
                MonitoringSnapshot.period_end < current.period_start,
                MonitoringSnapshot.id != current.id,
            )
            .order_by(MonitoringSnapshot.period_end.desc())
            .first()
        )
    elif mode == "n-1":
        # Find snapshot from ~1 year ago (period_start close to current - 365 days)
        from datetime import timedelta as td
        target_start = current.period_start - td(days=365)
        target_end = current.period_end - td(days=365)
        compare_snapshot = (
            db.query(MonitoringSnapshot)
            .filter(
                MonitoringSnapshot.site_id == site_id,
                MonitoringSnapshot.period_start >= target_start - td(days=30),
                MonitoringSnapshot.period_start <= target_start + td(days=30),
                MonitoringSnapshot.id != current.id,
            )
            .order_by(MonitoringSnapshot.created_at.desc())
            .first()
        )
    elif mode == "custom":
        # Find snapshot overlapping the custom date range
        if custom_start and custom_end:
            from datetime import datetime as dt_cls
            try:
                cs = dt_cls.fromisoformat(custom_start)
                ce = dt_cls.fromisoformat(custom_end)
            except ValueError:
                raise HTTPException(status_code=400, detail="Dates invalides (format ISO)")
            compare_snapshot = (
                db.query(MonitoringSnapshot)
                .filter(
                    MonitoringSnapshot.site_id == site_id,
                    MonitoringSnapshot.period_start >= cs,
                    MonitoringSnapshot.period_end <= ce,
                    MonitoringSnapshot.id != current.id,
                )
                .order_by(MonitoringSnapshot.created_at.desc())
                .first()
            )
        else:
            return {"compare": None, "reason": "custom_dates_required"}

    if not compare_snapshot:
        return {"compare": None, "reason": f"no_{mode}_snapshot"}

    # Build compare impact
    compare_impact = {}
    try:
        from services.impact_model import resolve_price, compute_off_hours_eur, compute_power_overrun_eur
        from dataclasses import asdict
        price_info = resolve_price(db, site_id)
        compare_impact["price"] = asdict(price_info)
        ckpis = compare_snapshot.kpis_json or {}
        cperiod_days = max(1, (compare_snapshot.period_end.date() - compare_snapshot.period_start.date()).days)
        off_kwh = ckpis.get("off_hours_kwh", 0) or 0
        compare_impact["off_hours"] = asdict(compute_off_hours_eur(off_kwh, cperiod_days, price_info))
        p95 = ckpis.get("p95_kw", 0) or 0
        psub = ckpis.get("puissance_souscrite_kva") or ckpis.get("psub_kva")
        compare_impact["power_overrun"] = asdict(compute_power_overrun_eur(p95, psub, price_info))
    except Exception:
        pass

    return {
        "compare": {
            "snapshot_id": compare_snapshot.id,
            "period": f"{compare_snapshot.period_start.date()} - {compare_snapshot.period_end.date()}",
            "kpis": compare_snapshot.kpis_json or {},
            "data_quality_score": compare_snapshot.data_quality_score,
            "risk_power_score": compare_snapshot.risk_power_score,
            "impact": compare_impact,
            "created_at": compare_snapshot.created_at.isoformat(),
        },
        "mode": mode,
        "reason": None,
    }


# --- 2. POST /api/monitoring/run ---

@router.post("/run")
def run_monitoring(request: MonitoringRunRequest, db: Session = Depends(get_db)):
    """Run full monitoring pipeline for a site/meter."""
    from services.electric_monitoring import MonitoringOrchestrator

    site = db.query(Site).filter_by(id=request.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {request.site_id} not found")

    orchestrator = MonitoringOrchestrator(db)
    result = orchestrator.run(
        site_id=request.site_id,
        meter_id=request.meter_id,
        days=request.days,
        interval_minutes=request.interval_minutes
    )

    return result


# --- 3. GET /api/monitoring/snapshots ---

@router.get("/snapshots")
def list_snapshots(
    site_id: Optional[int] = None,
    meter_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List monitoring snapshots with optional filters."""
    query = db.query(MonitoringSnapshot)
    if auth and auth.site_ids is not None:
        query = query.filter(MonitoringSnapshot.site_id.in_(auth.site_ids))
    if site_id:
        query = query.filter_by(site_id=site_id)
    if meter_id:
        query = query.filter_by(meter_id=meter_id)

    snapshots = query.order_by(MonitoringSnapshot.created_at.desc()).limit(limit).all()

    return [
        {
            "id": s.id,
            "site_id": s.site_id,
            "meter_id": s.meter_id,
            "period": f"{s.period_start.date()} - {s.period_end.date()}",
            "data_quality_score": s.data_quality_score,
            "risk_power_score": s.risk_power_score,
            "engine_version": s.engine_version,
            "created_at": s.created_at.isoformat(),
        }
        for s in snapshots
    ]


# --- 4. GET /api/monitoring/alerts ---

@router.get("/alerts")
def list_alerts(
    site_id: Optional[int] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List monitoring alerts with optional filters."""
    query = db.query(MonitoringAlert)

    if auth and auth.site_ids is not None:
        query = query.filter(MonitoringAlert.site_id.in_(auth.site_ids))
    if site_id:
        query = query.filter_by(site_id=site_id)
    if status:
        try:
            query = query.filter_by(status=AlertStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    if severity:
        try:
            query = query.filter_by(severity=AlertSeverity(severity))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

    alerts = query.order_by(MonitoringAlert.created_at.desc()).limit(limit).all()

    return [
        {
            "id": a.id,
            "alert_type": a.alert_type,
            "severity": a.severity.value,
            "site_id": a.site_id,
            "meter_id": a.meter_id,
            "explanation": a.explanation,
            "recommended_action": a.recommended_action,
            "estimated_impact_kwh": a.estimated_impact_kwh,
            "estimated_impact_eur": a.estimated_impact_eur,
            "evidence": a.evidence_json or {},
            "kb_link": a.kb_link_json or {},
            "status": a.status.value,
            "acknowledged_at": a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
            "resolution_note": a.resolution_note,
            "snapshot_id": a.snapshot_id,
            "created_at": a.created_at.isoformat(),
        }
        for a in alerts
    ]


# --- 5. POST /api/monitoring/alerts/{id}/ack ---

@router.post("/alerts/{alert_id}/ack")
def acknowledge_alert(
    alert_id: int,
    request: AlertAckRequest,
    db: Session = Depends(get_db)
):
    """Acknowledge an open alert."""
    alert = db.query(MonitoringAlert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    if alert.status != AlertStatus.OPEN:
        raise HTTPException(status_code=400, detail=f"Alert is {alert.status.value}, can only ack OPEN alerts")

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = request.acknowledged_by
    db.commit()

    return {"status": "acknowledged", "alert_id": alert_id}


# --- 6. POST /api/monitoring/alerts/{id}/resolve ---

@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    request: AlertResolveRequest,
    db: Session = Depends(get_db)
):
    """Resolve an alert (from open or acknowledged)."""
    alert = db.query(MonitoringAlert).filter_by(id=alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Alert is already resolved")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = datetime.now(timezone.utc)
    alert.resolved_by = request.resolved_by
    alert.resolution_note = request.resolution_note
    db.commit()

    return {"status": "resolved", "alert_id": alert_id}


# --- 7. POST /api/monitoring/demo/generate ---

class MonitoringDemoRequest(BaseModel):
    site_id: int
    days: int = 90
    profile: str = "office"


USAGE_PROFILES = {
    "office":    {"peak": 35, "shoulder": 18, "night": 6, "weekend": 5,
                  "peak_h": (8, 18), "heat_coeff": 1.5, "cool_coeff": 0.8,
                  "psub_kva": 80, "label": "Bureau tertiaire",
                  "open_days": "0,1,2,3,4", "open_time": "08:00", "close_time": "19:00", "is_24_7": False},
    "hotel":     {"peak": 25, "shoulder": 20, "night": 15, "weekend": 22,
                  "peak_h": (7, 22), "heat_coeff": 2.0, "cool_coeff": 1.2,
                  "psub_kva": 100, "label": "Hotel / Hebergement",
                  "open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
    "retail":    {"peak": 40, "shoulder": 15, "night": 4, "weekend": 38,
                  "peak_h": (9, 20), "heat_coeff": 1.0, "cool_coeff": 1.5,
                  "psub_kva": 120, "label": "Commerce / Retail",
                  "open_days": "0,1,2,3,4,5", "open_time": "09:00", "close_time": "20:00", "is_24_7": False},
    "warehouse": {"peak": 20, "shoulder": 15, "night": 12, "weekend": 10,
                  "peak_h": (6, 20), "heat_coeff": 0.5, "cool_coeff": 0.3,
                  "psub_kva": 60, "label": "Entrepot / Logistique",
                  "open_days": "0,1,2,3,4", "open_time": "06:00", "close_time": "20:00", "is_24_7": False},
    "school":    {"peak": 28, "shoulder": 12, "night": 3, "weekend": 3,
                  "peak_h": (8, 17), "heat_coeff": 2.5, "cool_coeff": 0.3,
                  "psub_kva": 60, "label": "Ecole / Etablissement scolaire",
                  "open_days": "0,1,2,3,4", "open_time": "07:30", "close_time": "18:00", "is_24_7": False,
                  "vacation_weeks": [1, 2, 7, 8, 16, 17, 27, 28, 29, 30, 31, 32, 33, 34]},
    "hospital":  {"peak": 45, "shoulder": 35, "night": 28, "weekend": 30,
                  "peak_h": (7, 21), "heat_coeff": 2.0, "cool_coeff": 1.8,
                  "psub_kva": 200, "label": "Hopital / Sante",
                  "open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
}

# Max plausible EUR/an impact per alert to prevent absurd values in demo
MAX_IMPACT_EUR_PER_ALERT = 50_000


@router.post("/demo/generate")
def generate_monitoring_demo(request: MonitoringDemoRequest, db: Session = Depends(get_db)):
    """Generate monitoring demo data (profiled pattern + weather correlation + anomalies)."""
    site = db.query(Site).filter_by(id=request.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {request.site_id} not found")

    profile = USAGE_PROFILES.get(request.profile, USAGE_PROFILES["office"])

    # Try to reuse existing EMS demo meter for this site (unified data)
    ems_meter_id_str = f"EMS-DEMO-{request.site_id:06d}"
    ems_meter = db.query(Meter).filter_by(meter_id=ems_meter_id_str).first()
    if ems_meter:
        # EMS demo data exists — reuse it, skip generation
        ems_readings_count = db.query(MeterReading).filter_by(meter_id=ems_meter.id).count()
        if ems_readings_count > 0:
            return {
                "status": "ok",
                "site_id": request.site_id,
                "meter_id": ems_meter.id,
                "meter_ref": ems_meter_id_str,
                "profile": request.profile,
                "readings_generated": 0,
                "readings_reused": ems_readings_count,
                "weather_days": 0,
                "period": f"reused EMS demo data ({ems_readings_count} readings)",
                "source": "ems_demo_reuse",
            }

    meter_id_str = f"PRM-MON-{request.site_id:03d}"
    meter = db.query(Meter).filter_by(meter_id=meter_id_str).first()
    if not meter:
        meter = Meter(
            meter_id=meter_id_str,
            name=f"Compteur Monitoring {site.nom or site.id}",
            site_id=site.id,
            energy_vector=EnergyVector.ELECTRICITY,
            subscribed_power_kva=float(profile.get("psub_kva", 80)),
            tariff_type="C5",
        )
        db.add(meter)
        db.commit()
        db.refresh(meter)
    else:
        db.query(MeterReading).filter_by(meter_id=meter.id).delete()
        db.commit()

    # Upsert operating schedule for this site
    sched = db.query(SiteOperatingSchedule).filter_by(site_id=site.id).first()
    if not sched:
        sched = SiteOperatingSchedule(site_id=site.id)
        db.add(sched)
    sched.open_days = profile.get("open_days", "0,1,2,3,4")
    sched.open_time = profile.get("open_time", "08:00")
    sched.close_time = profile.get("close_time", "19:00")
    sched.is_24_7 = profile.get("is_24_7", False)
    db.commit()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=request.days)

    # Pre-generate weather data so consumption can be correlated
    try:
        from services.ems.weather_service import get_weather
        weather_days = get_weather(db, request.site_id, start.date(), now.date())
    except Exception:
        weather_days = []

    # Build temperature lookup {date_str: temp_avg}
    temp_lookup = {}
    for w in weather_days:
        temp_lookup[str(w.get("date", ""))[:10]] = w.get("temp_avg_c", 12.0)

    readings = []
    random.seed(42 + request.site_id)
    peak_start, peak_end = profile["peak_h"]

    for day_offset in range(request.days):
        dt = start + timedelta(days=day_offset)
        is_weekend = dt.weekday() >= 5
        day_key = dt.date().isoformat()
        temp = temp_lookup.get(day_key, 12.0)

        for hour in range(24):
            ts = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

            # School vacation check (ISO week)
            vacation_weeks = profile.get("vacation_weeks", [])
            is_vacation = dt.isocalendar()[1] in vacation_weeks if vacation_weeks else False

            # Base pattern from profile
            if is_weekend or is_vacation:
                base_kwh = profile["weekend"]
            elif peak_start <= hour <= peak_end:
                base_kwh = profile["peak"]
            elif hour == peak_start - 1 or peak_end < hour <= peak_end + 2:
                base_kwh = profile["shoulder"]
            else:
                base_kwh = profile["night"]

            # Temperature sensitivity
            base_kwh += profile["heat_coeff"] * max(0, 15 - temp)
            base_kwh += profile["cool_coeff"] * max(0, temp - 22)

            # Seasonal variation
            seasonal = 1.0 + 0.15 * math.cos(2 * math.pi * (dt.month - 1) / 12.0)
            value = base_kwh * seasonal

            # Anomaly 1: high night base (days 30-44)
            if 30 <= day_offset <= 44 and (hour < peak_start or hour > peak_end) and not is_weekend:
                value *= 2.5

            # Anomaly 2: weekend spike (days 35-36)
            if day_offset in [35, 36] and is_weekend:
                value = 40.0

            # Anomaly 3: sudden ramp (day 55 14:00)
            if day_offset == 55 and hour == 14:
                value = profile["peak"] * 3.0

            # Anomaly 4: flat curve segment (days 70-73)
            if 70 <= day_offset <= 73:
                value = 15.0

            value *= random.uniform(0.90, 1.10)
            # Guardrail: cap at 3x subscribed power (no absurd spikes)
            max_kw = profile.get("psub_kva", 80) * 3
            value = max(0.1, min(round(value, 2), max_kw))

            readings.append(MeterReading(
                meter_id=meter.id,
                timestamp=ts,
                frequency=FrequencyType.HOURLY,
                value_kwh=value,
                is_estimated=False,
            ))

    db.bulk_save_objects(readings)
    db.commit()

    return {
        "status": "ok",
        "site_id": request.site_id,
        "meter_id": meter.id,
        "meter_ref": meter_id_str,
        "profile": request.profile,
        "profile_label": profile.get("label", request.profile),
        "psub_kva": profile.get("psub_kva", 80),
        "readings_generated": len(readings),
        "weather_days": len(weather_days),
        "period": f"{start.date()} - {now.date()}",
    }


# --- 8. GET /api/monitoring/emissions ---

@router.get("/emissions")
def get_emissions(
    site_id: int = Query(...),
    meter_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get CO2e emissions summary for a site based on latest monitoring snapshot."""
    if auth and auth.site_ids is not None and site_id not in auth.site_ids:
        raise HTTPException(status_code=403, detail="Site not in auth scope")

    query = db.query(MonitoringSnapshot).filter_by(site_id=site_id)
    if meter_id:
        query = query.filter_by(meter_id=meter_id)
    snapshot = query.order_by(MonitoringSnapshot.created_at.desc()).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No monitoring snapshot found. Run analysis first.")

    from services.emissions_service import compute_emissions_summary
    emissions = compute_emissions_summary(db, site_id, snapshot.kpis_json or {})

    return {
        "site_id": site_id,
        "snapshot_id": snapshot.id,
        "period": f"{snapshot.period_start.date()} - {snapshot.period_end.date()}",
        **emissions,
    }


# --- 9. GET /api/monitoring/emission-factors ---

@router.get("/emission-factors")
def list_emission_factors(
    energy_type: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List available emission factors."""
    from models import EmissionFactor

    query = db.query(EmissionFactor)
    if energy_type:
        query = query.filter_by(energy_type=energy_type)
    if region:
        query = query.filter_by(region=region)

    factors = query.order_by(EmissionFactor.created_at.desc()).all()
    return [
        {
            "id": f.id,
            "energy_type": f.energy_type,
            "region": f.region,
            "kgco2e_per_kwh": f.kgco2e_per_kwh,
            "source_label": f.source_label,
            "quality": f.quality,
            "valid_from": f.valid_from.isoformat() if f.valid_from else None,
            "valid_to": f.valid_to.isoformat() if f.valid_to else None,
        }
        for f in factors
    ]


# --- 10. POST /api/monitoring/emission-factors/seed ---

@router.post("/emission-factors/seed")
def seed_emission_factors(db: Session = Depends(get_db)):
    """Seed default FR emission factor for demo."""
    from models import EmissionFactor

    existing = db.query(EmissionFactor).filter_by(
        energy_type="electricity", region="FR"
    ).first()
    if existing:
        return {"status": "already_exists", "id": existing.id}

    factor = EmissionFactor(
        energy_type="electricity",
        region="FR",
        kgco2e_per_kwh=0.052,
        source_label="Facteur demo POC (base ADEME 2024)",
        quality="demo",
    )
    db.add(factor)
    db.commit()
    db.refresh(factor)

    return {"status": "created", "id": factor.id, "kgco2e_per_kwh": factor.kgco2e_per_kwh}
