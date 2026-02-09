"""
PROMEOS - Routes API Compliance Engine
Endpoint to trigger recomputation of site conformity snapshots
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from services.compliance_engine import (
    recompute_site,
    recompute_portfolio,
    recompute_organisation,
)

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


@router.post("/recompute")
def recompute_compliance(
    scope: str = Query(..., description="Scope: 'org', 'portfolio', or 'site'"),
    id: int = Query(..., description="ID of the org, portfolio, or site"),
    db: Session = Depends(get_db),
):
    """
    POST /api/compliance/recompute?scope=org|portfolio|site&id=<id>

    Recomputes compliance snapshots from obligations.
    """
    try:
        if scope == "site":
            snapshot = recompute_site(db, site_id=id)
            return {"status": "ok", "scope": "site", "site_id": id, "snapshot": snapshot}
        elif scope == "portfolio":
            result = recompute_portfolio(db, portefeuille_id=id)
            return {"status": "ok", "scope": "portfolio", **result}
        elif scope == "org":
            result = recompute_organisation(db, organisation_id=id)
            return {"status": "ok", "scope": "org", **result}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope '{scope}'. Must be 'org', 'portfolio', or 'site'.",
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
