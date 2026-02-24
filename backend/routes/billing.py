"""
PROMEOS — Bill Intelligence Routes (Sprint 7.1 → V66)
CSV import (idempotent) + audit + summary + site billing + insight workflow.
V66: org scoping (resolve_org_id), response_model Pydantic, PDF import, anomalies-scoped.
Prefix: /api/billing
"""
import csv
import hashlib
import io
import json
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Site, EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight,
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus,
    InsightStatus, BillingImportBatch,
    Portefeuille, EntiteJuridique,
)
from services.billing_service import (
    audit_invoice_full,
    get_billing_summary,
    get_site_billing,
    shadow_billing_simple,
    BILLING_RULES,
)
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/billing", tags=["Bill Intelligence V2"])


# ========================================
# Pydantic schemas — Input
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
# Pydantic schemas — Response (V66 P1.2)
# ========================================

class ContractResponse(BaseModel):
    id: int
    site_id: int
    energy_type: str
    supplier_name: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    price_ref_eur_per_kwh: Optional[float] = None
    auto_renew: Optional[bool] = None

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    id: int
    site_id: int
    invoice_number: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    total_eur: Optional[float] = None
    energy_kwh: Optional[float] = None
    status: Optional[str] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


class BillingInsightResponse(BaseModel):
    id: int
    site_id: int
    invoice_id: Optional[int] = None
    type: Optional[str] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    estimated_loss_eur: Optional[float] = None
    insight_status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class BillingSummaryResponse(BaseModel):
    total_invoices: int
    total_eur: float
    total_kwh: float
    total_insights: int
    total_estimated_loss_eur: float
    insights_by_type: dict
    insights_by_severity: dict
    invoices_with_anomalies: int
    invoices_clean: int


class ContractListResponse(BaseModel):
    contracts: List[dict]
    count: int


class InvoiceListResponse(BaseModel):
    invoices: List[dict]
    count: int


class InsightListResponse(BaseModel):
    insights: List[dict]
    count: int


# ========================================
# Org-scoping helpers (V66 P1.1)
# ========================================

def _org_sites_query(db: Session, model_class, effective_org_id: int):
    """Filter model_class queries via site→portefeuille→entite_juridique→org."""
    return (
        db.query(model_class)
        .join(Site, Site.id == model_class.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == effective_org_id)
    )


def _get_org_site_ids(db: Session, effective_org_id: int) -> List[int]:
    """Return all site IDs belonging to effective_org_id."""
    rows = (
        db.query(Site.id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == effective_org_id)
        .all()
    )
    return [r[0] for r in rows]


def _check_site_belongs_to_org(db: Session, site_id: int, effective_org_id: int) -> Site:
    """Return site if it belongs to org, or raise 404."""
    site = (
        db.query(Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(Site.id == site_id, EntiteJuridique.organisation_id == effective_org_id)
        .first()
    )
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé ou accès refusé")
    return site


# ========================================
# Contract endpoints
# ========================================

@router.post("/contracts")
def create_contract(
    data: ContractCreate,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create an energy contract."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    _check_site_belongs_to_org(db, data.site_id, effective_org_id)

    try:
        energy_type = BillingEnergyType(data.energy_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"energy_type invalide: {data.energy_type}")

    start = _parse_date(data.start_date)
    end = _parse_date(data.end_date)

    # Check for overlapping contracts on same site + energy_type
    overlap = check_contract_overlap(db, data.site_id, energy_type, start, end)
    if overlap:
        raise HTTPException(
            status_code=409,
            detail=f"Chevauchement avec le contrat #{overlap.id} "
                   f"({overlap.supplier_name}, "
                   f"{overlap.start_date or '...'} → {overlap.end_date or '...'})",
        )

    contract = EnergyContract(
        site_id=data.site_id,
        energy_type=energy_type,
        supplier_name=data.supplier_name,
        start_date=start,
        end_date=end,
        price_ref_eur_per_kwh=data.price_ref_eur_per_kwh,
        fixed_fee_eur_per_month=data.fixed_fee_eur_per_month,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return {"status": "created", "contract_id": contract.id}


@router.get("/contracts", response_model=ContractListResponse)
def list_contracts(
    request: Request,
    site_id: Optional[int] = Query(None),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List contracts, optionally filtered by site."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    q = _org_sites_query(db, EnergyContract, effective_org_id)
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
    request: Request,
    file: UploadFile = File(...),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Import invoices from CSV (idempotent).
    A re-upload of the same file (same org + same SHA-256) is rejected.
    Expected columns: site_id,invoice_number,period_start,period_end,issue_date,total_eur,energy_kwh,source
    Optional line columns: line_type,line_label,line_qty,line_unit,line_unit_price,line_amount_eur
    """
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Le fichier doit etre un CSV")

    content = file.file.read().decode("utf-8-sig")

    # --- Idempotency check (content hash) ---
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing_batch = db.query(BillingImportBatch).filter(
        BillingImportBatch.content_hash == content_hash,
        BillingImportBatch.org_id == effective_org_id,
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

            # Verify site exists and belongs to org
            site = (
                db.query(Site)
                .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
                .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
                .filter(Site.id == site_id, EntiteJuridique.organisation_id == effective_org_id)
                .first()
            )
            if not site:
                errors.append({"row": row_num, "error": f"Site {site_id} introuvable ou accès refusé"})
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
        org_id=effective_org_id,
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

@router.get("/import/batches", response_model=dict)
def list_import_batches(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List CSV import batches with stats."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    batches = (
        db.query(BillingImportBatch)
        .filter(BillingImportBatch.org_id == effective_org_id)
        .order_by(BillingImportBatch.imported_at.desc())
        .all()
    )
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
def create_invoice(
    data: InvoiceCreate,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create a single invoice manually."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    _check_site_belongs_to_org(db, data.site_id, effective_org_id)

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
def audit_invoice_endpoint(
    invoice_id: int,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Run shadow billing + anomaly engine on a persisted invoice."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    # Verify invoice belongs to org
    invoice = _org_sites_query(db, EnergyInvoice, effective_org_id).filter(
        EnergyInvoice.id == invoice_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée ou accès refusé")
    result = audit_invoice_full(db, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/audit-all")
def audit_all_invoices(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Audit all imported invoices (scoped to org)."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    invoices = _org_sites_query(db, EnergyInvoice, effective_org_id).all()
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

@router.get("/summary", response_model=BillingSummaryResponse)
def billing_summary(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Aggregate billing summary (invoices, insights, losses) — scoped to org."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    site_ids = _get_org_site_ids(db, effective_org_id)

    invoices = db.query(EnergyInvoice).filter(
        EnergyInvoice.site_id.in_(site_ids)
    ).all() if site_ids else []

    insights = db.query(BillingInsight).filter(
        BillingInsight.site_id.in_(site_ids)
    ).all() if site_ids else []

    total_eur = sum(i.total_eur or 0 for i in invoices)
    total_kwh = sum(i.energy_kwh or 0 for i in invoices)
    total_loss = sum(i.estimated_loss_eur or 0 for i in insights)
    by_type: dict = {}
    for i in insights:
        by_type[i.type] = by_type.get(i.type, 0) + 1
    by_severity: dict = {}
    for i in insights:
        by_severity[i.severity] = by_severity.get(i.severity, 0) + 1

    return {
        "total_invoices": len(invoices),
        "total_eur": round(total_eur, 2),
        "total_kwh": round(total_kwh, 0),
        "total_insights": len(insights),
        "total_estimated_loss_eur": round(total_loss, 2),
        "insights_by_type": by_type,
        "insights_by_severity": by_severity,
        "invoices_with_anomalies": len([i for i in invoices if i.status == BillingInvoiceStatus.ANOMALY]),
        "invoices_clean": len([i for i in invoices if i.status == BillingInvoiceStatus.AUDITED]),
    }


@router.get("/insights", response_model=InsightListResponse)
def list_insights(
    request: Request,
    site_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List billing insights with optional filters (site, severity, status) — scoped to org."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    q = _org_sites_query(db, BillingInsight, effective_org_id)
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
def patch_insight(
    insight_id: int,
    data: InsightPatch,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Update insight status / owner / notes (ops workflow) — scoped to org."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    insight = _org_sites_query(db, BillingInsight, effective_org_id).filter(
        BillingInsight.id == insight_id
    ).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight non trouve ou accès refusé")

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
def resolve_insight(
    insight_id: int,
    request: Request,
    notes: Optional[str] = Query(None),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Shortcut: mark insight as RESOLVED with optional notes — scoped to org."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    insight = _org_sites_query(db, BillingInsight, effective_org_id).filter(
        BillingInsight.id == insight_id
    ).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight non trouve ou accès refusé")

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


@router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices(
    request: Request,
    site_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List invoices with optional filters — scoped to org."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    q = _org_sites_query(db, EnergyInvoice, effective_org_id)
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


@router.get("/site/{site_id}", response_model=dict)
def site_billing_endpoint(
    site_id: int,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Full billing view for a site (contracts, invoices, insights) — scoped to org."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    _check_site_belongs_to_org(db, site_id, effective_org_id)
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
# PDF Import (V66 P2.2)
# ========================================

@router.post("/import-pdf")
async def import_invoice_pdf(
    request: Request,
    site_id: int = Query(...),
    file: UploadFile = File(...),
    run_audit: bool = Query(True),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Upload PDF facture → parse EDF/Engie templates → normalise → stocke → audit."""
    from app.bill_intelligence.parsers.pdf_parser import parse_pdf_bytes

    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    _check_site_belongs_to_org(db, site_id, effective_org_id)

    content = await file.read()
    invoice_domain = parse_pdf_bytes(content, file.filename or "upload.pdf")

    if not invoice_domain or invoice_domain.confidence < 0.5:
        raise HTTPException(
            status_code=422,
            detail="PDF non reconnu ou confiance insuffisante (< 0.5). "
                   "Vérifiez le format EDF/Engie ou saisissez manuellement.",
        )

    db_invoice = EnergyInvoice(
        site_id=site_id,
        invoice_number=invoice_domain.invoice_id or f"PDF-{file.filename}",
        period_start=invoice_domain.period_start,
        period_end=invoice_domain.period_end,
        issue_date=invoice_domain.invoice_date,
        total_eur=invoice_domain.total_ttc,
        energy_kwh=invoice_domain.total_kwh,
        status=BillingInvoiceStatus.IMPORTED,
        source="pdf",
        raw_json=json.dumps({
            "supplier": invoice_domain.supplier,
            "confidence": invoice_domain.confidence,
            "filename": file.filename,
        }),
    )
    db.add(db_invoice)
    db.flush()

    anomalies_count = 0
    if run_audit:
        result = audit_invoice_full(db, db_invoice.id)
        anomalies_count = len(result.get("anomalies", []))

    db.commit()
    return {
        "status": "imported",
        "invoice_id": db_invoice.id,
        "confidence": invoice_domain.confidence,
        "supplier": invoice_domain.supplier,
        "anomalies_count": anomalies_count,
    }


# ========================================
# Anomalies scoped (V66 P2.8)
# ========================================

@router.get("/anomalies-scoped")
def get_billing_anomalies_scoped(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """BillingInsights OPEN de l'org → format Patrimoine anomalies pour AnomaliesPage."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    insights = (
        _org_sites_query(db, BillingInsight, effective_org_id)
        .filter(BillingInsight.insight_status == InsightStatus.OPEN)
        .order_by(BillingInsight.estimated_loss_eur.desc().nullslast())
        .all()
    )

    anomalies = []
    for i in insights:
        site = db.query(Site).filter(Site.id == i.site_id).first()
        anomalies.append({
            "code": i.type or "billing_anomaly",
            "severity": (i.severity or "MEDIUM").upper(),
            "title_fr": i.message or "Anomalie facturation",
            "detail_fr": i.notes or i.message or "",
            "fix_hint_fr": "Vérifier la facture dans le module Facturation.",
            "business_impact": {"estimated_risk_eur": i.estimated_loss_eur or 0},
            "priority_score": 90 if i.severity == "CRITICAL" else 70 if i.severity == "HIGH" else 50,
            "framework": "FACTURATION",
            "site_id": i.site_id,
            "site_nom": site.nom if site else f"Site {i.site_id}",
            "insight_id": i.id,
        })

    return {"anomalies": anomalies, "count": len(anomalies)}


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


def check_contract_overlap(
    db: Session,
    site_id: int,
    energy_type: BillingEnergyType,
    start_date: Optional[date],
    end_date: Optional[date],
    exclude_id: Optional[int] = None,
) -> Optional[EnergyContract]:
    """Return first overlapping contract, or None.

    Overlap rule: (startA <= endB) AND (startB <= endA).
    NULL start = open-ended past (−∞).  NULL end = open-ended future (+∞).
    """
    q = db.query(EnergyContract).filter(
        EnergyContract.site_id == site_id,
        EnergyContract.energy_type == energy_type,
    )
    if exclude_id is not None:
        q = q.filter(EnergyContract.id != exclude_id)

    for c in q.all():
        # startA <= endB  (if either is None, condition is True)
        cond1 = (start_date is None or c.end_date is None or start_date <= c.end_date)
        # startB <= endA  (if either is None, condition is True)
        cond2 = (c.start_date is None or end_date is None or c.start_date <= end_date)
        if cond1 and cond2:
            return c
    return None
