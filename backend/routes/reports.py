"""
PROMEOS — Reports Routes (Sprint 10.1)
GET /api/reports/audit.pdf  - Download audit PDF
GET /api/reports/audit.json - Audit data as JSON
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from models import Organisation
from services.audit_report_service import build_audit_report_data, render_audit_pdf
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import get_effective_org_id

router = APIRouter(prefix="/api/reports", tags=["Reports"])


def _resolve_org_id(db: Session, org_id: Optional[int], auth: Optional[AuthContext] = None) -> int:
    effective = get_effective_org_id(auth, org_id)
    if effective is not None:
        return effective
    org = db.query(Organisation).first()
    if not org:
        raise HTTPException(status_code=400, detail="Aucune organisation trouvee.")
    return org.id


@router.get("/audit.json")
def get_audit_json(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/reports/audit.json?org_id=
    Retourne les donnees structurees de l'audit.
    """
    oid = _resolve_org_id(db, org_id, auth)
    data = build_audit_report_data(db, oid)
    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])
    return data


@router.get("/audit.pdf")
def get_audit_pdf(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/reports/audit.pdf?org_id=
    Genere et telecharge le rapport d'audit energetique en PDF — org-scoped.
    """
    oid = _resolve_org_id(db, org_id, auth)
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
