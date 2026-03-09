"""
PROMEOS — Onboarding Stepper Routes (V113 Chantier 5)
GET  /api/onboarding-progress          — status for org
PATCH /api/onboarding-progress/step    — mark step complete
POST /api/onboarding-progress/dismiss  — dismiss stepper
POST /api/onboarding-progress/auto     — auto-detect completed steps
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    OnboardingProgress,
    Organisation,
    Site,
    Compteur,
    User,
    UserOrgRole,
    ActionItem,
    Portefeuille,
    EntiteJuridique,
    EnergyInvoice,
)
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.data_quality_service import compute_org_completeness

router = APIRouter(prefix="/api/onboarding-progress", tags=["Onboarding Stepper"])

STEP_FIELDS = [
    "step_org_created",
    "step_sites_added",
    "step_meters_connected",
    "step_invoices_imported",
    "step_users_invited",
    "step_first_action",
]

STEP_META = [
    {"key": "step_org_created", "label": "Créer l'organisation", "icon": "Building2"},
    {"key": "step_sites_added", "label": "Ajouter des sites", "icon": "MapPin"},
    {"key": "step_meters_connected", "label": "Connecter les compteurs", "icon": "Zap"},
    {"key": "step_invoices_imported", "label": "Importer les factures", "icon": "FileText"},
    {"key": "step_users_invited", "label": "Inviter les utilisateurs", "icon": "Users"},
    {"key": "step_first_action", "label": "Créer une action", "icon": "Target"},
]


def _get_or_create(db: Session, org_id: int) -> OnboardingProgress:
    """Get or create OnboardingProgress for an org."""
    progress = db.query(OnboardingProgress).filter(OnboardingProgress.org_id == org_id).first()
    if not progress:
        progress = OnboardingProgress(org_id=org_id)
        db.add(progress)
        db.flush()
    return progress


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
    if all(getattr(progress, f) for f in STEP_FIELDS):
        if not progress.completed_at:
            progress.completed_at = datetime.utcnow()
            if progress.created_at:
                progress.ttfv_seconds = int((progress.completed_at - progress.created_at).total_seconds())
    else:
        progress.completed_at = None
        progress.ttfv_seconds = None

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
    progress.dismissed_at = datetime.utcnow()
    db.commit()
    db.refresh(progress)
    return _serialize(progress)


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

    # Step 1: org exists
    org = db.query(Organisation).filter(Organisation.id == oid).first()
    if org:
        progress.step_org_created = True

    # Step 2: has sites
    pf_ids = [
        r.id
        for r in (
            db.query(Portefeuille.id)
            .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(EntiteJuridique.organisation_id == oid)
            .all()
        )
    ]
    site_count = 0
    if pf_ids:
        site_count = db.query(Site).filter(Site.portefeuille_id.in_(pf_ids), Site.actif == True).count()
    if site_count > 0:
        progress.step_sites_added = True

    # Step 3: has meters connected
    if pf_ids:
        site_ids = [r.id for r in db.query(Site.id).filter(Site.portefeuille_id.in_(pf_ids)).all()]
        if site_ids:
            meter_count = db.query(Compteur).filter(Compteur.site_id.in_(site_ids)).count()
            if meter_count > 0:
                progress.step_meters_connected = True

    # Step 4: has invoices (via site_ids — EnergyInvoice has no org_id)
    if pf_ids:
        inv_site_ids = [r.id for r in db.query(Site.id).filter(Site.portefeuille_id.in_(pf_ids)).all()]
        if inv_site_ids:
            inv_count = db.query(EnergyInvoice).filter(EnergyInvoice.site_id.in_(inv_site_ids)).count()
            if inv_count > 0:
                progress.step_invoices_imported = True

    # Step 5: has users (via UserOrgRole — User has no org_id)
    user_count = db.query(UserOrgRole).filter(UserOrgRole.org_id == oid).count()
    if user_count >= 1:  # at least 1 user assigned to org
        progress.step_users_invited = True

    # Step 6: has actions
    action_count = db.query(ActionItem).filter(ActionItem.org_id == oid).count()
    if action_count > 0:
        progress.step_first_action = True

    # Check if all done
    if all(getattr(progress, f) for f in STEP_FIELDS):
        if not progress.completed_at:
            progress.completed_at = datetime.utcnow()

    db.commit()
    db.refresh(progress)
    return _serialize(progress)
