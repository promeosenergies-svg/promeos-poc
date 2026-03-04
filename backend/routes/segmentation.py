"""
PROMEOS - Routes Segmentation B2B
V100: profile enrichi (missing_questions, recommendations, segment_label) + recompute.
V101: next-best-step, action creation from recommendations.
"""

import json
import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Optional
from sqlalchemy.orm import Session

from database import get_db
from models import Organisation, ActionItem, ActionSourceType, ActionStatus
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.segmentation_service import (
    get_questions,
    get_or_create_profile,
    update_profile_with_answers,
    detect_typologie,
    recompute_profile,
    get_missing_questions,
    get_recommendations,
    compute_next_best_step,
    TYPO_LABELS,
)

router = APIRouter(prefix="/api/segmentation", tags=["Segmentation"])


# ========================================
# Schemas
# ========================================


class AnswersRequest(BaseModel):
    answers: Dict[str, str]


class FromRecommendationRequest(BaseModel):
    portfolio_id: Optional[int] = None
    recommendation_key: str


class FromNextStepRequest(BaseModel):
    portfolio_id: Optional[int] = None


# ========================================
# GET /api/segmentation/questions
# ========================================


@router.get("/questions")
def list_questions():
    """Retourne les questions du questionnaire de segmentation V1."""
    return {"questions": get_questions(), "total": len(get_questions())}


# ========================================
# POST /api/segmentation/answers
# ========================================


@router.post("/answers")
def submit_answers(
    req: AnswersRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Soumet les reponses au questionnaire et met a jour le profil."""
    org_id = resolve_org_id(request, auth, db)

    profile = update_profile_with_answers(db, org_id, req.answers)

    # Auto-recompute compliance after questionnaire answers
    compliance_sites = 0
    try:
        from services.compliance_rules import evaluate_organisation

        eval_result = evaluate_organisation(db, org_id)
        compliance_sites = eval_result.get("sites_evaluated", 0)
    except Exception:
        pass

    return {
        "has_profile": True,
        "typologie": profile.typologie,
        "segment_label": profile.segment_label,
        "confidence_score": profile.confidence_score,
        "derived_from": profile.derived_from,
        "answers_count": len(json.loads(profile.answers_json)) if profile.answers_json else 0,
        "reasons": json.loads(profile.reasons_json) if profile.reasons_json else [],
        "missing_questions": get_missing_questions(profile),
        "recommendations": get_recommendations(profile.typologie),
        "compliance_recomputed": compliance_sites,
    }


# ========================================
# GET /api/segmentation/profile
# ========================================


@router.get("/profile")
def get_profile(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Retourne le profil de segmentation de l'organisation courante.
    V100: enrichi avec missing_questions, recommendations, segment_label.
    """
    org_id = resolve_org_id(request, auth, db)
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        return {
            "has_profile": False,
            "typologie": None,
            "segment_label": None,
            "confidence_score": 0,
            "derived_from": None,
            "reasons": [],
            "answers": {},
            "naf_code": None,
            "missing_questions": [q["id"] for q in get_questions()],
            "recommendations": [],
        }

    profile = get_or_create_profile(db, org_id)

    return {
        "has_profile": True,
        "typologie": profile.typologie,
        "segment_label": profile.segment_label or TYPO_LABELS.get(profile.typologie, profile.typologie),
        "confidence_score": profile.confidence_score,
        "derived_from": profile.derived_from,
        "naf_code": profile.naf_code,
        "reasons": json.loads(profile.reasons_json) if profile.reasons_json else [],
        "answers": json.loads(profile.answers_json) if profile.answers_json else {},
        "missing_questions": get_missing_questions(profile),
        "recommendations": get_recommendations(profile.typologie),
        "organisation": {
            "id": org.id,
            "nom": org.nom,
            "type_client": org.type_client,
        },
    }


# ========================================
# POST /api/segmentation/recompute
# ========================================


@router.post("/recompute")
def recompute_segmentation(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V100: Force re-detection du profil apres import patrimoine ou changement NAF."""
    org_id = resolve_org_id(request, auth, db)
    profile = recompute_profile(db, org_id)

    return {
        "typologie": profile.typologie,
        "segment_label": profile.segment_label,
        "confidence_score": profile.confidence_score,
        "derived_from": profile.derived_from,
        "naf_code": profile.naf_code,
        "reasons": json.loads(profile.reasons_json) if profile.reasons_json else [],
        "missing_questions": get_missing_questions(profile),
        "recommendations": get_recommendations(profile.typologie),
    }


# ========================================
# V101: GET /api/segmentation/next-step
# ========================================


@router.get("/next-step")
def get_next_step(
    request: Request,
    portfolio_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V101: Profile summary + next best step + top 2 recommendations."""
    org_id = resolve_org_id(request, auth, db)
    profile = get_or_create_profile(db, org_id)

    next_step = compute_next_best_step(db, org_id, portfolio_id)
    recs = get_recommendations(profile.typologie)

    return {
        "profile_summary": {
            "typologie": profile.typologie,
            "segment_label": profile.segment_label or TYPO_LABELS.get(profile.typologie, profile.typologie),
            "confidence_score": profile.confidence_score,
            "derived_from": profile.derived_from,
        },
        "next_best_step": next_step,
        "top_recommendations": [
            {"key": r["key"], "label": r["label"], "priority": r.get("priority", "medium")} for r in recs[:2]
        ],
    }


# ========================================
# V101: POST /api/segmentation/actions/from-recommendation
# ========================================

_PRIORITY_MAP = {"high": 2, "medium": 3, "low": 4}
_CONFORMITE_KEYS = {"operat", "bacs", "iso50001", "dpe_collectif"}


@router.post("/actions/from-recommendation")
def create_action_from_recommendation(
    req: FromRecommendationRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V101: Create an action from a segmentation recommendation."""
    org_id = resolve_org_id(request, auth, db)
    profile = get_or_create_profile(db, org_id)

    # Find the recommendation
    recs = get_recommendations(profile.typologie)
    rec = next((r for r in recs if r["key"] == req.recommendation_key), None)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recommendation inconnue: {req.recommendation_key}")

    # Idempotency
    idem_key = hashlib.sha256(f"v101:seg:rec:{org_id}:{req.recommendation_key}".encode()).hexdigest()[:32]

    existing = db.query(ActionItem).filter(ActionItem.idempotency_key == idem_key).first()
    if existing:
        return {
            "id": existing.id,
            "title": existing.title,
            "status": "existing",
            "message": "Action deja creee.",
        }

    category = "conformite" if req.recommendation_key in _CONFORMITE_KEYS else "energie"
    priority = _PRIORITY_MAP.get(rec.get("priority", "medium"), 3)

    item = ActionItem(
        org_id=org_id,
        source_type=ActionSourceType.SEGMENTATION,
        source_id=f"v101:seg:rec:{org_id}:{req.recommendation_key}",
        source_key=f"v101:{req.recommendation_key}",
        title=rec["label"],
        rationale=rec.get("description", ""),
        priority=priority,
        severity="medium",
        status=ActionStatus.OPEN,
        idempotency_key=idem_key,
        evidence_required=False,
        category=category,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "title": item.title,
        "status": "created",
        "message": "Action creee avec succes.",
    }


# ========================================
# V101: POST /api/segmentation/actions/from-next-step
# ========================================


@router.post("/actions/from-next-step")
def create_action_from_next_step(
    req: FromNextStepRequest,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """V101: Create an action from the current next-best-step."""
    org_id = resolve_org_id(request, auth, db)
    next_step = compute_next_best_step(db, org_id, req.portfolio_id)

    idem_key = hashlib.sha256(f"v101:seg:nbs:{org_id}:{next_step['key']}".encode()).hexdigest()[:32]

    existing = db.query(ActionItem).filter(ActionItem.idempotency_key == idem_key).first()
    if existing:
        return {
            "id": existing.id,
            "title": existing.title,
            "status": "existing",
            "message": "Action deja creee.",
        }

    item = ActionItem(
        org_id=org_id,
        source_type=ActionSourceType.SEGMENTATION,
        source_id=f"v101:seg:nbs:{org_id}:{next_step['key']}",
        source_key=f"v101:nbs:{next_step['key']}",
        title=next_step["title"],
        rationale=next_step["why"],
        priority=2,
        severity="medium",
        status=ActionStatus.OPEN,
        idempotency_key=idem_key,
        evidence_required=False,
        category="onboarding",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "title": item.title,
        "status": "created",
        "message": "Action creee avec succes.",
    }
