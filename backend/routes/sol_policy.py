"""
PROMEOS — Sol V1 org policy routes (Phase 4)

- GET  /api/sol/policy  — admin only
- PUT  /api/sol/policy  — admin only (upsert SolOrgPolicy)
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth, require_platform_admin
from models.sol import SolOrgPolicy
from services.scope_utils import resolve_org_id
from sol.schemas import AgenticMode
from sol.utils import now_utc

router = APIRouter(prefix="/api/sol/policy", tags=["Sol V1 policy"])
logger = logging.getLogger("promeos.sol")


class SolOrgPolicyDTO(BaseModel):
    org_id: int
    agentic_mode: AgenticMode
    dry_run_until: Optional[datetime] = None
    dual_validation_threshold: Optional[float] = None
    confidence_threshold: float
    grace_period_seconds: int
    tone_preference: str
    updated_at: datetime


class SolOrgPolicyUpdate(BaseModel):
    """Upsert payload — tous les fields optionnels."""

    agentic_mode: Optional[AgenticMode] = None
    dry_run_until: Optional[datetime] = None
    dual_validation_threshold: Optional[float] = Field(None, ge=0)
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1)
    grace_period_seconds: Optional[int] = Field(None, ge=0)
    tone_preference: Optional[str] = Field(None, pattern=r"^(vous|tu)$")


def _to_dto(policy: SolOrgPolicy) -> SolOrgPolicyDTO:
    return SolOrgPolicyDTO(
        org_id=policy.org_id,
        agentic_mode=AgenticMode(policy.agentic_mode),
        dry_run_until=policy.dry_run_until,
        dual_validation_threshold=(
            float(policy.dual_validation_threshold)
            if policy.dual_validation_threshold is not None
            else None
        ),
        confidence_threshold=float(policy.confidence_threshold),
        grace_period_seconds=policy.grace_period_seconds,
        tone_preference=policy.tone_preference,
        updated_at=policy.updated_at,
    )


@router.get("", response_model=SolOrgPolicyDTO)
async def get_policy(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_platform_admin),
) -> SolOrgPolicyDTO:
    """Récupère la policy Sol pour l'org courante — admin only."""
    org_id = resolve_org_id(request, auth, db)

    policy = db.query(SolOrgPolicy).filter(SolOrgPolicy.org_id == org_id).one_or_none()
    if policy is None:
        # Upsert avec defaults pour retour cohérent (pas 404)
        policy = SolOrgPolicy(org_id=org_id)
        db.add(policy)
        db.commit()
        db.refresh(policy)

    return _to_dto(policy)


@router.put("", response_model=SolOrgPolicyDTO)
async def put_policy(
    body: SolOrgPolicyUpdate,
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_platform_admin),
) -> SolOrgPolicyDTO:
    """Upsert policy Sol pour l'org courante — admin only."""
    org_id = resolve_org_id(request, auth, db)

    policy = db.query(SolOrgPolicy).filter(SolOrgPolicy.org_id == org_id).one_or_none()
    created = False
    if policy is None:
        policy = SolOrgPolicy(org_id=org_id)
        created = True

    if body.agentic_mode is not None:
        policy.agentic_mode = body.agentic_mode.value
    if body.dry_run_until is not None:
        policy.dry_run_until = body.dry_run_until
    if body.dual_validation_threshold is not None:
        policy.dual_validation_threshold = Decimal(str(body.dual_validation_threshold))
    if body.confidence_threshold is not None:
        policy.confidence_threshold = Decimal(str(body.confidence_threshold))
    if body.grace_period_seconds is not None:
        policy.grace_period_seconds = body.grace_period_seconds
    if body.tone_preference is not None:
        policy.tone_preference = body.tone_preference
    policy.updated_at = now_utc()

    if created:
        db.add(policy)
    db.commit()
    db.refresh(policy)

    logger.info(
        "sol_policy_updated",
        extra={
            "sol_event": "sol_policy_updated",
            "org_id": org_id,
            "agentic_mode": policy.agentic_mode,
        },
    )

    return _to_dto(policy)
