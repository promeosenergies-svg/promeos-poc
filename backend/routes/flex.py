"""
PROMEOS - Flex Routes (Mini + Foundations Sprint 21)
GET  /api/sites/{site_id}/flex/mini — flex potential score + top 3 levers
GET  /api/flex/assets               — list flex assets
POST /api/flex/assets               — create flex asset
PATCH /api/flex/assets/{asset_id}   — update flex asset
GET  /api/flex/assets/sync-from-bacs — sync BACS CVC to flex assets
GET  /api/flex/assessment           — flex assessment (asset-based or heuristic)
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.flex_mini import compute_flex_mini

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


@flex_foundation_router.get("/assets/sync-from-bacs")
def sync_bacs(site_id: int = Query(...), db: Session = Depends(get_db)):
    """Sync CVC systems from BACS to FlexAsset inventory."""
    from services.flex_assessment_service import sync_bacs_to_flex_assets

    result = sync_bacs_to_flex_assets(db, site_id)
    db.commit()
    return result


@flex_foundation_router.get("/assessment")
def get_flex_assessment(site_id: int = Query(...), db: Session = Depends(get_db)):
    """Get flex assessment for a site (asset-based or heuristic fallback)."""
    from services.flex_assessment_service import compute_flex_assessment

    return compute_flex_assessment(db, site_id)


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
