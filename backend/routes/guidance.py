"""
PROMEOS - Guidance / Action Plan API
GET /api/guidance/action-plan
GET /api/guidance/readiness
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access

from services.action_plan_engine import compute_action_plan

router = APIRouter(prefix="/api/guidance", tags=["Guidance"])


@router.get("/action-plan")
def get_action_plan(
    portefeuille_id: Optional[int] = Query(None, description="Filtrer par portefeuille"),
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    limit: int = Query(50, le=500, description="Nombre max d'actions"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Plan d'action priorise cross-portfolio ("Waze" for compliance).
    """
    if site_id:
        check_site_access(auth, site_id)
    result = compute_action_plan(db, portefeuille_id=portefeuille_id, site_id=site_id)
    result["actions"] = result["actions"][:limit]
    return result


@router.get("/readiness")
def get_readiness(
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Score de readiness + summary (lightweight).
    """
    result = compute_action_plan(db)
    return {
        "readiness_score": result["readiness_score"],
        "summary": result["summary"],
    }
