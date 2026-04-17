"""
PROMEOS — CX Dashboard (usage interne)
GET /api/admin/cx-dashboard — KPIs CX agrégés par org
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import require_permission
from middleware.cx_logger import CX_EVENT_TYPES
from models.iam import AuditLog

router = APIRouter(prefix="/api/admin", tags=["Admin CX"])


@router.get("/cx-dashboard")
def get_cx_dashboard(
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    _auth=Depends(require_permission("admin:read")),
):
    """
    KPIs CX agrégés par org — usage interne PROMEOS.
    Détecte les orgs inactives (aucun event depuis > 10 jours).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    events = (
        db.query(
            AuditLog.resource_id.label("org_id"),
            AuditLog.action.label("event_type"),
            func.count().label("count"),
            func.max(AuditLog.created_at).label("last_at"),
        )
        .filter(
            AuditLog.action.in_(CX_EVENT_TYPES),
            AuditLog.resource_type == "cx_event",
            AuditLog.created_at >= cutoff,
        )
        .group_by(AuditLog.resource_id, AuditLog.action)
        .all()
    )

    # Agrégation par org
    by_org: dict = {}
    for row in events:
        org = by_org.setdefault(row.org_id, {"events": {}, "total": 0, "last_activity": None})
        org["events"][row.event_type] = row.count
        org["total"] += row.count
        if org["last_activity"] is None or (row.last_at and row.last_at > org["last_activity"]):
            org["last_activity"] = row.last_at

    # Détection inactivité
    inactive_threshold = datetime.now(timezone.utc) - timedelta(days=10)
    inactive_orgs = [
        oid for oid, data in by_org.items() if data["last_activity"] and data["last_activity"] < inactive_threshold
    ]

    return {
        "period_days": days,
        "orgs": {
            oid: {
                **data,
                "last_activity": data["last_activity"].isoformat() if data["last_activity"] else None,
            }
            for oid, data in by_org.items()
        },
        "inactive_orgs": inactive_orgs,
        "total_events": sum(d["total"] for d in by_org.values()),
    }
