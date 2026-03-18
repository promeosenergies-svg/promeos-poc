"""Decision workflow for recommendations: accept, dismiss, defer, convert."""

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.recommendation_decision import RecommendationDecision
from services.action_workflow_service import create_action_from_issue, serialize_action
from services.action_audit_service import log_event

logger = logging.getLogger("promeos.rec_decisions")


def record_decision(
    db: Session,
    recommendation_id: str,
    decision: str,
    action_id: int = None,
    reason: str = None,
    decision_score: float = None,
    actor: str = "system",
) -> RecommendationDecision:
    """Record a decision on a recommendation."""
    rec = RecommendationDecision(
        recommendation_id=recommendation_id,
        action_id=action_id,
        decision=decision,
        reason=reason,
        decision_score_at_time=decision_score,
        actor=actor,
    )
    db.add(rec)
    db.flush()

    # Log event on source action if exists
    if action_id:
        log_event(db, action_id, f"recommendation_{decision}", actor=actor, new_value=recommendation_id, comment=reason)

    logger.info("Decision %s on %s by %s", decision, recommendation_id, actor)
    return rec


def accept_recommendation(
    db: Session,
    recommendation_id: str,
    action_id: int,
    reason: str = None,
    actor: str = "system",
    decision_score: float = None,
):
    """Accept a recommendation — marks the source action as acknowledged."""
    from models.action_plan_item import ActionPlanItem

    item = db.query(ActionPlanItem).filter(ActionPlanItem.id == action_id).first()
    if item and item.status == "open":
        item.status = "in_progress"
        item.last_status_change_at = datetime.now(timezone.utc)
        item.updated_at = datetime.now(timezone.utc)

    return record_decision(db, recommendation_id, "accepted", action_id, reason, decision_score, actor)


def dismiss_recommendation(
    db: Session,
    recommendation_id: str,
    action_id: int = None,
    reason: str = None,
    actor: str = "system",
    decision_score: float = None,
):
    """Dismiss a recommendation — requires reason."""
    if not reason or len(str(reason).strip()) < 5:
        return None  # Reason required
    return record_decision(db, recommendation_id, "dismissed", action_id, reason, decision_score, actor)


def defer_recommendation(
    db: Session,
    recommendation_id: str,
    action_id: int = None,
    reason: str = None,
    actor: str = "system",
    decision_score: float = None,
):
    """Defer a recommendation for later."""
    return record_decision(db, recommendation_id, "deferred", action_id, reason, decision_score, actor)


def convert_to_action(
    db: Session, recommendation_id: str, rec_data: dict, actor: str = "system", decision_score: float = None
):
    """Convert a recommendation into a new persisted action."""
    new_action = create_action_from_issue(db, rec_data, owner=actor)
    decision = record_decision(
        db,
        recommendation_id,
        "converted_to_action",
        rec_data.get("action_id"),
        f"Converti en action #{new_action.id}",
        decision_score,
        actor,
    )
    decision.created_action_id = new_action.id
    db.flush()
    return decision, new_action


def get_decision_stats(db: Session) -> dict:
    """Get decision statistics for learning signals."""
    decisions = db.query(RecommendationDecision).all()
    by_type = {}
    reasons_dismiss = {}
    reasons_defer = {}

    for d in decisions:
        by_type[d.decision] = by_type.get(d.decision, 0) + 1
        if d.decision == "dismissed" and d.reason:
            key = d.reason[:50]
            reasons_dismiss[key] = reasons_dismiss.get(key, 0) + 1
        if d.decision == "deferred" and d.reason:
            key = d.reason[:50]
            reasons_defer[key] = reasons_defer.get(key, 0) + 1

    return {
        "total_decisions": len(decisions),
        "accepted_count": by_type.get("accepted", 0),
        "dismissed_count": by_type.get("dismissed", 0),
        "deferred_count": by_type.get("deferred", 0),
        "converted_to_action_count": by_type.get("converted_to_action", 0),
        "top_dismiss_reasons": dict(sorted(reasons_dismiss.items(), key=lambda x: -x[1])[:5]),
        "top_defer_reasons": dict(sorted(reasons_defer.items(), key=lambda x: -x[1])[:5]),
    }


def serialize_decision(d: RecommendationDecision) -> dict:
    return {
        "id": d.id,
        "recommendation_id": d.recommendation_id,
        "action_id": d.action_id,
        "decision": d.decision,
        "reason": d.reason,
        "created_action_id": d.created_action_id,
        "decision_score_at_time": d.decision_score_at_time,
        "actor": d.actor,
        "decided_at": d.decided_at.isoformat() if d.decided_at else None,
    }
