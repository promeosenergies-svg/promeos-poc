"""
PROMEOS - Patrimoine Staging routes.
Import, quality gate, corrections, activation, sync, demo loader, mapping preview.
"""

import csv
import io
import json
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from models import (
    StagingBatch,
    StagingSite,
    StagingCompteur,
    QualityFinding,
    ImportSourceType,
    StagingStatus,
    QualityRuleSeverity,
    ActivationLog,
    ActivationLogStatus,
)
from services.patrimoine_service import (
    create_staging_batch,
    import_csv_to_staging,
    import_invoices_to_staging,
    get_staging_summary,
    run_quality_gate,
    apply_fix,
    activate_batch,
    get_diff_plan,
    compute_content_hash,
    abandon_batch,
    match_staging_to_existing,
)
from services.import_mapping import (
    CANONICAL_COLUMNS,
    generate_csv_template,
    generate_xlsx_template,
    map_headers,
    detect_encoding,
    detect_delimiter,
    normalize_column_name,
    get_mapping_report,
)
from middleware.auth import get_optional_auth, AuthContext

from routes.patrimoine._helpers import (
    _get_org_id,
    _check_batch_org,
    _check_portfolio_belongs_to_org,
    _normalize_compteur_type,
    _parse_excel_to_staging,
    FixRequest,
    BulkFixRequest,
    ActivateRequest,
    InvoiceImportRequest,
    MappingPreviewRequest,
)

router = APIRouter(tags=["Patrimoine"])


# ========================================
# Template download
# ========================================


@router.get("/import/template")
def import_template(
    format: str = Query("xlsx", description="xlsx or csv"),
):
    """Download official patrimoine import template."""
    if format == "csv":
        content = generate_csv_template()
        return StreamingResponse(
            io.BytesIO(content),
            media_type="text/csv; charset=utf-8-sig",
            headers={"Content-Disposition": "attachment; filename=template_patrimoine.csv"},
        )
    else:
        try:
            content = generate_xlsx_template()
        except ImportError:
            raise HTTPException(status_code=500, detail="openpyxl not installed — Excel template unavailable")
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=template_patrimoine.xlsx"},
        )


@router.get("/import/template/columns")
def import_template_columns():
    """List canonical template columns with metadata."""
    return {
        "columns": CANONICAL_COLUMNS,
        "delimiter": ";",
        "encoding": "utf-8",
        "notes": [
            "Seule la colonne 'nom' est obligatoire.",
            "Les noms de colonnes sont flexibles (synonymes auto-detectes).",
            "delivery_code = PRM (elec) ou PCE (gaz), 14 chiffres.",
        ],
    }


# ========================================
# Import endpoints
# ========================================


@router.post("/staging/import")
async def staging_import(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Query("import", description="express, import, assiste, demo, update"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Import CSV/Excel file into staging pipeline.

    Performs: encoding detection, header mapping, normalization, dedup check.
    """
    org_id = _get_org_id(request, auth, db)

    content = await file.read()
    content_hash = compute_content_hash(content)

    # Detect source type
    filename = file.filename or ""
    if filename.endswith((".xlsx", ".xls")):
        source_type = ImportSourceType.EXCEL
    else:
        source_type = ImportSourceType.CSV

    # Check for duplicate import (same content hash, same org)
    existing = (
        db.query(StagingBatch)
        .filter(
            StagingBatch.content_hash == content_hash,
            StagingBatch.org_id == org_id,
            StagingBatch.status != StagingStatus.ABANDONED,
        )
        .first()
    )
    if existing:
        summary = get_staging_summary(db, existing.id)
        return {
            "batch_id": existing.id,
            "duplicate": True,
            "detail": "File already imported",
            **summary,
        }

    batch = create_staging_batch(
        db=db,
        org_id=org_id,
        user_id=auth.user.id if auth else None,
        source_type=source_type,
        mode=mode,
        filename=filename,
        content_hash=content_hash,
    )

    # Detect header mapping for the response
    mapping_info = None
    if source_type == ImportSourceType.EXCEL:
        try:
            result = _parse_excel_to_staging(db, batch.id, content)
        except ImportError:
            raise HTTPException(status_code=400, detail="openpyxl not installed — Excel import unavailable")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel parse error: {e}")
    else:
        # Detect mapping from CSV headers
        encoding = detect_encoding(content)
        text = content.decode(encoding)
        first_line = text.split("\n")[0].strip()
        delimiter = detect_delimiter(first_line)
        raw_headers = [h.strip() for h in first_line.split(delimiter)]
        header_mapping, mapping_warnings = map_headers(raw_headers)
        mapping_info = {
            "mapping": {k: v for k, v in header_mapping.items() if k != v},
            "warnings": mapping_warnings,
            "encoding": encoding,
            "delimiter": delimiter,
        }
        result = import_csv_to_staging(db, batch.id, content)

    # Step 35: auto-match for update mode
    if mode == "update" and org_id:
        matching = match_staging_to_existing(db, batch.id, org_id)
        db.commit()
        response = {
            "batch_id": batch.id,
            "duplicate": False,
            "mode": "update",
            "matching": matching,
            **result,
        }
    else:
        db.commit()
        response = {
            "batch_id": batch.id,
            "duplicate": False,
            **result,
        }

    if mapping_info:
        response["mapping"] = mapping_info

    return response


@router.post("/staging/import-invoices")
def staging_import_invoices(
    request: Request,
    body: InvoiceImportRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Import sites/meters from invoice metadata into staging."""
    org_id = _get_org_id(request, auth, db)

    batch = create_staging_batch(
        db=db,
        org_id=org_id,
        user_id=auth.user.id if auth else None,
        source_type=ImportSourceType.INVOICE,
        mode="assiste",
    )

    result = import_invoices_to_staging(db, batch.id, {"invoices": body.invoices})
    db.commit()

    return {
        "batch_id": batch.id,
        **result,
    }


# ========================================
# Quality gate & corrections
# ========================================


@router.get("/staging/{batch_id}/summary")
def staging_summary(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get staging batch summary stats."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)
    try:
        return get_staging_summary(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/staging/{batch_id}/rows")
def staging_rows(
    batch_id: int,
    request: Request,
    status: Optional[str] = Query(None, description="ok, error, skipped"),
    q: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List staging rows (sites + linked compteurs) with pagination & search."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)

    query = db.query(StagingSite).filter(StagingSite.batch_id == batch_id)

    # Filter by status
    if status == "skipped":
        query = query.filter(StagingSite.skip.is_(True))
    elif status == "ok":
        query = query.filter(StagingSite.skip.is_(False))
    elif status == "error":
        # Sites with unresolved findings
        error_site_ids = (
            db.query(QualityFinding.staging_site_id)
            .filter(
                QualityFinding.batch_id == batch_id,
                QualityFinding.resolved.is_(False),
                QualityFinding.staging_site_id.isnot(None),
            )
            .distinct()
            .all()
        )
        error_ids = [r[0] for r in error_site_ids]
        query = query.filter(StagingSite.id.in_(error_ids)) if error_ids else query.filter(False)

    # Search
    if q:
        search = f"%{q}%"
        query = query.filter(
            (StagingSite.nom.ilike(search))
            | (StagingSite.adresse.ilike(search))
            | (StagingSite.ville.ilike(search))
            | (StagingSite.siret.ilike(search))
        )

    total = query.count()
    sites = query.order_by(StagingSite.row_number).offset((page - 1) * page_size).limit(page_size).all()

    # Get findings indexed by staging_site_id
    all_findings = (
        db.query(QualityFinding)
        .filter(
            QualityFinding.batch_id == batch_id,
            QualityFinding.resolved.is_(False),
        )
        .all()
    )
    site_findings = {}
    for f in all_findings:
        if f.staging_site_id:
            site_findings.setdefault(f.staging_site_id, []).append(f)

    rows = []
    for ss in sites:
        compteurs = (
            db.query(StagingCompteur)
            .filter(
                StagingCompteur.staging_site_id == ss.id,
            )
            .all()
        )

        findings_for_site = site_findings.get(ss.id, [])

        rows.append(
            {
                "id": ss.id,
                "row_number": ss.row_number,
                "nom": ss.nom,
                "adresse": ss.adresse,
                "code_postal": ss.code_postal,
                "ville": ss.ville,
                "surface_m2": ss.surface_m2,
                "type_site": ss.type_site,
                "siret": ss.siret,
                "naf_code": ss.naf_code,
                "skip": ss.skip,
                "target_site_id": ss.target_site_id,
                "issues_count": len(findings_for_site),
                "compteurs": [
                    {
                        "id": sc.id,
                        "row_number": sc.row_number,
                        "numero_serie": sc.numero_serie,
                        "meter_id": sc.meter_id,
                        "type_compteur": sc.type_compteur,
                        "puissance_kw": sc.puissance_kw,
                        "skip": sc.skip,
                    }
                    for sc in compteurs
                ],
            }
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "rows": rows,
    }


@router.get("/staging/{batch_id}/issues")
def staging_issues(
    batch_id: int,
    request: Request,
    severity: Optional[str] = Query(None, description="blocking, critical, warning, info"),
    resolved: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List quality findings (issues) for a batch, optionally filtered."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)

    query = db.query(QualityFinding).filter(QualityFinding.batch_id == batch_id)

    if severity:
        try:
            sev_enum = QualityRuleSeverity(severity)
            query = query.filter(QualityFinding.severity == sev_enum)
        except ValueError:
            pass

    if resolved is not None:
        query = query.filter(QualityFinding.resolved.is_(resolved))

    findings = query.order_by(QualityFinding.id).all()

    return {
        "total": len(findings),
        "issues": [
            {
                "id": f.id,
                "rule_id": f.rule_id,
                "severity": f.severity.value,
                "staging_site_id": f.staging_site_id,
                "staging_compteur_id": f.staging_compteur_id,
                "evidence": f.evidence_json,
                "suggested_action": f.suggested_action,
                "resolved": f.resolved,
                "resolution": f.resolution,
            }
            for f in findings
        ],
    }


@router.post("/staging/{batch_id}/validate")
def staging_validate(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Run quality gate on staging batch."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)
    try:
        findings = run_quality_gate(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    blocking_count = sum(1 for f in findings if f["severity"] in ("blocking", "critical"))
    db.commit()

    return {
        "findings": findings,
        "blocking_count": blocking_count,
        "can_activate": blocking_count == 0,
    }


@router.put("/staging/{batch_id}/fix")
def staging_fix(
    batch_id: int,
    request: Request,
    body: FixRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Apply a correction to staging data."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)
    result = apply_fix(db, batch_id, body.fix_type, body.params)
    db.commit()
    return result


@router.put("/staging/{batch_id}/fix/bulk")
def staging_fix_bulk(
    batch_id: int,
    request: Request,
    body: BulkFixRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Apply multiple corrections in a single transaction."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)
    results = []
    for fix in body.fixes:
        r = apply_fix(db, batch_id, fix.fix_type, fix.params)
        results.append(r)
    db.commit()
    applied_count = sum(1 for r in results if r.get("applied"))
    return {
        "applied": applied_count,
        "total": len(results),
        "results": results,
    }


@router.post("/staging/{batch_id}/autofix")
def staging_autofix(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Apply safe auto-corrections to staging data.

    Safe fixes:
    - Trim whitespace on all text fields
    - Pad code_postal to 5 digits
    - Normalize type_compteur (electricite/gaz/eau)
    - Skip orphan compteurs without meter_id and without numero_serie
    """
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)

    fixes_applied = 0

    # Fix 1: Trim + normalize staging sites
    sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
            StagingSite.skip.is_(False),
        )
        .all()
    )

    for ss in sites:
        changed = False
        # Trim whitespace
        for field in ("nom", "adresse", "ville", "siret", "naf_code"):
            val = getattr(ss, field, None)
            if val and val != val.strip():
                setattr(ss, field, val.strip())
                changed = True
        # Pad postal code
        if ss.code_postal:
            padded = ss.code_postal.strip().zfill(5)[:5]
            if padded != ss.code_postal:
                ss.code_postal = padded
                changed = True
        if changed:
            fixes_applied += 1

    # Fix 2: Normalize compteur types + trim
    compteurs = (
        db.query(StagingCompteur)
        .filter(
            StagingCompteur.batch_id == batch_id,
            StagingCompteur.skip.is_(False),
        )
        .all()
    )

    for sc in compteurs:
        changed = False
        # Trim meter_id
        if sc.meter_id and sc.meter_id != sc.meter_id.strip():
            sc.meter_id = sc.meter_id.strip()
            changed = True
        # Normalize type_compteur
        if sc.type_compteur:
            normalized = _normalize_compteur_type(sc.type_compteur)
            if normalized != sc.type_compteur:
                sc.type_compteur = normalized
                changed = True
        # Skip empty compteurs (no meter_id AND no numero_serie)
        if not sc.meter_id and not sc.numero_serie:
            sc.skip = True
            changed = True
        if changed:
            fixes_applied += 1

    db.flush()
    db.commit()

    return {
        "fixes_applied": fixes_applied,
        "detail": f"Applied {fixes_applied} safe auto-corrections",
    }


@router.delete("/staging/{batch_id}")
def staging_abandon(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Abandon a staging batch."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)
    try:
        result = abandon_batch(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    db.commit()
    return result


# ========================================
# Activation
# ========================================


@router.post("/staging/{batch_id}/activate")
def staging_activate(
    batch_id: int,
    request: Request,
    body: ActivateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Activate a validated staging batch → create real entities."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)
    _check_portfolio_belongs_to_org(db, body.portefeuille_id, org_id)
    try:
        result = activate_batch(db, batch_id, body.portefeuille_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.commit()
    return result


@router.get("/staging/{batch_id}/matching")
def staging_matching(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Preview matching results for update mode (before activation)."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)
    if batch.mode != "update":
        raise HTTPException(status_code=400, detail="Matching only available for mode=update")
    result = match_staging_to_existing(db, batch.id, org_id)
    db.commit()
    return result


@router.get("/staging/{batch_id}/result")
def staging_result(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get activation result for a batch (post-activation)."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)

    summary = get_staging_summary(db, batch_id)

    # Find activation log
    log = (
        db.query(ActivationLog)
        .filter(
            ActivationLog.batch_id == batch_id,
        )
        .order_by(ActivationLog.id.desc())
        .first()
    )

    result = {
        "batch_id": batch_id,
        "status": batch.status.value if batch.status else None,
        "mode": batch.mode,
        "filename": batch.filename,
        **summary,
    }

    if log:
        result["activation"] = {
            "log_id": log.id,
            "status": log.status.value,
            "started_at": log.started_at.isoformat() if log.started_at else None,
            "completed_at": log.completed_at.isoformat() if log.completed_at else None,
            "sites_created": log.sites_created,
            "compteurs_created": log.compteurs_created,
            "error_message": log.error_message,
        }

    # Stats from batch
    if batch.stats_json:
        try:
            stats = json.loads(batch.stats_json)
            result["stats"] = stats
        except (json.JSONDecodeError, TypeError):
            pass

    return result


@router.get("/staging/{batch_id}/export/report.csv")
def staging_export_report(
    batch_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Export batch report as CSV: all rows + issues + status."""
    org_id = _get_org_id(request, auth, db)
    batch = db.get(StagingBatch, batch_id)
    _check_batch_org(batch, org_id)

    sites = (
        db.query(StagingSite)
        .filter(
            StagingSite.batch_id == batch_id,
        )
        .order_by(StagingSite.row_number)
        .all()
    )

    findings = (
        db.query(QualityFinding)
        .filter(
            QualityFinding.batch_id == batch_id,
        )
        .all()
    )

    # Index findings by staging_site_id
    site_findings_map = {}
    for f in findings:
        if f.staging_site_id:
            site_findings_map.setdefault(f.staging_site_id, []).append(f)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Header
    writer.writerow(
        [
            "row",
            "nom",
            "adresse",
            "code_postal",
            "ville",
            "surface_m2",
            "type_site",
            "siret",
            "naf_code",
            "status",
            "compteurs",
            "issues_count",
            "issues_detail",
        ]
    )

    for ss in sites:
        compteurs = (
            db.query(StagingCompteur)
            .filter(
                StagingCompteur.staging_site_id == ss.id,
            )
            .all()
        )
        cpt_list = "; ".join(f"{sc.meter_id or sc.numero_serie or '?'} ({sc.type_compteur or '?'})" for sc in compteurs)

        findings_for_site = site_findings_map.get(ss.id, [])
        issues_detail = "; ".join(f"[{f.severity.value}] {f.rule_id}" for f in findings_for_site)

        status = "skipped" if ss.skip else ("merged" if ss.target_site_id else "active")

        writer.writerow(
            [
                ss.row_number,
                ss.nom,
                ss.adresse,
                ss.code_postal,
                ss.ville,
                ss.surface_m2,
                ss.type_site,
                ss.siret,
                ss.naf_code,
                status,
                cpt_list,
                len(findings_for_site),
                issues_detail,
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8-sig")

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=rapport_import_batch_{batch_id}.csv"},
    )


# ========================================
# Incremental sync
# ========================================


@router.post("/{portfolio_id}/sync")
async def portfolio_sync(
    portfolio_id: int,
    request: Request,
    file: UploadFile = File(...),
    dry_run: bool = Query(True),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Incremental sync: compare uploaded file vs existing portfolio."""
    org_id = _get_org_id(request, auth, db)
    _check_portfolio_belongs_to_org(db, portfolio_id, org_id)

    content = await file.read()
    content_hash = compute_content_hash(content)
    filename = file.filename or ""

    # Create temporary staging batch
    batch = create_staging_batch(
        db=db,
        org_id=org_id,
        user_id=auth.user.id if auth else None,
        source_type=ImportSourceType.CSV,
        mode="sync",
        filename=filename,
        content_hash=content_hash,
    )
    import_csv_to_staging(db, batch.id, content)

    # Get diff plan
    diff = get_diff_plan(db, portfolio_id, batch.id)

    if not dry_run:
        # Apply: activate new sites
        result = activate_batch(db, batch.id, portfolio_id)
        diff["applied"] = True
        diff["activation"] = result
    else:
        diff["applied"] = False

    db.commit()
    return diff


# ========================================
# Demo loader
# ========================================


@router.post("/demo/load")
def demo_load(db: Session = Depends(get_db)):
    """Load demo patrimoine data (Collectivite Azur). Requires DEMO_MODE."""
    from middleware.auth import DEMO_MODE

    if not DEMO_MODE:
        raise HTTPException(status_code=403, detail="Demo load désactivé en production")
    try:
        from scripts.seed_data import seed_patrimoine_demo

        result = seed_patrimoine_demo(db)
        db.commit()
        return {"status": "ok", **result}
    except ImportError:
        raise HTTPException(status_code=500, detail="seed_data module not available")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# Mapping preview (header recognition)
# ========================================


@router.post("/mapping/preview")
def mapping_preview(body: MappingPreviewRequest):
    """Preview how CSV/Excel headers will be mapped to canonical columns."""
    return get_mapping_report(body.headers)
