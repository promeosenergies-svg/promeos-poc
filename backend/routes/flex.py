"""
PROMEOS - Flex Mini Routes
GET /api/sites/{site_id}/flex/mini — flex potential score + top 3 levers
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.flex_mini import compute_flex_mini

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
