"""
PROMEOS — Action Hub Routes (Sprint 10 + V4.9 + V5.0)
Endpoints: create, sync, list, summary, detail, patch, batches, export CSV.
"""
import csv
import hashlib
import io
from datetime import date as dt_date, datetime
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation, ActionItem, ActionSyncBatch,
    ActionSourceType, ActionStatus,
    ActionEvent, ActionComment, ActionEvidence,
)
from services.action_hub_service import sync_actions, compute_priority
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import apply_scope_filter

router = APIRouter(prefix="/api/actions", tags=["Actions"])


# ========================================
# Schemas
# ========================================

class ActionCreate(BaseModel):
    """Schema for direct action creation from UI."""
    org_id: Optional[int] = None
    site_id: Optional[int] = None
    source_type: str = "manual"
    source_id: Optional[str] = None
    title: str
    rationale: Optional[str] = None
    priority: Optional[int] = None
    severity: Optional[str] = None
    estimated_gain_eur: Optional[float] = None
    due_date: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


class ActionPatch(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[int] = None


class CommentCreate(BaseModel):
    author: str
    body: str


class EvidenceCreate(BaseModel):
    label: str
    file_url: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_by: Optional[str] = None


# ========================================
# Helpers
# ========================================

def _resolve_org_id(db: Session, org_id: Optional[int], auth: Optional[AuthContext] = None) -> int:
    if auth:
        return auth.org_id
    if org_id is not None:
        return org_id
    org = db.query(Organisation).first()
    if not org:
        raise HTTPException(status_code=400, detail="Aucune organisation trouvee.")
    return org.id


def _serialize_action(a: ActionItem) -> dict:
    return {
        "id": a.id,
        "org_id": a.org_id,
        "site_id": a.site_id,
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
    }


def _create_event(db: Session, action_id: int, event_type: str, actor: str = "system",
                   old_value: str = None, new_value: str = None):
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
    data: ActionCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    POST /api/actions
    Create a single action from the UI (manual or insight-driven).
    Supports idempotency_key and collision detection.
    """
    oid = _resolve_org_id(db, data.org_id, auth)

    # Idempotency: if key provided and action exists, return existing
    if data.idempotency_key:
        existing = (
            db.query(ActionItem)
            .filter(ActionItem.idempotency_key == data.idempotency_key)
            .first()
        )
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
    cutoff = datetime.utcnow() - timedelta(hours=24)
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
    source_id = data.source_id or f"manual_{int(datetime.utcnow().timestamp())}"
    source_key = hashlib.sha256(
        f"{data.title}:{source_id}".encode()
    ).hexdigest()[:16]

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
        notes=data.notes,
        idempotency_key=data.idempotency_key,
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
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    POST /api/actions/sync?org_id=
    Synchronise actions depuis les 4 briques. Idempotent.
    """
    oid = _resolve_org_id(db, org_id)
    result = sync_actions(db, oid, triggered_by="api")
    return {"status": "ok", **result}


@router.get("/list")
def list_actions(
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
    oid = _resolve_org_id(db, org_id, auth)

    q = db.query(ActionItem).filter(ActionItem.org_id == oid)

    # Scope filtering: restrict to accessible sites
    if auth and auth.site_ids is not None:
        q = q.filter(ActionItem.site_id.in_(auth.site_ids))

    if status:
        try:
            q = q.filter(ActionItem.status == ActionStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {status}")
    if source_type:
        try:
            q = q.filter(ActionItem.source_type == ActionSourceType(source_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Source invalide: {source_type}")
    if priority is not None:
        q = q.filter(ActionItem.priority == priority)
    if site_id is not None:
        q = q.filter(ActionItem.site_id == site_id)

    actions = q.order_by(ActionItem.priority.asc()).all()
    return [_serialize_action(a) for a in actions]


@router.get("/summary")
def actions_summary(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/actions/summary?org_id=
    Statistiques: counts par status, top 5 prioritaires, by_source.
    """
    oid = _resolve_org_id(db, org_id, auth)

    q = db.query(ActionItem).filter(ActionItem.org_id == oid)
    q = apply_scope_filter(q, auth, ActionItem.site_id)
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

    if data.status is not None:
        old_status = action.status.value if action.status else "open"
        try:
            new_status = ActionStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {data.status}")
        if old_status != data.status:
            action.status = new_status
            _create_event(db, action.id, "status_change", old_value=old_status, new_value=data.status)
            # Set closed_at when action is marked done
            if new_status == ActionStatus.DONE and action.closed_at is None:
                action.closed_at = datetime.utcnow()

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

    db.commit()
    db.refresh(action)
    return {"status": "updated", **_serialize_action(action)}


@router.get("/batches")
def list_batches(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/actions/batches?org_id=
    Historique des synchronisations.
    """
    oid = _resolve_org_id(db, org_id, auth)

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
    oid = _resolve_org_id(db, org_id, auth)

    q = db.query(ActionItem).filter(ActionItem.org_id == oid)
    q = apply_scope_filter(q, auth, ActionItem.site_id)
    if status:
        try:
            q = q.filter(ActionItem.status == ActionStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {status}")
    if source_type:
        try:
            q = q.filter(ActionItem.source_type == ActionSourceType(source_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Source invalide: {source_type}")

    actions = q.order_by(ActionItem.priority.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "id", "source", "titre", "priorite", "severite",
        "gain_eur", "echeance", "statut", "responsable", "notes",
    ])
    for a in actions:
        writer.writerow([
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
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=actions_promeos.csv"},
    )


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
        db.query(ActionEvent)
        .filter(ActionEvent.action_id == action_id)
        .order_by(ActionEvent.created_at.asc())
        .all()
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

    return {
        **_serialize_action(action),
        "comments_count": comments_count,
        "evidence_count": evidence_count,
        "events_count": events_count,
    }
