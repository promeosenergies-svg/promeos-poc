"""
PROMEOS Routes - Watchers endpoints
Pipeline: NEW -> REVIEWED -> APPLIED | DISMISSED
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
from watchers.registry import list_watchers, run_watcher
from models import RegSourceEvent, WatcherEventStatus

router = APIRouter(prefix="/api/watchers", tags=["Watchers"])


class ReviewBody(BaseModel):
    decision: str  # "apply" | "dismiss"
    notes: Optional[str] = ""


@router.get("/list")
def watchers_list():
    """Liste tous les watchers."""
    return {"watchers": list_watchers()}


@router.post("/{name}/run")
def trigger_watcher(name: str, db: Session = Depends(get_db)):
    """Declenche un watcher."""
    try:
        events = run_watcher(name, db)
        return {"watcher": name, "new_events": len(events)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
def list_events(
    source: str = Query(None),
    reviewed: bool = Query(None),
    status: str = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    """Liste les evenements reglementaires avec filtre status."""
    query = db.query(RegSourceEvent)

    if source:
        query = query.filter(RegSourceEvent.source_name == source)

    # Status filter (new pipeline)
    if status:
        try:
            status_enum = WatcherEventStatus(status)
            query = query.filter(RegSourceEvent.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    elif reviewed is not None:
        # Legacy filter
        query = query.filter(RegSourceEvent.reviewed == reviewed)

    events = query.order_by(RegSourceEvent.retrieved_at.desc()).limit(limit).all()

    return {
        "events": [
            {
                "id": e.id,
                "source_name": e.source_name,
                "title": e.title,
                "url": e.url,
                "snippet": e.snippet,
                "tags": e.tags,
                "published_at": e.published_at.isoformat() if e.published_at else None,
                "retrieved_at": e.retrieved_at.isoformat(),
                "reviewed": e.reviewed,
                "review_note": e.review_note,
                "status": e.status.value if e.status else "new",
                "dedup_key": e.dedup_key,
                "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None,
                "reviewed_by": e.reviewed_by,
                "applied_at": e.applied_at.isoformat() if e.applied_at else None,
            }
            for e in events
        ],
        "total": len(events),
    }


@router.get("/events/{event_id}")
def get_event_detail(event_id: int, db: Session = Depends(get_db)):
    """Detail d'un evenement avec audit trail."""
    event = db.query(RegSourceEvent).filter(RegSourceEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "id": event.id,
        "source_name": event.source_name,
        "title": event.title,
        "url": event.url,
        "snippet": event.snippet,
        "tags": event.tags,
        "content_hash": event.content_hash,
        "dedup_key": event.dedup_key,
        "published_at": event.published_at.isoformat() if event.published_at else None,
        "retrieved_at": event.retrieved_at.isoformat(),
        "status": event.status.value if event.status else "new",
        "reviewed": event.reviewed,
        "review_note": event.review_note,
        "reviewed_at": event.reviewed_at.isoformat() if event.reviewed_at else None,
        "reviewed_by": event.reviewed_by,
        "applied_at": event.applied_at.isoformat() if event.applied_at else None,
        "diff_summary": event.diff_summary,
    }


@router.patch("/events/{event_id}/review")
def review_event(
    event_id: int,
    body: ReviewBody = None,
    review_note: str = "",
    db: Session = Depends(get_db),
):
    """Review an event: apply or dismiss."""
    event = db.query(RegSourceEvent).filter(RegSourceEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    now = datetime.now(timezone.utc)

    if body and body.decision:
        decision = body.decision
        notes = body.notes or ""
    else:
        # Legacy: simple review (backward compat)
        decision = "apply"
        notes = review_note

    if decision == "dismiss":
        event.status = WatcherEventStatus.DISMISSED
        event.reviewed = True
        event.review_note = notes
        event.reviewed_at = now
    elif decision == "apply":
        event.status = WatcherEventStatus.REVIEWED
        event.reviewed = True
        event.review_note = notes
        event.reviewed_at = now
    else:
        raise HTTPException(status_code=400, detail=f"Invalid decision: {decision}")

    db.commit()

    return {
        "id": event_id,
        "status": event.status.value,
        "reviewed": event.reviewed,
        "reviewed_at": event.reviewed_at.isoformat() if event.reviewed_at else None,
    }
