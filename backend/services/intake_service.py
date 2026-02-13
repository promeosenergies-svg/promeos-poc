"""
PROMEOS - Smart Intake Service (DIAMANT)
Session CRUD, submit answers, apply to models, compute diff, demo autofill.
"""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    Site, Batiment, Evidence, AuditLog,
    IntakeSession, IntakeAnswer, IntakeFieldOverride,
    IntakeSessionStatus, IntakeMode, IntakeSource,
    TypeEvidence, StatutEvidence, ParkingType, OperatStatus,
)
from services.intake_engine import (
    generate_questions, prefill_from_existing, compute_before_after,
    DEMO_DEFAULTS, QUESTION_BANK,
)
from services.compliance_engine import recompute_site
from services.onboarding_service import (
    create_batiment_for_site, create_obligations_for_site,
)


# ========================================
# Field apply map: field_path → (model, column)
# ========================================

FIELD_APPLY_MAP = {
    "site.tertiaire_area_m2": ("site", "tertiaire_area_m2"),
    "site.parking_area_m2": ("site", "parking_area_m2"),
    "site.roof_area_m2": ("site", "roof_area_m2"),
    "site.parking_type": ("site", "parking_type"),
    "site.operat_status": ("site", "operat_status"),
    "site.annual_kwh_total": ("site", "annual_kwh_total"),
    "site.surface_m2": ("site", "surface_m2"),
    "site.naf_code": ("site", "naf_code"),
    "site.is_multi_occupied": ("site", "is_multi_occupied"),
    "site.nombre_employes": ("site", "nombre_employes"),
    "batiment.cvc_power_kw": ("batiment", "cvc_power_kw"),
    "evidence.attestation_bacs": ("evidence", "ATTESTATION_BACS"),
    "evidence.derogation_bacs": ("evidence", "DEROGATION_BACS"),
}

# Enum converters for string → enum
_ENUM_CONVERTERS = {
    "parking_type": lambda v: ParkingType(v) if isinstance(v, str) else v,
    "operat_status": lambda v: OperatStatus(v) if isinstance(v, str) else v,
}


# ========================================
# Session lifecycle
# ========================================

def create_session(
    db: Session,
    site_id: int,
    user_id: Optional[int] = None,
    mode: IntakeMode = IntakeMode.WIZARD,
    scope_type: str = "site",
) -> IntakeSession:
    """Create an intake session for a site. Computes score_before."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    # Compute current score
    diff = compute_before_after(db, site_id, {})
    score_before = diff["score_before"]

    # Count questions
    questions = generate_questions(db, site_id)

    session = IntakeSession(
        site_id=site_id,
        org_id=None,
        scope_type=scope_type,
        scope_id=site_id,
        status=IntakeSessionStatus.IN_PROGRESS,
        mode=mode,
        user_id=user_id,
        score_before=score_before,
        questions_count=len(questions),
        answers_count=0,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.flush()

    return session


# ========================================
# Submit answers
# ========================================

def _get_previous_value(db: Session, site_id: int, field_path: str):
    """Get the current value of a field from the database."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return None

    if field_path.startswith("site."):
        col = field_path.split(".", 1)[1]
        val = getattr(site, col, None)
        if val is not None and hasattr(val, "value"):
            val = val.value
        return val

    if field_path == "batiment.cvc_power_kw":
        bat = db.query(Batiment).filter(Batiment.site_id == site_id).first()
        return bat.cvc_power_kw if bat else None

    if field_path == "evidence.attestation_bacs":
        return any(
            e.type == TypeEvidence.ATTESTATION_BACS and e.statut == StatutEvidence.VALIDE
            for e in db.query(Evidence).filter(Evidence.site_id == site_id).all()
        )

    if field_path == "evidence.derogation_bacs":
        return any(
            e.type == TypeEvidence.DEROGATION_BACS and e.statut == StatutEvidence.VALIDE
            for e in db.query(Evidence).filter(Evidence.site_id == site_id).all()
        )

    return None


def submit_answer(
    db: Session,
    session_id: int,
    field_path: str,
    value,
    source: IntakeSource = IntakeSource.USER,
) -> IntakeAnswer:
    """Submit one answer to an intake session."""
    session = db.query(IntakeSession).filter(IntakeSession.id == session_id).first()
    if not session:
        raise ValueError(f"IntakeSession {session_id} not found")

    if field_path not in FIELD_APPLY_MAP:
        raise ValueError(f"Unknown field_path: {field_path}")

    # Get previous value
    previous = _get_previous_value(db, session.site_id, field_path)

    answer = IntakeAnswer(
        session_id=session_id,
        field_path=field_path,
        value_json=json.dumps(value),
        source=source,
        previous_value_json=json.dumps(previous) if previous is not None else None,
    )
    db.add(answer)

    # Update session answer count
    session.answers_count = (session.answers_count or 0) + 1
    db.flush()

    # Log audit
    _log_audit(db, session.user_id, "intake_answer", "site", str(session.site_id), {
        "session_id": session_id,
        "field_path": field_path,
        "value": value,
        "previous": previous,
        "source": source.value if hasattr(source, "value") else str(source),
    })

    return answer


# ========================================
# Compute diff
# ========================================

def compute_diff(db: Session, session_id: int) -> dict:
    """Compute before/after compliance diff from all unapplied answers."""
    session = db.query(IntakeSession).filter(IntakeSession.id == session_id).first()
    if not session:
        raise ValueError(f"IntakeSession {session_id} not found")

    # Collect unapplied answers
    answers = db.query(IntakeAnswer).filter(
        IntakeAnswer.session_id == session_id,
        IntakeAnswer.applied_at.is_(None),
    ).all()

    proposed = {}
    for a in answers:
        proposed[a.field_path] = json.loads(a.value_json)

    diff = compute_before_after(db, session.site_id, proposed)
    return {
        "session_id": session_id,
        "answers_count": len(answers),
        **diff,
    }


# ========================================
# Apply answers to final models
# ========================================

def apply_answers(db: Session, session_id: int) -> dict:
    """Write answers to final models, then recompute compliance."""
    session = db.query(IntakeSession).filter(IntakeSession.id == session_id).first()
    if not session:
        raise ValueError(f"IntakeSession {session_id} not found")

    site = db.query(Site).filter(Site.id == session.site_id).first()
    if not site:
        raise ValueError(f"Site {session.site_id} not found")

    # Get unapplied answers
    answers = db.query(IntakeAnswer).filter(
        IntakeAnswer.session_id == session_id,
        IntakeAnswer.applied_at.is_(None),
    ).all()

    if not answers:
        return {"fields_applied": 0, "score_before": session.score_before, "score_after": session.score_before}

    fields_applied = 0
    now = datetime.utcnow()

    for answer in answers:
        value = json.loads(answer.value_json)
        mapping = FIELD_APPLY_MAP.get(answer.field_path)
        if not mapping:
            continue

        model_type, column = mapping

        if model_type == "site":
            # Convert enums
            converter = _ENUM_CONVERTERS.get(column)
            if converter:
                value = converter(value)
            setattr(site, column, value)
            fields_applied += 1

        elif model_type == "batiment":
            bat = db.query(Batiment).filter(Batiment.site_id == site.id).first()
            if not bat:
                bat = create_batiment_for_site(db, site)
            setattr(bat, column, value)
            fields_applied += 1

        elif model_type == "evidence":
            # column is the TypeEvidence name (e.g., "ATTESTATION_BACS")
            if value:  # Only create evidence if answer is True
                evidence_type = TypeEvidence(column.lower())
                # Check if already exists
                existing = db.query(Evidence).filter(
                    Evidence.site_id == site.id,
                    Evidence.type == evidence_type,
                ).first()
                if not existing:
                    ev = Evidence(
                        site_id=site.id,
                        type=evidence_type,
                        statut=StatutEvidence.VALIDE,
                        note="Declare via Smart Intake",
                    )
                    db.add(ev)
                else:
                    existing.statut = StatutEvidence.VALIDE
                fields_applied += 1

        answer.applied_at = now

    db.flush()

    # Create obligations if needed (e.g., CVC power changed)
    bat = db.query(Batiment).filter(Batiment.site_id == site.id).first()
    if bat and bat.cvc_power_kw:
        create_obligations_for_site(db, site, bat.cvc_power_kw)

    # Recompute compliance
    recompute_site(db, site.id)

    # Compute new score
    diff = compute_before_after(db, site.id, {})
    session.score_after = diff["score_before"]  # Current score IS the "after"
    db.flush()

    _log_audit(db, session.user_id, "intake_apply", "site", str(site.id), {
        "session_id": session_id,
        "fields_applied": fields_applied,
        "score_before": session.score_before,
        "score_after": session.score_after,
    })

    return {
        "fields_applied": fields_applied,
        "score_before": session.score_before,
        "score_after": session.score_after,
        "delta": round((session.score_after or 0) - (session.score_before or 0), 1),
    }


# ========================================
# Demo autofill
# ========================================

def demo_autofill(db: Session, session_id: int) -> dict:
    """Fill all missing fields with demo defaults, then apply."""
    session = db.query(IntakeSession).filter(IntakeSession.id == session_id).first()
    if not session:
        raise ValueError(f"IntakeSession {session_id} not found")

    # Generate questions to know which fields are missing
    questions = generate_questions(db, session.site_id)
    answers_created = 0

    for q in questions:
        default_value = DEMO_DEFAULTS.get(q["field_path"])
        if default_value is not None:
            submit_answer(db, session_id, q["field_path"], default_value, IntakeSource.SYSTEM_DEMO)
            answers_created += 1

    # Apply all
    result = apply_answers(db, session_id)

    return {
        "answers_created": answers_created,
        "score_before": session.score_before,
        "score_after": result["score_after"],
        "delta": result["delta"],
    }


# ========================================
# Complete session
# ========================================

def complete_session(db: Session, session_id: int) -> IntakeSession:
    """Mark session as COMPLETED."""
    session = db.query(IntakeSession).filter(IntakeSession.id == session_id).first()
    if not session:
        raise ValueError(f"IntakeSession {session_id} not found")

    session.status = IntakeSessionStatus.COMPLETED
    session.completed_at = datetime.utcnow()
    db.flush()

    _log_audit(db, session.user_id, "intake_complete", "intake_session", str(session_id), {
        "site_id": session.site_id,
        "score_before": session.score_before,
        "score_after": session.score_after,
        "answers_count": session.answers_count,
    })

    return session


# ========================================
# Get session detail
# ========================================

def get_session_detail(db: Session, session_id: int) -> dict:
    """Return full session with answers and diff."""
    session = db.query(IntakeSession).filter(IntakeSession.id == session_id).first()
    if not session:
        raise ValueError(f"IntakeSession {session_id} not found")

    answers = db.query(IntakeAnswer).filter(
        IntakeAnswer.session_id == session_id
    ).all()

    return {
        "session": {
            "id": session.id,
            "site_id": session.site_id,
            "status": session.status.value,
            "mode": session.mode.value,
            "score_before": session.score_before,
            "score_after": session.score_after,
            "questions_count": session.questions_count,
            "answers_count": session.answers_count,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        },
        "answers": [
            {
                "id": a.id,
                "field_path": a.field_path,
                "value": json.loads(a.value_json),
                "source": a.source.value,
                "previous_value": json.loads(a.previous_value_json) if a.previous_value_json else None,
                "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            }
            for a in answers
        ],
    }


# ========================================
# Purge demo sessions
# ========================================

def purge_demo_sessions(db: Session, org_id: Optional[int] = None) -> int:
    """Delete all DEMO-mode sessions and their answers."""
    query = db.query(IntakeSession).filter(IntakeSession.mode == IntakeMode.DEMO)
    if org_id:
        query = query.filter(IntakeSession.org_id == org_id)

    sessions = query.all()
    count = len(sessions)

    for session in sessions:
        # Delete answers
        db.query(IntakeAnswer).filter(IntakeAnswer.session_id == session.id).delete()
        db.delete(session)

    db.flush()
    return count


# ========================================
# Audit helper
# ========================================

def _log_audit(db: Session, user_id: Optional[int], action: str,
               resource_type: str, resource_id: str, detail: dict):
    """Log to existing AuditLog model."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_json=json.dumps(detail, default=str),
    )
    db.add(log)
