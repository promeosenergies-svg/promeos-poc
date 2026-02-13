"""
PROMEOS — Bill Intelligence Routes (Sprint 7.1)
CSV import (idempotent) + audit + summary + site billing + insight workflow.
Prefix: /api/billing
"""
import csv
import hashlib
import io
import json
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Site, EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight,
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus,
    InsightStatus, BillingImportBatch,
)
from services.billing_service import (
    audit_invoice_full,
    get_billing_summary,
    get_site_billing,
    shadow_billing_simple,
    BILLING_RULES,
)
from middleware.auth import get_optional_auth, AuthContext

router = APIRouter(prefix="/api/billing", tags=["Bill Intelligence V2"])


# ========================================
# Pydantic schemas
# ========================================

class ContractCreate(BaseModel):
    site_id: int
    energy_type: str  # elec / gaz
    supplier_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    price_ref_eur_per_kwh: Optional[float] = None
    fixed_fee_eur_per_month: Optional[float] = None


class InvoiceCreate(BaseModel):
    site_id: int
    contract_id: Optional[int] = None
    invoice_number: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    issue_date: Optional[str] = None
    total_eur: Optional[float] = None
    energy_kwh: Optional[float] = None
    lines: Optional[List[dict]] = None


class InsightPatch(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


# ========================================
# Contract endpoints
# ========================================

@router.post("/contracts")
def create_contract(data: ContractCreate, db: Session = Depends(get_db)):
    """Create an energy contract."""
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")
    try:
        energy_type = BillingEnergyType(data.energy_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"energy_type invalide: {data.energy_type}")

    contract = EnergyContract(
        site_id=data.site_id,
        energy_type=energy_type,
        supplier_name=data.supplier_name,
        start_date=_parse_date(data.start_date),
        end_date=_parse_date(data.end_date),
        price_ref_eur_per_kwh=data.price_ref_eur_per_kwh,
        fixed_fee_eur_per_month=data.fixed_fee_eur_per_month,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return {"status": "created", "contract_id": contract.id}


@router.get("/contracts")
def list_contracts(site_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """List contracts, optionally filtered by site."""
    q = db.query(EnergyContract)
    if site_id:
        q = q.filter(EnergyContract.site_id == site_id)
    contracts = q.all()
    return {
        "contracts": [
            {
                "id": c.id, "site_id": c.site_id,
                "energy_type": c.energy_type.value,
                "supplier_name": c.supplier_name,
                "price_ref_eur_per_kwh": c.price_ref_eur_per_kwh,
                "start_date": str(c.start_date) if c.start_date else None,
                "end_date": str(c.end_date) if c.end_date else None,
            }
            for c in contracts
        ],
        "count": len(contracts),
    }


# ========================================
# CSV Import (idempotent — Sprint 7.1)
# ========================================

@router.post("/import-csv")
def import_invoices_csv(
    file: UploadFile = File(...),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Import invoices from CSV (idempotent).
    A re-upload of the same file (same org + same SHA-256) is rejected.
    Expected columns: site_id,invoice_number,period_start,period_end,issue_date,total_eur,energy_kwh,source
    Optional line columns: line_type,line_label,line_qty,line_unit,line_unit_price,line_amount_eur
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Le fichier doit etre un CSV")

    content = file.file.read().decode("utf-8-sig")

    # --- Idempotency check (content hash) ---
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing_batch = db.query(BillingImportBatch).filter(
        BillingImportBatch.content_hash == content_hash,
        BillingImportBatch.org_id == org_id,
    ).first()
    if existing_batch:
        return {
            "status": "already_imported",
            "batch_id": existing_batch.id,
            "imported_at": existing_batch.imported_at.isoformat() if existing_batch.imported_at else None,
            "rows_total": existing_batch.rows_total,
            "rows_inserted": existing_batch.rows_inserted,
            "rows_skipped": existing_batch.rows_skipped,
            "message": "Ce fichier a deja ete importe (meme contenu).",
        }

    # --- Parse & import rows ---
    reader = csv.DictReader(io.StringIO(content), delimiter=",")

    imported = 0
    skipped = 0
    errors = []
    invoices_created = []
    rows_total = 0

    for row_num, row in enumerate(reader, start=2):
        rows_total += 1
        try:
            site_id = int(row.get("site_id", "0").strip())
            invoice_number = row.get("invoice_number", "").strip()
            if not invoice_number:
                errors.append({"row": row_num, "error": "invoice_number manquant"})
                continue

            # Verify site exists
            site = db.query(Site).filter(Site.id == site_id).first()
            if not site:
                errors.append({"row": row_num, "error": f"Site {site_id} introuvable"})
                continue

            # Check duplicate
            existing = db.query(EnergyInvoice).filter(
                EnergyInvoice.site_id == site_id,
                EnergyInvoice.invoice_number == invoice_number,
            ).first()
            if existing:
                skipped += 1
                errors.append({"row": row_num, "error": f"Facture {invoice_number} deja importee"})
                continue

            invoice = EnergyInvoice(
                site_id=site_id,
                invoice_number=invoice_number,
                period_start=_parse_date(row.get("period_start", "").strip()),
                period_end=_parse_date(row.get("period_end", "").strip()),
                issue_date=_parse_date(row.get("issue_date", "").strip()),
                total_eur=_parse_float(row.get("total_eur", "")),
                energy_kwh=_parse_float(row.get("energy_kwh", "")),
                status=BillingInvoiceStatus.IMPORTED,
                source="csv",
            )

            # Try to link to contract
            contract_id = row.get("contract_id", "").strip()
            if contract_id:
                invoice.contract_id = int(contract_id)

            db.add(invoice)
            db.flush()  # Get the ID

            # Import lines if present
            line_type = row.get("line_type", "").strip()
            if line_type:
                try:
                    lt = InvoiceLineType(line_type)
                except ValueError:
                    lt = InvoiceLineType.OTHER
                line = EnergyInvoiceLine(
                    invoice_id=invoice.id,
                    line_type=lt,
                    label=row.get("line_label", line_type).strip() or line_type,
                    qty=_parse_float(row.get("line_qty", "")),
                    unit=row.get("line_unit", "").strip() or None,
                    unit_price=_parse_float(row.get("line_unit_price", "")),
                    amount_eur=_parse_float(row.get("line_amount_eur", "")),
                )
                db.add(line)

            invoices_created.append(invoice)
            imported += 1

        except Exception as e:
            errors.append({"row": row_num, "error": str(e)[:200]})

    # --- Record batch ---
    batch = BillingImportBatch(
        org_id=org_id,
        filename=file.filename,
        content_hash=content_hash,
        rows_total=rows_total,
        rows_inserted=imported,
        rows_skipped=skipped,
        errors_json=json.dumps(errors, ensure_ascii=False) if errors else None,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    return {
        "status": "ok",
        "batch_id": batch.id,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "error_count": len(errors),
    }


# ========================================
# Import batches listing (Sprint 7.1)
# ========================================

@router.get("/import/batches")
def list_import_batches(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """List CSV import batches with stats."""
    q = db.query(BillingImportBatch)
    if org_id is not None:
        q = q.filter(BillingImportBatch.org_id == org_id)
    batches = q.order_by(BillingImportBatch.imported_at.desc()).all()
    return {
        "batches": [
            {
                "id": b.id,
                "org_id": b.org_id,
                "filename": b.filename,
                "content_hash": b.content_hash,
                "imported_at": b.imported_at.isoformat() if b.imported_at else None,
                "rows_total": b.rows_total,
                "rows_inserted": b.rows_inserted,
                "rows_skipped": b.rows_skipped,
            }
            for b in batches
        ],
        "count": len(batches),
    }


# ========================================
# Single invoice create
# ========================================

@router.post("/invoices")
def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    """Create a single invoice manually."""
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    invoice = EnergyInvoice(
        site_id=data.site_id,
        contract_id=data.contract_id,
        invoice_number=data.invoice_number,
        period_start=_parse_date(data.period_start),
        period_end=_parse_date(data.period_end),
        issue_date=_parse_date(data.issue_date),
        total_eur=data.total_eur,
        energy_kwh=data.energy_kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source="manual",
    )
    db.add(invoice)
    db.flush()

    # Add lines if provided
    if data.lines:
        for ld in data.lines:
            try:
                lt = InvoiceLineType(ld.get("line_type", "other"))
            except ValueError:
                lt = InvoiceLineType.OTHER
            line = EnergyInvoiceLine(
                invoice_id=invoice.id,
                line_type=lt,
                label=ld.get("label", ""),
                qty=ld.get("qty"),
                unit=ld.get("unit"),
                unit_price=ld.get("unit_price"),
                amount_eur=ld.get("amount_eur"),
            )
            db.add(line)

    db.commit()
    db.refresh(invoice)
    return {"status": "created", "invoice_id": invoice.id}


# ========================================
# Audit
# ========================================

@router.post("/audit/{invoice_id}")
def audit_invoice_endpoint(invoice_id: int, db: Session = Depends(get_db)):
    """Run shadow billing + anomaly engine on a persisted invoice."""
    result = audit_invoice_full(db, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/audit-all")
def audit_all_invoices(db: Session = Depends(get_db)):
    """Audit all imported invoices."""
    invoices = db.query(EnergyInvoice).all()
    results = []
    for inv in invoices:
        r = audit_invoice_full(db, inv.id)
        results.append({
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "anomalies_count": r.get("anomalies_count", 0),
        })
    return {
        "status": "ok",
        "audited": len(results),
        "total_anomalies": sum(r["anomalies_count"] for r in results),
        "results": results,
    }


# ========================================
# Read endpoints
# ========================================

@router.get("/summary")
def billing_summary(db: Session = Depends(get_db)):
    """Aggregate billing summary (invoices, insights, losses)."""
    return get_billing_summary(db)


@router.get("/insights")
def list_insights(
    site_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List billing insights with optional filters (site, severity, status)."""
    q = db.query(BillingInsight)
    # Scope filtering
    if auth and auth.site_ids is not None:
        q = q.filter(BillingInsight.site_id.in_(auth.site_ids))
    if site_id:
        q = q.filter(BillingInsight.site_id == site_id)
    if severity:
        q = q.filter(BillingInsight.severity == severity)
    if status:
        try:
            q = q.filter(BillingInsight.insight_status == InsightStatus(status))
        except ValueError:
            pass
    insights = q.order_by(BillingInsight.estimated_loss_eur.desc().nullslast()).all()
    return {
        "insights": [
            {
                "id": i.id, "site_id": i.site_id, "invoice_id": i.invoice_id,
                "type": i.type, "severity": i.severity, "message": i.message,
                "estimated_loss_eur": i.estimated_loss_eur,
                "insight_status": i.insight_status.value if i.insight_status else "open",
                "owner": i.owner,
                "notes": i.notes,
            }
            for i in insights
        ],
        "count": len(insights),
    }


# ========================================
# Insight workflow (Sprint 7.1)
# ========================================

@router.patch("/insights/{insight_id}")
def patch_insight(insight_id: int, data: InsightPatch, db: Session = Depends(get_db)):
    """Update insight status / owner / notes (ops workflow)."""
    insight = db.query(BillingInsight).filter(BillingInsight.id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight non trouve")

    if data.status is not None:
        try:
            insight.insight_status = InsightStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {data.status}")
    if data.owner is not None:
        insight.owner = data.owner
    if data.notes is not None:
        insight.notes = data.notes

    db.commit()
    db.refresh(insight)
    return {
        "status": "updated",
        "insight_id": insight.id,
        "insight_status": insight.insight_status.value if insight.insight_status else "open",
        "owner": insight.owner,
        "notes": insight.notes,
    }


@router.post("/insights/{insight_id}/resolve")
def resolve_insight(insight_id: int, notes: Optional[str] = Query(None), db: Session = Depends(get_db)):
    """Shortcut: mark insight as RESOLVED with optional notes."""
    insight = db.query(BillingInsight).filter(BillingInsight.id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight non trouve")

    insight.insight_status = InsightStatus.RESOLVED
    if notes:
        insight.notes = notes
    db.commit()
    db.refresh(insight)
    return {
        "status": "resolved",
        "insight_id": insight.id,
        "insight_status": "resolved",
    }


@router.get("/invoices")
def list_invoices(
    site_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List invoices with optional filters."""
    q = db.query(EnergyInvoice)
    if site_id:
        q = q.filter(EnergyInvoice.site_id == site_id)
    if status:
        try:
            q = q.filter(EnergyInvoice.status == BillingInvoiceStatus(status))
        except ValueError:
            pass
    invoices = q.order_by(EnergyInvoice.period_start.desc().nullslast()).all()
    return {
        "invoices": [
            {
                "id": i.id, "site_id": i.site_id, "invoice_number": i.invoice_number,
                "period_start": str(i.period_start) if i.period_start else None,
                "period_end": str(i.period_end) if i.period_end else None,
                "total_eur": i.total_eur, "energy_kwh": i.energy_kwh,
                "status": i.status.value if i.status else None,
                "source": i.source,
            }
            for i in invoices
        ],
        "count": len(invoices),
    }


@router.get("/site/{site_id}")
def site_billing_endpoint(site_id: int, db: Session = Depends(get_db)):
    """Full billing view for a site (contracts, invoices, insights)."""
    result = get_site_billing(db, site_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/rules")
def list_billing_rules():
    """List all billing anomaly rules."""
    return {
        "rules": [
            {"id": r[0], "name": r[1]}
            for r in BILLING_RULES
        ],
        "count": len(BILLING_RULES),
    }


# ========================================
# Seed demo
# ========================================

@router.post("/seed-demo")
def seed_demo(db: Session = Depends(get_db)):
    """Seed 2 contracts + 5 invoices (3 good + 2 anomalous) for demo."""
    from services.billing_seed import seed_billing_demo
    result = seed_billing_demo(db)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"status": "ok", **result}


# ========================================
# Helpers
# ========================================

def _parse_date(val: Optional[str]) -> Optional[date]:
    """Parse date string (YYYY-MM-DD) or return None."""
    if not val or not val.strip():
        return None
    try:
        return date.fromisoformat(val.strip())
    except ValueError:
        return None


def _parse_float(val: Optional[str]) -> Optional[float]:
    """Parse float from string, handling comma as decimal sep."""
    if not val or not val.strip():
        return None
    try:
        return float(val.strip().replace(",", "."))
    except ValueError:
        return None
