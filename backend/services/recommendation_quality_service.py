"""Recommendation engine quality measurement and calibration."""

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models.recommendation_decision import RecommendationDecision
from models.action_plan_item import ActionPlanItem
from services.action_workflow_service import compute_sla_status
from services.action_management_service import _is_stale

logger = logging.getLogger("promeos.rec_quality")

# ── Calibration (versioned weights) ──────────────────────────────────

CALIBRATION_VERSIONS = [
    {
        "version": "1.0",
        "effective_date": "2026-03-18",
        "weights": {"urgency": 0.4, "risk": 0.3, "ease": 0.1, "confidence": 0.2},
        "domain_adjustments": {},
        "notes": "Initial calibration — Sprint 17",
    },
]


def get_current_calibration() -> dict:
    return CALIBRATION_VERSIONS[-1]


def get_calibration_history() -> list:
    return CALIBRATION_VERSIONS


# ── Quality Summary ─────────────────────────────────────────────────


def compute_quality_summary(db: Session, period_days: int = 30) -> dict:
    """Compute recommendation engine quality metrics."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=period_days)

    # All decisions in period
    decisions = db.query(RecommendationDecision).all()
    period_decisions = [
        d
        for d in decisions
        if d.decided_at
        and (d.decided_at.replace(tzinfo=timezone.utc) if d.decided_at.tzinfo is None else d.decided_at) >= cutoff
    ]

    total = len(period_decisions)
    accepted = sum(1 for d in period_decisions if d.decision == "accepted")
    dismissed = sum(1 for d in period_decisions if d.decision == "dismissed")
    deferred = sum(1 for d in period_decisions if d.decision == "deferred")
    converted = sum(1 for d in period_decisions if d.decision == "converted_to_action")

    # Rates
    acceptance_rate = round(accepted / total * 100, 1) if total else None
    dismissal_rate = round(dismissed / total * 100, 1) if total else None
    defer_rate = round(deferred / total * 100, 1) if total else None
    conversion_rate = round(converted / total * 100, 1) if total else None

    # By domain
    by_domain = {}
    for d in period_decisions:
        # Get domain from linked action
        if d.action_id:
            item = db.query(ActionPlanItem).filter(ActionPlanItem.id == d.action_id).first()
            domain = item.domain if item else "unknown"
        else:
            domain = "unknown"
        if domain not in by_domain:
            by_domain[domain] = {"total": 0, "accepted": 0, "dismissed": 0, "deferred": 0, "converted": 0}
        by_domain[domain]["total"] += 1
        by_domain[domain][d.decision] = by_domain[domain].get(d.decision, 0) + 1

    # Top reasons
    dismiss_reasons = {}
    defer_reasons = {}
    for d in period_decisions:
        if d.decision == "dismissed" and d.reason:
            key = d.reason[:80]
            dismiss_reasons[key] = dismiss_reasons.get(key, 0) + 1
        if d.decision == "deferred" and d.reason:
            key = d.reason[:80]
            defer_reasons[key] = defer_reasons.get(key, 0) + 1

    top_dismiss = sorted(dismiss_reasons.items(), key=lambda x: -x[1])[:5]
    top_defer = sorted(defer_reasons.items(), key=lambda x: -x[1])[:5]

    # Confidence distribution from current open actions
    open_statuses = ("open", "in_progress", "reopened")
    open_items = db.query(ActionPlanItem).filter(ActionPlanItem.status.in_(open_statuses)).all()

    confidence_dist = {"high": 0, "medium": 0, "low": 0}
    for item in open_items:
        if item.evidence_received:
            confidence_dist["high"] += 1
        elif not item.evidence_required:
            confidence_dist["medium"] += 1
        else:
            confidence_dist["low"] += 1

    # Stale recommendations (open actions with no recent change)
    stale_count = sum(1 for i in open_items if _is_stale(i, now))

    # Avg decision score at time of decision
    scores = [d.decision_score_at_time for d in period_decisions if d.decision_score_at_time is not None]
    avg_decision_score = round(sum(scores) / len(scores), 1) if scores else None

    return {
        "period_days": period_days,
        "total_recommendations_decided": total,
        "accepted_count": accepted,
        "dismissed_count": dismissed,
        "deferred_count": deferred,
        "converted_to_action_count": converted,
        "acceptance_rate": acceptance_rate,
        "dismissal_rate": dismissal_rate,
        "defer_rate": defer_rate,
        "conversion_rate": conversion_rate,
        "by_domain": by_domain,
        "top_dismiss_reasons": [{"reason": r, "count": c} for r, c in top_dismiss],
        "top_defer_reasons": [{"reason": r, "count": c} for r, c in top_defer],
        "confidence_distribution": confidence_dist,
        "stale_recommendations_count": stale_count,
        "avg_decision_score_at_time": avg_decision_score,
        "calibration": get_current_calibration(),
    }
