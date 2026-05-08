"""
PROMEOS — Phase F3.2 (ADR-F-03) : endpoint REST parser PDF contrat.

`POST /api/contracts/parse-pdf` — preview parsing 8 champs cardinaux + bridge
Fournisseur Phase F1, sans persistance auto. UX onboarding contrat :
1. User upload PDF contrat signé
2. Backend retourne dict pré-rempli + confidence
3. Frontend affiche formulaire avec valeurs extraites
4. User valide → POST /api/billing/contracts (existant) crée EnergyContract

Pattern Phase E IDOR : `resolve_org_id` + scope_org_id passé au resolver.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from services.contract_pdf_parser import parse_contract_pdf_bytes
from services.scope_utils import resolve_org_id


router = APIRouter(prefix="/api/contracts", tags=["Contracts Parsing"])


@router.post("/parse-pdf")
async def parse_contract_pdf(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Preview parsing PDF contrat (8 champs cardinaux + Fournisseur F1 résolu).

    Phase F3 (ADR-F-03) — pas de persistance auto, frontend valide avant CREATE
    EnergyContract via endpoint billing existant.

    Phase F3 P1 fix code-reviewer : opération READ-only logique → pas de
    `require_write_access` (n'exclut pas VIEWER/AUDITEUR du preview).
    Le scope_org_id reste résolu pour pattern Phase E IDOR.

    Returns:
        dict : 8 champs extraits + fournisseur_id résolu + confidence + fields_extracted
    """
    scope_org_id = resolve_org_id(request, auth, db)

    fname = (file.filename or "").lower()
    if not fname.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF trop volumineux (max 20 Mo)")

    result = parse_contract_pdf_bytes(content, db, scope_org_id=scope_org_id)
    return {
        "status": "parsed",
        "filename": file.filename or "",
        **result.to_dict(),
    }
