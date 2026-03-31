"""
Site Intelligence endpoint — KB-driven anomalies, recommendations, archetype for a site.
Single source of truth for Site360 intelligence panel.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Site, Meter
from models.energy_models import UsageProfile, Anomaly, Recommendation
from models.kb_models import KBArchetype

router = APIRouter(prefix="/api/sites", tags=["site-intelligence"])


@router.get("/{site_id}/intelligence")
def get_site_intelligence(site_id: int, db: Session = Depends(get_db)):
    """Return full KB intelligence for a site: archetype, anomalies, recommendations, summary."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    meters = db.query(Meter).filter(Meter.site_id == site_id).all()
    if not meters:
        return {
            "site_id": site_id,
            "site_name": site.nom,
            "archetype": None,
            "anomalies": [],
            "recommendations": [],
            "summary": _empty_summary(),
            "status": "no_meters",
        }

    meter_ids = [m.id for m in meters]

    # --- Archetype (best profile) ---
    profile = (
        db.query(UsageProfile)
        .filter(UsageProfile.meter_id.in_(meter_ids))
        .order_by(UsageProfile.archetype_match_score.desc().nullslast())
        .first()
    )

    archetype_data = None
    if profile and profile.archetype_code:
        kb_arch = db.query(KBArchetype).filter(KBArchetype.code == profile.archetype_code).first()
        archetype_data = {
            "code": profile.archetype_code,
            "match_score": round(profile.archetype_match_score or 0, 2),
            "title": kb_arch.title if kb_arch else profile.archetype_code,
            "kwh_m2_range": {
                "min": kb_arch.kwh_m2_min,
                "max": kb_arch.kwh_m2_max,
                "avg": kb_arch.kwh_m2_avg,
            }
            if kb_arch
            else None,
        }

    # --- Anomalies KB (active) ---
    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.meter_id.in_(meter_ids), Anomaly.is_active == True)
        .order_by(Anomaly.severity.desc(), Anomaly.confidence.desc())
        .all()
    )

    anomalies_data = [
        {
            "id": a.id,
            "anomaly_code": a.anomaly_code,
            "title": a.title,
            "severity": a.severity.value if hasattr(a.severity, "value") else str(a.severity),
            "confidence": round(a.confidence, 2) if a.confidence else 0,
            "deviation_pct": round(a.deviation_pct, 1) if a.deviation_pct else None,
            "measured_value": a.measured_value,
            "threshold_value": a.threshold_value,
        }
        for a in anomalies
    ]

    # --- Recommendations (non-dismissed, by ICE) ---
    recos = (
        db.query(Recommendation)
        .filter(Recommendation.meter_id.in_(meter_ids))
        .order_by(Recommendation.ice_score.desc().nullslast())
        .all()
    )

    recos_data = [
        {
            "id": r.id,
            "recommendation_code": r.recommendation_code,
            "title": r.title,
            "estimated_savings_pct": r.estimated_savings_pct,
            "estimated_savings_kwh_year": r.estimated_savings_kwh_year,
            "estimated_savings_eur_year": r.estimated_savings_eur_year,
            "ice_score": round(r.ice_score, 3) if r.ice_score else None,
            "impact_score": r.impact_score,
            "confidence_score": r.confidence_score,
            "ease_score": r.ease_score,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
        }
        for r in recos
    ]

    # --- Summary ---
    severity_counts = {}
    for a in anomalies:
        sev = a.severity.value if hasattr(a.severity, "value") else str(a.severity)
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    total_savings_kwh = sum(r.estimated_savings_kwh_year or 0 for r in recos)
    total_savings_eur = sum(r.estimated_savings_eur_year or 0 for r in recos)

    return {
        "site_id": site_id,
        "site_name": site.nom,
        "archetype": archetype_data,
        "anomalies": anomalies_data,
        "recommendations": recos_data,
        "summary": {
            "total_anomalies": len(anomalies),
            "severity_breakdown": severity_counts,
            "total_recommendations": len(recos),
            "potential_savings_kwh_year": round(total_savings_kwh),
            "potential_savings_eur_year": round(total_savings_eur),
        },
        "status": "analyzed" if profile else "pending_analysis",
    }


def _empty_summary():
    return {
        "total_anomalies": 0,
        "severity_breakdown": {},
        "total_recommendations": 0,
        "potential_savings_kwh_year": 0,
        "potential_savings_eur_year": 0,
    }
