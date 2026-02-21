"""
PROMEOS — Reports Routes (Sprint 10.1)
GET /api/reports/audit.pdf  - Download audit PDF
GET /api/reports/audit.json - Audit data as JSON
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import Organisation
from services.audit_report_service import build_audit_report_data, render_audit_pdf
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/audit.json")
def get_audit_json(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/reports/audit.json?org_id=
    Retourne les donnees structurees de l'audit.
    """
    oid = resolve_org_id(request, auth, db, org_id_override=org_id)
    data = build_audit_report_data(db, oid)
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])
    return data


@router.get("/audit.pdf")
def get_audit_pdf(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/reports/audit.pdf?org_id=
    Genere et telecharge le rapport d'audit energetique en PDF — org-scoped.
    """
    oid = resolve_org_id(request, auth, db, org_id_override=org_id)
    data = build_audit_report_data(db, oid)
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    pdf_bytes = render_audit_pdf(data)

    org_name = data.get("organisation", {}).get("nom", "promeos")
    safe_name = org_name.replace(" ", "_").replace("/", "_")[:30]
    filename = f"audit_{safe_name}_{data.get('generated_at', '')[:10]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
