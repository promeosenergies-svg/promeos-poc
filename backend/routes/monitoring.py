"""
PROMEOS - Routes API Monitoring (Electric Consumption Mastery)
6 endpoints for KPIs, analysis, snapshots, alerts lifecycle.
"""
import math
import random
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from models import (
    Site, Meter, MeterReading, MonitoringSnapshot, MonitoringAlert,
    AlertStatus, AlertSeverity, FrequencyType
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
        "engine_version": snapshot.engine_version,
        "created_at": snapshot.created_at.isoformat(),
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
    alert.acknowledged_at = datetime.utcnow()
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
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = request.resolved_by
    alert.resolution_note = request.resolution_note
    db.commit()

    return {"status": "resolved", "alert_id": alert_id}


# --- 7. POST /api/monitoring/demo/generate ---

class MonitoringDemoRequest(BaseModel):
    site_id: int
    days: int = 90


@router.post("/demo/generate")
def generate_monitoring_demo(request: MonitoringDemoRequest, db: Session = Depends(get_db)):
    """Generate monitoring demo data (office pattern + anomalies) for a site."""
    site = db.query(Site).filter_by(id=request.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {request.site_id} not found")

    meter_id_str = f"PRM-MON-{request.site_id:03d}"
    meter = db.query(Meter).filter_by(meter_id=meter_id_str).first()
    if not meter:
        meter = Meter(
            meter_id=meter_id_str,
            name=f"Compteur Monitoring {site.nom or site.id}",
            site_id=site.id,
            energy_vector=EnergyVector.ELECTRICITY,
            subscribed_power_kva=80.0,
            tariff_type="C5",
        )
        db.add(meter)
        db.commit()
        db.refresh(meter)
    else:
        db.query(MeterReading).filter_by(meter_id=meter.id).delete()
        db.commit()

    now = datetime.utcnow()
    start = now - timedelta(days=request.days)
    readings = []
    random.seed(42 + request.site_id)

    for day_offset in range(request.days):
        dt = start + timedelta(days=day_offset)
        is_weekend = dt.weekday() >= 5

        for hour in range(24):
            ts = dt.replace(hour=hour, minute=0, second=0, microsecond=0)

            # Office pattern
            if is_weekend:
                base_kwh = 5.0
            elif 8 <= hour <= 18:
                base_kwh = 35.0
            elif hour == 7 or 19 <= hour <= 20:
                base_kwh = 18.0
            else:
                base_kwh = 6.0

            seasonal = 1.0 + 0.15 * math.cos(2 * math.pi * (dt.month - 1) / 12.0)
            value = base_kwh * seasonal

            # Anomaly 1: high night base (days 30-44)
            if 30 <= day_offset <= 44 and (hour < 7 or hour > 19) and not is_weekend:
                value *= 2.5

            # Anomaly 2: weekend spike (days 35-36)
            if day_offset in [35, 36] and is_weekend:
                value = 40.0

            value *= random.uniform(0.90, 1.10)
            value = max(0.1, round(value, 2))

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
        "readings_generated": len(readings),
        "period": f"{start.date()} - {now.date()}",
    }
