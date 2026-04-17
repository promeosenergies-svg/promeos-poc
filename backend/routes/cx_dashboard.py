"""
PROMEOS — CX Dashboard (usage interne)
GET /api/admin/cx-dashboard       — KPIs CX agrégés par org (vue générale)
GET /api/admin/cx-dashboard/t2v   — Time-to-Value (délai account → 1ʳᵉ action validée)
GET /api/admin/cx-dashboard/iar   — Insight-to-Action Rate (actions validées / findings consultés)
GET /api/admin/cx-dashboard/wau-mau — Stickiness WAU/MAU (users actifs 7j / 30j)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import require_permission
from middleware.cx_logger import CX_EVENT_TYPES
from models.iam import AuditLog, User

router = APIRouter(prefix="/api/admin", tags=["Admin CX"])

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _percentile(sorted_values: list[float], p: float) -> Optional[float]:
    if not sorted_values:
        return None
    k = (len(sorted_values) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if lo == hi:
        return sorted_values[lo]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (k - lo)


# ─────────────────────────────────────────────────────────────────────────────
# Vue générale (existant)
# ─────────────────────────────────────────────────────────────────────────────


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

    by_org: dict = {}
    for row in events:
        org = by_org.setdefault(row.org_id, {"events": {}, "total": 0, "last_activity": None})
        org["events"][row.event_type] = row.count
        org["total"] += row.count
        if org["last_activity"] is None or (row.last_at and row.last_at > org["last_activity"]):
            org["last_activity"] = row.last_at

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


# ─────────────────────────────────────────────────────────────────────────────
# Driver 1 : Time-to-Value
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/cx-dashboard/t2v")
def get_t2v(
    days: int = Query(180, le=365, description="Fenêtre d'observation"),
    db: Session = Depends(get_db),
    _auth=Depends(require_permission("admin:read")),
):
    """
    Time-to-Value = délai entre création compte user et 1ʳᵉ action validée.

    Signal considéré comme "value delivered" : event CX_ACTION_FROM_INSIGHT
    (une action passée au statut DONE dans /api/actions).

    Retourne p50, p90, p95 en jours + nombre de users mesurés.
    Un user sans action validée n'est pas dans l'échantillon (T2V non mesurable).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    first_action = (
        db.query(
            AuditLog.user_id.label("user_id"),
            AuditLog.resource_id.label("org_id"),
            func.min(AuditLog.created_at).label("first_action_at"),
        )
        .filter(
            AuditLog.action == "CX_ACTION_FROM_INSIGHT",
            AuditLog.resource_type == "cx_event",
            AuditLog.user_id.isnot(None),
            AuditLog.created_at >= cutoff,
        )
        .group_by(AuditLog.user_id, AuditLog.resource_id)
        .subquery()
    )

    rows = (
        db.query(
            User.id.label("user_id"),
            User.created_at.label("user_created_at"),
            first_action.c.org_id,
            first_action.c.first_action_at,
        )
        .join(first_action, first_action.c.user_id == User.id)
        .all()
    )

    deltas_days: list[float] = []
    per_org: dict[str, list[float]] = {}
    for r in rows:
        if r.user_created_at is None or r.first_action_at is None:
            continue
        user_ref = r.user_created_at
        if user_ref.tzinfo is None:
            user_ref = user_ref.replace(tzinfo=timezone.utc)
        action_ref = r.first_action_at
        if action_ref.tzinfo is None:
            action_ref = action_ref.replace(tzinfo=timezone.utc)
        delta = (action_ref - user_ref).total_seconds() / 86400.0
        if delta < 0:
            continue  # incohérence : action antérieure au user (backfill)
        deltas_days.append(delta)
        per_org.setdefault(str(r.org_id), []).append(delta)

    deltas_days.sort()

    return {
        "period_days": days,
        "sample_size": len(deltas_days),
        "p50_days": _percentile(deltas_days, 0.5),
        "p90_days": _percentile(deltas_days, 0.9),
        "p95_days": _percentile(deltas_days, 0.95),
        "by_org": {
            org_id: {
                "sample_size": len(vals),
                "p50_days": _percentile(sorted(vals), 0.5),
                "p95_days": _percentile(sorted(vals), 0.95),
            }
            for org_id, vals in per_org.items()
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Driver 2 : Insight-to-Action Rate
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/cx-dashboard/iar")
def get_iar(
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
    _auth=Depends(require_permission("admin:read")),
):
    """
    Insight-to-Action Rate = actions validées / insights consultés sur la période.

    Numérateur : CX_ACTION_FROM_INSIGHT
    Dénominateur : CX_INSIGHT_CONSULTED

    Retourne le ratio global + décomposition par org.
    Ratio "null" si dénominateur=0 (pas assez de signal).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    counts = (
        db.query(
            AuditLog.resource_id.label("org_id"),
            AuditLog.action.label("event_type"),
            func.count().label("n"),
        )
        .filter(
            AuditLog.action.in_({"CX_INSIGHT_CONSULTED", "CX_ACTION_FROM_INSIGHT"}),
            AuditLog.resource_type == "cx_event",
            AuditLog.created_at >= cutoff,
        )
        .group_by(AuditLog.resource_id, AuditLog.action)
        .all()
    )

    by_org: dict[str, dict[str, int]] = {}
    for row in counts:
        org = by_org.setdefault(row.org_id, {"insights": 0, "actions": 0})
        if row.event_type == "CX_INSIGHT_CONSULTED":
            org["insights"] = row.n
        else:
            org["actions"] = row.n

    def _ratio(actions: int, insights: int) -> Optional[float]:
        if insights <= 0:
            return None
        return round(actions / insights, 4)

    global_insights = sum(d["insights"] for d in by_org.values())
    global_actions = sum(d["actions"] for d in by_org.values())

    return {
        "period_days": days,
        "global": {
            "insights_consulted": global_insights,
            "actions_validated": global_actions,
            "iar": _ratio(global_actions, global_insights),
        },
        "by_org": {
            oid: {
                "insights_consulted": d["insights"],
                "actions_validated": d["actions"],
                "iar": _ratio(d["actions"], d["insights"]),
            }
            for oid, d in by_org.items()
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Driver 3 : WAU / MAU
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/cx-dashboard/wau-mau")
def get_wau_mau(
    db: Session = Depends(get_db),
    _auth=Depends(require_permission("admin:read")),
):
    """
    WAU/MAU stickiness ratio.

    WAU = users distincts avec ≥1 event CX_* sur 7 derniers jours
    MAU = users distincts avec ≥1 event CX_* sur 30 derniers jours
    Ratio = WAU / MAU (plus c'est haut, plus les users reviennent souvent)

    Seuil de référence marché B2B SaaS : 20-30% = normal, 40%+ = excellent.
    """
    now = datetime.now(timezone.utc)

    wau_cutoff = now - timedelta(days=7)
    mau_cutoff = now - timedelta(days=30)

    def _distinct_users(since: datetime) -> int:
        return (
            db.query(func.count(distinct(AuditLog.user_id)))
            .filter(
                AuditLog.action.in_(CX_EVENT_TYPES),
                AuditLog.resource_type == "cx_event",
                AuditLog.user_id.isnot(None),
                AuditLog.created_at >= since,
            )
            .scalar()
            or 0
        )

    wau = _distinct_users(wau_cutoff)
    mau = _distinct_users(mau_cutoff)
    ratio = round(wau / mau, 4) if mau > 0 else None

    return {
        "as_of": now.isoformat(),
        "wau": wau,
        "mau": mau,
        "stickiness_ratio": ratio,
        "interpretation": (
            "excellent"
            if ratio is not None and ratio >= 0.4
            else "bon"
            if ratio is not None and ratio >= 0.3
            else "à travailler"
            if ratio is not None and ratio >= 0.2
            else "faible"
            if ratio is not None
            else "signal insuffisant"
        ),
    }
