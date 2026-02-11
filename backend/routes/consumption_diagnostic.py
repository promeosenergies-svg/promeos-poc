"""
PROMEOS - Routes Diagnostic Consommation V1
GET /api/consumption/insights — insights aggreges par org
POST /api/consumption/diagnose — lancer le diagnostic
POST /api/consumption/seed-demo — generer des conso demo
GET /api/consumption/site/:id — insights d'un site
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Organisation, Site, ConsumptionInsight
from services.consumption_diagnostic import (
    generate_demo_consumption,
    run_diagnostic,
    run_diagnostic_org,
    get_insights_summary,
)

router = APIRouter(prefix="/api/consumption", tags=["Consumption Diagnostic"])


@router.get("/insights")
def consumption_insights(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Aggregate consumption insights for an organisation."""
    if org_id is None:
        org = db.query(Organisation).first()
        if not org:
            return {
                "total_insights": 0, "by_type": {},
                "total_loss_kwh": 0, "total_loss_eur": 0,
                "sites_with_insights": 0, "insights": [],
            }
        org_id = org.id

    return get_insights_summary(db, org_id)


@router.get("/site/{site_id}")
def site_insights(site_id: int, db: Session = Depends(get_db)):
    """Get consumption insights for a specific site."""
    import json
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    insights = (
        db.query(ConsumptionInsight)
        .filter(ConsumptionInsight.site_id == site_id)
        .all()
    )

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "insights": [
            {
                "id": ci.id,
                "type": ci.type,
                "severity": ci.severity,
                "message": ci.message,
                "estimated_loss_kwh": ci.estimated_loss_kwh,
                "estimated_loss_eur": ci.estimated_loss_eur,
                "metrics": json.loads(ci.metrics_json) if ci.metrics_json else {},
                "period_start": ci.period_start.isoformat() if ci.period_start else None,
                "period_end": ci.period_end.isoformat() if ci.period_end else None,
            }
            for ci in insights
        ],
    }


@router.post("/diagnose")
def diagnose(
    org_id: Optional[int] = Query(None),
    days: int = Query(30),
    db: Session = Depends(get_db),
):
    """Run diagnostics for all sites of an organisation."""
    if org_id is None:
        org = db.query(Organisation).first()
        if not org:
            raise HTTPException(status_code=400, detail="Aucune organisation trouvee.")
        org_id = org.id

    result = run_diagnostic_org(db, org_id, days=days)
    return {"status": "ok", **result}


@router.post("/seed-demo")
def seed_demo_consumption(
    site_id: Optional[int] = Query(None),
    days: int = Query(30),
    db: Session = Depends(get_db),
):
    """Generate demo consumption data for a site (or all sites if site_id is None)."""
    if site_id:
        result = generate_demo_consumption(db, site_id, days=days)
        return {"status": "ok", "sites": [result]}

    # Seed all sites
    sites = db.query(Site).filter(Site.actif == True).all()
    if not sites:
        raise HTTPException(status_code=400, detail="Aucun site actif.")

    results = []
    for site in sites:
        r = generate_demo_consumption(db, site.id, days=days)
        results.append(r)

    return {"status": "ok", "sites": results, "total": len(results)}
