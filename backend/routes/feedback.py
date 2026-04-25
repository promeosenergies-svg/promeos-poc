"""
PROMEOS — Feedback endpoints (CX Gap #7)
POST /api/feedback/csat — enregistre une réponse CSAT (score 1-5 + verbatim)
GET  /api/feedback/csat/should-show — True si l'utilisateur doit voir le CSAT
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import get_effective_org_id
from models import Organisation
from models.csat import CsatResponse

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])

CSAT_MIN_DAYS_SINCE_CREATION = 14
CSAT_COOLDOWN_DAYS = 90


@router.post("/csat")
def submit_csat(
    org_id: int = Query(...),
    score: int = Body(..., ge=1, le=5),
    verbatim: Optional[str] = Body(None, max_length=500),
    trigger_type: str = Body("j14_auto"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    effective_org_id = get_effective_org_id(auth, org_id)
    if not effective_org_id:
        raise HTTPException(status_code=400, detail="org_id requis")

    entry = CsatResponse(
        org_id=effective_org_id,
        user_id=auth.user.id if auth else None,
        score=score,
        verbatim=verbatim,
        trigger_type=trigger_type,
    )
    db.add(entry)
    db.commit()
    return {"status": "recorded", "id": entry.id}


@router.get("/csat/should-show")
def should_show_csat(
    org_id: int = Query(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Retourne True si l'utilisateur doit voir le CSAT :
    - org créée > 14 jours
    - aucun CSAT récent (< 90 jours)
    """
    effective_org_id = get_effective_org_id(auth, org_id)
    if not effective_org_id:
        return {"show": False}

    org = db.query(Organisation).filter(Organisation.id == effective_org_id).first()
    if not org or not org.created_at:
        return {"show": False}

    now = datetime.now(timezone.utc)
    # Handle timezone-naive created_at from older rows
    org_created = org.created_at
    if org_created.tzinfo is None:
        org_created = org_created.replace(tzinfo=timezone.utc)

    days_since_creation = (now - org_created).days
    if days_since_creation < CSAT_MIN_DAYS_SINCE_CREATION:
        return {"show": False, "days_since_creation": days_since_creation}

    cooldown_cutoff = now - timedelta(days=CSAT_COOLDOWN_DAYS)
    recent = (
        db.query(CsatResponse)
        .filter(
            CsatResponse.org_id == effective_org_id,
            CsatResponse.created_at >= cooldown_cutoff,
        )
        .first()
    )

    return {
        "show": recent is None,
        "days_since_creation": days_since_creation,
    }
