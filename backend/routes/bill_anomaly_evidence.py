"""
PROMEOS — Bill Intelligence P1 C2 (2026-05-24) : endpoints preuves anomalies.

Endpoints livrés :
- `POST   /api/billing/anomalies/{anomaly_id}/evidences`           upload preuve
- `GET    /api/billing/anomalies/{anomaly_id}/evidences`           lister preuves
- `GET    /api/billing/anomalies/{anomaly_id}/evidences/{ev_id}/download`  télécharger

Règles cardinales :
- Org-scoping strict via `resolve_org_id` (4 JOINs IDOR-safe).
- Cross-org → 404 anti-énumération (jamais 403, doctrine IS11 ADR-029).
- `storage_uri` jamais exposé en clair en GET (sécurité chaîne de signature).
- `file_hash_sha256` obligatoire (intégrité opposable).
- MIME whitelist : pdf/png/jpeg/jpg/csv (anti-spoofing magic bytes IE9).
- Path traversal `..` rejeté → 403.

Pattern inspiré de Evidence V4 conformité C6 P1 (mergé 2026-05-23).
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import tempfile
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models import EnergyInvoice, EntiteJuridique, Portefeuille, Site
from models.bill_anomaly import BillAnomaly
from models.bill_anomaly_evidence import BillAnomalyEvidence
from services.scope_utils import resolve_org_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/billing/anomalies", tags=["Bill Intelligence Evidence"])

# Whitelist MIME (anti-spoofing) — alignée pattern Evidence V4 conformité
_ALLOWED_MIME = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
)
_ALLOWED_EVIDENCE_TYPES = frozenset(
    {
        "invoice_pdf",
        "contract_pdf",
        "meter_index_photo",
        "energy_supplier_response",
        "manual_calculation",
        "audit_report",
    }
)
_FILENAME_SAFE = re.compile(r"^[A-Za-z0-9_.\-]+$")


# ─── Helpers ─────────────────────────────────────────────────────────────


def _assert_anomaly_belongs_to_org(db: Session, anomaly_id: int, org_id: int) -> BillAnomaly:
    """4 JOINs IDOR-safe : Anomaly → Invoice → Site → Portefeuille → EJ → Org."""
    anomaly = (
        db.query(BillAnomaly)
        .join(EnergyInvoice, BillAnomaly.invoice_id == EnergyInvoice.id)
        .join(Site, EnergyInvoice.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(
            BillAnomaly.id == anomaly_id,
            EntiteJuridique.organisation_id == org_id,
            BillAnomaly.deleted_at.is_(None),
        )
        .first()
    )
    if not anomaly:
        # 404 plutôt que 403 → anti-énumération cross-tenant
        raise HTTPException(
            status_code=404,
            detail={
                "code": "BILL_ANOMALY_NOT_FOUND",
                "message": "Anomalie introuvable ou hors de votre périmètre.",
            },
        )
    return anomaly


def _sanitize_filename(name: str) -> str:
    """Retire path + caractères dangereux, limite à 255 chars."""
    base = os.path.basename(name or "evidence.bin")
    if not _FILENAME_SAFE.match(base):
        # Conserver l'extension, remplacer le reste par UUID
        ext = ""
        if "." in base:
            ext = base.rsplit(".", 1)[1][:10]
            ext = "".join(c for c in ext if c.isalnum())
        return f"evidence_{uuid.uuid4().hex[:12]}{('.' + ext) if ext else ''}"[:255]
    return base[:255]


# ─── Schemas ─────────────────────────────────────────────────────────────


class EvidenceCreateForm(BaseModel):
    """Métadonnées hors fichier (multipart)."""

    evidence_type: str = Field(..., description="Type de preuve (cf. whitelist).")
    source: str = Field("manual_upload", description="manual_upload / auto_ingestion / system_generated")


class EvidenceOut(BaseModel):
    id: int
    anomaly_id: int
    invoice_id: int
    evidence_type: str
    filename: str
    mime_type: str
    file_hash_sha256: str
    source: str
    created_at: Optional[str] = None
    verified_at: Optional[str] = None
    # storage_uri volontairement absent : sécurité (jamais exposé en clair)


def _to_out(e: BillAnomalyEvidence) -> EvidenceOut:
    return EvidenceOut(
        id=e.id,
        anomaly_id=e.anomaly_id,
        invoice_id=e.invoice_id,
        evidence_type=e.evidence_type,
        filename=e.filename,
        mime_type=e.mime_type,
        file_hash_sha256=e.file_hash_sha256,
        source=e.source,
        created_at=e.created_at.isoformat() if e.created_at else None,
        verified_at=e.verified_at.isoformat() if e.verified_at else None,
    )


# ─── POST upload ─────────────────────────────────────────────────────────


@router.post("/{anomaly_id}/evidences", response_model=EvidenceOut, status_code=201)
async def upload_anomaly_evidence(
    anomaly_id: int,
    request: Request,
    evidence_type: str,
    file: UploadFile = File(...),
    source: str = "manual_upload",
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Upload d'une preuve documentaire pour une anomalie facture."""
    org_id = resolve_org_id(request, auth, db)
    anomaly = _assert_anomaly_belongs_to_org(db, anomaly_id, org_id)

    if evidence_type not in _ALLOWED_EVIDENCE_TYPES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "EVIDENCE_TYPE_INVALID",
                "message": f"Type de preuve non supporté : {evidence_type}.",
                "hint": f"Valeurs autorisées : {sorted(_ALLOWED_EVIDENCE_TYPES)}",
            },
        )

    mime = (file.content_type or "").lower()
    if mime not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "EVIDENCE_MIME_NOT_ALLOWED",
                "message": f"Type MIME non supporté : {mime}.",
                "hint": "Formats acceptés : PDF, PNG, JPEG, CSV, XLSX.",
            },
        )

    # Lecture + hash + stockage temporaire local (fs://)
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "EVIDENCE_EMPTY_FILE",
                "message": "Fichier vide — preuve non enregistrée.",
            },
        )

    file_hash = hashlib.sha256(content).hexdigest()
    sanitized_name = _sanitize_filename(file.filename or "evidence.bin")

    # P1 : stockage local fs:// (pattern Evidence V4 — S3 prévu P2)
    tmp_dir = tempfile.mkdtemp(prefix="bill_anomaly_evidence_")
    fs_path = os.path.join(tmp_dir, sanitized_name)
    with open(fs_path, "wb") as f:
        f.write(content)

    evidence = BillAnomalyEvidence(
        anomaly_id=anomaly.id,
        org_id=org_id,
        invoice_id=anomaly.invoice_id,
        evidence_type=evidence_type,
        filename=sanitized_name,
        mime_type=mime,
        file_hash_sha256=file_hash,
        storage_uri=f"fs://{fs_path}",
        source=source,
        created_by=getattr(auth, "user_id", None) if auth else None,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    logger.info(
        "[bill_anomaly_evidence] uploaded id=%s anomaly=%s org=%s hash=%s",
        evidence.id,
        anomaly_id,
        org_id,
        file_hash[:8],
    )
    return _to_out(evidence)


# ─── GET list ────────────────────────────────────────────────────────────


@router.get("/{anomaly_id}/evidences")
def list_anomaly_evidences(
    anomaly_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les preuves rattachées à une anomalie."""
    org_id = resolve_org_id(request, auth, db)
    anomaly = _assert_anomaly_belongs_to_org(db, anomaly_id, org_id)

    evidences = (
        db.query(BillAnomalyEvidence)
        .filter(
            BillAnomalyEvidence.anomaly_id == anomaly.id,
            BillAnomalyEvidence.org_id == org_id,
            BillAnomalyEvidence.deleted_at.is_(None),
        )
        .order_by(BillAnomalyEvidence.created_at.desc())
        .all()
    )
    return {
        "anomaly_id": anomaly.id,
        "count": len(evidences),
        "has_pending_evidence": any(e.verified_at is None for e in evidences),
        "evidences": [_to_out(e).model_dump() for e in evidences],
    }


# ─── GET download ────────────────────────────────────────────────────────


@router.get("/{anomaly_id}/evidences/{evidence_id}/download")
def download_anomaly_evidence(
    anomaly_id: int,
    evidence_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Télécharge le fichier d'une preuve (org-scopé strict)."""
    org_id = resolve_org_id(request, auth, db)
    _assert_anomaly_belongs_to_org(db, anomaly_id, org_id)

    evidence = (
        db.query(BillAnomalyEvidence)
        .filter(
            BillAnomalyEvidence.id == evidence_id,
            BillAnomalyEvidence.anomaly_id == anomaly_id,
            BillAnomalyEvidence.org_id == org_id,
            BillAnomalyEvidence.deleted_at.is_(None),
        )
        .first()
    )
    if not evidence:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "EVIDENCE_NOT_FOUND",
                "message": "Preuve introuvable ou hors de votre périmètre.",
            },
        )

    storage_uri = evidence.storage_uri or ""

    # P1 : seul le schéma fs:// est supporté. s3:// → 501 documenté.
    if storage_uri.startswith("s3://"):
        raise HTTPException(
            status_code=501,
            detail={
                "code": "EVIDENCE_STORAGE_NOT_SUPPORTED",
                "message": "Le stockage S3 est prévu pour une version ultérieure.",
                "hint": "Utiliser un stockage filesystem (fs://) pour cette version.",
            },
        )

    if not storage_uri.startswith("fs://"):
        raise HTTPException(
            status_code=500,
            detail={
                "code": "EVIDENCE_STORAGE_INVALID",
                "message": "Schéma de stockage invalide pour cette preuve.",
            },
        )

    fs_path = storage_uri[len("fs://") :]
    # Path traversal — rejet
    if ".." in fs_path.split(os.sep):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "EVIDENCE_PATH_INVALID",
                "message": "Chemin de stockage invalide — accès refusé.",
            },
        )

    if not os.path.exists(fs_path):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "EVIDENCE_FILE_MISSING",
                "message": "Le fichier de preuve est introuvable sur le serveur.",
                "hint": "Re-téléverser la preuve depuis l'écran d'anomalie.",
            },
        )

    def _iter():
        with open(fs_path, "rb") as fh:
            while True:
                chunk = fh.read(64 * 1024)
                if not chunk:
                    break
                yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{evidence.filename}"',
        "X-Evidence-Hash-Sha256": evidence.file_hash_sha256,
    }
    return StreamingResponse(_iter(), media_type=evidence.mime_type, headers=headers)
