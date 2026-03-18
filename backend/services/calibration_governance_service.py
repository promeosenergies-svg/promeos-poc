"""Calibration governance: create, activate, rollback, compare, history."""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.recommendation_outcome import CalibrationVersion, RecommendationOutcome

logger = logging.getLogger("promeos.calibration")

DEFAULT_WEIGHTS = {"urgency": 0.4, "risk": 0.3, "ease": 0.1, "confidence": 0.2}


def ensure_initial_version(db: Session):
    """Create v1.0 if no versions exist."""
    existing = db.query(CalibrationVersion).first()
    if not existing:
        v = CalibrationVersion(
            version="1.0",
            status="active",
            weights_json=json.dumps(DEFAULT_WEIGHTS),
            comment="Initial calibration — Sprint 17",
            created_by="system",
            effective_date=datetime.now(timezone.utc),
            activated_at=datetime.now(timezone.utc),
        )
        db.add(v)
        db.flush()
        return v
    return existing


def get_active_calibration(db: Session) -> dict:
    ensure_initial_version(db)
    v = (
        db.query(CalibrationVersion)
        .filter(CalibrationVersion.status == "active")
        .order_by(CalibrationVersion.id.desc())
        .first()
    )
    if not v:
        return {"version": "1.0", "weights": DEFAULT_WEIGHTS, "status": "active"}
    return _serialize(v)


def get_calibration_history(db: Session) -> list:
    ensure_initial_version(db)
    versions = db.query(CalibrationVersion).order_by(CalibrationVersion.id.desc()).all()
    return [_serialize(v) for v in versions]


def create_calibration(
    db: Session,
    version: str,
    weights: dict,
    comment: str = None,
    created_by: str = "system",
    domain_adjustments: dict = None,
) -> dict:
    # Validate weights sum ~1.0
    total = sum(weights.values())
    if abs(total - 1.0) > 0.01:
        return None

    existing = db.query(CalibrationVersion).filter(CalibrationVersion.version == version).first()
    if existing:
        return None  # Version already exists

    v = CalibrationVersion(
        version=version,
        status="draft",
        weights_json=json.dumps(weights),
        domain_adjustments_json=json.dumps(domain_adjustments) if domain_adjustments else None,
        comment=comment,
        created_by=created_by,
    )
    db.add(v)
    db.flush()
    logger.info("Calibration %s created by %s", version, created_by)
    return _serialize(v)


def activate_calibration(db: Session, version: str, actor: str = "system") -> dict:
    ensure_initial_version(db)
    target = db.query(CalibrationVersion).filter(CalibrationVersion.version == version).first()
    if not target or target.status not in ("draft", "rolled_back"):
        return None

    # Archive current active
    current = db.query(CalibrationVersion).filter(CalibrationVersion.status == "active").first()
    if current:
        current.status = "archived"

    target.status = "active"
    target.activated_at = datetime.now(timezone.utc)
    target.effective_date = datetime.now(timezone.utc)
    db.flush()
    logger.info("Calibration %s activated by %s", version, actor)
    return _serialize(target)


def rollback_calibration(db: Session, actor: str = "system") -> dict:
    current = db.query(CalibrationVersion).filter(CalibrationVersion.status == "active").first()
    if not current:
        return None

    # Find previous archived version
    previous = (
        db.query(CalibrationVersion)
        .filter(CalibrationVersion.status == "archived")
        .order_by(CalibrationVersion.id.desc())
        .first()
    )

    if not previous:
        return None

    current.status = "rolled_back"
    current.rolled_back_at = datetime.now(timezone.utc)
    previous.status = "active"
    previous.activated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("Rolled back to %s by %s", previous.version, actor)
    return _serialize(previous)


def compare_calibrations(db: Session, v1: str, v2: str) -> dict:
    c1 = db.query(CalibrationVersion).filter(CalibrationVersion.version == v1).first()
    c2 = db.query(CalibrationVersion).filter(CalibrationVersion.version == v2).first()
    if not c1 or not c2:
        return None

    w1 = json.loads(c1.weights_json)
    w2 = json.loads(c2.weights_json)

    deltas = {}
    all_keys = set(w1.keys()) | set(w2.keys())
    for k in all_keys:
        v1_val = w1.get(k, 0)
        v2_val = w2.get(k, 0)
        deltas[k] = {"v1": v1_val, "v2": v2_val, "delta": round(v2_val - v1_val, 3)}

    return {
        "v1": {"version": c1.version, "status": c1.status, "weights": w1},
        "v2": {"version": c2.version, "status": c2.status, "weights": w2},
        "deltas": deltas,
    }


def _serialize(v: CalibrationVersion) -> dict:
    return {
        "id": v.id,
        "version": v.version,
        "status": v.status,
        "weights": json.loads(v.weights_json),
        "domain_adjustments": json.loads(v.domain_adjustments_json) if v.domain_adjustments_json else None,
        "comment": v.comment,
        "created_by": v.created_by,
        "effective_date": v.effective_date.isoformat() if v.effective_date else None,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "activated_at": v.activated_at.isoformat() if v.activated_at else None,
        "rolled_back_at": v.rolled_back_at.isoformat() if v.rolled_back_at else None,
    }


# ── Outcomes ────────────────────────────────────────────────────────


def record_outcome(
    db: Session,
    recommendation_id: str,
    outcome_status: str,
    action_id: int = None,
    domain: str = None,
    decision: str = None,
    outcome_reason: str = None,
    backlog_delta: int = None,
    overdue_delta: int = None,
    impact_delta_eur: float = None,
) -> RecommendationOutcome:
    active = get_active_calibration(db)
    o = RecommendationOutcome(
        recommendation_id=recommendation_id,
        action_id=action_id,
        calibration_version=active.get("version", "1.0"),
        domain=domain,
        decision=decision,
        outcome_status=outcome_status,
        outcome_reason=outcome_reason,
        backlog_delta=backlog_delta,
        overdue_delta=overdue_delta,
        impact_delta_eur=impact_delta_eur,
    )
    db.add(o)
    db.flush()
    return o


def get_outcomes(db: Session, limit: int = 50) -> list:
    outcomes = db.query(RecommendationOutcome).order_by(RecommendationOutcome.measured_at.desc()).limit(limit).all()
    return [
        {
            "id": o.id,
            "recommendation_id": o.recommendation_id,
            "action_id": o.action_id,
            "calibration_version": o.calibration_version,
            "domain": o.domain,
            "decision": o.decision,
            "outcome_status": o.outcome_status,
            "outcome_reason": o.outcome_reason,
            "backlog_delta": o.backlog_delta,
            "overdue_delta": o.overdue_delta,
            "impact_delta_eur": o.impact_delta_eur,
            "measured_at": o.measured_at.isoformat() if o.measured_at else None,
        }
        for o in outcomes
    ]
