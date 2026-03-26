"""
PROMEOS — Action Hub Routes (Sprint 10 + V4.9 + V5.0)
Endpoints: create, sync, list, summary, detail, patch, batches, export CSV.
"""

import csv
import hashlib
import io
from datetime import date as dt_date, datetime, timezone
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation,
    ActionItem,
    ActionSyncBatch,
    ActionSourceType,
    ActionStatus,
    ActionEvent,
    ActionComment,
    ActionEvidence,
    AnomalyActionLink,
    AnomalyDismissal,
    DismissReason,
)
from services.action_hub_service import sync_actions, compute_priority
from services.action_close_rules import is_operat_action, check_closable
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import apply_scope_filter
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/actions", tags=["Actions"])


# ========================================
# Schemas
# ========================================


class ActionCreate(BaseModel):
    """Schema for direct action creation from UI."""

    org_id: Optional[int] = Field(None, ge=1)
    site_id: Optional[int] = Field(None, ge=1)
    campaign_sites: Optional[List[int]] = Field(None, max_length=50)
    source_type: str = "manual"
    source_id: Optional[str] = Field(None, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    rationale: Optional[str] = Field(None, max_length=2000)
    priority: Optional[int] = Field(None, ge=1, le=5)
    severity: Optional[str] = None
    estimated_gain_eur: Optional[float] = Field(None, ge=0, le=1e9)
    due_date: Optional[str] = None
    owner: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=5000)
    idempotency_key: Optional[str] = Field(None, max_length=100)
    co2e_savings_est_kg: Optional[float] = Field(None, ge=0, le=1e9)
    evidence_required: Optional[bool] = None


class ActionPatch(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=5000)
    due_date: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    realized_gain_eur: Optional[float] = Field(None, ge=0, le=1e9)
    realized_at: Optional[str] = None
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    co2e_savings_est_kg: Optional[float] = Field(None, ge=0, le=1e9)
    closure_justification: Optional[str] = Field(None, max_length=2000)  # V49
    evidence_required: Optional[bool] = None


class CommentCreate(BaseModel):
    author: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=5000)


class EvidenceCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=300)
    file_url: Optional[str] = Field(None, max_length=1000)
    mime_type: Optional[str] = Field(None, max_length=100)
    uploaded_by: Optional[str] = Field(None, max_length=200)


# ========================================
# Helpers
# ========================================


def _resolve_org(request: Request, auth: Optional[AuthContext], db: Session, org_id: Optional[int] = None) -> int:
    """Delegate to centralized resolve_org_id (DEMO_MODE-aware)."""
    return resolve_org_id(request, auth, db, org_id_override=org_id)


_SOURCE_LABELS = {
    "compliance": "Conformité",
    "consumption": "Consommation",
    "billing": "Facturation",
    "purchase": "Achats",
    "manual": "Manuelle",
    "insight": "Diagnostic",
    "lever_engine": "Levier",
}


def _source_label(source_type) -> str:
    """FR label for a source type."""
    val = source_type.value if hasattr(source_type, "value") else str(source_type or "")
    return _SOURCE_LABELS.get(val, val)


def _source_deeplink(source_type, source_id) -> str | None:
    """Build a relative URL to navigate back to the source object."""
    val = source_type.value if hasattr(source_type, "value") else str(source_type or "")
    sid = source_id or ""
    if val == "compliance":
        return "/conformite?tab=obligations"
    if val == "billing":
        return "/bill-intel"
    if val == "consumption":
        return "/consommations/explorer"
    if val == "purchase":
        return "/achats"
    if val == "insight":
        if sid.startswith("readiness:"):
            return "/activation"
        if sid.startswith("operat:"):
            parts = sid.split(":")
            efa_id = parts[1] if len(parts) > 1 else None
            return f"/conformite/tertiaire/efa/{efa_id}" if efa_id else "/conformite/tertiaire/efa"
        return "/anomalies"
    if val == "lever_engine":
        return "/actions"
    return None


def _serialize_action(a: ActionItem) -> dict:
    # campaign_sites stored as JSON in notes field prefix "##CAMPAIGN:"
    campaign_sites = None
    if a.notes and a.notes.startswith("##CAMPAIGN:"):
        import json as _json

        try:
            campaign_sites = _json.loads(a.notes.split("##CAMPAIGN:", 1)[1].split("\n", 1)[0])
        except Exception:
            pass

    site_nom = a.site.nom if a.site and hasattr(a.site, "nom") else None

    return {
        "id": a.id,
        "org_id": a.org_id,
        "site_id": a.site_id,
        "site_nom": site_nom,
        "campaign_sites": campaign_sites,
        "source_type": a.source_type.value if a.source_type else None,
        "source_id": a.source_id,
        "source_key": a.source_key,
        "title": a.title,
        "rationale": a.rationale,
        "priority": a.priority,
        "severity": a.severity,
        "estimated_gain_eur": a.estimated_gain_eur,
        "due_date": a.due_date.isoformat() if a.due_date else None,
        "status": a.status.value if a.status else "open",
        "owner": a.owner,
        "notes": a.notes,
        # V5.0 fields
        "category": a.category,
        "description": a.description,
        "realized_gain_eur": a.realized_gain_eur,
        "realized_at": a.realized_at.isoformat() if a.realized_at else None,
        "closed_at": a.closed_at.isoformat() if a.closed_at else None,
        # V9 Decarbonation
        "co2e_savings_est_kg": a.co2e_savings_est_kg,
        # V49
        "closure_justification": a.closure_justification,
        # Etape 4: Evidence gate
        "evidence_required": a.evidence_required,
        # Étape 4.1: Source tracing
        "source_label": _source_label(a.source_type),
        "source_deeplink": _source_deeplink(a.source_type, a.source_id),
        # Timestamps
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "updated_at": a.updated_at.isoformat() if a.updated_at else None,
    }


def _create_event(
    db: Session, action_id: int, event_type: str, actor: str = "system", old_value: str = None, new_value: str = None
):
    """Insert an audit trail event."""
    event = ActionEvent(
        action_id=action_id,
        event_type=event_type,
        actor=actor,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(event)
    return event


# ========================================
# Endpoints
# ========================================


@router.post("")
def create_action(
    request: Request,
    data: ActionCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    POST /api/actions
    Create a single action from the UI (manual or insight-driven).
    Supports idempotency_key and collision detection.
    """
    oid = _resolve_org(request, auth, db, data.org_id)

    # Idempotency: if key provided and action exists, return existing
    if data.idempotency_key:
        existing = db.query(ActionItem).filter(ActionItem.idempotency_key == data.idempotency_key).first()
        if existing:
            return {"status": "existing", **_serialize_action(existing)}

    # Validate source_type
    try:
        source_type = ActionSourceType(data.source_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Source invalide: {data.source_type}")

    if source_type not in (ActionSourceType.MANUAL, ActionSourceType.INSIGHT):
        raise HTTPException(
            status_code=400,
            detail="Creation directe: source_type doit etre 'manual' ou 'insight'",
        )

    # Validate title
    if not data.title or not data.title.strip():
        raise HTTPException(status_code=422, detail="Titre requis")

    # Parse due_date
    parsed_due = None
    if data.due_date:
        try:
            parsed_due = dt_date.fromisoformat(data.due_date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Date invalide: {data.due_date}")

    # Validate priority
    if data.priority is not None and not (1 <= data.priority <= 5):
        raise HTTPException(status_code=400, detail="Priorite doit etre entre 1 et 5")

    # Auto-compute priority if absent
    priority = data.priority
    if priority is None:
        priority = compute_priority(data.severity, data.estimated_gain_eur, parsed_due)

    # Collision detection: similar title + same site within 24h
    warning = None
    similar_id = None
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    similar = (
        db.query(ActionItem)
        .filter(
            ActionItem.title == data.title.strip()[:500],
            ActionItem.site_id == data.site_id,
            ActionItem.created_at >= cutoff,
        )
        .first()
    )
    if similar:
        warning = "similar_action_exists"
        similar_id = similar.id

    # Generate source_key for uniqueness
    source_id = data.source_id or f"manual_{int(datetime.now(timezone.utc).timestamp())}"
    source_key = hashlib.sha256(f"{data.title}:{source_id}".encode()).hexdigest()[:16]

    # Encode campaign_sites into notes prefix (no schema migration needed)
    import json as _json

    notes = data.notes or ""
    if data.campaign_sites:
        notes = f"##CAMPAIGN:{_json.dumps(data.campaign_sites)}\n{notes}"

    item = ActionItem(
        org_id=oid,
        site_id=data.site_id,
        source_type=source_type,
        source_id=source_id,
        source_key=source_key,
        title=data.title.strip()[:500],
        rationale=data.rationale,
        priority=priority,
        severity=data.severity,
        estimated_gain_eur=data.estimated_gain_eur,
        due_date=parsed_due,
        status=ActionStatus.OPEN,
        owner=data.owner,
        notes=notes,
        idempotency_key=data.idempotency_key,
        co2e_savings_est_kg=data.co2e_savings_est_kg,
        evidence_required=data.evidence_required or False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    # Auto-event: created
    _create_event(db, item.id, "created", new_value="open")
    db.commit()

    result = {"status": "created", **_serialize_action(item)}
    if warning:
        result["warning"] = warning
        result["similar_id"] = similar_id
    return result


@router.post("/sync")
def sync_action_hub(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    POST /api/actions/sync?org_id=
    Synchronise actions depuis les 4 briques. Idempotent.
    """
    oid = _resolve_org(request, auth, db, org_id)
    result = sync_actions(db, oid, triggered_by="api")
    return {"status": "ok", **result}


@router.get("/list")
def list_actions(
    request: Request,
    org_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    priority: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/actions/list?org_id=&status=&source_type=&priority=&site_id=
    Liste filtrable des actions.
    """
    oid = _resolve_org(request, auth, db, org_id)

    q = db.query(ActionItem).filter(ActionItem.org_id == oid)

    # Scope filtering: restrict to accessible sites
    if auth and auth.site_ids is not None:
        q = q.filter(ActionItem.site_id.in_(auth.site_ids))

    if status:
        # Support comma-separated multi-status: ?status=backlog,planned,in_progress
        raw_statuses = [s.strip() for s in status.split(",") if s.strip()]
        try:
            enum_statuses = [ActionStatus(s) for s in raw_statuses]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {status}")
        if len(enum_statuses) == 1:
            q = q.filter(ActionItem.status == enum_statuses[0])
        else:
            q = q.filter(ActionItem.status.in_(enum_statuses))
    if source_type:
        try:
            q = q.filter(ActionItem.source_type == ActionSourceType(source_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Source invalide: {source_type}")
    if priority is not None:
        q = q.filter(ActionItem.priority == priority)
    if site_id is not None:
        q = q.filter(ActionItem.site_id == site_id)

    actions = q.order_by(ActionItem.priority.asc()).limit(500).all()
    return [_serialize_action(a) for a in actions]


@router.get("/summary")
def actions_summary(
    request: Request,
    org_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/actions/summary?org_id=&site_id=
    Statistiques: counts par status, top 5 prioritaires, by_source.
    """
    oid = _resolve_org(request, auth, db, org_id)

    q = db.query(ActionItem).filter(ActionItem.org_id == oid)
    q = apply_scope_filter(q, auth, ActionItem.site_id)
    if site_id is not None:
        q = q.filter(ActionItem.site_id == site_id)
    items = q.all()

    counts = {"open": 0, "in_progress": 0, "done": 0, "blocked": 0, "false_positive": 0, "total": 0}
    by_source = {}
    total_gain = 0.0

    for a in items:
        st = a.status.value if a.status else "open"
        counts[st] = counts.get(st, 0) + 1
        counts["total"] += 1

        src = a.source_type.value if a.source_type else "unknown"
        by_source[src] = by_source.get(src, 0) + 1

        if a.estimated_gain_eur and a.status != ActionStatus.DONE:
            total_gain += a.estimated_gain_eur

    # Top 5 open by priority
    open_items = [a for a in items if a.status in (ActionStatus.OPEN, ActionStatus.IN_PROGRESS)]
    open_items.sort(key=lambda a: (a.priority or 5, a.due_date or "9999-12-31"))
    top5 = [_serialize_action(a) for a in open_items[:5]]

    return {
        "counts": counts,
        "by_source": by_source,
        "total_gain_eur": round(total_gain, 2),
        "top5": top5,
    }


@router.patch("/{action_id}")
def patch_action(
    action_id: int,
    data: ActionPatch,
    db: Session = Depends(get_db),
):
    """
    PATCH /api/actions/{action_id}
    Workflow update: status, owner, notes, due_date, priority.
    Auto-creates audit events for each changed field.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvee")

    # V49: store closure_justification before status check (needed for closability)
    if data.closure_justification is not None:
        action.closure_justification = data.closure_justification

    if data.status is not None:
        old_status = action.status.value if action.status else "open"
        try:
            new_status = ActionStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {data.status}")
        if old_status != data.status:
            # V49 + Etape 4: Enforce close rules (OPERAT + evidence_required)
            if new_status == ActionStatus.DONE:
                ev_count = db.query(ActionEvidence).filter(ActionEvidence.action_id == action_id).count()
                result = check_closable(action, data.closure_justification, evidence_count=ev_count)
                if not result["closable"]:
                    raise HTTPException(
                        status_code=400,
                        detail={"code": result.get("code", "CLOSE_BLOCKED"), "message": result["reason"]},
                    )

            action.status = new_status
            _create_event(db, action.id, "status_change", old_value=old_status, new_value=data.status)
            # Set closed_at when action is marked done
            if new_status == ActionStatus.DONE and action.closed_at is None:
                action.closed_at = datetime.now(timezone.utc)

    if data.owner is not None:
        old_owner = action.owner
        if old_owner != data.owner:
            action.owner = data.owner
            _create_event(db, action.id, "assigned", old_value=old_owner, new_value=data.owner)

    if data.notes is not None:
        action.notes = data.notes

    if data.due_date is not None:
        try:
            action.due_date = dt_date.fromisoformat(data.due_date)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Date invalide: {data.due_date}")

    if data.priority is not None:
        if not 1 <= data.priority <= 5:
            raise HTTPException(status_code=400, detail="Priorite doit etre entre 1 et 5")
        old_prio = action.priority
        if old_prio != data.priority:
            action.priority = data.priority
            _create_event(db, action.id, "priority_change", old_value=str(old_prio), new_value=str(data.priority))

    # V5.0: ROI + metadata fields
    if data.realized_gain_eur is not None:
        old_val = action.realized_gain_eur
        action.realized_gain_eur = data.realized_gain_eur
        if old_val != data.realized_gain_eur:
            _create_event(
                db,
                action.id,
                "realized_updated",
                old_value=str(old_val) if old_val else None,
                new_value=str(data.realized_gain_eur),
            )

    if data.realized_at is not None:
        try:
            action.realized_at = dt_date.fromisoformat(data.realized_at)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Date invalide: {data.realized_at}")

    if data.category is not None:
        action.category = data.category

    if data.description is not None:
        action.description = data.description

    if data.co2e_savings_est_kg is not None:
        action.co2e_savings_est_kg = data.co2e_savings_est_kg

    if data.evidence_required is not None:
        action.evidence_required = data.evidence_required

    db.commit()
    db.refresh(action)
    return {"status": "updated", **_serialize_action(action)}


@router.get("/batches")
def list_batches(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/actions/batches?org_id=
    Historique des synchronisations.
    """
    oid = _resolve_org(request, auth, db, org_id)

    batches = (
        db.query(ActionSyncBatch)
        .filter(ActionSyncBatch.org_id == oid)
        .order_by(ActionSyncBatch.started_at.desc())
        .all()
    )

    return [
        {
            "id": b.id,
            "org_id": b.org_id,
            "triggered_by": b.triggered_by,
            "started_at": b.started_at.isoformat() if b.started_at else None,
            "finished_at": b.finished_at.isoformat() if b.finished_at else None,
            "created_count": b.created_count,
            "updated_count": b.updated_count,
            "skipped_count": b.skipped_count,
            "closed_count": b.closed_count,
        }
        for b in batches
    ]


@router.get("/export.csv")
def export_csv(
    request: Request,
    org_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/actions/export.csv?org_id=&status=&source_type=
    Export CSV des actions — scope-filtered.
    """
    oid = _resolve_org(request, auth, db, org_id)

    q = db.query(ActionItem).filter(ActionItem.org_id == oid)
    q = apply_scope_filter(q, auth, ActionItem.site_id)
    if status:
        raw_statuses = [s.strip() for s in status.split(",") if s.strip()]
        try:
            enum_statuses = [ActionStatus(s) for s in raw_statuses]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {status}")
        if len(enum_statuses) == 1:
            q = q.filter(ActionItem.status == enum_statuses[0])
        else:
            q = q.filter(ActionItem.status.in_(enum_statuses))
    if source_type:
        try:
            q = q.filter(ActionItem.source_type == ActionSourceType(source_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Source invalide: {source_type}")

    actions = q.order_by(ActionItem.priority.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "id",
            "source",
            "titre",
            "priorite",
            "severite",
            "gain_eur",
            "echeance",
            "statut",
            "responsable",
            "notes",
        ]
    )
    for a in actions:
        writer.writerow(
            [
                a.id,
                a.source_type.value if a.source_type else "",
                a.title,
                a.priority,
                a.severity or "",
                a.estimated_gain_eur or "",
                a.due_date.isoformat() if a.due_date else "",
                a.status.value if a.status else "",
                a.owner or "",
                a.notes or "",
            ]
        )

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=actions_promeos.csv"},
    )


# ========================================
# ROI Summary
# ========================================


@router.get("/roi_summary")
def roi_summary(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/actions/roi_summary?org_id=
    Aggregate ROI: estimated vs realized gains.
    """
    oid = _resolve_org(request, auth, db, org_id)

    q = db.query(ActionItem).filter(ActionItem.org_id == oid)
    q = apply_scope_filter(q, auth, ActionItem.site_id)
    items = q.all()

    total_estimated = 0.0
    total_realized = 0.0
    actions_with_realized = 0
    by_source = {}
    by_category = {}

    for a in items:
        # Exclude false positives from totals
        if a.status == ActionStatus.FALSE_POSITIVE:
            continue

        est = a.estimated_gain_eur or 0.0
        real = a.realized_gain_eur or 0.0
        total_estimated += est
        total_realized += real
        if a.realized_gain_eur and a.realized_gain_eur > 0:
            actions_with_realized += 1

        # by_source breakdown
        src = a.source_type.value if a.source_type else "unknown"
        if src not in by_source:
            by_source[src] = {"estimated": 0.0, "realized": 0.0, "count": 0}
        by_source[src]["estimated"] += est
        by_source[src]["realized"] += real
        by_source[src]["count"] += 1

        # by_category breakdown
        cat = a.category or "non_classe"
        if cat not in by_category:
            by_category[cat] = {"estimated": 0.0, "realized": 0.0, "count": 0}
        by_category[cat]["estimated"] += est
        by_category[cat]["realized"] += real
        by_category[cat]["count"] += 1

    roi_ratio = round(total_realized / total_estimated, 4) if total_estimated > 0 else 0.0

    # Top 5 actions by realized gain
    realized_items = [a for a in items if a.realized_gain_eur and a.realized_gain_eur > 0]
    realized_items.sort(key=lambda a: a.realized_gain_eur, reverse=True)
    top_roi = [_serialize_action(a) for a in realized_items[:5]]

    return {
        "total_estimated_eur": round(total_estimated, 2),
        "total_realized_eur": round(total_realized, 2),
        "roi_ratio": roi_ratio,
        "actions_with_realized": actions_with_realized,
        "by_source": {
            k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in by_source.items()
        },
        "by_category": {
            k: {kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}
            for k, v in by_category.items()
        },
        "top_roi_actions": top_roi,
    }


# ========================================
# Sub-resource endpoints: comments, evidence, events
# ========================================


@router.post("/{action_id}/comments")
def add_comment(
    action_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
):
    """
    POST /api/actions/{action_id}/comments
    Add a comment to an action.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvee")

    if not data.body or not data.body.strip():
        raise HTTPException(status_code=422, detail="Contenu du commentaire requis")
    if not data.author or not data.author.strip():
        raise HTTPException(status_code=422, detail="Auteur requis")

    comment = ActionComment(
        action_id=action_id,
        author=data.author.strip(),
        body=data.body.strip(),
    )
    db.add(comment)

    # Auto-event
    _create_event(db, action_id, "commented", actor=data.author.strip(), new_value=data.body.strip()[:200])

    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "action_id": comment.action_id,
        "author": comment.author,
        "body": comment.body,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


@router.get("/{action_id}/comments")
def list_comments(
    action_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/actions/{action_id}/comments
    List comments for an action, ordered by creation date.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvee")

    comments = (
        db.query(ActionComment)
        .filter(ActionComment.action_id == action_id)
        .order_by(ActionComment.created_at.asc())
        .all()
    )
    return [
        {
            "id": c.id,
            "action_id": c.action_id,
            "author": c.author,
            "body": c.body,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in comments
    ]


@router.post("/{action_id}/evidence")
def add_evidence(
    action_id: int,
    data: EvidenceCreate,
    db: Session = Depends(get_db),
):
    """
    POST /api/actions/{action_id}/evidence
    Add an evidence/attachment reference to an action.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvee")

    if not data.label or not data.label.strip():
        raise HTTPException(status_code=422, detail="Libelle de la piece requis")

    evidence = ActionEvidence(
        action_id=action_id,
        label=data.label.strip(),
        file_url=data.file_url,
        mime_type=data.mime_type,
        uploaded_by=data.uploaded_by,
    )
    db.add(evidence)

    # Auto-event
    _create_event(db, action_id, "evidence_added", actor=data.uploaded_by, new_value=data.label.strip())

    db.commit()
    db.refresh(evidence)

    return {
        "id": evidence.id,
        "action_id": evidence.action_id,
        "label": evidence.label,
        "file_url": evidence.file_url,
        "mime_type": evidence.mime_type,
        "uploaded_by": evidence.uploaded_by,
        "created_at": evidence.created_at.isoformat() if evidence.created_at else None,
    }


@router.get("/{action_id}/evidence")
def list_evidence(
    action_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/actions/{action_id}/evidence
    List evidence items for an action.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvee")

    items = (
        db.query(ActionEvidence)
        .filter(ActionEvidence.action_id == action_id)
        .order_by(ActionEvidence.created_at.asc())
        .all()
    )
    return [
        {
            "id": e.id,
            "action_id": e.action_id,
            "label": e.label,
            "file_url": e.file_url,
            "mime_type": e.mime_type,
            "uploaded_by": e.uploaded_by,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in items
    ]


@router.get("/{action_id}/events")
def list_events(
    action_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/actions/{action_id}/events
    Audit trail for an action.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvee")

    events = (
        db.query(ActionEvent).filter(ActionEvent.action_id == action_id).order_by(ActionEvent.created_at.asc()).all()
    )
    return [
        {
            "id": e.id,
            "action_id": e.action_id,
            "event_type": e.event_type,
            "actor": e.actor,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


# ========================================
# V49: Action closeability check
# ========================================


@router.get("/{action_id}/closeability")
def get_action_closeability(action_id: int, db: Session = Depends(get_db)):
    """
    GET /api/actions/{action_id}/closeability
    Returns whether this action can be closed and why/why not.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvée")

    ev_count = db.query(ActionEvidence).filter(ActionEvidence.action_id == action_id).count()
    result = check_closable(action, evidence_count=ev_count)
    result["is_operat"] = is_operat_action(action)
    result["evidence_required"] = getattr(action, "evidence_required", False)
    result["evidence_count"] = ev_count
    return result


# ========================================
# V48: Action ↔ Proof persistence endpoints
# ========================================


@router.get("/{action_id}/proofs")
def get_action_proofs(action_id: int, db: Session = Depends(get_db)):
    """
    GET /api/actions/{action_id}/proofs
    List all KB docs linked to this action + summary.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvée")

    try:
        from app.kb.store import KBStore

        kb_store = KBStore()
        return kb_store.list_action_proofs(action_id)
    except Exception:
        # KB store not available — return empty (backward compat)
        return {"docs": [], "summary": {"total": 0, "draft": 0, "review": 0, "validated": 0, "decisional": 0}}


@router.post("/{action_id}/proofs/{kb_doc_id}")
def link_proof_to_action(
    action_id: int,
    kb_doc_id: str,
    db: Session = Depends(get_db),
):
    """
    POST /api/actions/{action_id}/proofs/{kb_doc_id}
    Manually link an existing KB doc to an action. Idempotent.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvée")

    try:
        from app.kb.store import KBStore

        kb_store = KBStore()
        result = kb_store.link_doc_to_action(action_id, kb_doc_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("detail", "Erreur lors du rattachement"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur KB: {str(e)}")


# ========================================
# Detail endpoint (after fixed-path routes to avoid conflict)
# ========================================


@router.get("/{action_id}")
def get_action_detail(
    action_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/actions/{action_id}
    Full detail with sub-resource counts.
    """
    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action non trouvee")

    comments_count = db.query(ActionComment).filter(ActionComment.action_id == action_id).count()
    evidence_count = db.query(ActionEvidence).filter(ActionEvidence.action_id == action_id).count()
    events_count = db.query(ActionEvent).filter(ActionEvent.action_id == action_id).count()

    # Include linked anomalies
    links = db.query(AnomalyActionLink).filter(AnomalyActionLink.action_id == action_id).all()

    return {
        **_serialize_action(action),
        "comments_count": comments_count,
        "evidence_count": evidence_count,
        "events_count": events_count,
        "anomaly_links": [
            {
                "id": lk.id,
                "anomaly_source": lk.anomaly_source,
                "anomaly_ref": lk.anomaly_ref,
                "site_id": lk.site_id,
                "link_reason": lk.link_reason,
                "created_at": lk.created_at.isoformat() if lk.created_at else None,
            }
            for lk in links
        ],
    }


# ========================================
# V117: Anomaly ↔ Action Link
# ========================================


class AnomalyLinkCreate(BaseModel):
    """Create action from anomaly + link them."""

    anomaly_source: str = Field(..., description="patrimoine, billing, monitoring")
    anomaly_ref: str = Field(..., description="Anomaly code or insight ID")
    site_id: Optional[int] = None
    action_id: Optional[int] = Field(None, description="Link to existing action")
    # Fields for creating a new action (if action_id is None)
    title: Optional[str] = None
    severity: Optional[str] = None
    estimated_gain_eur: Optional[float] = None
    due_date: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    link_reason: Optional[str] = None
    idempotency_key: Optional[str] = None


@router.post("/anomaly-links")
def create_anomaly_action_link(
    request: Request,
    data: AnomalyLinkCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    POST /api/actions/anomaly-links
    Create an action from an anomaly (or link to existing) + create explicit link.
    Returns the action + link.
    """
    oid = _resolve_org(request, auth, db)
    actor = auth.email if auth else "system"

    action_id = data.action_id

    if action_id is None:
        # Check idempotency first
        if data.idempotency_key:
            existing = db.query(ActionItem).filter(ActionItem.idempotency_key == data.idempotency_key).first()
            if existing:
                action_id = existing.id
                # Check if link already exists
                existing_link = (
                    db.query(AnomalyActionLink)
                    .filter(
                        AnomalyActionLink.anomaly_source == data.anomaly_source,
                        AnomalyActionLink.anomaly_ref == data.anomaly_ref,
                        AnomalyActionLink.site_id == data.site_id,
                        AnomalyActionLink.action_id == action_id,
                    )
                    .first()
                )
                if existing_link:
                    return {
                        "status": "existing",
                        "action": _serialize_action(existing),
                        "link_id": existing_link.id,
                    }

        if action_id is None:
            # Create new action
            action = ActionItem(
                org_id=oid,
                site_id=data.site_id,
                source_type=ActionSourceType.INSIGHT,
                source_id=data.anomaly_ref,
                source_key=f"{data.anomaly_source}:{data.anomaly_ref}:{data.site_id or 0}",
                title=data.title or f"Action pour anomalie {data.anomaly_ref}",
                severity=data.severity or "medium",
                estimated_gain_eur=data.estimated_gain_eur,
                due_date=dt_date.fromisoformat(data.due_date) if data.due_date else None,
                owner=data.owner,
                notes=data.notes,
                status=ActionStatus.OPEN,
                priority=compute_priority(
                    data.severity or "medium",
                    data.estimated_gain_eur or 0,
                    dt_date.fromisoformat(data.due_date) if data.due_date else None,
                ),
                idempotency_key=data.idempotency_key,
            )
            db.add(action)
            db.flush()
            action_id = action.id
            _create_event(db, action_id, "created", actor=actor)

    # Create link (idempotent)
    existing_link = (
        db.query(AnomalyActionLink)
        .filter(
            AnomalyActionLink.anomaly_source == data.anomaly_source,
            AnomalyActionLink.anomaly_ref == data.anomaly_ref,
            AnomalyActionLink.site_id == data.site_id,
            AnomalyActionLink.action_id == action_id,
        )
        .first()
    )
    if not existing_link:
        link = AnomalyActionLink(
            anomaly_source=data.anomaly_source,
            anomaly_ref=data.anomaly_ref,
            site_id=data.site_id,
            action_id=action_id,
            link_reason=data.link_reason,
            created_by=actor,
        )
        db.add(link)
        _create_event(
            db,
            action_id,
            "anomaly_linked",
            actor=actor,
            new_value=f"{data.anomaly_source}:{data.anomaly_ref}",
        )
        db.commit()
        link_id = link.id
        status = "created"
    else:
        db.commit()
        link_id = existing_link.id
        status = "existing"

    action = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    return {
        "status": status,
        "action": _serialize_action(action),
        "link_id": link_id,
    }


class AnomalyDismissCreate(BaseModel):
    """Dismiss an anomaly with a required reason."""

    anomaly_source: str
    anomaly_ref: str
    site_id: Optional[int] = None
    reason_code: str = Field(..., description="false_positive, known_issue, out_of_scope, duplicate, other")
    reason_text: Optional[str] = None


@router.post("/anomaly-dismiss")
def dismiss_anomaly(
    data: AnomalyDismissCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    POST /api/actions/anomaly-dismiss
    Dismiss an anomaly with required reason_code.
    """
    actor = auth.email if auth else "system"

    # Validate reason_code
    try:
        reason = DismissReason(data.reason_code)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"reason_code invalide: {data.reason_code}. Valeurs: {[r.value for r in DismissReason]}",
        )

    # Upsert dismissal (idempotent)
    existing = (
        db.query(AnomalyDismissal)
        .filter(
            AnomalyDismissal.anomaly_source == data.anomaly_source,
            AnomalyDismissal.anomaly_ref == data.anomaly_ref,
            AnomalyDismissal.site_id == data.site_id,
        )
        .first()
    )
    if existing:
        existing.reason_code = reason
        existing.reason_text = data.reason_text
        existing.dismissed_by = actor
        existing.dismissed_at = datetime.now(timezone.utc)
        db.commit()
        return {"status": "updated", "id": existing.id}

    dismissal = AnomalyDismissal(
        anomaly_source=data.anomaly_source,
        anomaly_ref=data.anomaly_ref,
        site_id=data.site_id,
        reason_code=reason,
        reason_text=data.reason_text,
        dismissed_by=actor,
    )
    db.add(dismissal)
    db.commit()
    return {"status": "created", "id": dismissal.id}


class AnomalyStatusQuery(BaseModel):
    """Query statuses for a batch of anomalies."""

    anomalies: list = Field(..., description="List of {anomaly_source, anomaly_ref, site_id}")


@router.post("/anomaly-statuses")
def get_anomaly_statuses(
    data: AnomalyStatusQuery,
    db: Session = Depends(get_db),
):
    """
    POST /api/actions/anomaly-statuses
    Batch query: for each anomaly, return linked actions + dismissal status.
    """
    results = []
    for anom in data.anomalies:
        source = anom.get("anomaly_source", "")
        ref = anom.get("anomaly_ref", "")
        site_id = anom.get("site_id")

        # Find linked actions
        links = (
            db.query(AnomalyActionLink)
            .filter(
                AnomalyActionLink.anomaly_source == source,
                AnomalyActionLink.anomaly_ref == ref,
                AnomalyActionLink.site_id == site_id,
            )
            .all()
        )

        linked_actions = []
        for lk in links:
            action = db.query(ActionItem).filter(ActionItem.id == lk.action_id).first()
            if action:
                linked_actions.append(
                    {
                        "id": action.id,
                        "title": action.title,
                        "status": action.status.value if action.status else None,
                    }
                )

        # Check dismissal
        dismissal = (
            db.query(AnomalyDismissal)
            .filter(
                AnomalyDismissal.anomaly_source == source,
                AnomalyDismissal.anomaly_ref == ref,
                AnomalyDismissal.site_id == site_id,
            )
            .first()
        )

        status = "open"
        if dismissal:
            status = "dismissed"
        elif linked_actions:
            all_done = all(a["status"] == "done" for a in linked_actions)
            status = "resolved" if all_done else "linked"

        results.append(
            {
                "anomaly_source": source,
                "anomaly_ref": ref,
                "site_id": site_id,
                "status": status,
                "linked_actions": linked_actions,
                "dismissal": {
                    "reason_code": dismissal.reason_code.value if dismissal else None,
                    "reason_text": dismissal.reason_text if dismissal else None,
                    "dismissed_by": dismissal.dismissed_by if dismissal else None,
                }
                if dismissal
                else None,
            }
        )

    return {"statuses": results}
