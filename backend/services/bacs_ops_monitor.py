"""
PROMEOS - BACS Ops Monitor
Operational KPIs, consumption linkage, and monitoring panel for BACS.
"""
import json
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Site, BacsAsset, BacsAssessment, BacsInspection,
    ConsumptionInsight, MeterReading, Meter, InspectionStatus,
)


def compute_bacs_ops_kpis(db: Session, site_id: int, period_days: int = 30) -> dict:
    """
    Compute operational KPIs for a BACS-obligated site.

    Returns:
    - compliance_delay_days: deadline - today (negative if overdue)
    - inspection_countdown_days: due_next - today
    - has_attestation: bool (stub: checks assessment compliance_score)
    - cvc_alerts_count: number of CVC-related monitoring alerts (stub)
    - gains_vs_baseline_pct: delta consumption if available
    """
    asset = db.query(BacsAsset).filter(BacsAsset.site_id == site_id).first()
    if not asset:
        return {"error": "No BACS asset configured"}

    assessment = (
        db.query(BacsAssessment)
        .filter(BacsAssessment.asset_id == asset.id)
        .order_by(BacsAssessment.assessed_at.desc())
        .first()
    )

    today = date.today()
    kpis = {
        "site_id": site_id,
        "is_obligated": assessment.is_obligated if assessment else False,
        "compliance_delay_days": None,
        "inspection_countdown_days": None,
        "has_attestation": False,
        "cvc_alerts_count": 3,  # Stub: simulated
        "gains_vs_baseline_pct": None,
    }

    if assessment and assessment.deadline_date:
        kpis["compliance_delay_days"] = (assessment.deadline_date - today).days

    # Inspection countdown
    inspections = db.query(BacsInspection).filter(BacsInspection.asset_id == asset.id).all()
    completed = [i for i in inspections if i.status == InspectionStatus.COMPLETED and i.inspection_date]
    if completed:
        last = max(completed, key=lambda i: i.inspection_date)
        next_due = last.inspection_date + timedelta(days=5 * 365)
        kpis["inspection_countdown_days"] = (next_due - today).days
    elif assessment and assessment.deadline_date:
        kpis["inspection_countdown_days"] = (assessment.deadline_date - today).days

    # Has attestation (simplified: compliance_score > 50 = considered attested)
    if assessment and assessment.compliance_score and assessment.compliance_score > 50:
        kpis["has_attestation"] = True

    # Gains vs baseline (compare last 30 days vs previous 30 days from MeterReading)
    try:
        meter = db.query(Meter).filter(Meter.site_id == site_id).first()
        if meter:
            now = datetime.utcnow()
            current_start = now - timedelta(days=period_days)
            prev_start = now - timedelta(days=period_days * 2)

            current_sum = db.query(func.sum(MeterReading.value_kwh)).filter(
                MeterReading.meter_id == meter.id,
                MeterReading.timestamp >= current_start,
            ).scalar() or 0

            prev_sum = db.query(func.sum(MeterReading.value_kwh)).filter(
                MeterReading.meter_id == meter.id,
                MeterReading.timestamp >= prev_start,
                MeterReading.timestamp < current_start,
            ).scalar() or 0

            if prev_sum > 0:
                kpis["gains_vs_baseline_pct"] = round((current_sum - prev_sum) / prev_sum * 100, 1)
    except Exception:
        pass  # Best-effort

    return kpis


def link_consumption_findings(db: Session, site_id: int) -> list[dict]:
    """
    Link ConsumptionInsight findings to BACS context.
    Enriches hors_horaires / derive / pointe insights with GTB recommendations.
    """
    insights = db.query(ConsumptionInsight).filter(ConsumptionInsight.site_id == site_id).all()

    enriched = []
    for ins in insights:
        insight_str = str(ins.type) if ins.type else ""

        bacs_context = None
        if "hors_horaires" in insight_str:
            bacs_context = "Programmation GTB a verifier — consommation hors horaires detectee"
        elif "derive" in insight_str:
            bacs_context = "Derive detectee — la GTB devrait optimiser la regulation"
        elif "pointe" in insight_str or "base_load" in insight_str:
            bacs_context = "Talon/pointe anormal — verifier les consignes GTB"

        enriched.append({
            "id": ins.id,
            "type": insight_str,
            "bacs_context": bacs_context,
            "site_id": ins.site_id,
        })

    return enriched


def get_monthly_consumption(db: Session, site_id: int, months: int = 12) -> list[dict]:
    """Get monthly consumption data for chart display."""
    try:
        meter = db.query(Meter).filter(Meter.site_id == site_id).first()
        if not meter:
            return []

        now = datetime.utcnow()
        start = now - timedelta(days=months * 30)

        readings = (
            db.query(
                func.strftime('%Y-%m', MeterReading.timestamp).label('month'),
                func.sum(MeterReading.value_kwh).label('total_kwh'),
            )
            .filter(MeterReading.meter_id == meter.id, MeterReading.timestamp >= start)
            .group_by('month')
            .order_by('month')
            .all()
        )

        return [{"month": r.month, "kwh": round(r.total_kwh or 0, 1)} for r in readings]
    except Exception:
        return []


def get_hourly_heatmap(db: Session, site_id: int, days: int = 7) -> list[list[float]]:
    """
    Get 24x7 hourly heatmap data for CVC monitoring.
    Returns a 7x24 grid of average kWh per hour per day of week.
    """
    try:
        meter = db.query(Meter).filter(Meter.site_id == site_id).first()
        if not meter:
            return []

        now = datetime.utcnow()
        start = now - timedelta(days=days * 4)  # 4 weeks of data

        readings = (
            db.query(MeterReading)
            .filter(MeterReading.meter_id == meter.id, MeterReading.timestamp >= start)
            .all()
        )

        # Build 7x24 grid
        grid = [[0.0] * 24 for _ in range(7)]
        counts = [[0] * 24 for _ in range(7)]

        for r in readings:
            dow = r.timestamp.weekday()  # 0=Mon, 6=Sun
            hour = r.timestamp.hour
            grid[dow][hour] += r.value_kwh or 0
            counts[dow][hour] += 1

        # Average
        for d in range(7):
            for h in range(24):
                if counts[d][h] > 0:
                    grid[d][h] = round(grid[d][h] / counts[d][h], 1)

        return grid
    except Exception:
        return []


def get_bacs_ops_panel(db: Session, site_id: int) -> dict:
    """
    Combined ops panel data for BACS monitoring.
    KPIs + consumption findings + monthly chart + hourly heatmap.
    """
    kpis = compute_bacs_ops_kpis(db, site_id)
    findings = link_consumption_findings(db, site_id)
    monthly = get_monthly_consumption(db, site_id)
    heatmap = get_hourly_heatmap(db, site_id)

    return {
        "kpis": kpis,
        "consumption_findings": findings,
        "monthly_consumption": monthly,
        "hourly_heatmap": heatmap,
        "cvc_alerts_stub": [
            {"type": "temperature_drift", "message": "Derive temperature +2C zone Nord", "severity": "medium"},
            {"type": "schedule_mismatch", "message": "CVC actif hors planning (dimanche 14h)", "severity": "high"},
            {"type": "efficiency_drop", "message": "COP chiller 1 en baisse: 2.8 vs 3.5 nominal", "severity": "low"},
        ],
    }
