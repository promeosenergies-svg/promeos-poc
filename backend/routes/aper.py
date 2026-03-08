"""
PROMEOS — Routes APER (solarisation parkings & toitures)
Prefix: /api/aper
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.aper_service import get_aper_dashboard, estimate_pv_production

logger = logging.getLogger("promeos.aper")

router = APIRouter(prefix="/api/aper", tags=["APER — Solarisation"])


@router.get("/dashboard")
def aper_dashboard(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Vue agregee APER : sites eligibles, surfaces, echeances."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    try:
        return get_aper_dashboard(db, effective_org_id)
    except Exception as e:
        logger.error(f"APER dashboard error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur calcul dashboard APER")


@router.get("/site/{site_id}/estimate")
def aper_estimate(
    site_id: int,
    request: Request,
    surface_type: str = Query("parking", pattern="^(parking|roof)$"),
    surface_m2: Optional[float] = Query(None, ge=0),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Estimation production PV pour un site."""
    resolve_org_id(request, auth, db, org_id_override=org_id)
    result = estimate_pv_production(db, site_id, surface_m2=surface_m2, surface_type=surface_type)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return result
