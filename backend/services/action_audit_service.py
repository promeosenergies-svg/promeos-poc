"""Audit trail service for action plan items (Sprint 13)."""

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.action_event import ActionPlanEvent, ActionPlanEvidence


def log_event(
    db: Session,
    action_id: int,
    event_type: str,
    actor: str = "system",
    old_value: str = None,
    new_value: str = None,
    comment: str = None,
):
    event = ActionPlanEvent(
        action_id=action_id,
        event_type=event_type,
        actor=actor or "system",
        old_value=old_value,
        new_value=new_value,
        comment=comment,
    )
    db.add(event)
    db.flush()
    return event


def get_history(db: Session, action_id: int) -> list:
    events = (
        db.query(ActionPlanEvent)
        .filter(ActionPlanEvent.action_id == action_id)
        .order_by(ActionPlanEvent.occurred_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "action_id": e.action_id,
            "event_type": e.event_type,
            "actor": e.actor,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "comment": e.comment,
            "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
        }
        for e in events
    ]


def add_evidence(
    db: Session,
    action_id: int,
    evidence_type: str,
    label: str,
    value: str = None,
    document_name: str = None,
    uploaded_by: str = "system",
):
    ev = ActionPlanEvidence(
        action_id=action_id,
        evidence_type=evidence_type,
        label=label,
        value=value,
        document_name=document_name,
        uploaded_by=uploaded_by or "system",
    )
    db.add(ev)
    db.flush()
    # Also log event
    log_event(
        db, action_id, "evidence_added", actor=uploaded_by, new_value=f"{evidence_type}:{label}", comment=document_name
    )
    return ev


def get_evidence(db: Session, action_id: int) -> list:
    evs = (
        db.query(ActionPlanEvidence)
        .filter(ActionPlanEvidence.action_id == action_id)
        .order_by(ActionPlanEvidence.uploaded_at.desc())
        .all()
    )
    return [
        {
            "id": e.id,
            "action_id": e.action_id,
            "evidence_type": e.evidence_type,
            "label": e.label,
            "value": e.value,
            "document_name": e.document_name,
            "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
            "uploaded_by": e.uploaded_by,
        }
        for e in evs
    ]


def export_action_dossier(db: Session, action_id: int) -> dict:
    """Export complete action dossier: action + history + evidence."""
    from models.action_plan_item import ActionPlanItem
    from services.action_workflow_service import serialize_action

    item = db.query(ActionPlanItem).filter(ActionPlanItem.id == action_id).first()
    if not item:
        return None

    return {
        "action": serialize_action(item),
        "history": get_history(db, action_id),
        "evidence": get_evidence(db, action_id),
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "complete": True,
    }
