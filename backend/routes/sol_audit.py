"""
PROMEOS — Sol V1 audit trail routes (Phase 4)

- GET  /api/sol/audit          — paginated list des SolActionLog org-scoped
- GET  /api/sol/audit/export   — export CSV anti-injection
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models.sol import SolActionLog
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/sol/audit", tags=["Sol V1 audit"])
logger = logging.getLogger("promeos.sol")


class SolActionLogDTO(BaseModel):
    id: int
    correlation_id: str
    intent_kind: str
    action_phase: str
    outcome_code: Optional[str] = None
    outcome_message: Optional[str] = None
    confidence: Optional[float] = None
    created_at: datetime


class AuditListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[SolActionLogDTO]


# Caractères leading dangereux pour injection formulas Excel/Google Sheets
_CSV_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_escape(value: object) -> str:
    """
    Anti-CSV-injection : préfixe un `'` (apostrophe) devant les valeurs
    commençant par =, +, -, @, TAB ou CR pour neutraliser l'évaluation
    formula dans Excel / LibreOffice / Google Sheets.

    Standard OWASP CSV injection.
    """
    if value is None:
        return ""
    s = str(value)
    if s and s[0] in _CSV_INJECTION_PREFIXES:
        return "'" + s
    return s


@router.get("", response_model=AuditListResponse)
async def list_audit(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action_phase: Optional[str] = None,
    intent_kind: Optional[str] = None,
) -> AuditListResponse:
    """Liste paginée du trail d'audit Sol, strictement org-scoped."""
    org_id = resolve_org_id(request, auth, db)

    q = db.query(SolActionLog).filter(SolActionLog.org_id == org_id)
    if action_phase:
        q = q.filter(SolActionLog.action_phase == action_phase)
    if intent_kind:
        q = q.filter(SolActionLog.intent_kind == intent_kind)

    total = q.count()
    rows = q.order_by(SolActionLog.id.desc()).offset(offset).limit(limit).all()

    items = [
        SolActionLogDTO(
            id=r.id,
            correlation_id=r.correlation_id,
            intent_kind=r.intent_kind,
            action_phase=r.action_phase,
            outcome_code=r.outcome_code,
            outcome_message=r.outcome_message,
            confidence=float(r.confidence) if r.confidence is not None else None,
            created_at=r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=timezone.utc),
        )
        for r in rows
    ]
    return AuditListResponse(total=total, limit=limit, offset=offset, items=items)


@router.get("/export")
async def export_audit_csv(
    request: Request,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
    db: Session = Depends(get_db),
    action_phase: Optional[str] = None,
    intent_kind: Optional[str] = None,
) -> StreamingResponse:
    """
    Export CSV du trail d'audit, org-scoped strict.
    Anti-CSV-injection appliqué sur chaque cellule (OWASP).
    """
    org_id = resolve_org_id(request, auth, db)

    q = db.query(SolActionLog).filter(SolActionLog.org_id == org_id)
    if action_phase:
        q = q.filter(SolActionLog.action_phase == action_phase)
    if intent_kind:
        q = q.filter(SolActionLog.intent_kind == intent_kind)
    rows = q.order_by(SolActionLog.id.desc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(
        [
            "id",
            "correlation_id",
            "intent_kind",
            "action_phase",
            "outcome_code",
            "outcome_message",
            "confidence",
            "created_at",
        ]
    )
    for r in rows:
        writer.writerow(
            [
                _csv_escape(r.id),
                _csv_escape(r.correlation_id),
                _csv_escape(r.intent_kind),
                _csv_escape(r.action_phase),
                _csv_escape(r.outcome_code),
                _csv_escape(r.outcome_message),
                _csv_escape(f"{float(r.confidence):.2f}" if r.confidence is not None else ""),
                _csv_escape(r.created_at.isoformat() if r.created_at else ""),
            ]
        )

    buf.seek(0)
    filename = f"sol_audit_org{org_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
