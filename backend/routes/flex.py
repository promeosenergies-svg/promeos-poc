"""
PROMEOS - Flex Routes (Mini + Foundations Sprint 21)
GET  /api/sites/{site_id}/flex/mini — flex potential score + top 3 levers
GET  /api/flex/assets               — list flex assets
POST /api/flex/assets               — create flex asset
PATCH /api/flex/assets/{asset_id}   — update flex asset
POST /api/flex/assets/sync-from-bacs — sync BACS CVC to flex assets
GET  /api/flex/assessment           — flex assessment (asset-based or heuristic)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Body, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from services.flex_mini import compute_flex_mini
from middleware.auth import get_optional_auth, AuthContext

# --- Original router: /api/sites prefix (flex mini) ---
router = APIRouter(prefix="/api/sites", tags=["Flex Mini"])


@router.get("/{site_id}/flex/mini")
def flex_mini(
    site_id: int,
    start: Optional[str] = Query(None, description="Period start (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="Period end (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """Mini flex potential: score 0-100 + top 3 levers with justification."""
    return compute_flex_mini(db, site_id, start, end)


# --- New router: /api/flex prefix (Sprint 21 Foundations) ---
flex_foundation_router = APIRouter(prefix="/api/flex", tags=["Flex Foundations"])


@flex_foundation_router.get("/assets")
def list_flex_assets(
    site_id: Optional[int] = Query(None),
    asset_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List flex assets, optionally filtered by site."""
    from models.flex_models import FlexAsset

    q = db.query(FlexAsset).filter(FlexAsset.status == "active")
    if site_id:
        q = q.filter(FlexAsset.site_id == site_id)
    if asset_type:
        q = q.filter(FlexAsset.asset_type == asset_type)
    assets = q.all()
    return {"total": len(assets), "assets": [_serialize_flex_asset(a) for a in assets]}


@flex_foundation_router.post("/assets")
def create_flex_asset(body: dict = Body(...), db: Session = Depends(get_db)):
    """Create a flex asset."""
    from models.flex_models import FlexAsset

    # Validate confidence rule
    if body.get("confidence") == "high" and not body.get("data_source"):
        raise HTTPException(status_code=400, detail="confidence=high requires data_source")

    asset = FlexAsset(
        site_id=body["site_id"],
        batiment_id=body.get("batiment_id"),
        bacs_cvc_system_id=body.get("bacs_cvc_system_id"),
        asset_type=body["asset_type"],
        label=body["label"],
        power_kw=body.get("power_kw"),
        energy_kwh=body.get("energy_kwh"),
        is_controllable=body.get("is_controllable", False),
        control_method=body.get("control_method"),
        gtb_class=body.get("gtb_class"),
        data_source=body.get("data_source"),
        confidence=body.get("confidence", "unverified"),
        notes=body.get("notes"),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return _serialize_flex_asset(asset)


@flex_foundation_router.patch("/assets/{asset_id}")
def update_flex_asset(asset_id: int, body: dict = Body(...), db: Session = Depends(get_db)):
    """Update a flex asset."""
    from models.flex_models import FlexAsset

    asset = db.query(FlexAsset).filter(FlexAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset non trouve")
    for key in (
        "label",
        "power_kw",
        "energy_kwh",
        "is_controllable",
        "control_method",
        "gtb_class",
        "data_source",
        "confidence",
        "status",
        "notes",
    ):
        if key in body:
            setattr(asset, key, body[key])
    if body.get("confidence") == "high" and not (body.get("data_source") or asset.data_source):
        raise HTTPException(status_code=400, detail="confidence=high requires data_source")
    db.commit()
    return _serialize_flex_asset(asset)


@flex_foundation_router.post("/assets/sync-from-bacs")
def sync_bacs(body: dict = Body(...), db: Session = Depends(get_db)):
    """Sync CVC systems from BACS to FlexAsset inventory."""
    from services.flex_assessment_service import sync_bacs_to_flex_assets

    site_id = body["site_id"]
    result = sync_bacs_to_flex_assets(db, site_id)
    db.commit()
    return result


@flex_foundation_router.get("/assessment")
def get_flex_assessment(site_id: int = Query(...), db: Session = Depends(get_db)):
    """Get flex assessment for a site (asset-based or heuristic fallback)."""
    from services.flex_assessment_service import compute_flex_assessment

    return compute_flex_assessment(db, site_id)


@flex_foundation_router.get("/regulatory-opportunities")
def list_regulatory_opportunities(
    site_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List regulatory opportunities (APER, CEE, BACS flex, NEBCO)."""
    from models.flex_models import RegulatoryOpportunity

    q = db.query(RegulatoryOpportunity)
    if site_id:
        q = q.filter(RegulatoryOpportunity.site_id == site_id)
    if regulation:
        q = q.filter(RegulatoryOpportunity.regulation == regulation)
    items = q.order_by(RegulatoryOpportunity.deadline.asc().nullslast()).all()
    return {"total": len(items), "opportunities": [_serialize_reg_opp(o) for o in items]}


@flex_foundation_router.post("/regulatory-opportunities")
def create_regulatory_opportunity(body: dict = Body(...), db: Session = Depends(get_db)):
    """Create a regulatory opportunity for a site."""
    from datetime import datetime
    from models.flex_models import RegulatoryOpportunity

    # Parse deadline string to datetime if provided
    deadline_raw = body.get("deadline")
    deadline_val = None
    if deadline_raw:
        if isinstance(deadline_raw, str):
            try:
                deadline_val = datetime.fromisoformat(deadline_raw)
            except ValueError:
                deadline_val = datetime.strptime(deadline_raw, "%Y-%m-%d")
        else:
            deadline_val = deadline_raw

    opp = RegulatoryOpportunity(
        site_id=body["site_id"],
        regulation=body["regulation"],
        is_obligation=body.get("is_obligation", False),
        obligation_type=body.get("obligation_type"),
        opportunity_type=body.get("opportunity_type"),
        eligible=body.get("eligible"),
        eligibility_reason=body.get("eligibility_reason"),
        eligibility_caveat=body.get("eligibility_caveat"),
        surface_m2=body.get("surface_m2"),
        surface_type=body.get("surface_type"),
        threshold_m2=body.get("threshold_m2"),
        deadline=deadline_val,
        deadline_source=body.get("deadline_source"),
        cee_eligible=body.get("cee_eligible"),
        cee_caveat=body.get(
            "cee_caveat", "Eligibilite potentielle — volume et valorisation a confirmer par operateur CEE agree"
        ),
        cee_tri_min_years=body.get("cee_tri_min_years", 3),
        source_regulation=body.get("source_regulation"),
        notes=body.get("notes"),
    )
    db.add(opp)
    db.commit()
    db.refresh(opp)
    return _serialize_reg_opp(opp)


@flex_foundation_router.get("/tariff-windows")
def list_tariff_windows(
    segment: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List tariff windows (saisonnalisees, versionnees)."""
    from models.flex_models import TariffWindow

    q = db.query(TariffWindow)
    if segment:
        q = q.filter(TariffWindow.segment == segment)
    if season:
        q = q.filter(TariffWindow.season == season)
    return {
        "total": q.count(),
        "windows": [
            {
                "id": w.id,
                "name": w.name,
                "segment": w.segment,
                "season": w.season,
                "months": w.months,
                "period_type": w.period_type,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "day_types": w.day_types,
                "price_component_eur_kwh": w.price_component_eur_kwh,
                "effective_from": w.effective_from,
                "source": w.source,
            }
            for w in q.all()
        ],
    }


@flex_foundation_router.post("/tariff-windows")
def create_tariff_window(body: dict = Body(...), db: Session = Depends(get_db)):
    """Create a tariff window."""
    import json
    from models.flex_models import TariffWindow

    w = TariffWindow(
        calendar_id=body.get("calendar_id"),
        name=body["name"],
        segment=body.get("segment"),
        season=body["season"],
        months=json.dumps(body["months"]) if isinstance(body["months"], list) else body["months"],
        period_type=body["period_type"],
        start_time=body["start_time"],
        end_time=body["end_time"],
        day_types=json.dumps(body.get("day_types", ["all"])),
        price_component_eur_kwh=body.get("price_component_eur_kwh"),
        effective_from=body.get("effective_from"),
        source=body.get("source"),
        source_ref=body.get("source_ref"),
        notes=body.get("notes"),
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "name": w.name, "period_type": w.period_type}


@flex_foundation_router.get("/portfolio")
def flex_portfolio(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Portfolio-level flex ranking: quick wins by site."""
    from models import Site, Portefeuille, EntiteJuridique
    from models.flex_models import FlexAsset
    from models.base import not_deleted
    from services.flex_assessment_service import compute_flex_assessment

    org_header = request.headers.get("X-Org-Id")
    org_id = int(org_header) if org_header else (auth.org_id if auth and auth.org_id else 1)

    sites = (
        db.query(Site)
        .join(Portefeuille)
        .join(EntiteJuridique)
        .filter(
            EntiteJuridique.organisation_id == org_id,
            not_deleted(Site),
        )
        .all()
    )

    rankings = []
    for site in sites:
        assessment = compute_flex_assessment(db, site.id)
        asset_count = db.query(FlexAsset).filter(FlexAsset.site_id == site.id, FlexAsset.status == "active").count()

        rankings.append(
            {
                "site_id": site.id,
                "site_name": site.nom,
                "flex_score": assessment.get("flex_score", 0),
                "potential_kw": assessment.get("potential_kw", 0),
                "source": assessment.get("source", "unknown"),
                "confidence": assessment.get("confidence", "low"),
                "asset_count": asset_count,
                "dimensions": assessment.get("dimensions", {}),
            }
        )

    rankings.sort(key=lambda r: -(r["flex_score"] or 0))

    return {
        "total_sites": len(rankings),
        "total_potential_kw": sum(r["potential_kw"] for r in rankings),
        "avg_flex_score": round(sum(r["flex_score"] for r in rankings) / max(len(rankings), 1), 1),
        "rankings": rankings,
    }


def _serialize_flex_asset(a) -> dict:
    return {
        "id": a.id,
        "site_id": a.site_id,
        "batiment_id": a.batiment_id,
        "bacs_cvc_system_id": a.bacs_cvc_system_id,
        "asset_type": a.asset_type.value if hasattr(a.asset_type, "value") else a.asset_type,
        "label": a.label,
        "power_kw": a.power_kw,
        "energy_kwh": a.energy_kwh,
        "is_controllable": a.is_controllable,
        "control_method": a.control_method.value
        if a.control_method and hasattr(a.control_method, "value")
        else a.control_method,
        "gtb_class": a.gtb_class,
        "data_source": a.data_source,
        "confidence": a.confidence,
        "status": a.status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_reg_opp(o) -> dict:
    return {
        "id": o.id,
        "site_id": o.site_id,
        "regulation": o.regulation,
        "is_obligation": o.is_obligation,
        "obligation_type": o.obligation_type,
        "opportunity_type": o.opportunity_type,
        "eligible": o.eligible,
        "eligibility_reason": o.eligibility_reason,
        "eligibility_caveat": o.eligibility_caveat,
        "surface_m2": o.surface_m2,
        "surface_type": o.surface_type,
        "threshold_m2": o.threshold_m2,
        "deadline": o.deadline.isoformat() if o.deadline else None,
        "deadline_source": o.deadline_source,
        "cee_eligible": o.cee_eligible,
        "cee_caveat": o.cee_caveat,
        "cee_tri_min_years": o.cee_tri_min_years,
        "source_regulation": o.source_regulation,
        "notes": o.notes,
    }
