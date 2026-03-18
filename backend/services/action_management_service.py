"""Management-level summary for the action center."""

from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models.action_plan_item import ActionPlanItem
from services.action_workflow_service import compute_sla_status

STALE_THRESHOLD_DAYS = 14  # Action unchanged for 14+ days = stale


def compute_management_summary(db: Session) -> dict:
    """Compute management-level aggregates across all actions."""
    items = db.query(ActionPlanItem).all()
    now = datetime.now(timezone.utc)

    open_statuses = ("open", "in_progress", "reopened")
    open_items = [i for i in items if i.status in open_statuses]
    resolved_items = [i for i in items if i.status == "resolved"]

    # Basic counts
    open_count = len(open_items)
    overdue_count = sum(1 for i in open_items if compute_sla_status(i) == "overdue")
    critical_count = sum(1 for i in open_items if i.priority == "critical")
    high_count = sum(1 for i in open_items if i.priority == "high")
    needs_evidence_count = sum(1 for i in open_items if i.evidence_required and not i.evidence_received)
    reopened_count = sum(1 for i in items if i.status == "reopened")

    # Stale: open + no update for STALE_THRESHOLD_DAYS
    stale_count = 0
    for i in open_items:
        last_change = i.last_status_change_at or i.updated_at or i.created_at
        if last_change:
            lc = last_change.replace(tzinfo=timezone.utc) if last_change.tzinfo is None else last_change
            if (now - lc).days >= STALE_THRESHOLD_DAYS:
                stale_count += 1

    # Avg resolution days
    resolution_days = []
    for i in resolved_items:
        if i.resolved_at and i.created_at:
            created = i.created_at.replace(tzinfo=timezone.utc) if i.created_at.tzinfo is None else i.created_at
            resolved = i.resolved_at.replace(tzinfo=timezone.utc) if i.resolved_at.tzinfo is None else i.resolved_at
            days = (resolved - created).days
            if days >= 0:
                resolution_days.append(days)
    avg_resolution_days = round(sum(resolution_days) / len(resolution_days), 1) if resolution_days else None

    # Ageing: average age of open items
    ages = []
    for i in open_items:
        if i.created_at:
            created = i.created_at.replace(tzinfo=timezone.utc) if i.created_at.tzinfo is None else i.created_at
            ages.append((now - created).days)
    avg_age_days = round(sum(ages) / len(ages), 1) if ages else None

    # Breakdowns
    by_owner = {}
    by_domain = {}
    by_site = {}
    by_priority = {}
    for i in open_items:
        o = i.owner or "non assigné"
        by_owner[o] = by_owner.get(o, 0) + 1
        by_domain[i.domain] = by_domain.get(i.domain, 0) + 1
        s = f"{i.site_id}"
        by_site[s] = by_site.get(s, 0) + 1
        p = i.priority or "medium"
        by_priority[p] = by_priority.get(p, 0) + 1

    # Top overdue (up to 5)
    overdue_items = [i for i in open_items if compute_sla_status(i) == "overdue"]
    overdue_items.sort(key=lambda i: i.created_at or now)
    top_overdue = [
        {
            "id": i.id,
            "issue_label": i.issue_label,
            "site_id": i.site_id,
            "priority": i.priority,
            "owner": i.owner,
            "age_days": (
                now
                - (
                    i.created_at.replace(tzinfo=timezone.utc)
                    if i.created_at and i.created_at.tzinfo is None
                    else (i.created_at or now)
                )
            ).days,
        }
        for i in overdue_items[:5]
    ]

    return {
        "total_actions": len(items),
        "open_count": open_count,
        "resolved_count": len(resolved_items),
        "overdue_count": overdue_count,
        "critical_count": critical_count,
        "high_count": high_count,
        "needs_evidence_count": needs_evidence_count,
        "reopened_count": reopened_count,
        "stale_count": stale_count,
        "stale_threshold_days": STALE_THRESHOLD_DAYS,
        "avg_resolution_days": avg_resolution_days,
        "avg_age_days": avg_age_days,
        "by_owner": by_owner,
        "by_domain": by_domain,
        "by_site": by_site,
        "by_priority": by_priority,
        "top_overdue": top_overdue,
    }
