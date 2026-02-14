"""
PROMEOS - Routes Patrimoine (DIAMANT)
Staging pipeline: import, quality gate, corrections, activation, demo.
"""
import csv

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation, Portefeuille, StagingBatch, ImportSourceType, StagingStatus,
    Site, DeliveryPoint, not_deleted,
)
from services.patrimoine_service import (
    create_staging_batch, import_csv_to_staging, import_invoices_to_staging,
    get_staging_summary, run_quality_gate, apply_fix, activate_batch,
    get_diff_plan, compute_content_hash, abandon_batch,
)

router = APIRouter(prefix="/api/patrimoine", tags=["Patrimoine"])


# ========================================
# Schemas
# ========================================

class FixRequest(BaseModel):
    fix_type: str
    params: dict


class ActivateRequest(BaseModel):
    portefeuille_id: int


class InvoiceImportRequest(BaseModel):
    invoices: list


# ========================================
# Import endpoints
# ========================================

@router.post("/staging/import")
async def staging_import(
    file: UploadFile = File(...),
    mode: str = Query("import", description="express, import, assiste, demo"),
    db: Session = Depends(get_db),
):
    """Import CSV/Excel file into staging pipeline."""
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

    if source_type == ImportSourceType.EXCEL:
        # Excel: convert to CSV-like via openpyxl
        try:
            result = _parse_excel_to_staging(db, batch.id, content)
        except ImportError:
            raise HTTPException(status_code=400, detail="openpyxl not installed — Excel import unavailable")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Excel parse error: {e}")
    else:
        result = import_csv_to_staging(db, batch.id, content)

    db.commit()

    return {
        "batch_id": batch.id,
        "duplicate": False,
        **result,
    }


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


@router.post("/staging/{batch_id}/validate")
def staging_validate(batch_id: int, db: Session = Depends(get_db)):
    """Run quality gate on staging batch."""
    try:
        findings = run_quality_gate(db, batch_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    blocking_count = sum(1 for f in findings if f["severity"] == "blocking")
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
# Excel helper
# ========================================

def _parse_excel_to_staging(db: Session, batch_id: int, content: bytes) -> dict:
    """Parse Excel file via openpyxl and feed into staging."""
    import io
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return {"sites_count": 0, "compteurs_count": 0, "parse_errors": [{"row": 0, "error": "Empty workbook"}]}

    # First row = headers
    headers = [str(h or "").strip().lower() for h in rows[0]]

    # Convert to CSV bytes
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for row in rows[1:]:
        writer.writerow([str(c) if c is not None else "" for c in row])

    csv_bytes = output.getvalue().encode("utf-8")
    return import_csv_to_staging(db, batch_id, csv_bytes)
