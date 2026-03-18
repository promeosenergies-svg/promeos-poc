"""Bulk operations on action plan items."""

from sqlalchemy.orm import Session
from models.action_plan_item import ActionPlanItem
from services.action_audit_service import log_event
from datetime import datetime, timezone


def bulk_assign_owner(db: Session, action_ids: list, owner: str, actor: str = "system") -> dict:
    updated = 0
    for aid in action_ids:
        item = db.query(ActionPlanItem).filter(ActionPlanItem.id == aid).first()
        if item and item.status not in ("resolved", "dismissed"):
            old = item.owner
            item.owner = owner
            item.updated_at = datetime.now(timezone.utc)
            log_event(db, aid, "owner_change", actor=actor, old_value=old, new_value=owner, comment="Bulk assign")
            updated += 1
    db.flush()
    return {"updated": updated, "total": len(action_ids)}


def bulk_update_due_date(db: Session, action_ids: list, due_date: str, actor: str = "system") -> dict:
    updated = 0
    dt = datetime.fromisoformat(due_date) if isinstance(due_date, str) else due_date
    for aid in action_ids:
        item = db.query(ActionPlanItem).filter(ActionPlanItem.id == aid).first()
        if item and item.status not in ("resolved", "dismissed"):
            old = item.due_date.isoformat() if item.due_date else None
            item.due_date = dt
            item.updated_at = datetime.now(timezone.utc)
            log_event(db, aid, "due_date_change", actor=actor, old_value=old, new_value=due_date, comment="Bulk update")
            updated += 1
    db.flush()
    return {"updated": updated, "total": len(action_ids)}


def bulk_update_status(db: Session, action_ids: list, status: str, actor: str = "system") -> dict:
    if status in ("resolved",):
        return {
            "updated": 0,
            "total": len(action_ids),
            "error": "Bulk resolve not allowed — use individual resolve with evidence",
        }
    updated = 0
    for aid in action_ids:
        item = db.query(ActionPlanItem).filter(ActionPlanItem.id == aid).first()
        if item and item.status not in ("resolved", "dismissed"):
            old = item.status
            item.status = status
            item.last_status_change_at = datetime.now(timezone.utc)
            item.updated_at = datetime.now(timezone.utc)
            log_event(db, aid, "status_change", actor=actor, old_value=old, new_value=status, comment="Bulk update")
            updated += 1
    db.flush()
    return {"updated": updated, "total": len(action_ids)}
