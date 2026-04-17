"""
PROMEOS — Energy Copilot routes (Chantier 3)
GET  /api/copilot/actions     — list copilot actions for org
POST /api/copilot/run         — trigger monthly analysis
POST /api/copilot/actions/{id}/validate — convert to ActionItem
POST /api/copilot/actions/{id}/reject   — reject proposal
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import get_effective_org_id
from models.copilot_models import CopilotAction
from services.copilot_engine import (
    run_copilot_monthly,
    validate_copilot_action,
    reject_copilot_action,
)

router = APIRouter(prefix="/api/copilot", tags=["energy-copilot"])


@router.get("/actions")
def list_copilot_actions(
    org_id: int = Query(...),
    status: Optional[str] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List copilot actions for an org, sorted by priority_score desc."""
    effective_org_id = get_effective_org_id(auth, org_id)
    query = db.query(CopilotAction).filter(CopilotAction.org_id == effective_org_id)
    if status:
        query = query.filter(CopilotAction.status == status)
    if site_id:
        query = query.filter(CopilotAction.site_id == site_id)

    actions = (
        query.order_by(
            CopilotAction.priority_score.desc().nullslast(),
            CopilotAction.created_at.desc(),
        )
        .limit(200)
        .all()
    )

    return {
        "actions": [
            {
                "id": a.id,
                "site_id": a.site_id,
                "rule_code": a.rule_code,
                "rule_label": a.rule_label,
                "title": a.title,
                "description": a.description,
                "category": a.category,
                "priority": a.priority,
                "priority_score": a.priority_score,
                "estimated_savings_kwh": a.estimated_savings_kwh,
                "estimated_savings_eur": a.estimated_savings_eur,
                "evidence": json.loads(a.evidence_json) if a.evidence_json else {},
                "status": a.status.value if hasattr(a.status, "value") else a.status,
                "period_month": a.period_month,
                "period_year": a.period_year,
                "action_item_id": a.action_item_id,
                "created_at": str(a.created_at) if a.created_at else None,
            }
            for a in actions
        ],
        "total": len(actions),
    }


class RunBody(BaseModel):
    org_id: int


@router.post("/run")
def run_monthly_copilot(
    body: RunBody,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Trigger monthly copilot analysis for an org."""
    effective_org_id = get_effective_org_id(auth, body.org_id)
    result = run_copilot_monthly(db, effective_org_id)
    return result


@router.post("/actions/{action_id}/validate")
def validate_action(
    action_id: int,
    db: Session = Depends(get_db),
):
    """Validate a copilot action — creates an ActionItem."""
    try:
        return validate_copilot_action(db, action_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class RejectBody(BaseModel):
    reason: str  # Motif obligatoire


@router.post("/actions/{action_id}/reject")
def reject_action(
    action_id: int,
    body: RejectBody,
    db: Session = Depends(get_db),
):
    """Reject a copilot action (motif obligatoire)."""
    try:
        return reject_copilot_action(db, action_id, body.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
