"""
PROMEOS — Onboarding Stepper Routes (V113 Chantier 5)
GET  /api/onboarding-progress          — status for org
PATCH /api/onboarding-progress/step    — mark step complete
POST /api/onboarding-progress/dismiss  — dismiss stepper
POST /api/onboarding-progress/auto     — auto-detect completed steps
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import OnboardingProgress
from middleware.auth import get_optional_auth, AuthContext
from middleware.cx_logger import log_cx_event, CX_ONBOARDING_COMPLETED
from services.scope_utils import resolve_org_id
from services.data_quality_service import compute_org_completeness
from services.onboarding_stepper_service import (
    STEP_FIELDS as _SVC_STEP_FIELDS,
    get_or_create_progress,
    auto_detect_steps as _svc_auto_detect,
)

router = APIRouter(prefix="/api/onboarding-progress", tags=["Onboarding Stepper"])

STEP_FIELDS = list(_SVC_STEP_FIELDS)  # backward-compat pour tests externes

STEP_META = [
    {"key": "step_org_created", "label": "Créer l'organisation", "icon": "Building2"},
    {"key": "step_sites_added", "label": "Ajouter des sites", "icon": "MapPin"},
    {"key": "step_meters_connected", "label": "Connecter les compteurs", "icon": "Zap"},
    {"key": "step_invoices_imported", "label": "Importer les factures", "icon": "FileText"},
    {"key": "step_users_invited", "label": "Inviter les utilisateurs", "icon": "Users"},
    {"key": "step_first_action", "label": "Créer une action", "icon": "Target"},
]


# Alias backward-compat : routes/sirene.py et anciens tests continuent de fonctionner.
# V119 a extrait la vraie logique vers services/onboarding_stepper_service.py.
def _get_or_create(db: Session, org_id: int) -> OnboardingProgress:
    return get_or_create_progress(db, org_id)


def _serialize(progress: OnboardingProgress, data_quality_pct: float = None) -> dict:
    steps = []
    completed_count = 0
    for meta in STEP_META:
        done = getattr(progress, meta["key"], False)
        if done:
            completed_count += 1
        steps.append({**meta, "done": done})

    total = len(STEP_META)
    all_done = completed_count == total

    result = {
        "id": progress.id,
        "org_id": progress.org_id,
        "steps": steps,
        "completed_count": completed_count,
        "total": total,
        "progress_pct": round(completed_count / total * 100) if total else 0,
        "all_done": all_done,
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "dismissed_at": progress.dismissed_at.isoformat() if progress.dismissed_at else None,
        "ttfv_seconds": progress.ttfv_seconds,
    }

    # DataQuality gating: if below threshold, flag incomplete data step
    if data_quality_pct is not None:
        result["data_quality_pct"] = data_quality_pct
        result["data_quality_gate"] = data_quality_pct >= 50

    return result


@router.get("")
def get_onboarding_progress(
    request: Request,
    org_id: int = Query(None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_optional_auth),
):
    """Get onboarding progress for org, with data quality gating."""
    oid = resolve_org_id(request, auth, db, org_id_override=org_id)
    if not oid:
        raise HTTPException(400, "org_id requis")

    progress = _get_or_create(db, oid)

    # Auto-detect completed steps if all steps are still False (fresh record)
    if not any(getattr(progress, f) for f in STEP_FIELDS):
        _auto_detect(db, oid, progress)

    db.commit()

    # Data quality gating — check org's overall coverage
    dq_pct = None
    try:
        dq = compute_org_completeness(db, oid)
        dq_pct = dq.get("overall_coverage_pct", 0)
    except Exception:
        pass  # Non-blocking — don't fail onboarding if DQ errors

    return _serialize(progress, data_quality_pct=dq_pct)


class StepUpdate(BaseModel):
    step: str
    done: bool = True


@router.patch("/step")
def update_step(
    request: Request,
    body: StepUpdate,
    org_id: int = Query(None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_optional_auth),
):
    """Mark a single step as complete/incomplete."""
    oid = resolve_org_id(request, auth, db, org_id_override=org_id)
    if not oid:
        raise HTTPException(400, "org_id requis")

    if body.step not in STEP_FIELDS:
        raise HTTPException(400, f"Step inconnu: {body.step}")

    progress = _get_or_create(db, oid)
    setattr(progress, body.step, body.done)

    # Check if all done + compute TTFV
    just_completed = False
    if all(getattr(progress, f) for f in STEP_FIELDS):
        if not progress.completed_at:
            progress.completed_at = datetime.now(timezone.utc)
            if progress.created_at:
                progress.ttfv_seconds = int((progress.completed_at - progress.created_at).total_seconds())
            just_completed = True
    else:
        progress.completed_at = None
        progress.ttfv_seconds = None

    # Sprint CX 3 P0.4 : fire CX_ONBOARDING_COMPLETED sur transition 1ère fois.
    # Option B (fire-and-forget à chaque complétion) : l'event est rare (1x/org)
    # grâce au gate `not progress.completed_at` ci-dessus.
    if just_completed:
        log_cx_event(
            db,
            oid,
            auth.user.id if auth else None,
            CX_ONBOARDING_COMPLETED,
            {"ttfv_seconds": progress.ttfv_seconds, "trigger": "stepper_all_done"},
        )

    db.commit()
    db.refresh(progress)
    return _serialize(progress)


@router.post("/dismiss")
def dismiss_stepper(
    request: Request,
    org_id: int = Query(None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_optional_auth),
):
    """Dismiss (hide) the onboarding stepper."""
    oid = resolve_org_id(request, auth, db, org_id_override=org_id)
    if not oid:
        raise HTTPException(400, "org_id requis")

    progress = _get_or_create(db, oid)
    progress.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(progress)
    return _serialize(progress)


def _auto_detect(db: Session, oid: int, progress: OnboardingProgress):
    """Alias backward-compat, delegue au service."""
    return _svc_auto_detect(db, oid, progress)


@router.post("/auto")
def auto_detect_steps(
    request: Request,
    org_id: int = Query(None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_optional_auth),
):
    """Auto-detect completed steps from actual data."""
    oid = resolve_org_id(request, auth, db, org_id_override=org_id)
    if not oid:
        raise HTTPException(400, "org_id requis")

    progress = _get_or_create(db, oid)
    _auto_detect(db, oid, progress)

    db.commit()
    db.refresh(progress)
    return _serialize(progress)
