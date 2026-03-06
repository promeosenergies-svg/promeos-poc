"""
PROMEOS — A.1 Unified Consumption Routes
3 endpoints: site summary, portfolio summary, reconciliation.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.consumption_unified_service import (
    ConsumptionSource,
    get_consumption_summary,
    get_portfolio_consumption,
    reconcile_metered_billed,
)

router = APIRouter(prefix="/api/consumption-unified", tags=["Consumption Unified"])


def _default_period(start: Optional[date], end: Optional[date]):
    """Default to last 12 months if no period specified."""
    if not end:
        end = date.today()
    if not start:
        start = end - timedelta(days=365)
    return start, end


@router.get("/site/{site_id}")
def site_consumption_summary(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    start: Optional[date] = Query(None, description="Debut periode (YYYY-MM-DD)"),
    end: Optional[date] = Query(None, description="Fin periode (YYYY-MM-DD)"),
    source: Optional[str] = Query("reconciled", description="metered|billed|reconciled"),
):
    """
    GET /api/consumption-unified/site/{site_id}
    Consommation unifiee d'un site sur une periode.
    """
    resolve_org_id(request, auth, db)
    start, end = _default_period(start, end)

    try:
        src = ConsumptionSource(source)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Source invalide: {source}. Valeurs: metered, billed, reconciled")

    return get_consumption_summary(db, site_id, start, end, src)


@router.get("/portfolio")
def portfolio_consumption_summary(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    source: Optional[str] = Query("reconciled"),
):
    """
    GET /api/consumption-unified/portfolio
    Consommation unifiee agregee pour tous les sites de l'org.
    """
    org_id = resolve_org_id(request, auth, db)
    start, end = _default_period(start, end)

    try:
        src = ConsumptionSource(source)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Source invalide: {source}")

    return get_portfolio_consumption(db, org_id, start, end, src)


@router.get("/reconcile/{site_id}")
def reconcile_site(
    site_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
):
    """
    GET /api/consumption-unified/reconcile/{site_id}
    Compare metered vs billed et retourne l'ecart.
    """
    resolve_org_id(request, auth, db)
    start, end = _default_period(start, end)

    return reconcile_metered_billed(db, site_id, start, end)
