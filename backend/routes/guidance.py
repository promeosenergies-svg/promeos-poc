"""
PROMEOS - Guidance / Action Plan API
GET /api/guidance/action-plan
GET /api/guidance/readiness
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from services.action_plan_engine import compute_action_plan

router = APIRouter(prefix="/api/guidance", tags=["Guidance"])


@router.get("/action-plan")
def get_action_plan(
    portefeuille_id: Optional[int] = Query(None, description="Filtrer par portefeuille"),
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    limit: int = Query(50, le=500, description="Nombre max d'actions"),
    db: Session = Depends(get_db),
):
    """
    Plan d'action priorise cross-portfolio ("Waze" for compliance).
    """
    result = compute_action_plan(db, portefeuille_id=portefeuille_id, site_id=site_id)
    result["actions"] = result["actions"][:limit]
    return result


@router.get("/readiness")
def get_readiness(db: Session = Depends(get_db)):
    """
    Score de readiness + summary (lightweight).
    """
    result = compute_action_plan(db)
    return {
        "readiness_score": result["readiness_score"],
        "summary": result["summary"],
    }
