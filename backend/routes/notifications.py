"""
PROMEOS — Notifications Routes (Sprint 10.2)
6 endpoints: sync, list, summary, patch, preferences, batches.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation,
    NotificationEvent,
    NotificationBatch,
    NotificationPreference,
    NotificationSeverity,
    NotificationStatus,
    NotificationSourceType,
    WebhookSubscription,
    DigestPreference,
)
from services.notification_service import sync_notifications, _count_summary
from services.webhook_service import dispatch_webhooks, build_digest
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import apply_scope_filter
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


# ========================================
# Schemas
# ========================================


class NotifPatch(BaseModel):
    status: Optional[str] = None


class PreferencePatch(BaseModel):
    enable_badges: Optional[bool] = None
    snooze_days: Optional[int] = Field(None, ge=0, le=365)
    thresholds_json: Optional[str] = Field(None, max_length=2000)


# ========================================
# Helpers
# ========================================


def _resolve_org(request: Request, auth: Optional[AuthContext], db: Session, org_id: Optional[int] = None) -> int:
    """Delegate to centralized resolve_org_id (DEMO_MODE-aware)."""
    return resolve_org_id(request, auth, db, org_id_override=org_id)


def _serialize_event(e: NotificationEvent) -> dict:
    return {
        "id": e.id,
        "org_id": e.org_id,
        "site_id": e.site_id,
        "source_type": e.source_type.value if e.source_type else None,
        "source_id": e.source_id,
        "source_key": e.source_key,
        "severity": e.severity.value if e.severity else "info",
        "title": e.title,
        "message": e.message,
        "due_date": e.due_date.isoformat() if e.due_date else None,
        "estimated_impact_eur": e.estimated_impact_eur,
        "deeplink_path": e.deeplink_path,
        "status": e.status.value if e.status else "new",
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


# ========================================
# Endpoints
# ========================================


@router.post("/sync")
def sync_notifs(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """POST /api/notifications/sync — Sync alerts from 5 briques."""
    oid = _resolve_org(request, auth, db, org_id)
    result = sync_notifications(db, oid, triggered_by="api")
    return {"status": "ok", **result}


@router.get("/list")
def list_notifs(
    request: Request,
    org_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """GET /api/notifications/list — Filterable list."""
    oid = _resolve_org(request, auth, db, org_id)

    q = db.query(NotificationEvent).filter(NotificationEvent.org_id == oid)
    q = apply_scope_filter(q, auth, NotificationEvent.site_id)

    if severity:
        try:
            q = q.filter(NotificationEvent.severity == NotificationSeverity(severity))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Severite invalide: {severity}")
    if status:
        try:
            q = q.filter(NotificationEvent.status == NotificationStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {status}")
    if source_type:
        try:
            q = q.filter(NotificationEvent.source_type == NotificationSourceType(source_type))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Source invalide: {source_type}")
    if site_id is not None:
        q = q.filter(NotificationEvent.site_id == site_id)

    events = (
        q.order_by(
            NotificationEvent.severity.desc(),
            NotificationEvent.created_at.desc(),
        )
        .limit(500)
        .all()
    )

    return [_serialize_event(e) for e in events]


@router.get("/summary")
def notif_summary(
    request: Request,
    org_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """GET /api/notifications/summary — Counts by severity + status."""
    oid = _resolve_org(request, auth, db, org_id)
    return _count_summary(db, oid, site_id=site_id)


@router.patch("/{event_id}")
def patch_notif(
    event_id: int,
    data: NotifPatch,
    db: Session = Depends(get_db),
):
    """PATCH /api/notifications/{id} — Mark as read/dismissed."""
    event = db.query(NotificationEvent).filter(NotificationEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Notification non trouvee")

    if data.status is not None:
        try:
            event.status = NotificationStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {data.status}")

    db.commit()
    db.refresh(event)
    return {"result": "updated", **_serialize_event(event)}


@router.get("/preferences")
def get_preferences(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """GET /api/notifications/preferences — Get org notification preferences."""
    oid = _resolve_org(request, auth, db, org_id)
    pref = db.query(NotificationPreference).filter(NotificationPreference.org_id == oid).first()

    if not pref:
        return {
            "org_id": oid,
            "enable_badges": True,
            "snooze_days": 0,
            "thresholds": {"critical_due_days": 30, "warn_due_days": 60},
        }

    thresholds = {"critical_due_days": 30, "warn_due_days": 60}
    if pref.thresholds_json:
        try:
            thresholds = {**thresholds, **json.loads(pref.thresholds_json)}
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "org_id": oid,
        "enable_badges": pref.enable_badges,
        "snooze_days": pref.snooze_days,
        "thresholds": thresholds,
    }


@router.put("/preferences")
def update_preferences(
    request: Request,
    data: PreferencePatch,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """PUT /api/notifications/preferences — Update org notification preferences."""
    oid = _resolve_org(request, auth, db, org_id)
    pref = db.query(NotificationPreference).filter(NotificationPreference.org_id == oid).first()

    if not pref:
        pref = NotificationPreference(org_id=oid)
        db.add(pref)

    if data.enable_badges is not None:
        pref.enable_badges = data.enable_badges
    if data.snooze_days is not None:
        pref.snooze_days = data.snooze_days
    if data.thresholds_json is not None:
        # Validate JSON
        try:
            json.loads(data.thresholds_json)
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="thresholds_json invalide")
        pref.thresholds_json = data.thresholds_json

    db.commit()
    db.refresh(pref)
    return {"status": "updated", "org_id": oid}


@router.get("/batches")
def list_batches(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """GET /api/notifications/batches — Sync history."""
    oid = _resolve_org(request, auth, db, org_id)

    batches = (
        db.query(NotificationBatch)
        .filter(NotificationBatch.org_id == oid)
        .order_by(NotificationBatch.started_at.desc())
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
        }
        for b in batches
    ]


# ── Webhooks (V2) ──────────────────────────────────────────────


class WebhookCreate(BaseModel):
    url: str
    secret: Optional[str] = None
    events_filter: Optional[list[str]] = None


@router.get("/webhooks")
def list_webhooks(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    oid = _resolve_org(request, auth, db, org_id)
    subs = db.query(WebhookSubscription).filter(WebhookSubscription.org_id == oid).all()
    return [
        {
            "id": s.id,
            "url": s.url,
            "active": s.active,
            "events_filter": json.loads(s.events_filter) if s.events_filter else None,
            "failure_count": s.failure_count,
            "last_triggered_at": s.last_triggered_at.isoformat() if s.last_triggered_at else None,
        }
        for s in subs
    ]


@router.post("/webhooks")
def create_webhook(
    body: WebhookCreate,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    oid = _resolve_org(request, auth, db, org_id)
    sub = WebhookSubscription(
        org_id=oid,
        url=body.url,
        secret=body.secret,
        events_filter=json.dumps(body.events_filter) if body.events_filter else None,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {"id": sub.id, "url": sub.url, "active": sub.active}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    sub = db.get(WebhookSubscription, webhook_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Webhook non trouve")
    db.delete(sub)
    db.commit()
    return {"deleted": True}


# ── Digest (V2) ────────────────────────────────────────────────


class DigestUpdate(BaseModel):
    enabled: bool = False
    frequency: str = "daily"
    recipient_emails: Optional[str] = None


@router.get("/digest")
def get_digest_pref(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    oid = _resolve_org(request, auth, db, org_id)
    pref = db.query(DigestPreference).filter(DigestPreference.org_id == oid).first()
    if not pref:
        return {"enabled": False, "frequency": "daily", "recipient_emails": None}
    return {
        "enabled": pref.enabled,
        "frequency": pref.frequency,
        "recipient_emails": pref.recipient_emails,
        "last_sent_at": pref.last_sent_at.isoformat() if pref.last_sent_at else None,
    }


@router.put("/digest")
def update_digest_pref(
    body: DigestUpdate,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    oid = _resolve_org(request, auth, db, org_id)
    pref = db.query(DigestPreference).filter(DigestPreference.org_id == oid).first()
    if not pref:
        pref = DigestPreference(org_id=oid)
        db.add(pref)
    pref.enabled = body.enabled
    pref.frequency = body.frequency
    pref.recipient_emails = body.recipient_emails
    db.commit()
    return {"ok": True}


@router.post("/digest/preview")
def preview_digest(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Preview digest content without marking as sent."""
    oid = _resolve_org(request, auth, db, org_id)
    digest = build_digest(db, oid)
    if not digest:
        return {"message": "Aucune alerte nouvelle pour le digest"}
    return digest
