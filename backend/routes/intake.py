"""
PROMEOS - Routes Smart Intake (DIAMANT)
Question engine, answers, apply, demo autofill, before/after diff.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from database import get_db
from models import Site, IntakeMode, IntakeSource, IntakeFieldOverride
from services.intake_engine import generate_questions, prefill_from_existing, resolve_overrides, compute_before_after
from services.intake_service import (
    create_session, submit_answer, compute_diff, apply_answers,
    demo_autofill, complete_session, get_session_detail,
    purge_demo_sessions,
)

router = APIRouter(prefix="/api/intake", tags=["Smart Intake"])


# ========================================
# Schemas
# ========================================

class AnswerRequest(BaseModel):
    field_path: str
    value: object  # any JSON-serializable value
    source: Optional[str] = "user"


class ApplySuggestionsRequest(BaseModel):
    field_paths: List[str]


class BulkOverrideRequest(BaseModel):
    scope_type: str  # "org" | "entity" | "site"
    scope_id: int
    overrides: List[dict]  # [{field_path, value}]


# ========================================
# Endpoints
# ========================================

@router.get("/{site_id}/questions")
def get_questions(site_id: int, db: Session = Depends(get_db)):
    """Generate questions for a site based on missing regulatory fields."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, f"Site {site_id} not found")

    questions = generate_questions(db, site_id)
    prefills = prefill_from_existing(db, site_id)
    overrides = resolve_overrides(db, site_id)

    # Create session
    session = create_session(db, site_id, mode=IntakeMode.WIZARD)
    db.commit()

    return {
        "site_id": site_id,
        "session_id": session.id,
        "questions_count": len(questions),
        "questions": questions,
        "prefills": prefills,
        "overrides": {k: v for k, v in overrides.items()},
    }


@router.post("/{site_id}/answers")
def post_answer(site_id: int, body: AnswerRequest, db: Session = Depends(get_db)):
    """Submit one answer to the current intake session."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, f"Site {site_id} not found")

    # Find or create active session
    from models import IntakeSession, IntakeSessionStatus
    session = db.query(IntakeSession).filter(
        IntakeSession.site_id == site_id,
        IntakeSession.status == IntakeSessionStatus.IN_PROGRESS,
    ).first()

    if not session:
        session = create_session(db, site_id, mode=IntakeMode.WIZARD)

    # Map source string to enum
    source_map = {s.value: s for s in IntakeSource}
    source = source_map.get(body.source, IntakeSource.USER)

    try:
        answer = submit_answer(db, session.id, body.field_path, body.value, source)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Compute diff preview
    diff = compute_diff(db, session.id)
    db.commit()

    return {
        "answer_id": answer.id,
        "field_path": answer.field_path,
        "previous_value": answer.previous_value_json,
        "diff_preview": {
            "score_before": diff.get("score_before"),
            "score_after": diff.get("score_after"),
            "delta": diff.get("delta"),
        },
    }


@router.post("/{site_id}/apply-suggestions")
def apply_suggestions(site_id: int, body: ApplySuggestionsRequest, db: Session = Depends(get_db)):
    """Accept prefilled values and apply them."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, f"Site {site_id} not found")

    from models import IntakeSession, IntakeSessionStatus
    session = db.query(IntakeSession).filter(
        IntakeSession.site_id == site_id,
        IntakeSession.status == IntakeSessionStatus.IN_PROGRESS,
    ).first()

    if not session:
        session = create_session(db, site_id, mode=IntakeMode.WIZARD)

    # Get prefills and submit as AI_PREFILL
    prefills = prefill_from_existing(db, site_id)
    overrides = resolve_overrides(db, site_id)
    applied_count = 0

    for fp in body.field_paths:
        value = None
        if fp in prefills:
            value = prefills[fp]
        elif fp in overrides:
            value = overrides[fp]["value"]

        if value is not None:
            submit_answer(db, session.id, fp, value, IntakeSource.AI_PREFILL)
            applied_count += 1

    result = apply_answers(db, session.id)
    db.commit()

    return {
        "applied_count": applied_count,
        "score_before": result["score_before"],
        "score_after": result["score_after"],
        "delta": result["delta"],
    }


@router.post("/{site_id}/demo-autofill")
def demo_autofill_endpoint(site_id: int, db: Session = Depends(get_db)):
    """Demo mode: auto-fill all missing fields with realistic values."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(404, f"Site {site_id} not found")

    session = create_session(db, site_id, mode=IntakeMode.DEMO)
    result = demo_autofill(db, session.id)
    complete_session(db, session.id)
    db.commit()

    return {
        "session_id": session.id,
        **result,
    }


@router.post("/{site_id}/complete")
def complete_endpoint(site_id: int, db: Session = Depends(get_db)):
    """Apply all answers and complete the session."""
    from models import IntakeSession, IntakeSessionStatus
    session = db.query(IntakeSession).filter(
        IntakeSession.site_id == site_id,
        IntakeSession.status == IntakeSessionStatus.IN_PROGRESS,
    ).first()

    if not session:
        raise HTTPException(404, "No active intake session for this site")

    result = apply_answers(db, session.id)
    completed = complete_session(db, session.id)
    db.commit()

    return {
        "session_id": completed.id,
        "score_before": result["score_before"],
        "score_after": result["score_after"],
        "delta": result["delta"],
        "fields_applied": result["fields_applied"],
    }


@router.get("/session/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get full session detail with answers."""
    try:
        return get_session_detail(db, session_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/bulk")
def bulk_override(body: BulkOverrideRequest, db: Session = Depends(get_db)):
    """Create field overrides at org/entity/site level for bulk intake."""
    import json

    overrides_created = 0
    for ov in body.overrides:
        fp = ov.get("field_path")
        val = ov.get("value")
        if not fp or val is None:
            continue

        # Upsert: check existing
        existing = db.query(IntakeFieldOverride).filter(
            IntakeFieldOverride.scope_type == body.scope_type,
            IntakeFieldOverride.scope_id == body.scope_id,
            IntakeFieldOverride.field_path == fp,
        ).first()

        if existing:
            existing.value_json = json.dumps(val)
        else:
            db.add(IntakeFieldOverride(
                scope_type=body.scope_type,
                scope_id=body.scope_id,
                field_path=fp,
                value_json=json.dumps(val),
                source="bulk",
            ))
        overrides_created += 1

    db.commit()

    return {
        "overrides_created": overrides_created,
        "scope_type": body.scope_type,
        "scope_id": body.scope_id,
    }


@router.delete("/demo/purge")
def purge_demo(db: Session = Depends(get_db)):
    """Purge all demo intake sessions."""
    count = purge_demo_sessions(db)
    db.commit()
    return {"purged_count": count}
