"""Prescriptive recommendation engine for PROMEOS.

Scoring rules (documented):
- urgency_score = f(sla_status, priority, overdue days)
  - overdue critical: 100
  - overdue high: 85
  - at_risk critical: 75
  - overdue medium: 70
  - at_risk high: 60
  - open critical: 55
  - open high: 40
  - open medium: 25
  - open low: 10

- risk_score = f(estimated_impact_eur, domain, severity)
  - impact > 20k: 90
  - impact > 10k: 70
  - impact > 5k: 50
  - compliance domain: +15
  - billing domain: +10

- confidence_score = f(data completeness, evidence status)
  - evidence received: 90
  - evidence not required: 75
  - evidence required but missing: 40
  - stale data: 30

- decision_score = urgency * 0.4 + risk * 0.3 + (100 - effort) * 0.1 + confidence * 0.2
"""

import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.action_plan_item import ActionPlanItem
from services.action_workflow_service import compute_sla_status
from services.action_management_service import _is_stale

logger = logging.getLogger("promeos.recommendations")


def _compute_urgency(item: ActionPlanItem) -> float:
    sla = compute_sla_status(item)
    p = item.priority or "medium"

    URGENCY_MAP = {
        ("overdue", "critical"): 100,
        ("overdue", "high"): 85,
        ("at_risk", "critical"): 75,
        ("overdue", "medium"): 70,
        ("at_risk", "high"): 60,
        ("on_track", "critical"): 55,
        ("overdue", "low"): 50,
        ("at_risk", "medium"): 45,
        ("on_track", "high"): 40,
        ("at_risk", "low"): 30,
        ("on_track", "medium"): 25,
        ("on_track", "low"): 10,
    }
    return URGENCY_MAP.get((sla, p), 25)


def _compute_risk(item: ActionPlanItem) -> float:
    base = 20
    impact = item.estimated_impact_eur or 0
    if impact > 20000:
        base = 90
    elif impact > 10000:
        base = 70
    elif impact > 5000:
        base = 50
    elif impact > 1000:
        base = 35

    if item.domain == "compliance":
        base = min(100, base + 15)
    elif item.domain == "billing":
        base = min(100, base + 10)
    return base


def _compute_confidence(item: ActionPlanItem) -> float:
    if item.evidence_received:
        return 90
    if not item.evidence_required:
        return 75
    if _is_stale(item):
        return 30
    return 40  # evidence required but missing


def _compute_effort(item: ActionPlanItem) -> float:
    # Simple heuristic: critical = harder, compliance = harder
    base = 50
    if item.priority == "critical":
        base = 70
    elif item.priority == "high":
        base = 60
    elif item.priority == "low":
        base = 30
    if item.domain == "compliance":
        base = min(100, base + 10)
    return base


def _why_now(item: ActionPlanItem) -> str:
    sla = compute_sla_status(item)
    reasons = []
    if sla == "overdue":
        reasons.append("Échéance dépassée")
    elif sla == "at_risk":
        reasons.append("Échéance proche")
    if item.priority in ("critical", "high"):
        reasons.append(f"Priorité {item.priority}")
    impact = item.estimated_impact_eur or 0
    if impact > 5000:
        reasons.append(f"Impact estimé {int(impact / 1000)} k€")
    if item.evidence_required and not item.evidence_received:
        reasons.append("Preuve requise non fournie")
    if not reasons:
        reasons.append("Action ouverte à traiter")
    return " · ".join(reasons)


def compute_recommendations(
    db: Session, scope: str = None, site_id: int = None, domain: str = None, limit: int = 20
) -> list:
    """Generate prioritized recommendations from open actions."""
    open_statuses = ("open", "in_progress", "reopened")
    q = db.query(ActionPlanItem).filter(ActionPlanItem.status.in_(open_statuses))
    if site_id:
        q = q.filter(ActionPlanItem.site_id == site_id)
    if domain:
        q = q.filter(ActionPlanItem.domain == domain)

    items = q.all()
    recommendations = []

    for item in items:
        urgency = _compute_urgency(item)
        risk = _compute_risk(item)
        confidence = _compute_confidence(item)
        effort = _compute_effort(item)
        decision = round(urgency * 0.4 + risk * 0.3 + (100 - effort) * 0.1 + confidence * 0.2, 1)

        # Determine scope
        if scope:
            item_scope = scope
        elif urgency >= 70 or risk >= 70:
            item_scope = "executive"
        elif urgency >= 40:
            item_scope = "portfolio"
        else:
            item_scope = "site"

        blockers = []
        if item.evidence_required and not item.evidence_received:
            blockers.append("preuve_manquante")
        if not item.owner:
            blockers.append("non_assigne")

        recommendations.append(
            {
                "recommendation_id": f"rec_{item.id}",
                "issue_id": item.issue_id,
                "action_id": item.id,
                "scope": item_scope,
                "domain": item.domain,
                "site_id": item.site_id,
                "recommended_action": item.recommended_action or item.issue_label,
                "why_now": _why_now(item),
                "estimated_impact_eur": item.estimated_impact_eur,
                "urgency_score": urgency,
                "risk_score": risk,
                "confidence_score": confidence,
                "effort_score": effort,
                "decision_score": decision,
                "blockers": blockers,
                "traceable": True,
            }
        )

    # Sort by decision_score descending
    recommendations.sort(key=lambda r: -r["decision_score"])

    if scope:
        recommendations = [r for r in recommendations if r["scope"] == scope]

    return recommendations[:limit]


def compute_recommendation_summary(db: Session) -> dict:
    """Summary of recommendations."""
    recs = compute_recommendations(db, limit=100)

    by_scope = {}
    by_domain = {}
    scores = []
    for r in recs:
        by_scope[r["scope"]] = by_scope.get(r["scope"], 0) + 1
        by_domain[r["domain"]] = by_domain.get(r["domain"], 0) + 1
        scores.append(r["decision_score"])

    return {
        "total": len(recs),
        "by_scope": by_scope,
        "by_domain": by_domain,
        "avg_decision_score": round(sum(scores) / len(scores), 1) if scores else None,
        "top_5": recs[:5],
    }
