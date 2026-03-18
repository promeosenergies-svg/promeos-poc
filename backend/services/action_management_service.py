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


def _is_stale(item, now=None):
    if now is None:
        now = datetime.now(timezone.utc)
    last = item.last_status_change_at or item.updated_at or item.created_at
    if not last:
        return False
    last = last.replace(tzinfo=timezone.utc) if last.tzinfo is None else last
    return (now - last).days >= STALE_THRESHOLD_DAYS


def compute_executive_summary(db: Session, period_days: int = 30) -> dict:
    """Executive-level summary with backlog health and top risks."""
    items = db.query(ActionPlanItem).all()
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=period_days)

    open_statuses = ("open", "in_progress", "reopened")
    open_items = [i for i in items if i.status in open_statuses]
    resolved_items = [i for i in items if i.status == "resolved"]

    # Period-scoped
    resolved_in_period = [
        i
        for i in resolved_items
        if i.resolved_at
        and (i.resolved_at.replace(tzinfo=timezone.utc) if i.resolved_at.tzinfo is None else i.resolved_at) >= cutoff
    ]
    created_in_period = [
        i
        for i in items
        if i.created_at
        and (i.created_at.replace(tzinfo=timezone.utc) if i.created_at.tzinfo is None else i.created_at) >= cutoff
    ]
    reopened_in_period = [
        i
        for i in items
        if i.status == "reopened"
        and i.reopened_at
        and (i.reopened_at.replace(tzinfo=timezone.utc) if i.reopened_at.tzinfo is None else i.reopened_at) >= cutoff
    ]

    overdue_count = sum(1 for i in open_items if compute_sla_status(i) == "overdue")
    needs_evidence = sum(1 for i in open_items if i.evidence_required and not i.evidence_received)
    stale = sum(1 for i in open_items if _is_stale(i, now))

    # Avg resolution
    res_days = []
    for i in resolved_in_period:
        if i.created_at:
            c = i.created_at.replace(tzinfo=timezone.utc) if i.created_at.tzinfo is None else i.created_at
            r = i.resolved_at.replace(tzinfo=timezone.utc) if i.resolved_at.tzinfo is None else i.resolved_at
            d = (r - c).days
            if d >= 0:
                res_days.append(d)
    avg_resolution = round(sum(res_days) / len(res_days), 1) if res_days else None

    # Backlog health: healthy if overdue < 10% and stale < 20%
    total_open = len(open_items) or 1
    overdue_pct = overdue_count / total_open * 100
    stale_pct = stale / total_open * 100
    if overdue_pct <= 10 and stale_pct <= 20:
        backlog_health = "healthy"
    elif overdue_pct <= 25 and stale_pct <= 40:
        backlog_health = "at_risk"
    else:
        backlog_health = "unhealthy"

    # Top sites (by open action count)
    site_counts = {}
    for i in open_items:
        site_counts[i.site_id] = site_counts.get(i.site_id, 0) + 1
    top_sites = sorted(site_counts.items(), key=lambda x: -x[1])[:5]
    top_sites = [{"site_id": s, "open_count": c} for s, c in top_sites]

    # Top domains
    domain_counts = {}
    for i in open_items:
        domain_counts[i.domain] = domain_counts.get(i.domain, 0) + 1
    top_domains = sorted(domain_counts.items(), key=lambda x: -x[1])[:5]
    top_domains = [{"domain": d, "open_count": c} for d, c in top_domains]

    # Top actions (highest priority open)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_open = sorted(open_items, key=lambda i: priority_order.get(i.priority or "medium", 2))
    top_actions = [
        {
            "id": i.id,
            "issue_label": i.issue_label,
            "priority": i.priority,
            "site_id": i.site_id,
            "domain": i.domain,
            "sla_status": compute_sla_status(i),
        }
        for i in sorted_open[:5]
    ]

    return {
        "period_days": period_days,
        "open_count": len(open_items),
        "resolved_count": len(resolved_in_period),
        "created_count": len(created_in_period),
        "overdue_count": overdue_count,
        "reopened_count": len(reopened_in_period),
        "stale_count": stale,
        "needs_evidence_count": needs_evidence,
        "avg_resolution_days": avg_resolution,
        "backlog_health": backlog_health,
        "backlog_health_rules": {
            "healthy": "overdue <= 10% AND stale <= 20%",
            "at_risk": "overdue <= 25% AND stale <= 40%",
            "unhealthy": "otherwise",
        },
        "top_sites": top_sites,
        "top_domains": top_domains,
        "top_actions": top_actions,
    }


def compute_trends(db: Session, window_days: int = 30) -> dict:
    """Compute action center trends over a time window."""
    items = db.query(ActionPlanItem).all()
    now = datetime.now(timezone.utc)

    # Build daily buckets
    buckets = {}
    for day_offset in range(window_days):
        date_key = (now - timedelta(days=day_offset)).strftime("%Y-%m-%d")
        buckets[date_key] = {"created": 0, "resolved": 0, "reopened": 0}

    for i in items:
        if i.created_at:
            c = i.created_at.replace(tzinfo=timezone.utc) if i.created_at.tzinfo is None else i.created_at
            key = c.strftime("%Y-%m-%d")
            if key in buckets:
                buckets[key]["created"] += 1
        if i.resolved_at:
            r = i.resolved_at.replace(tzinfo=timezone.utc) if i.resolved_at.tzinfo is None else i.resolved_at
            key = r.strftime("%Y-%m-%d")
            if key in buckets:
                buckets[key]["resolved"] += 1
        if i.reopened_at:
            ro = i.reopened_at.replace(tzinfo=timezone.utc) if i.reopened_at.tzinfo is None else i.reopened_at
            key = ro.strftime("%Y-%m-%d")
            if key in buckets:
                buckets[key]["reopened"] += 1

    # Compute running totals
    open_statuses = ("open", "in_progress", "reopened")
    current_open = sum(1 for i in items if i.status in open_statuses)
    current_overdue = sum(1 for i in items if i.status in open_statuses and compute_sla_status(i) == "overdue")

    return {
        "window_days": window_days,
        "daily": [{"date": k, **v} for k, v in sorted(buckets.items())],
        "totals": {
            "created": sum(b["created"] for b in buckets.values()),
            "resolved": sum(b["resolved"] for b in buckets.values()),
            "reopened": sum(b["reopened"] for b in buckets.values()),
        },
        "current_snapshot": {
            "open": current_open,
            "overdue": current_overdue,
        },
    }
