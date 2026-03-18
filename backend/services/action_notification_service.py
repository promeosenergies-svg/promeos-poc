"""Generate and manage action center notifications."""

from sqlalchemy.orm import Session
from models.action_notification import ActionNotification
from models.action_plan_item import ActionPlanItem
from services.action_workflow_service import compute_sla_status


def generate_notifications(db: Session, action_id: int, event_type: str, actor: str = "system"):
    """Generate notifications based on action events."""
    item = db.query(ActionPlanItem).filter(ActionPlanItem.id == action_id).first()
    if not item:
        return []

    notifications = []

    if event_type == "created" and item.owner:
        notifications.append(
            _create(db, action_id, "assigned", item.owner, f"Action assignée : {item.issue_label[:100]}")
        )

    if event_type == "reopened" and item.owner:
        notifications.append(
            _create(db, action_id, "reopened", item.owner, f"Action réouverte : {item.issue_label[:100]}")
        )

    # Check SLA
    sla = compute_sla_status(item)
    if sla == "overdue":
        existing = (
            db.query(ActionNotification)
            .filter(
                ActionNotification.action_id == action_id,
                ActionNotification.notification_type == "overdue",
                ActionNotification.read == False,
            )
            .first()
        )
        if not existing:
            notifications.append(
                _create(db, action_id, "overdue", item.owner, f"Action en retard : {item.issue_label[:100]}")
            )
    elif sla == "at_risk":
        existing = (
            db.query(ActionNotification)
            .filter(
                ActionNotification.action_id == action_id,
                ActionNotification.notification_type == "due_soon",
                ActionNotification.read == False,
            )
            .first()
        )
        if not existing:
            notifications.append(
                _create(db, action_id, "due_soon", item.owner, f"Échéance proche : {item.issue_label[:100]}")
            )

    if item.evidence_required and not item.evidence_received:
        existing = (
            db.query(ActionNotification)
            .filter(
                ActionNotification.action_id == action_id,
                ActionNotification.notification_type == "evidence_missing",
                ActionNotification.read == False,
            )
            .first()
        )
        if not existing:
            notifications.append(
                _create(db, action_id, "evidence_missing", item.owner, f"Preuve requise : {item.issue_label[:100]}")
            )

    db.flush()
    return notifications


def _create(db, action_id, ntype, recipient, message):
    n = ActionNotification(action_id=action_id, notification_type=ntype, recipient=recipient, message=message)
    db.add(n)
    return n


def get_notifications(db: Session, recipient: str = None, unread_only: bool = True) -> list:
    q = db.query(ActionNotification)
    if recipient:
        q = q.filter(ActionNotification.recipient == recipient)
    if unread_only:
        q = q.filter(ActionNotification.read == False)
    return [
        {
            "id": n.id,
            "action_id": n.action_id,
            "type": n.notification_type,
            "recipient": n.recipient,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in q.order_by(ActionNotification.created_at.desc()).limit(50).all()
    ]


def mark_read(db: Session, notification_id: int):
    n = db.query(ActionNotification).filter(ActionNotification.id == notification_id).first()
    if n:
        n.read = True
        db.flush()
    return n
