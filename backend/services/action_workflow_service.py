"""Workflow for action plan items: create, update, resolve, reopen."""

import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.action_plan_item import ActionPlanItem

logger = logging.getLogger("promeos.action_workflow")

SEVERITY_TO_PRIORITY = {"critical": "critical", "high": "high", "medium": "medium", "low": "low", "info": "low"}
SLA_DAYS = {"critical": 7, "high": 14, "medium": 30, "low": 90}


def create_action_from_issue(db: Session, issue_data: dict, owner: str = None, due_date: str = None) -> ActionPlanItem:
    """Create a persisted action from an ActionableIssue."""
    priority = SEVERITY_TO_PRIORITY.get(issue_data.get("severity", "medium"), "medium")
    item = ActionPlanItem(
        issue_id=issue_data["issue_id"],
        domain=issue_data["domain"],
        severity=issue_data["severity"],
        site_id=issue_data["site_id"],
        issue_code=issue_data["issue_code"],
        issue_label=issue_data["issue_label"],
        reason_codes=json.dumps(issue_data.get("reason_codes", [])),
        estimated_impact_eur=issue_data.get("estimated_impact_eur"),
        recommended_action=issue_data.get("recommended_action"),
        status="open",
        owner=owner,
        evidence_required=issue_data.get("severity") in ("critical", "high"),
        priority=priority,
        priority_source="auto",
        sla_days=SLA_DAYS.get(priority, 30),
        source_ref=f"{issue_data.get('domain', 'unknown')}:{issue_data.get('issue_code', 'unknown')}",
    )
    if due_date:
        item.due_date = datetime.fromisoformat(due_date)
    db.add(item)
    db.flush()
    logger.info("Action %d created from issue %s", item.id, item.issue_id)
    return item


def update_action(db: Session, action_id: int, updates: dict) -> ActionPlanItem:
    """Update action fields (owner, due_date, status, notes)."""
    item = db.query(ActionPlanItem).filter(ActionPlanItem.id == action_id).first()
    if not item:
        return None
    for key in ("owner", "status", "evidence_note", "evidence_received"):
        if key in updates and updates[key] is not None:
            setattr(item, key, updates[key])
    if "due_date" in updates:
        val = updates["due_date"]
        if val:
            item.due_date = datetime.fromisoformat(val) if isinstance(val, str) else val
        else:
            item.due_date = None
    if "status" in updates and updates["status"] == "in_progress" and item.status == "open":
        item.status = "in_progress"
    if "status" in updates:
        item.last_status_change_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    db.flush()
    return item


def override_priority(db: Session, action_id: int, new_priority: str, reason: str = None) -> ActionPlanItem:
    """Override priority manually. Reason required."""
    if new_priority not in ("critical", "high", "medium", "low"):
        return None
    if not reason or len(reason.strip()) < 5:
        return None  # Reason required for override
    item = db.query(ActionPlanItem).filter(ActionPlanItem.id == action_id).first()
    if not item:
        return None
    item.priority = new_priority
    item.priority_source = "manual"
    item.priority_override_reason = reason.strip()
    # Recalc SLA based on new priority
    item.sla_days = SLA_DAYS.get(new_priority, 30)
    item.updated_at = datetime.now(timezone.utc)
    db.flush()
    return item


def resolve_action(db: Session, action_id: int, resolution_note: str = None, resolved_by: str = None) -> ActionPlanItem:
    """Resolve an action with optional note and actor."""
    item = db.query(ActionPlanItem).filter(ActionPlanItem.id == action_id).first()
    if not item:
        return None
    if item.evidence_required and not item.evidence_received:
        return None  # Cannot resolve without evidence
    item.status = "resolved"
    item.resolution_note = resolution_note
    item.resolved_at = datetime.now(timezone.utc)
    item.resolved_by = resolved_by or "system"
    item.last_status_change_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("Action %d resolved by %s", action_id, resolved_by)
    return item


def reopen_action(db: Session, action_id: int, reason: str = None) -> ActionPlanItem:
    """Reopen a resolved/dismissed action."""
    item = db.query(ActionPlanItem).filter(ActionPlanItem.id == action_id).first()
    if not item:
        return None
    item.status = "reopened"
    item.reopened_at = datetime.now(timezone.utc)
    item.resolved_at = None
    item.resolution_note = reason or f"Réouvert (précédent: {item.resolution_note or 'N/A'})"
    item.last_status_change_at = datetime.now(timezone.utc)
    item.updated_at = datetime.now(timezone.utc)
    db.flush()
    logger.info("Action %d reopened", action_id)
    return item


def compute_sla_status(item: ActionPlanItem) -> str:
    """Compute SLA status. Prefers due_date if set, falls back to sla_days from creation."""
    if item.status in ("resolved", "dismissed"):
        return "resolved"

    from datetime import timedelta

    now = datetime.now(timezone.utc)

    # Prefer explicit due_date
    if item.due_date:
        deadline = item.due_date
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
    elif item.sla_days and item.created_at:
        created = item.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        deadline = created + timedelta(days=item.sla_days)
    else:
        return "on_track"

    days_left = (deadline - now).days
    if days_left < 0:
        return "overdue"
    elif days_left <= 3:
        return "at_risk"
    return "on_track"


def list_actions(
    db: Session,
    site_id: int = None,
    domain: str = None,
    status: str = None,
    priority: str = None,
    owner: str = None,
    due_before: str = None,
    due_after: str = None,
) -> list:
    """List persisted actions with optional filters."""
    q = db.query(ActionPlanItem)
    if site_id:
        q = q.filter(ActionPlanItem.site_id == site_id)
    if domain:
        q = q.filter(ActionPlanItem.domain == domain)
    if status:
        q = q.filter(ActionPlanItem.status == status)
    if priority:
        q = q.filter(ActionPlanItem.priority == priority)
    if owner:
        q = q.filter(ActionPlanItem.owner == owner)
    if due_before:
        q = q.filter(ActionPlanItem.due_date <= datetime.fromisoformat(due_before))
    if due_after:
        q = q.filter(ActionPlanItem.due_date >= datetime.fromisoformat(due_after))
    return q.order_by(ActionPlanItem.created_at.desc()).all()


def serialize_action(item: ActionPlanItem) -> dict:
    """Serialize an ActionPlanItem for API response."""
    return {
        "id": item.id,
        "issue_id": item.issue_id,
        "domain": item.domain,
        "severity": item.severity,
        "site_id": item.site_id,
        "issue_code": item.issue_code,
        "issue_label": item.issue_label,
        "reason_codes": json.loads(item.reason_codes) if item.reason_codes else [],
        "estimated_impact_eur": item.estimated_impact_eur,
        "recommended_action": item.recommended_action,
        "priority": item.priority or "medium",
        "priority_source": item.priority_source or "auto",
        "priority_override_reason": item.priority_override_reason,
        "sla_days": item.sla_days,
        "sla_status": compute_sla_status(item),
        "source_ref": item.source_ref,
        "evidence_type": item.evidence_type,
        "status": item.status,
        "owner": item.owner,
        "due_date": item.due_date.isoformat() if item.due_date else None,
        "evidence_required": item.evidence_required,
        "evidence_received": item.evidence_received,
        "evidence_note": item.evidence_note,
        "resolution_note": item.resolution_note,
        "resolved_at": item.resolved_at.isoformat() if item.resolved_at else None,
        "resolved_by": item.resolved_by,
        "reopened_at": item.reopened_at.isoformat() if item.reopened_at else None,
        "last_status_change_at": item.last_status_change_at.isoformat() if item.last_status_change_at else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "traceable": True,
    }
