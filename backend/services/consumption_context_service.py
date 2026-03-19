"""
PROMEOS — Consumption Context Service V0
Orchestrateur: profil conso (heatmap 7x24, daily profile, baseload),
contexte d'activite (schedule, archetype, TOU), anomalies & behavior_score.

Reutilise 100% des services existants:
- consumption_diagnostic.py (5 detecteurs + run_diagnostic)
- tou_service.py (compute_hphc_breakdown_v2 → heatmap)
- site_config.py (get_site_schedule_params, get_site_price_ref)
- kb archetypes (NAF → archetype lookup)
"""

import json
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models import Site, Meter, MeterReading, ConsumptionInsight, Portefeuille, EntiteJuridique
from models.energy_models import FrequencyType, EnergyVector
from services.ems.timeseries_service import resolve_best_freq, get_site_meter_ids

logger = logging.getLogger(__name__)


# ========================================
# Pure computation: behavior_score
# ========================================


def compute_behavior_score(
    offhours_pct: float,
    baseload_ratio: float,
    drift_pct: float,
    weekend_ratio: float,
) -> Tuple[int, dict]:
    """Compute behavior_score (0-100) from 4 KPIs.

    Deterministic, transparent, capped penalties.
    Returns (score, breakdown_dict).
    """
    p_offhours = min(40, max(0, offhours_pct * 0.8))
    p_baseload = min(25, max(0, (baseload_ratio - 30) * 0.5))
    p_drift = min(20, max(0, drift_pct * 2))
    p_weekend = min(15, max(0, (weekend_ratio - 0.3) * 30))

    total_penalty = p_offhours + p_baseload + p_drift + p_weekend
    score = max(0, round(100 - total_penalty))

    breakdown = {
        "offhours_penalty": round(p_offhours, 1),
        "baseload_penalty": round(p_baseload, 1),
        "drift_penalty": round(p_drift, 1),
        "weekend_penalty": round(p_weekend, 1),
        "total_penalty": round(total_penalty, 1),
    }
    return score, breakdown


# ========================================
# Pure computation: weekend_active detection
# ========================================


def detect_weekend_active(readings: list, schedule: dict) -> dict:
    """Detect significant weekend activity when schedule says closed.

    Returns dict with detected, ratio, severity, message.
    """
    if not readings or len(readings) < 48:
        return {"detected": False, "reason": "insufficient_data"}

    # If 24/7 or weekends are open days, no detection
    if schedule.get("is_24_7", False):
        return {"detected": False, "reason": "is_24_7"}

    open_days = schedule.get("open_days", {0, 1, 2, 3, 4})
    if isinstance(open_days, (list, tuple)):
        open_days = set(open_days)
    if 5 in open_days and 6 in open_days:
        return {"detected": False, "reason": "weekends_open"}

    weekday_kwh = []
    weekend_kwh = []

    for r in readings:
        wd = r.timestamp.weekday() if hasattr(r, "timestamp") else r.get("weekday", 0)
        val = r.value_kwh if hasattr(r, "value_kwh") else r.get("value_kwh", 0)
        if wd >= 5:
            weekend_kwh.append(val)
        else:
            weekday_kwh.append(val)

    if not weekday_kwh or not weekend_kwh:
        return {"detected": False, "reason": "no_data_for_period"}

    avg_weekday = sum(weekday_kwh) / len(weekday_kwh)
    avg_weekend = sum(weekend_kwh) / len(weekend_kwh)

    if avg_weekday == 0:
        return {"detected": False, "reason": "zero_weekday"}

    ratio = avg_weekend / avg_weekday

    if ratio < 0.5:
        return {
            "detected": False,
            "weekend_avg_kwh": round(avg_weekend, 2),
            "weekday_avg_kwh": round(avg_weekday, 2),
            "ratio": round(ratio, 3),
        }

    severity = "high" if ratio > 0.8 else "medium"
    return {
        "detected": True,
        "weekend_avg_kwh": round(avg_weekend, 2),
        "weekday_avg_kwh": round(avg_weekday, 2),
        "ratio": round(ratio, 3),
        "severity": severity,
        "message": f"Consommation weekend = {ratio:.0%} de la semaine "
        f"({avg_weekend:.1f} vs {avg_weekday:.1f} kWh/h moy.) — "
        f"verifier les equipements en fonctionnement le week-end",
    }


# ========================================
# Profile: heatmap + daily profile + baseload
# ========================================


def get_consumption_profile(db: Session, site_id: int, days: int = 30) -> dict:
    """Generate consumption profile: heatmap 7x24, daily profile 24pts, baseload, peak."""
    from services.tou_service import compute_hphc_breakdown_v2

    # Heatmap from existing service
    hphc = compute_hphc_breakdown_v2(db, site_id, days)
    heatmap = hphc.get("heatmap", [])

    # Get raw readings for daily profile + baseload
    meter_ids = get_site_meter_ids(db, site_id, EnergyVector.ELECTRICITY)

    readings = []
    if meter_ids:
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now_dt - timedelta(days=days)
        best = resolve_best_freq(db, meter_ids, cutoff, now_dt)
        readings = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= cutoff,
                MeterReading.frequency.in_(best),
            )
            .order_by(MeterReading.timestamp)
            .all()
        )

    # Daily profile: 24 points (avg, min, max per hour)
    hour_buckets = {h: [] for h in range(24)}
    for r in readings:
        hour_buckets[r.timestamp.hour].append(r.value_kwh)

    daily_profile = []
    for h in range(24):
        vals = hour_buckets[h]
        if vals:
            daily_profile.append(
                {
                    "hour": h,
                    "avg_kwh": round(sum(vals) / len(vals), 2),
                    "min_kwh": round(min(vals), 2),
                    "max_kwh": round(max(vals), 2),
                    "count": len(vals),
                }
            )
        else:
            daily_profile.append(
                {
                    "hour": h,
                    "avg_kwh": 0,
                    "min_kwh": 0,
                    "max_kwh": 0,
                    "count": 0,
                }
            )

    # Baseload: Q10 of night readings (00h-05h weekdays)
    all_values = sorted([r.value_kwh for r in readings]) if readings else []
    night_values = [r.value_kwh for r in readings if r.timestamp.hour < 5 and r.timestamp.weekday() < 5]
    if not night_values and all_values:
        night_values = all_values  # fallback: use all data

    baseload_kw = 0.0
    peak_kw = 0.0
    if night_values:
        sorted_night = sorted(night_values)
        q10_idx = max(0, int(len(sorted_night) * 0.10))
        baseload_kw = round(sorted_night[q10_idx], 2)
    if all_values:
        p90_idx = min(len(all_values) - 1, int(len(all_values) * 0.90))
        peak_kw = round(all_values[p90_idx], 2)

    load_factor = round(baseload_kw / peak_kw, 3) if peak_kw > 0 else 0

    # Days analyzed
    if readings:
        days_span = (readings[-1].timestamp - readings[0].timestamp).days
    else:
        days_span = 0

    confidence = "high" if len(readings) >= days * 20 else ("medium" if len(readings) >= days * 10 else "low")

    return {
        "site_id": site_id,
        "heatmap": heatmap,
        "daily_profile": daily_profile,
        "baseload_kw": baseload_kw,
        "peak_kw": peak_kw,
        "load_factor": load_factor,
        "total_kwh": hphc.get("total_kwh", 0),
        "hp_kwh": hphc.get("hp_kwh", 0),
        "hc_kwh": hphc.get("hc_kwh", 0),
        "hp_ratio": hphc.get("hp_ratio", 0),
        "readings_count": len(readings),
        "days_analyzed": days_span,
        "confidence": confidence,
    }


# ========================================
# Activity context: schedule + archetype + TOU
# ========================================


def get_activity_context(db: Session, site_id: int) -> dict:
    """Get activity context: operating schedule, archetype from NAF, active TOU."""
    from fastapi import HTTPException
    from routes.site_config import get_site_schedule_params
    from services.tou_service import get_active_schedule
    from models.site_operating_schedule import SiteOperatingSchedule

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    # Schedule
    schedule_params = get_site_schedule_params(db, site_id)

    # Raw schedule for UI (with string times)
    raw_sched = db.query(SiteOperatingSchedule).filter(SiteOperatingSchedule.site_id == site_id).first()
    schedule_detail = None
    if raw_sched:
        schedule_detail = {
            "open_days": raw_sched.open_days,
            "open_time": raw_sched.open_time,
            "close_time": raw_sched.close_time,
            "is_24_7": raw_sched.is_24_7,
            "timezone": raw_sched.timezone,
            "exceptions_json": raw_sched.exceptions_json,
            "source": "database",
        }
    else:
        schedule_detail = {
            "open_days": "0,1,2,3,4",
            "open_time": "08:00",
            "close_time": "19:00",
            "is_24_7": False,
            "timezone": "Europe/Paris",
            "exceptions_json": None,
            "source": "default",
        }

    # Archetype from NAF
    archetype = None
    naf_code = site.naf_code if hasattr(site, "naf_code") else None
    if naf_code:
        try:
            from models.kb_models import KBArchetype, KBMappingCode

            mapping = db.query(KBMappingCode).filter(KBMappingCode.code == naf_code).first()
            if mapping:
                arch = db.query(KBArchetype).filter(KBArchetype.code == mapping.archetype_code).first()
                if arch:
                    archetype = {
                        "code": arch.code,
                        "title": arch.title,
                        "kwh_m2_min": arch.kwh_m2_min,
                        "kwh_m2_max": arch.kwh_m2_max,
                        "kwh_m2_avg": arch.kwh_m2_avg,
                        "segment_tags": json.loads(arch.segment_tags) if arch.segment_tags else [],
                    }
        except (json.JSONDecodeError, ValueError, AttributeError) as exc:
            logger.warning("Archetype lookup failed for NAF %s on site %d: %s", naf_code, site_id, exc)

    # Active TOU schedule
    tou = get_active_schedule(db, site_id)

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "naf_code": naf_code,
        "schedule": schedule_detail,
        "schedule_params": {
            "open_time": schedule_params["open_time"],
            "close_time": schedule_params["close_time"],
            "open_days": list(schedule_params["open_days"]),
            "is_24_7": schedule_params["is_24_7"],
        },
        "archetype": archetype,
        "tou_schedule": tou,
    }


# ========================================
# Anomalies + score
# ========================================


def get_anomalies_and_score(db: Session, site_id: int, days: int = 30) -> dict:
    """Get anomalies, KPIs, and behavior_score for a site."""
    from services.consumption_diagnostic import run_diagnostic
    from routes.site_config import get_site_schedule_params

    # Run or refresh diagnostics
    existing = db.query(ConsumptionInsight).filter(ConsumptionInsight.site_id == site_id).all()

    if not existing:
        existing = run_diagnostic(db, site_id, days=days)
        db.commit()

    # Extract KPIs from insight metrics
    offhours_pct = 0.0
    baseload_ratio = 0.0
    drift_pct = 0.0
    insights_list = []

    for ci in existing:
        metrics = {}
        if ci.metrics_json:
            try:
                metrics = json.loads(ci.metrics_json)
            except (json.JSONDecodeError, TypeError):
                pass

        insight_dict = {
            "id": ci.id,
            "type": ci.type,
            "severity": ci.severity,
            "message": ci.message,
            "metrics": metrics,
            "estimated_loss_kwh": ci.estimated_loss_kwh,
            "estimated_loss_eur": ci.estimated_loss_eur,
            "status": ci.insight_status if hasattr(ci, "insight_status") else "open",
        }

        if ci.recommended_actions_json:
            try:
                insight_dict["recommended_actions"] = json.loads(ci.recommended_actions_json)
            except (json.JSONDecodeError, TypeError):
                pass

        insights_list.append(insight_dict)

        # Extract KPIs
        if ci.type == "hors_horaires":
            offhours_pct = metrics.get("off_hours_pct", 0)
        elif ci.type == "base_load":
            baseload_ratio = metrics.get("base_ratio_pct", 0)
        elif ci.type == "derive":
            drift_pct = metrics.get("drift_pct", 0)

    # Weekend active detection
    schedule = get_site_schedule_params(db, site_id)
    meter_ids = get_site_meter_ids(db, site_id, EnergyVector.ELECTRICITY)

    weekend_result = {"detected": False, "reason": "no_meters"}
    weekend_ratio = 0.0

    if meter_ids:
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        cutoff = now_dt - timedelta(days=days)
        best = resolve_best_freq(db, meter_ids, cutoff, now_dt)
        readings = (
            db.query(MeterReading)
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= cutoff,
                MeterReading.frequency.in_(best),
            )
            .all()
        )
        weekend_result = detect_weekend_active(readings, schedule)
        weekend_ratio = weekend_result.get("ratio", 0)

    # Behavior score
    score, breakdown = compute_behavior_score(offhours_pct, baseload_ratio, drift_pct, weekend_ratio)

    # Max severity
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    max_sev = "low"
    for ci in existing:
        if severity_order.get(ci.severity, 0) > severity_order.get(max_sev, 0):
            max_sev = ci.severity

    return {
        "site_id": site_id,
        "behavior_score": score,
        "score_breakdown": breakdown,
        "kpis": {
            "offhours_pct": round(offhours_pct, 1),
            "baseload_ratio_pct": round(baseload_ratio, 1),
            "drift_pct": round(drift_pct, 1),
            "weekend_ratio": round(weekend_ratio, 3),
        },
        "insights": insights_list,
        "insights_count": len(insights_list),
        "weekend_active": weekend_result,
        "max_severity": max_sev,
    }


# ========================================
# Suggest schedule from NAF
# ========================================


def suggest_schedule_from_naf(db: Session, site_id: int) -> Optional[dict]:
    """Auto-suggest operating schedule based on site NAF code and KB archetypes."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site or not getattr(site, "naf_code", None):
        return None

    from services.naf_classifier import classify_naf

    type_site = classify_naf(site.naf_code)

    # Simple archetype mapping based on TypeSite
    SCHEDULE_HINTS = {
        "bureau": {"open_days": "0,1,2,3,4", "open_time": "08:00", "close_time": "19:00", "is_24_7": False},
        "commerce": {"open_days": "0,1,2,3,4,5", "open_time": "09:00", "close_time": "20:00", "is_24_7": False},
        "usine": {"open_days": "0,1,2,3,4", "open_time": "06:00", "close_time": "22:00", "is_24_7": False},
        "entrepot": {"open_days": "0,1,2,3,4,5", "open_time": "06:00", "close_time": "22:00", "is_24_7": False},
        "hotel": {"open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
        "hopital": {"open_days": "0,1,2,3,4,5,6", "open_time": "00:00", "close_time": "23:59", "is_24_7": True},
        "enseignement": {"open_days": "0,1,2,3,4", "open_time": "07:00", "close_time": "20:00", "is_24_7": False},
        "collectivite": {"open_days": "0,1,2,3,4", "open_time": "08:00", "close_time": "18:00", "is_24_7": False},
    }

    ts_lower = type_site.value.lower() if hasattr(type_site, "value") else str(type_site).lower()
    hint = SCHEDULE_HINTS.get(ts_lower, SCHEDULE_HINTS["bureau"])

    return {
        "naf_code": site.naf_code,
        "type_site": ts_lower,
        "suggested_schedule": hint,
        "source": "naf_heuristic",
        "confidence": "medium",
    }


# ========================================
# Portfolio summary (ranked by behavior_score)
# ========================================


def get_portfolio_behavior_summary(db: Session, org_id: int, days: int = 30) -> dict:
    """Return all org sites ranked by behavior_score, with KPI deltas."""
    sites = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif == True)
        .all()
    )

    # A.1: unified consumption for source tracking
    from services.consumption_unified_service import get_consumption_summary
    from datetime import date as _date

    today = _date.today()
    conso_start = today - timedelta(days=days)

    rows = []
    for site in sites:
        try:
            anomalies = get_anomalies_and_score(db, site.id, days)
            profile = get_consumption_profile(db, site.id, days)
            # A.1: get consumption source info
            try:
                conso_unified = get_consumption_summary(db, site.id, conso_start, today)
                consumption_source = conso_unified["source_used"]
            except Exception:
                consumption_source = None
            rows.append(
                {
                    "site_id": site.id,
                    "site_name": site.nom,
                    "behavior_score": anomalies.get("behavior_score"),
                    "max_severity": anomalies.get("max_severity"),
                    "offhours_pct": (anomalies.get("kpis") or {}).get("offhours_pct", 0),
                    "baseload_kw": profile.get("baseload_kw", 0),
                    "total_kwh": profile.get("total_kwh", 0),
                    "consumption_source": consumption_source,
                    "insights_count": len(anomalies.get("insights") or []),
                    "weekend_active": (anomalies.get("weekend_active") or {}).get("detected", False),
                }
            )
        except (ValueError, KeyError, AttributeError) as exc:
            logger.warning("Portfolio score failed for site %d: %s", site.id, exc)
            rows.append(
                {
                    "site_id": site.id,
                    "site_name": site.nom,
                    "behavior_score": None,
                    "max_severity": None,
                    "error": str(exc),
                    "offhours_pct": 0,
                    "baseload_kw": 0,
                    "total_kwh": 0,
                    "insights_count": 0,
                    "weekend_active": False,
                }
            )

    # Sort: sites with score first (ascending = worst first), then no-score
    scored = sorted([r for r in rows if r["behavior_score"] is not None], key=lambda r: r["behavior_score"])
    unscored = [r for r in rows if r["behavior_score"] is None]

    return {
        "org_id": org_id,
        "days": days,
        "sites_count": len(rows),
        "sites_scored": len(scored),
        "avg_behavior_score": round(sum(r["behavior_score"] for r in scored) / len(scored), 1) if scored else None,
        "sites": scored + unscored,
    }


# ========================================
# Full context (aggregator)
# ========================================


def get_full_context(db: Session, site_id: int, days: int = 30) -> dict:
    """Aggregate profile + activity + anomalies into one response."""
    return {
        "profile": get_consumption_profile(db, site_id, days),
        "activity": get_activity_context(db, site_id),
        "anomalies": get_anomalies_and_score(db, site_id, days),
    }
