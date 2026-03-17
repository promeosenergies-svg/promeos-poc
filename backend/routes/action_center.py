"""Action Center — aggregated actionable issues across PROMEOS domains."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import get_optional_auth, AuthContext

router = APIRouter(prefix="/api/action-center", tags=["action-center"])


def _get_org_id(request: Request, auth: Optional[AuthContext]) -> int:
    org_header = request.headers.get("X-Org-Id")
    if org_header:
        return int(org_header)
    if auth and auth.org_id:
        return auth.org_id
    return 1


@router.get("/issues")
def list_issues(
    request: Request,
    domain: Optional[str] = Query(None, description="Filter by domain: compliance, billing, purchase, patrimoine"),
    severity: Optional[str] = Query(None, description="Filter by severity: critical, high, medium, low, info"),
    site_id: Optional[int] = Query(None, description="Filter by site ID"),
    status: Optional[str] = Query(None, description="Filter by status: open, acknowledged, resolved, dismissed"),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Get all actionable issues across compliance, billing, purchase, patrimoine."""
    org_id = _get_org_id(request, auth)
    from services.action_center_service import get_action_center_issues

    return get_action_center_issues(db, org_id, domain, severity, site_id, status)


@router.get("/summary")
def action_center_summary(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Quick summary: count of issues by domain and severity."""
    org_id = _get_org_id(request, auth)
    from services.action_center_service import get_action_center_issues

    result = get_action_center_issues(db, org_id)
    return {
        "total": result["total"],
        "domains": result["domains"],
        "severities": result["severities"],
        "critical_count": result["severities"].get("critical", 0),
        "high_count": result["severities"].get("high", 0),
    }


# ── Action Workflow endpoints ────────────────────────────────────────────


@router.post("/actions")
def create_action(
    body: dict = Body(...),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Create a persisted action from an issue."""
    from services.action_workflow_service import create_action_from_issue, serialize_action

    owner = body.get("owner") or (auth.email if auth else None)
    item = create_action_from_issue(db, body, owner=owner, due_date=body.get("due_date"))
    db.commit()
    return serialize_action(item)


@router.get("/actions")
def list_actions_endpoint(
    site_id: Optional[int] = Query(None),
    domain: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    owner: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List persisted action plan items."""
    from services.action_workflow_service import list_actions, serialize_action

    items = list_actions(db, site_id=site_id, domain=domain, status=status_filter, priority=priority, owner=owner)
    return {"total": len(items), "actions": [serialize_action(i) for i in items]}


@router.get("/actions/summary")
def actions_summary(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Summary of persisted actions by status, priority, domain."""
    from services.action_workflow_service import list_actions, serialize_action, compute_sla_status

    items = list_actions(db)

    by_status = {}
    by_priority = {}
    by_domain = {}
    by_owner = {}
    overdue_count = 0

    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        p = item.priority or "medium"
        by_priority[p] = by_priority.get(p, 0) + 1
        by_domain[item.domain] = by_domain.get(item.domain, 0) + 1
        o = item.owner or "non assigné"
        by_owner[o] = by_owner.get(o, 0) + 1
        if compute_sla_status(item) == "overdue":
            overdue_count += 1

    return {
        "total": len(items),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_domain": by_domain,
        "by_owner": by_owner,
        "overdue_count": overdue_count,
        "open_count": by_status.get("open", 0) + by_status.get("in_progress", 0) + by_status.get("reopened", 0),
        "resolved_count": by_status.get("resolved", 0),
    }


@router.post("/actions/{action_id}/override-priority")
def override_priority_endpoint(
    action_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Override action priority manually. Requires reason (min 5 chars)."""
    from services.action_workflow_service import override_priority, serialize_action

    new_priority = body.get("priority")
    reason = body.get("reason")
    if not new_priority:
        raise HTTPException(status_code=400, detail="priority is required")
    if not reason or len(str(reason).strip()) < 5:
        raise HTTPException(status_code=400, detail="reason is required (min 5 chars)")
    item = override_priority(db, action_id, new_priority, reason)
    if not item:
        raise HTTPException(status_code=404, detail="Action non trouvée ou priorité invalide")
    db.commit()
    return serialize_action(item)


@router.patch("/actions/{action_id}")
def update_action_endpoint(
    action_id: int,
    body: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Update action fields."""
    from services.action_workflow_service import update_action, serialize_action

    item = update_action(db, action_id, body)
    if not item:
        raise HTTPException(status_code=404, detail="Action non trouvée")
    db.commit()
    return serialize_action(item)


@router.post("/actions/{action_id}/resolve")
def resolve_action_endpoint(
    action_id: int,
    body: dict = Body(default={}),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    """Resolve an action with optional note."""
    from services.action_workflow_service import resolve_action, serialize_action

    resolved_by = (auth.email if auth else None) or body.get("resolved_by", "system")
    item = resolve_action(db, action_id, body.get("resolution_note"), resolved_by)
    if not item:
        raise HTTPException(status_code=400, detail="Action non trouvée ou preuve requise non fournie")
    db.commit()
    return serialize_action(item)


@router.post("/actions/{action_id}/reopen")
def reopen_action_endpoint(
    action_id: int,
    body: dict = Body(default={}),
    db: Session = Depends(get_db),
):
    """Reopen a resolved/dismissed action."""
    from services.action_workflow_service import reopen_action, serialize_action

    item = reopen_action(db, action_id, body.get("reason"))
    if not item:
        raise HTTPException(status_code=404, detail="Action non trouvée")
    db.commit()
    return serialize_action(item)
