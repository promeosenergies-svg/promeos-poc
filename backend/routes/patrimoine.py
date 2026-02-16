"""
PROMEOS - Routes Patrimoine (WORLD CLASS)
VNext pipeline: template, import, quality gate, corrections, activation, export.
CRUD Sites/Compteurs/Contrats + QA scoring.
"""
import csv
import io
import json
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation, Portefeuille, StagingBatch, StagingSite, StagingCompteur,
    QualityFinding, ImportSourceType, StagingStatus, QualityRuleSeverity,
    ActivationLog, ActivationLogStatus,
    Site, DeliveryPoint, not_deleted,
    Compteur, TypeSite, TypeCompteur, EnergyVector,
    EnergyContract, BillingEnergyType,
)
from services.patrimoine_service import (
    create_staging_batch, import_csv_to_staging, import_invoices_to_staging,
    get_staging_summary, run_quality_gate, apply_fix, activate_batch,
    get_diff_plan, compute_content_hash, abandon_batch,
)
from services.import_mapping import (
    CANONICAL_COLUMNS, generate_csv_template, generate_xlsx_template,
    map_headers, detect_encoding, detect_delimiter, normalize_column_name,
    get_mapping_report,
)

router = APIRouter(prefix="/api/patrimoine", tags=["Patrimoine"])


# ========================================
# Schemas
# ========================================

class FixRequest(BaseModel):
    fix_type: str
    params: dict


class BulkFixRequest(BaseModel):
    fixes: List[FixRequest]


class ActivateRequest(BaseModel):
    portefeuille_id: int


class InvoiceImportRequest(BaseModel):
    invoices: list


class UpdateFieldRequest(BaseModel):
    staging_site_id: Optional[int] = None
    staging_compteur_id: Optional[int] = None
    field: str
    value: Optional[str] = None


class SiteUpdateRequest(BaseModel):
    nom: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    region: Optional[str] = None
    surface_m2: Optional[float] = None
    nombre_employes: Optional[int] = None
    naf_code: Optional[str] = None
    siret: Optional[str] = None
    type: Optional[str] = None


class SiteMergeRequest(BaseModel):
    source_site_id: int
    target_site_id: int


class CompteurMoveRequest(BaseModel):
    target_site_id: int


class CompteurUpdateRequest(BaseModel):
    numero_serie: Optional[str] = None
    meter_id: Optional[str] = None
    puissance_souscrite_kw: Optional[float] = None
    type: Optional[str] = None


class ContractCreateRequest(BaseModel):
    site_id: int
    energy_type: str = "elec"
    supplier_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    price_ref_eur_per_kwh: Optional[float] = None
    fixed_fee_eur_per_month: Optional[float] = None
    notice_period_days: int = 90
    auto_renew: bool = False


class ContractUpdateRequest(BaseModel):
    supplier_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    price_ref_eur_per_kwh: Optional[float] = None
    fixed_fee_eur_per_month: Optional[float] = None
    notice_period_days: Optional[int] = None
    auto_renew: Optional[bool] = None


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
    file: UploadFile = File(...),
    mode: str = Query("import", description="express, import, assiste, demo"),
    db: Session = Depends(get_db),
):
    """Import CSV/Excel file into staging pipeline.

    Performs: encoding detection, header mapping, normalization, dedup check.
    """
    content = await file.read()
    content_hash = compute_content_hash(content)

    # Detect source type
    filename = file.filename or ""
    if filename.endswith((".xlsx", ".xls")):
        source_type = ImportSourceType.EXCEL
    else:
        source_type = ImportSourceType.CSV

    # Check for duplicate import (same content hash)
    existing = db.query(StagingBatch).filter(
        StagingBatch.content_hash == content_hash,
        StagingBatch.status != StagingStatus.ABANDONED,
    ).first()
    if existing:
        summary = get_staging_summary(db, existing.id)
        return {
            "batch_id": existing.id,
            "duplicate": True,
            "detail": "File already imported",
            **summary,
        }

    # Get default org (first available)
    org = db.query(Organisation).first()

    batch = create_staging_batch(
        db=db,
        org_id=org.id if org else None,
        user_id=None,
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
    body: InvoiceImportRequest,
    db: Session = Depends(get_db),
):
    """Import sites/meters from invoice metadata into staging."""
    org = db.query(Organisation).first()

    batch = create_staging_batch(
        db=db,
        org_id=org.id if org else None,
        user_id=None,
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
def staging_summary(batch_id: int, db: Session = Depends(get_db)):
    """Get staging batch summary stats."""
    try:
        return get_staging_summary(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/staging/{batch_id}/rows")
def staging_rows(
    batch_id: int,
    status: Optional[str] = Query(None, description="ok, error, skipped"),
    q: Optional[str] = Query(None, description="Search query"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List staging rows (sites + linked compteurs) with pagination & search."""
    batch = db.query(StagingBatch).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    query = db.query(StagingSite).filter(StagingSite.batch_id == batch_id)

    # Filter by status
    if status == "skipped":
        query = query.filter(StagingSite.skip.is_(True))
    elif status == "ok":
        query = query.filter(StagingSite.skip.is_(False))
    elif status == "error":
        # Sites with unresolved findings
        error_site_ids = db.query(QualityFinding.staging_site_id).filter(
            QualityFinding.batch_id == batch_id,
            QualityFinding.resolved.is_(False),
            QualityFinding.staging_site_id.isnot(None),
        ).distinct().all()
        error_ids = [r[0] for r in error_site_ids]
        query = query.filter(StagingSite.id.in_(error_ids)) if error_ids else query.filter(False)

    # Search
    if q:
        search = f"%{q}%"
        query = query.filter(
            (StagingSite.nom.ilike(search)) |
            (StagingSite.adresse.ilike(search)) |
            (StagingSite.ville.ilike(search)) |
            (StagingSite.siret.ilike(search))
        )

    total = query.count()
    sites = query.order_by(StagingSite.row_number).offset((page - 1) * page_size).limit(page_size).all()

    # Get findings indexed by staging_site_id
    all_findings = db.query(QualityFinding).filter(
        QualityFinding.batch_id == batch_id,
        QualityFinding.resolved.is_(False),
    ).all()
    site_findings = {}
    for f in all_findings:
        if f.staging_site_id:
            site_findings.setdefault(f.staging_site_id, []).append(f)

    rows = []
    for ss in sites:
        compteurs = db.query(StagingCompteur).filter(
            StagingCompteur.staging_site_id == ss.id,
        ).all()

        findings_for_site = site_findings.get(ss.id, [])

        rows.append({
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
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "rows": rows,
    }


@router.get("/staging/{batch_id}/issues")
def staging_issues(
    batch_id: int,
    severity: Optional[str] = Query(None, description="blocking, critical, warning, info"),
    resolved: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """List quality findings (issues) for a batch, optionally filtered."""
    batch = db.query(StagingBatch).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

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
def staging_validate(batch_id: int, db: Session = Depends(get_db)):
    """Run quality gate on staging batch."""
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
def staging_fix(batch_id: int, body: FixRequest, db: Session = Depends(get_db)):
    """Apply a correction to staging data."""
    result = apply_fix(db, batch_id, body.fix_type, body.params)
    db.commit()
    return result


@router.put("/staging/{batch_id}/fix/bulk")
def staging_fix_bulk(batch_id: int, body: BulkFixRequest, db: Session = Depends(get_db)):
    """Apply multiple corrections in a single transaction."""
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
def staging_autofix(batch_id: int, db: Session = Depends(get_db)):
    """Apply safe auto-corrections to staging data.

    Safe fixes:
    - Trim whitespace on all text fields
    - Pad code_postal to 5 digits
    - Normalize type_compteur (electricite/gaz/eau)
    - Skip orphan compteurs without meter_id and without numero_serie
    """
    batch = db.query(StagingBatch).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    fixes_applied = 0

    # Fix 1: Trim + normalize staging sites
    sites = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
        StagingSite.skip.is_(False),
    ).all()

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
    compteurs = db.query(StagingCompteur).filter(
        StagingCompteur.batch_id == batch_id,
        StagingCompteur.skip.is_(False),
    ).all()

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
def staging_abandon(batch_id: int, db: Session = Depends(get_db)):
    """Abandon a staging batch."""
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
def staging_activate(batch_id: int, body: ActivateRequest, db: Session = Depends(get_db)):
    """Activate a validated staging batch → create real entities."""
    try:
        result = activate_batch(db, batch_id, body.portefeuille_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    db.commit()
    return result


@router.get("/staging/{batch_id}/result")
def staging_result(batch_id: int, db: Session = Depends(get_db)):
    """Get activation result for a batch (post-activation)."""
    batch = db.query(StagingBatch).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    summary = get_staging_summary(db, batch_id)

    # Find activation log
    log = db.query(ActivationLog).filter(
        ActivationLog.batch_id == batch_id,
    ).order_by(ActivationLog.id.desc()).first()

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
def staging_export_report(batch_id: int, db: Session = Depends(get_db)):
    """Export batch report as CSV: all rows + issues + status."""
    batch = db.query(StagingBatch).get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")

    sites = db.query(StagingSite).filter(
        StagingSite.batch_id == batch_id,
    ).order_by(StagingSite.row_number).all()

    findings = db.query(QualityFinding).filter(
        QualityFinding.batch_id == batch_id,
    ).all()

    # Index findings by staging_site_id
    site_findings_map = {}
    for f in findings:
        if f.staging_site_id:
            site_findings_map.setdefault(f.staging_site_id, []).append(f)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Header
    writer.writerow([
        "row", "nom", "adresse", "code_postal", "ville", "surface_m2",
        "type_site", "siret", "naf_code", "status",
        "compteurs", "issues_count", "issues_detail",
    ])

    for ss in sites:
        compteurs = db.query(StagingCompteur).filter(
            StagingCompteur.staging_site_id == ss.id,
        ).all()
        cpt_list = "; ".join(
            f"{sc.meter_id or sc.numero_serie or '?'} ({sc.type_compteur or '?'})"
            for sc in compteurs
        )

        findings_for_site = site_findings_map.get(ss.id, [])
        issues_detail = "; ".join(
            f"[{f.severity.value}] {f.rule_id}"
            for f in findings_for_site
        )

        status = "skipped" if ss.skip else ("merged" if ss.target_site_id else "active")

        writer.writerow([
            ss.row_number, ss.nom, ss.adresse, ss.code_postal, ss.ville,
            ss.surface_m2, ss.type_site, ss.siret, ss.naf_code, status,
            cpt_list, len(findings_for_site), issues_detail,
        ])

    csv_bytes = output.getvalue().encode("utf-8-sig")

    return StreamingResponse(
        io.BytesIO(csv_bytes),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f"attachment; filename=rapport_import_batch_{batch_id}.csv"},
    )


# ========================================
# Delivery Points
# ========================================

@router.get("/sites/{site_id}/delivery-points")
def site_delivery_points(site_id: int, db: Session = Depends(get_db)):
    """List active delivery points (PRM/PCE) for a site."""
    site = db.query(Site).get(site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found")

    dps = not_deleted(db.query(DeliveryPoint), DeliveryPoint).filter(
        DeliveryPoint.site_id == site_id,
    ).all()

    return [
        {
            "id": dp.id,
            "code": dp.code,
            "energy_type": dp.energy_type.value if dp.energy_type else None,
            "status": dp.status.value if dp.status else None,
            "compteurs_count": len(dp.compteurs) if dp.compteurs else 0,
            "data_source": dp.data_source,
            "created_at": dp.created_at.isoformat() if dp.created_at else None,
        }
        for dp in dps
    ]


# ========================================
# Incremental sync
# ========================================

@router.post("/{portfolio_id}/sync")
async def portfolio_sync(
    portfolio_id: int,
    file: UploadFile = File(...),
    dry_run: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Incremental sync: compare uploaded file vs existing portfolio."""
    pf = db.query(Portefeuille).get(portfolio_id)
    if not pf:
        raise HTTPException(status_code=404, detail=f"Portefeuille {portfolio_id} not found")

    content = await file.read()
    content_hash = compute_content_hash(content)
    filename = file.filename or ""

    # Create temporary staging batch
    batch = create_staging_batch(
        db=db,
        org_id=None,
        user_id=None,
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
    """Load demo patrimoine data (Collectivite Azur)."""
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
# Helpers
# ========================================

def _normalize_compteur_type(raw: str) -> str:
    """Normalize compteur type string for autofix."""
    low = raw.lower().strip()
    if any(k in low for k in ("elec", "elect")):
        return "electricite"
    if any(k in low for k in ("gaz", "gas")):
        return "gaz"
    if any(k in low for k in ("eau", "water")):
        return "eau"
    return raw


def _parse_excel_to_staging(db: Session, batch_id: int, content: bytes) -> dict:
    """Parse Excel file via openpyxl and feed into staging."""
    import io as _io
    from openpyxl import load_workbook

    wb = load_workbook(_io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"sites_count": 0, "compteurs_count": 0, "parse_errors": [{"row": 0, "error": "Empty workbook"}]}

    # First row = headers — normalize via mapping
    raw_headers = [str(h or "").strip() for h in rows[0]]
    normalized_headers = [normalize_column_name(h) for h in raw_headers]

    # Convert to CSV bytes with normalized headers
    output = _io.StringIO()
    writer = csv.writer(output)
    writer.writerow(normalized_headers)
    for row in rows[1:]:
        writer.writerow([str(c) if c is not None else "" for c in row])

    csv_bytes = output.getvalue().encode("utf-8")
    return import_csv_to_staging(db, batch_id, csv_bytes)


# ========================================
# Mapping preview (header recognition)
# ========================================

class MappingPreviewRequest(BaseModel):
    headers: list


@router.post("/mapping/preview")
def mapping_preview(body: MappingPreviewRequest):
    """Preview how CSV/Excel headers will be mapped to canonical columns."""
    return get_mapping_report(body.headers)


# ========================================
# Site CRUD (WORLD CLASS)
# ========================================

def _serialize_site(site: Site) -> dict:
    return {
        "id": site.id,
        "nom": site.nom,
        "type": site.type.value if site.type else None,
        "adresse": site.adresse,
        "code_postal": site.code_postal,
        "ville": site.ville,
        "region": site.region,
        "surface_m2": site.surface_m2,
        "nombre_employes": site.nombre_employes,
        "siret": site.siret,
        "naf_code": site.naf_code,
        "actif": site.actif,
        "portefeuille_id": site.portefeuille_id,
        "data_source": site.data_source,
        "created_at": site.created_at.isoformat() if site.created_at else None,
        "updated_at": site.updated_at.isoformat() if site.updated_at else None,
    }


@router.get("/sites")
def list_sites(
    portefeuille_id: Optional[int] = None,
    actif: Optional[bool] = None,
    ville: Optional[str] = None,
    type_site: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List sites with filters."""
    q = db.query(Site)
    if portefeuille_id is not None:
        q = q.filter(Site.portefeuille_id == portefeuille_id)
    if actif is not None:
        q = q.filter(Site.actif == actif)
    if ville:
        q = q.filter(Site.ville.ilike(f"%{ville}%"))
    if type_site:
        q = q.filter(Site.type == type_site)
    if search:
        q = q.filter(
            (Site.nom.ilike(f"%{search}%")) |
            (Site.ville.ilike(f"%{search}%")) |
            (Site.adresse.ilike(f"%{search}%"))
        )
    total = q.count()
    sites = q.offset(skip).limit(limit).all()
    return {
        "total": total,
        "sites": [_serialize_site(s) for s in sites],
    }


@router.get("/sites/{site_id}")
def get_site_detail(site_id: int, db: Session = Depends(get_db)):
    """Get a site with compteurs and contracts count."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} non trouve")
    compteurs_count = db.query(Compteur).filter(Compteur.site_id == site_id, Compteur.actif.is_(True)).count()
    contracts_count = db.query(EnergyContract).filter(EnergyContract.site_id == site_id).count()
    return {
        **_serialize_site(site),
        "compteurs_count": compteurs_count,
        "contracts_count": contracts_count,
    }


@router.patch("/sites/{site_id}")
def update_site(site_id: int, body: SiteUpdateRequest, db: Session = Depends(get_db)):
    """Update a site (partial update)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} non trouve")

    updated_fields = []
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "type" and value is not None:
            try:
                value = TypeSite(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type invalide: {value}")
        setattr(site, field, value)
        updated_fields.append(field)

    db.commit()
    return {"updated": updated_fields, **_serialize_site(site)}


@router.post("/sites/{site_id}/archive")
def archive_site(site_id: int, db: Session = Depends(get_db)):
    """Soft-delete a site (set actif=False)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} non trouve")
    if not site.actif:
        return {"detail": "Site deja archive", "site_id": site_id}
    site.actif = False
    db.commit()
    return {"detail": "Site archive", "site_id": site_id}


@router.post("/sites/{site_id}/restore")
def restore_site(site_id: int, db: Session = Depends(get_db)):
    """Restore an archived site (set actif=True)."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {site_id} non trouve")
    if site.actif:
        return {"detail": "Site deja actif", "site_id": site_id}
    site.actif = True
    db.commit()
    return {"detail": "Site restaure", "site_id": site_id}


@router.post("/sites/merge")
def merge_sites(body: SiteMergeRequest, db: Session = Depends(get_db)):
    """Merge source site into target: transfer compteurs+contracts, archive source."""
    source = db.query(Site).filter(Site.id == body.source_site_id).first()
    target = db.query(Site).filter(Site.id == body.target_site_id).first()
    if not source:
        raise HTTPException(status_code=404, detail=f"Site source {body.source_site_id} non trouve")
    if not target:
        raise HTTPException(status_code=404, detail=f"Site cible {body.target_site_id} non trouve")
    if source.id == target.id:
        raise HTTPException(status_code=400, detail="Source et cible identiques")

    # Transfer compteurs
    compteurs_moved = db.query(Compteur).filter(Compteur.site_id == source.id).update(
        {"site_id": target.id}, synchronize_session="fetch"
    )
    # Transfer contracts
    contracts_moved = db.query(EnergyContract).filter(EnergyContract.site_id == source.id).update(
        {"site_id": target.id}, synchronize_session="fetch"
    )
    # Archive source
    source.actif = False
    db.commit()

    return {
        "detail": f"Site {source.id} fusionne dans {target.id}",
        "compteurs_moved": compteurs_moved,
        "contracts_moved": contracts_moved,
        "source_archived": True,
    }


# ========================================
# Compteur Operations (WORLD CLASS)
# ========================================

def _serialize_compteur(c: Compteur) -> dict:
    return {
        "id": c.id,
        "site_id": c.site_id,
        "type": c.type.value if c.type else None,
        "numero_serie": c.numero_serie,
        "meter_id": c.meter_id,
        "puissance_souscrite_kw": c.puissance_souscrite_kw,
        "energy_vector": c.energy_vector.value if c.energy_vector else None,
        "actif": c.actif,
        "data_source": c.data_source,
    }


@router.get("/compteurs")
def list_compteurs(
    site_id: Optional[int] = None,
    actif: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List compteurs with filters."""
    q = db.query(Compteur)
    if site_id is not None:
        q = q.filter(Compteur.site_id == site_id)
    if actif is not None:
        q = q.filter(Compteur.actif == actif)
    total = q.count()
    compteurs = q.offset(skip).limit(limit).all()
    return {"total": total, "compteurs": [_serialize_compteur(c) for c in compteurs]}


@router.patch("/compteurs/{compteur_id}")
def update_compteur(compteur_id: int, body: CompteurUpdateRequest, db: Session = Depends(get_db)):
    """Update a compteur (partial update)."""
    c = db.query(Compteur).filter(Compteur.id == compteur_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Compteur {compteur_id} non trouve")

    updated = []
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "type" and value is not None:
            try:
                value = TypeCompteur(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type invalide: {value}")
        setattr(c, field, value)
        updated.append(field)

    db.commit()
    return {"updated": updated, **_serialize_compteur(c)}


@router.post("/compteurs/{compteur_id}/move")
def move_compteur(compteur_id: int, body: CompteurMoveRequest, db: Session = Depends(get_db)):
    """Move a compteur to another site."""
    c = db.query(Compteur).filter(Compteur.id == compteur_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Compteur {compteur_id} non trouve")
    target = db.query(Site).filter(Site.id == body.target_site_id).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"Site cible {body.target_site_id} non trouve")

    old_site_id = c.site_id
    c.site_id = target.id
    db.commit()
    return {
        "detail": f"Compteur {compteur_id} deplace de site {old_site_id} vers {target.id}",
        **_serialize_compteur(c),
    }


@router.post("/compteurs/{compteur_id}/detach")
def detach_compteur(compteur_id: int, db: Session = Depends(get_db)):
    """Deactivate a compteur (soft detach)."""
    c = db.query(Compteur).filter(Compteur.id == compteur_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Compteur {compteur_id} non trouve")
    c.actif = False
    db.commit()
    return {"detail": f"Compteur {compteur_id} desactive", **_serialize_compteur(c)}


# ========================================
# Contract CRUD (WORLD CLASS)
# ========================================

def _serialize_contract(ct: EnergyContract) -> dict:
    return {
        "id": ct.id,
        "site_id": ct.site_id,
        "energy_type": ct.energy_type.value if ct.energy_type else None,
        "supplier_name": ct.supplier_name,
        "start_date": ct.start_date.isoformat() if ct.start_date else None,
        "end_date": ct.end_date.isoformat() if ct.end_date else None,
        "price_ref_eur_per_kwh": ct.price_ref_eur_per_kwh,
        "fixed_fee_eur_per_month": ct.fixed_fee_eur_per_month,
        "notice_period_days": ct.notice_period_days,
        "auto_renew": ct.auto_renew,
        "created_at": ct.created_at.isoformat() if ct.created_at else None,
    }


@router.get("/contracts")
def list_contracts(
    site_id: Optional[int] = None,
    energy_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List energy contracts with filters."""
    q = db.query(EnergyContract)
    if site_id is not None:
        q = q.filter(EnergyContract.site_id == site_id)
    if energy_type:
        q = q.filter(EnergyContract.energy_type == energy_type)
    total = q.count()
    contracts = q.offset(skip).limit(limit).all()
    return {"total": total, "contracts": [_serialize_contract(ct) for ct in contracts]}


@router.post("/contracts")
def create_contract(body: ContractCreateRequest, db: Session = Depends(get_db)):
    """Create a new energy contract."""
    site = db.query(Site).filter(Site.id == body.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail=f"Site {body.site_id} non trouve")

    try:
        et = BillingEnergyType(body.energy_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Type energie invalide: {body.energy_type}")

    ct = EnergyContract(
        site_id=body.site_id,
        energy_type=et,
        supplier_name=body.supplier_name,
        start_date=date.fromisoformat(body.start_date) if body.start_date else None,
        end_date=date.fromisoformat(body.end_date) if body.end_date else None,
        price_ref_eur_per_kwh=body.price_ref_eur_per_kwh,
        fixed_fee_eur_per_month=body.fixed_fee_eur_per_month,
        notice_period_days=body.notice_period_days,
        auto_renew=body.auto_renew,
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return _serialize_contract(ct)


@router.patch("/contracts/{contract_id}")
def update_contract(contract_id: int, body: ContractUpdateRequest, db: Session = Depends(get_db)):
    """Update an energy contract (partial update)."""
    ct = db.query(EnergyContract).filter(EnergyContract.id == contract_id).first()
    if not ct:
        raise HTTPException(status_code=404, detail=f"Contrat {contract_id} non trouve")

    updated = []
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in ("start_date", "end_date") and value is not None:
            value = date.fromisoformat(value)
        setattr(ct, field, value)
        updated.append(field)

    db.commit()
    return {"updated": updated, **_serialize_contract(ct)}


@router.delete("/contracts/{contract_id}")
def delete_contract(contract_id: int, db: Session = Depends(get_db)):
    """Delete an energy contract."""
    ct = db.query(EnergyContract).filter(EnergyContract.id == contract_id).first()
    if not ct:
        raise HTTPException(status_code=404, detail=f"Contrat {contract_id} non trouve")
    db.delete(ct)
    db.commit()
    return {"detail": f"Contrat {contract_id} supprime"}
