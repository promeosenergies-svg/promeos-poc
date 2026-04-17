"""
PROMEOS — OPERAT Export routes
POST /api/operat/export          — generate OPERAT CSV + manifest + audit log
POST /api/operat/export/preview  — preview export data (JSON)
POST /api/operat/export/validate — validate before export
GET  /api/operat/export-manifests — historique des exports
GET  /api/operat/export-manifests/{id} — detail d'un manifest
"""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import get_effective_org_id
from models.operat_export_manifest import OperatExportManifest
from models.compliance_event_log import ComplianceEventLog
from services.operat_export_service import generate_operat_csv, log_operat_export, validate_operat_export

router = APIRouter(prefix="/api/operat", tags=["operat-export"])


class ExportRequest(BaseModel):
    org_id: int
    year: int
    efa_ids: Optional[List[int]] = None
    actor: Optional[str] = None


def _build_manifest(db, org_id, year, csv_content, filename, efa_ids=None, actor="system"):
    """Cree un manifest d'export avec checksum et metadonnees tracabilite."""
    from services.operat_trajectory import validate_trajectory, _reliability_for_source
    from models import TertiaireEfa, TertiaireEfaConsumption, not_deleted

    checksum = hashlib.sha256(csv_content.encode("utf-8")).hexdigest()
    efa_count = csv_content.count("\n") - 1

    # Recuperer les metadonnees du premier EFA pour le manifest
    baseline_year = baseline_kwh = current_kwh = None
    baseline_source = current_source = baseline_rel = current_rel = None
    trajectory_status = None
    evidence_warnings = []

    query = db.query(TertiaireEfa).filter(TertiaireEfa.org_id == org_id, not_deleted(TertiaireEfa))
    if efa_ids:
        query = query.filter(TertiaireEfa.id.in_(efa_ids))
    first_efa = query.first()

    if first_efa:
        ref = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == first_efa.id, TertiaireEfaConsumption.is_reference.is_(True))
            .first()
        )
        cur = (
            db.query(TertiaireEfaConsumption)
            .filter(TertiaireEfaConsumption.efa_id == first_efa.id, TertiaireEfaConsumption.year == year)
            .first()
        )
        if ref:
            baseline_year = ref.year
            baseline_kwh = ref.kwh_total
            baseline_source = ref.source
            baseline_rel = _reliability_for_source(ref.source)
        if cur:
            current_kwh = cur.kwh_total
            current_source = cur.source
            current_rel = _reliability_for_source(cur.source)

        trajectory_status = first_efa.trajectory_status

        if baseline_rel and baseline_rel in ("low", "unverified"):
            evidence_warnings.append(f"Baseline fiabilite {baseline_rel}")
        if current_rel and current_rel in ("low", "unverified"):
            evidence_warnings.append(f"Conso courante fiabilite {current_rel}")
        if not ref:
            evidence_warnings.append("Consommation de reference absente")

    manifest = OperatExportManifest(
        efa_id=first_efa.id if first_efa else None,
        org_id=org_id,
        actor=actor or "system",
        file_name=filename,
        checksum_sha256=checksum,
        observation_year=year,
        baseline_year=baseline_year,
        baseline_kwh=baseline_kwh,
        current_kwh=current_kwh,
        baseline_source=baseline_source,
        current_source=current_source,
        baseline_reliability=baseline_rel,
        current_reliability=current_rel,
        trajectory_status=trajectory_status,
        efa_count=max(0, efa_count),
        evidence_warnings_json=json.dumps(evidence_warnings) if evidence_warnings else None,
        # Hardening
        retention_until=datetime.now(timezone.utc) + timedelta(days=5 * 365),  # 5 ans
        archive_status="active",
        weather_provider=ref.source if ref and hasattr(ref, "source") else None,
        baseline_normalization_status=first_efa.baseline_normalization_status
        if first_efa and hasattr(first_efa, "baseline_normalization_status")
        else None,
        promeos_version="2.0",
    )
    db.add(manifest)
    db.flush()

    # Event log
    db.add(
        ComplianceEventLog(
            entity_type="OperatExportManifest",
            entity_id=manifest.id,
            action="export_generate",
            after_json=json.dumps(
                {
                    "file_name": filename,
                    "checksum": checksum,
                    "efa_count": max(0, efa_count),
                    "year": year,
                    "trajectory_status": trajectory_status,
                }
            ),
            actor=actor or "system",
            source_context="api_export",
        )
    )
    db.flush()

    return manifest


@router.post("/export")
def export_operat_csv_route(
    body: ExportRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Generate OPERAT-compatible CSV + manifest + audit log."""
    effective_org_id = get_effective_org_id(auth, body.org_id)
    csv_content = generate_operat_csv(db, effective_org_id, body.year, body.efa_ids)
    filename = f"OPERAT_PREPARATOIRE_{body.org_id}_{body.year}.csv"

    # Legacy audit log
    efa_count = csv_content.count("\n") - 1
    log_operat_export(db, effective_org_id, body.year, max(0, efa_count))

    # Manifest + event log (actor depuis body ou fallback)
    from services.actor_resolver import resolve_actor

    actor = body.actor or resolve_actor(fallback="api_export")
    manifest = _build_manifest(db, effective_org_id, body.year, csv_content, filename, body.efa_ids, actor)
    db.commit()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-PROMEOS-Submission-Type": "simulation_preparatoire",
            "X-PROMEOS-Disclaimer": "Pack preparatoire — aucun depot ADEME/OPERAT reel effectue",
            "X-PROMEOS-Manifest-Id": str(manifest.id),
            "X-PROMEOS-Checksum-SHA256": manifest.checksum_sha256,
        },
    )


@router.post("/export/preview")
def preview_operat_export(
    body: ExportRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Preview OPERAT export data without downloading (returns JSON)."""
    effective_org_id = get_effective_org_id(auth, body.org_id)
    csv_content = generate_operat_csv(db, effective_org_id, body.year, body.efa_ids)
    lines = csv_content.strip().split("\n")
    header = lines[0].split(";") if lines else []
    rows = []
    for line in lines[1:]:
        vals = line.split(";")
        rows.append(dict(zip(header, vals)))
    return {
        "year": body.year,
        "efa_count": len(rows),
        "columns": header,
        "rows": rows,
        "is_real_submission": False,
        "submission_type": "simulation_preparatoire",
        "disclaimer": "Pack preparatoire — aucun depot ADEME/OPERAT reel effectue.",
    }


@router.post("/export/validate")
def validate_export(
    body: ExportRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Validate OPERAT export data — returns errors (blocking) + warnings."""
    effective_org_id = get_effective_org_id(auth, body.org_id)
    return validate_operat_export(db, effective_org_id, body.year, body.efa_ids)


# ═══════════════════════════════════════════════════════════════════════
# EXPORT MANIFESTS — historique + detail
# ═══════════════════════════════════════════════════════════════════════


@router.get("/export-manifests")
def list_export_manifests(
    org_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Historique des exports preparatoires OPERAT pour une organisation."""
    effective_org_id = get_effective_org_id(auth, org_id)
    rows = (
        db.query(OperatExportManifest)
        .filter(OperatExportManifest.org_id == effective_org_id)
        .order_by(OperatExportManifest.generated_at.desc())
        .limit(50)
        .all()
    )
    return {
        "count": len(rows),
        "manifests": [_manifest_to_dict(m) for m in rows],
    }


@router.get("/export-manifests/{manifest_id}")
def get_export_manifest(
    manifest_id: int,
    db: Session = Depends(get_db),
):
    """Detail d'un manifest d'export OPERAT."""
    m = db.query(OperatExportManifest).filter(OperatExportManifest.id == manifest_id).first()
    if not m:
        raise HTTPException(404, "Manifest introuvable")
    return _manifest_to_dict(m)


def _manifest_to_dict(m):
    return {
        "id": m.id,
        "efa_id": m.efa_id,
        "org_id": m.org_id,
        "generated_at": m.generated_at.isoformat() if m.generated_at else None,
        "actor": m.actor,
        "file_name": m.file_name,
        "checksum_sha256": m.checksum_sha256,
        "observation_year": m.observation_year,
        "baseline_year": m.baseline_year,
        "baseline_kwh": m.baseline_kwh,
        "current_kwh": m.current_kwh,
        "baseline_source": m.baseline_source,
        "current_source": m.current_source,
        "baseline_reliability": m.baseline_reliability,
        "current_reliability": m.current_reliability,
        "trajectory_status": m.trajectory_status,
        "efa_count": m.efa_count,
        "evidence_warnings": json.loads(m.evidence_warnings_json) if m.evidence_warnings_json else [],
        "export_version": m.export_version,
        "retention_until": m.retention_until.isoformat() if getattr(m, "retention_until", None) else None,
        "archive_status": getattr(m, "archive_status", "active"),
        "weather_provider": getattr(m, "weather_provider", None),
        "baseline_normalization_status": getattr(m, "baseline_normalization_status", None),
        "promeos_version": getattr(m, "promeos_version", "1.0"),
    }
