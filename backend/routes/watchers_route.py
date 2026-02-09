"""
PROMEOS Routes - Watchers endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from watchers.registry import list_watchers, run_watcher
from models import RegSourceEvent

router = APIRouter(prefix="/api/watchers", tags=["Watchers"])


@router.get("/list")
def watchers_list():
    """Liste tous les watchers."""
    return {"watchers": list_watchers()}


@router.post("/{name}/run")
def trigger_watcher(name: str, db: Session = Depends(get_db)):
    """Declenche un watcher."""
    try:
        events = run_watcher(name, db)
        return {
            "watcher": name,
            "new_events": len(events)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events")
def list_events(
    source: str = Query(None),
    reviewed: bool = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """Liste les evenements reglementaires."""
    query = db.query(RegSourceEvent)

    if source:
        query = query.filter(RegSourceEvent.source_name == source)
    if reviewed is not None:
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
                "review_note": e.review_note
            }
            for e in events
        ],
        "total": len(events)
    }


@router.patch("/events/{event_id}/review")
def review_event(event_id: int, review_note: str = "", db: Session = Depends(get_db)):
    """Marque un evenement comme reviewed."""
    event = db.query(RegSourceEvent).filter(RegSourceEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    event.reviewed = True
    event.review_note = review_note
    db.commit()

    return {"id": event_id, "reviewed": True}
