"""Action Center — aggregated actionable issues across PROMEOS domains."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import get_optional_auth, AuthContext

router = APIRouter(prefix="/api/action-center", tags=["action-center"])

# ── Saved Views (in-memory for POC) ─────────────────────────────────────
SAVED_VIEWS = {
    "mes_actions": {"label": "Mes actions", "filters": {"owner": "__CURRENT_USER__"}},
    "overdue": {"label": "En retard", "filters": {"sla_status": "overdue"}},
    "critiques": {"label": "Critiques", "filters": {"priority": "critical"}},
    "cette_semaine": {"label": "Cette semaine", "filters": {"due_before": "__THIS_WEEK__"}},
}


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
    due_before: Optional[str] = Query(None, description="Due date before (ISO)"),
    due_after: Optional[str] = Query(None, description="Due date after (ISO)"),
    db: Session = Depends(get_db),
):
    """List persisted action plan items."""
    from services.action_workflow_service import list_actions, serialize_action

    items = list_actions(
        db,
        site_id=site_id,
        domain=domain,
        status=status_filter,
        priority=priority,
        owner=owner,
        due_before=due_before,
        due_after=due_after,
    )
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

    by_sla = {}
    for item in items:
        by_status[item.status] = by_status.get(item.status, 0) + 1
        p = item.priority or "medium"
        by_priority[p] = by_priority.get(p, 0) + 1
        by_domain[item.domain] = by_domain.get(item.domain, 0) + 1
        o = item.owner or "non assigné"
        by_owner[o] = by_owner.get(o, 0) + 1
        sla = compute_sla_status(item)
        by_sla[sla] = by_sla.get(sla, 0) + 1
        if sla == "overdue":
            overdue_count += 1

    needs_evidence = sum(
        1
        for item in items
        if item.evidence_required and not item.evidence_received and item.status not in ("resolved", "dismissed")
    )

    return {
        "total": len(items),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_domain": by_domain,
        "by_owner": by_owner,
        "by_sla": by_sla,
        "overdue_count": overdue_count,
        "open_count": by_status.get("open", 0) + by_status.get("in_progress", 0) + by_status.get("reopened", 0),
        "resolved_count": by_status.get("resolved", 0),
        "needs_evidence_count": needs_evidence,
    }


@router.get("/recommendations")
def get_recommendations(
    scope: Optional[str] = Query(None, description="executive|portfolio|site"),
    site_id: Optional[int] = Query(None),
    domain: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Prioritized recommendations across all domains."""
    from services.recommendation_service import compute_recommendations

    recs = compute_recommendations(db, scope=scope, site_id=site_id, domain=domain, limit=limit)
    return {"total": len(recs), "recommendations": recs}


@router.get("/recommendations/summary")
def recommendations_summary(db: Session = Depends(get_db)):
    """Summary of recommendations by scope, domain, and scores."""
    from services.recommendation_service import compute_recommendation_summary

    return compute_recommendation_summary(db)


# ── Recommendation Quality & Calibration (Sprint 19) ──────────────────


@router.get("/recommendations/quality-summary")
def quality_summary(
    period: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    """Quality metrics for the recommendation engine."""
    from services.recommendation_quality_service import compute_quality_summary

    return compute_quality_summary(db, period)


@router.get("/recommendations/calibration")
def get_calibration(db: Session = Depends(get_db)):
    """Current and historical calibration weights."""
    from services.calibration_governance_service import get_active_calibration, get_calibration_history

    result = {
        "current": get_active_calibration(db),
        "history": get_calibration_history(db),
    }
    db.commit()  # persist initial version if created
    return result


@router.get("/recommendations/calibration/history")
def calibration_history(db: Session = Depends(get_db)):
    from services.calibration_governance_service import get_calibration_history

    return {"versions": get_calibration_history(db)}


@router.get("/recommendations/calibration/compare")
def calibration_compare(
    v1: str = Query(...),
    v2: str = Query(...),
    db: Session = Depends(get_db),
):
    from services.calibration_governance_service import compare_calibrations

    result = compare_calibrations(db, v1, v2)
    if not result:
        raise HTTPException(status_code=404, detail="Version non trouvée")
    return result


@router.post("/recommendations/calibration")
def create_calibration_endpoint(
    body: dict = Body(...),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.calibration_governance_service import create_calibration

    actor = (auth.email if auth else None) or body.get("created_by", "system")
    result = create_calibration(
        db, body["version"], body["weights"], body.get("comment"), actor, body.get("domain_adjustments")
    )
    if not result:
        raise HTTPException(status_code=400, detail="Version existe déjà ou poids invalides (somme != 1.0)")
    db.commit()
    return result


@router.post("/recommendations/calibration/activate")
def activate_calibration_endpoint(
    body: dict = Body(...),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.calibration_governance_service import activate_calibration

    actor = (auth.email if auth else None) or body.get("actor", "system")
    result = activate_calibration(db, body["version"], actor)
    if not result:
        raise HTTPException(status_code=400, detail="Version non trouvée ou statut incompatible")
    db.commit()
    return result


@router.post("/recommendations/calibration/rollback")
def rollback_calibration_endpoint(
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.calibration_governance_service import rollback_calibration

    actor = (auth.email if auth else None) or "system"
    result = rollback_calibration(db, actor)
    if not result:
        raise HTTPException(status_code=400, detail="Aucune version précédente disponible")
    db.commit()
    return result


@router.get("/recommendations/outcomes")
def list_outcomes(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    from services.calibration_governance_service import get_outcomes

    outcomes = get_outcomes(db, limit)
    return {"total": len(outcomes), "outcomes": outcomes}


@router.post("/recommendations/outcomes")
def record_outcome_endpoint(body: dict = Body(...), db: Session = Depends(get_db)):
    from services.calibration_governance_service import record_outcome

    o = record_outcome(
        db,
        body["recommendation_id"],
        body["outcome_status"],
        body.get("action_id"),
        body.get("domain"),
        body.get("decision"),
        body.get("outcome_reason"),
        body.get("backlog_delta"),
        body.get("overdue_delta"),
        body.get("impact_delta_eur"),
    )
    db.commit()
    return {"id": o.id, "outcome_status": o.outcome_status}


# ── Recommendation Decisions (Sprint 18) ──────────────────────────────


@router.post("/recommendations/{rec_id}/accept")
def accept_rec(
    rec_id: str,
    body: dict = Body(default={}),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.recommendation_decision_service import accept_recommendation, serialize_decision

    actor = (auth.email if auth else None) or body.get("actor", "system")
    action_id = body.get("action_id")
    d = accept_recommendation(db, rec_id, action_id, body.get("reason"), actor, body.get("decision_score"))
    db.commit()
    return serialize_decision(d)


@router.post("/recommendations/{rec_id}/dismiss")
def dismiss_rec(
    rec_id: str,
    body: dict = Body(...),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.recommendation_decision_service import dismiss_recommendation, serialize_decision

    actor = (auth.email if auth else None) or body.get("actor", "system")
    d = dismiss_recommendation(db, rec_id, body.get("action_id"), body.get("reason"), actor, body.get("decision_score"))
    if not d:
        raise HTTPException(status_code=400, detail="Motif requis (min 5 caractères)")
    db.commit()
    return serialize_decision(d)


@router.post("/recommendations/{rec_id}/defer")
def defer_rec(
    rec_id: str,
    body: dict = Body(default={}),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.recommendation_decision_service import defer_recommendation, serialize_decision

    actor = (auth.email if auth else None) or body.get("actor", "system")
    d = defer_recommendation(db, rec_id, body.get("action_id"), body.get("reason"), actor, body.get("decision_score"))
    db.commit()
    return serialize_decision(d)


@router.post("/recommendations/{rec_id}/create-action")
def convert_rec(
    rec_id: str,
    body: dict = Body(...),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.recommendation_decision_service import convert_to_action, serialize_decision
    from services.action_workflow_service import serialize_action

    actor = (auth.email if auth else None) or body.get("actor", "system")
    d, action = convert_to_action(db, rec_id, body, actor, body.get("decision_score"))
    db.commit()
    return {"decision": serialize_decision(d), "action": serialize_action(action)}


@router.get("/recommendations/decisions")
def list_decisions(db: Session = Depends(get_db)):
    from services.recommendation_decision_service import get_decision_stats

    return get_decision_stats(db)


@router.get("/management-summary")
def management_summary(db: Session = Depends(get_db)):
    """Management-level summary: backlog health, ageing, workload, top risks."""
    from services.action_management_service import compute_management_summary

    return compute_management_summary(db)


@router.get("/executive-summary")
def executive_summary(
    period: int = Query(30, ge=7, le=365, description="Period in days"),
    db: Session = Depends(get_db),
):
    """Executive-level summary with backlog health and top risks."""
    from services.action_management_service import compute_executive_summary

    return compute_executive_summary(db, period)


@router.get("/trends")
def action_trends(
    window: int = Query(30, ge=7, le=365, description="Window in days"),
    db: Session = Depends(get_db),
):
    """Action center trends over time."""
    from services.action_management_service import compute_trends

    return compute_trends(db, window)


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


@router.get("/actions/{action_id}/history")
def get_action_history(action_id: int, db: Session = Depends(get_db)):
    from services.action_audit_service import get_history

    return {"action_id": action_id, "events": get_history(db, action_id)}


@router.get("/actions/{action_id}/evidence")
def get_action_evidence(action_id: int, db: Session = Depends(get_db)):
    from services.action_audit_service import get_evidence

    return {"action_id": action_id, "evidence": get_evidence(db, action_id)}


@router.post("/actions/{action_id}/evidence")
def add_action_evidence(
    action_id: int,
    body: dict = Body(...),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
):
    from services.action_audit_service import add_evidence

    uploaded_by = (auth.email if auth else None) or body.get("uploaded_by", "system")
    ev = add_evidence(
        db,
        action_id,
        evidence_type=body.get("evidence_type", "note"),
        label=body.get("label", "Preuve"),
        value=body.get("value"),
        document_name=body.get("document_name"),
        uploaded_by=uploaded_by,
    )
    db.commit()
    return {"id": ev.id, "evidence_type": ev.evidence_type, "label": ev.label}


@router.get("/actions/{action_id}/export")
def export_action_dossier_endpoint(action_id: int, db: Session = Depends(get_db)):
    from services.action_audit_service import export_action_dossier

    dossier = export_action_dossier(db, action_id)
    if not dossier:
        raise HTTPException(status_code=404, detail="Action non trouvée")
    return dossier


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


# ── Saved Views ──────────────────────────────────────────────────────────


@router.get("/views")
def list_saved_views():
    return {"views": [{"id": k, **v} for k, v in SAVED_VIEWS.items()]}


# ── Notifications ────────────────────────────────────────────────────────


@router.get("/notifications")
def list_notifications(
    recipient: Optional[str] = Query(None),
    unread_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    from services.action_notification_service import get_notifications

    return {"notifications": get_notifications(db, recipient, unread_only)}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    from services.action_notification_service import mark_read

    mark_read(db, notification_id)
    db.commit()
    return {"status": "read"}


# ── Bulk Actions ─────────────────────────────────────────────────────────


@router.post("/actions/bulk/assign-owner")
def bulk_assign(body: dict = Body(...), db: Session = Depends(get_db)):
    from services.action_bulk_service import bulk_assign_owner

    result = bulk_assign_owner(db, body["action_ids"], body["owner"], actor=body.get("actor", "system"))
    db.commit()
    return result


@router.post("/actions/bulk/update-due-date")
def bulk_due_date(body: dict = Body(...), db: Session = Depends(get_db)):
    from services.action_bulk_service import bulk_update_due_date

    result = bulk_update_due_date(db, body["action_ids"], body["due_date"], actor=body.get("actor", "system"))
    db.commit()
    return result


@router.post("/actions/bulk/update-status")
def bulk_status(body: dict = Body(...), db: Session = Depends(get_db)):
    from services.action_bulk_service import bulk_update_status

    result = bulk_update_status(db, body["action_ids"], body["status"], actor=body.get("actor", "system"))
    db.commit()
    return result
