"""
PROMEOS — NPS micro-survey (Sprint CX P1 residual)

POST /api/nps/submit — enregistre une note NPS (0-10) + verbatim optionnel.

Classification industry-standard :
  - Promoteurs : 9-10
  - Passifs    : 7-8
  - Détracteurs: 0-6

Anti-flood : 1 seule soumission par user dans une fenêtre de 90 jours
(check AuditLog.action == CX_NPS_SUBMITTED + user_id + created_at).

Le stockage s'appuie sur AuditLog via log_cx_event (pas de nouvelle table)
pour rester homogène avec les autres events CX (T2V, IAR, WAU/MAU...).
"""

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from middleware.cx_logger import CX_NPS_SUBMITTED, has_recent_audit_event, log_cx_event
from services.iam_scope import get_effective_org_id

router = APIRouter(prefix="/api/nps", tags=["NPS"])

NPS_COOLDOWN_DAYS = 90


class NpsSubmission(BaseModel):
    score: int = Field(..., ge=0, le=10, description="Note NPS 0-10")
    verbatim: Optional[str] = Field(None, max_length=1000)


def _classify(score: int) -> str:
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


@router.post("/submit")
def submit_nps(
    payload: NpsSubmission = Body(...),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Enregistre une note NPS pour l'utilisateur authentifié.

    - Validation : score ∈ [0, 10] (enforced by pydantic Field)
    - Anti-flood : 1 soumission / user / 90 jours
    - Fire event CX_NPS_SUBMITTED avec context {score, has_verbatim, category}
    """
    effective_org_id = get_effective_org_id(auth, org_id)
    if not effective_org_id:
        raise HTTPException(status_code=400, detail="org_id requis")

    user_id = auth.user.id if auth else None

    # Anti-flood : check précédente soumission dans les 90 jours
    # (seulement pertinent si user_id connu — en DEMO_MODE anonyme on laisse passer)
    if user_id is not None and has_recent_audit_event(db, user_id, CX_NPS_SUBMITTED, NPS_COOLDOWN_DAYS):
        return {"status": "already_submitted"}

    category = _classify(payload.score)
    log_cx_event(
        db,
        org_id=effective_org_id,
        user_id=user_id,
        event_type=CX_NPS_SUBMITTED,
        context={
            "score": payload.score,
            "has_verbatim": bool(payload.verbatim and payload.verbatim.strip()),
            "category": category,
        },
    )
    db.commit()

    return {"status": "recorded", "category": category}
