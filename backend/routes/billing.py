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
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, UploadFile, File
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Site,
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    BillingInsight,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
    InsightStatus,
    BillingImportBatch,
    Portefeuille,
    EntiteJuridique,
    ActionItem,
    ActionSourceType,
)
from services.billing_service import (
    audit_invoice_full,
    get_billing_summary,
    get_site_billing,
    shadow_billing_simple,
    BILLING_RULES,
)
from middleware.auth import get_optional_auth, require_admin, AuthContext
from middleware.rate_limit import check_rate_limit
from services.scope_utils import resolve_org_id
from services.billing_reconcile import auto_reconcile_after_import
from schemas.contract_perimeter import ContractPerimeter

router = APIRouter(prefix="/api/billing", tags=["Bill Intelligence V2"])


# ========================================
# Pydantic schemas — Input
# ========================================


class ContractCreate(BaseModel):
    site_id: int = Field(..., ge=1)
    energy_type: str = Field(..., max_length=20)  # elec / gaz
    supplier_name: str = Field(..., min_length=1, max_length=200)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    price_ref_eur_per_kwh: Optional[float] = Field(None, ge=0, le=10)
    fixed_fee_eur_per_month: Optional[float] = Field(None, ge=0, le=1e6)


class InvoiceCreate(BaseModel):
    site_id: int = Field(..., ge=1)
    contract_id: Optional[int] = Field(None, ge=1)
    invoice_number: str = Field(..., min_length=1, max_length=100)
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    issue_date: Optional[str] = None
    total_eur: Optional[float] = Field(None, ge=0, le=1e8)
    energy_kwh: Optional[float] = Field(None, ge=0, le=1e9)
    lines: Optional[List[dict]] = Field(None, max_length=100)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class BillingSummaryResponse(BaseModel):
    total_invoices: int
    total_eur: float
    total_kwh: float
    total_insights: int
    total_estimated_loss_eur: float
    total_loss_eur: float = 0
    coverage_months: int = 0
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
                "id": c.id,
                "site_id": c.site_id,
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
    check_rate_limit(request, key_prefix="billing_import", max_requests=20, window_seconds=60)
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    fname = (file.filename or "").lower()
    if not fname.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Le fichier doit etre un CSV")
    if file.content_type and file.content_type not in (
        "text/csv",
        "text/plain",
        "application/vnd.ms-excel",
        "application/octet-stream",
    ):
        raise HTTPException(status_code=400, detail="Type MIME invalide — CSV attendu")

    raw = file.file.read()
    if len(raw) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 50 Mo)")
    content = raw.decode("utf-8-sig")

    # --- Idempotency check (content hash) ---
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    existing_batch = (
        db.query(BillingImportBatch)
        .filter(
            BillingImportBatch.content_hash == content_hash,
            BillingImportBatch.org_id == effective_org_id,
        )
        .first()
    )
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
            existing = (
                db.query(EnergyInvoice)
                .filter(
                    EnergyInvoice.site_id == site_id,
                    EnergyInvoice.invoice_number == invoice_number,
                )
                .first()
            )
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

    # --- Auto-reconciliation compteur/facture (Step 9 B3) ---
    reconcile_results = []
    for inv in invoices_created:
        if inv.period_start and inv.period_end:
            r = auto_reconcile_after_import(db, inv.site_id, inv.period_start, inv.period_end)
            if r:
                reconcile_results.append(r)
    if reconcile_results:
        db.commit()

    return {
        "status": "ok",
        "batch_id": batch.id,
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "error_count": len(errors),
        "reconciliation": reconcile_results,
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
    invoice = _org_sites_query(db, EnergyInvoice, effective_org_id).filter(EnergyInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée ou accès refusé")
    result = audit_invoice_full(db, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/invoices/{invoice_id}/shadow-breakdown")
def get_shadow_breakdown(
    invoice_id: int,
    request: Request,
    org_id: Optional[int] = Query(None),
    engine: Optional[str] = Query(None, description="v1=legacy, v2=new engine"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Shadow breakdown par composante (fourniture / TURPE / taxes / TVA)."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    invoice = _org_sites_query(db, EnergyInvoice, effective_org_id).filter(EnergyInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Facture non trouvée ou accès refusé")

    # V2 engine (new deterministic reconstitution)
    if engine != "v1":
        try:
            return _compute_breakdown_v2(db, invoice)
        except Exception as e:
            logger.warning("Billing engine V2 failed for invoice %s: %s — falling back to V1", invoice_id, str(e)[:200])
            if engine == "v2":
                raise HTTPException(status_code=500, detail=f"Erreur billing engine V2: {str(e)[:200]}")

    # V1 legacy fallback
    try:
        from services.billing_shadow_v2 import compute_shadow_breakdown

        result = compute_shadow_breakdown(db, invoice)
        result["fallback_used"] = True
        return result
    except Exception as e:
        logger.warning("Shadow breakdown V1 failed for invoice %s: %s", invoice_id, str(e)[:200])
        raise HTTPException(status_code=500, detail="Erreur lors du calcul du shadow breakdown")


def _compute_breakdown_v2(db: Session, invoice) -> dict:
    """
    Adapter: bridge the new billing engine into the shadow-breakdown API shape.
    Reads contract data from DB, calls the deterministic engine, returns
    a dict compatible with the frontend ShadowBreakdownCard.
    """
    from services.billing_engine.engine import (
        build_invoice_reconstitution,
        compare_to_supplier_invoice,
    )
    from services.billing_engine.types import TariffOption, InvoiceType

    # ── Resolve contract ─────────────────────────────────────────────────
    contract = None
    if invoice.contract_id:
        contract = db.query(EnergyContract).filter(EnergyContract.id == invoice.contract_id).first()

    # ── Extract inputs from contract + invoice ───────────────────────────
    energy_type = "ELEC"
    if contract and hasattr(contract, "energy_type"):
        et = getattr(contract.energy_type, "value", str(contract.energy_type))
        if "gaz" in et.lower() or "gas" in et.lower():
            energy_type = "GAZ"

    subscribed_power = getattr(contract, "subscribed_power_kva", None) if contract else None

    # Map DB enum to engine enum
    tariff_option = None
    if contract and getattr(contract, "tariff_option", None):
        opt_map = {
            "base": TariffOption.BASE,
            "hp_hc": TariffOption.HP_HC,
            "cu": TariffOption.CU,
            "mu": TariffOption.MU,
            "lu": TariffOption.LU,
        }
        raw = getattr(contract.tariff_option, "value", str(contract.tariff_option))
        tariff_option = opt_map.get(raw.lower())

    # Invoice type
    invoice_type = InvoiceType.NORMAL
    if hasattr(invoice, "invoice_type") and invoice.invoice_type:
        it_map = {
            "normal": InvoiceType.NORMAL,
            "advance": InvoiceType.ADVANCE,
            "regularization": InvoiceType.REGULARIZATION,
            "credit_note": InvoiceType.CREDIT_NOTE,
        }
        raw = getattr(invoice.invoice_type, "value", str(invoice.invoice_type))
        invoice_type = it_map.get(raw.lower(), InvoiceType.NORMAL)

    # kWh by period — from invoice lines if available
    kwh_by_period = {}
    lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == invoice.id).all()
    for line in lines:
        pc = getattr(line, "period_code", None)
        if pc and line.qty:
            kwh_by_period[pc] = kwh_by_period.get(pc, 0) + line.qty

    # Fallback: if no period breakdown, use total kwh as BASE
    if not kwh_by_period and invoice.energy_kwh:
        kwh_by_period = {"BASE": invoice.energy_kwh}

    # Supply prices from contract
    supply_prices = {}
    if contract:
        price_map = {
            "HPE": "price_hpe_eur_kwh",
            "HCE": "price_hce_eur_kwh",
            "HP": "price_hp_eur_kwh",
            "HC": "price_hc_eur_kwh",
            "BASE": "price_base_eur_kwh",
        }
        for period, attr in price_map.items():
            val = getattr(contract, attr, None)
            if val is not None:
                supply_prices[period] = val
        # Fallback to generic price_ref
        if not supply_prices and getattr(contract, "price_ref_eur_per_kwh", None):
            for period in kwh_by_period:
                supply_prices[period] = contract.price_ref_eur_per_kwh

    # Period
    period_start = invoice.period_start or invoice.issue_date or date.today()
    period_end = invoice.period_end or (period_start + __import__("datetime").timedelta(days=30))

    fixed_fee = getattr(contract, "fixed_fee_eur_per_month", 0) or 0

    # ── Call engine ──────────────────────────────────────────────────────
    result = build_invoice_reconstitution(
        energy_type=energy_type,
        subscribed_power_kva=subscribed_power,
        tariff_option=tariff_option,
        kwh_by_period=kwh_by_period,
        supply_prices_by_period=supply_prices,
        period_start=period_start,
        period_end=period_end,
        invoice_type=invoice_type,
        fixed_fee_eur_month=fixed_fee,
    )

    # ── Compare to supplier ──────────────────────────────────────────────
    supplier_ttc = invoice.total_eur or 0
    comparison = compare_to_supplier_invoice(result, supplier_ttc) if supplier_ttc > 0 else None

    # ── Resolve site for identification ─────────────────────────────────
    site = None
    if invoice.site_id:
        try:
            from models.energy_models import Site

            site = db.query(Site).filter(Site.id == invoice.site_id).first()
        except Exception:
            pass

    from services.billing_shadow_v2 import _extract_pdl_prm, _compute_reconstitution_meta

    pdl_prm = _extract_pdl_prm(invoice, site)
    supplier_name = getattr(contract, "supplier_name", None) if contract else None
    site_name = getattr(site, "nom", None) or getattr(site, "name", None) if site else None

    # ── Format response (compatible with frontend) ───────────────────────
    components_out = []
    for c in result.components:
        comp_status = c.gap_status or "unknown"
        comp_status_message = None
        expected_ht = c.amount_ht
        if c.code == "fourniture" and not supply_prices:
            comp_status = "missing_price"
            comp_status_message = "Prix de fourniture non disponible — contrat ou offre requis"
            expected_ht = None
        comp = {
            "code": c.code,
            "label": c.label,
            "expected_ht": expected_ht,
            "tva_rate": c.tva_rate,
            "tva": c.amount_tva,
            "ttc": c.amount_ttc,
            "formula": c.formula_used,
            "inputs": c.inputs_used,
            "gap_eur": c.gap_eur if expected_ht is not None else None,
            "gap_pct": c.gap_pct if expected_ht is not None else None,
            "gap_status": comp_status,
            "status": comp_status,
            "status_message": comp_status_message,
            "rate_sources": [
                {"code": rs.code, "rate": rs.rate, "unit": rs.unit, "source": rs.source} for rs in c.rate_sources
            ],
            "source_ref": c.rate_sources[0].source if c.rate_sources else None,
        }
        if c.supplier_amount_ht is not None:
            comp["invoice_ht"] = c.supplier_amount_ht
        components_out.append(comp)

    recon_meta = _compute_reconstitution_meta(components_out)

    return {
        "engine_version": result.engine_version,
        "status": result.status.value,
        # IDENTIFICATION FACTURE (P0.1)
        "invoice_id": invoice.id,
        "invoice_number": getattr(invoice, "invoice_number", None),
        "period_start": str(period_start) if period_start else None,
        "period_end": str(period_end) if period_end else None,
        "period_days": result.prorata_days,
        "pdl_prm": pdl_prm,
        "supplier": supplier_name,
        "site_name": site_name,
        # RECONSTITUTION META (P0.3/P0.4)
        "reconstitution_status": recon_meta["reconstitution_status"],
        "reconstitution_label": recon_meta["reconstitution_label"],
        "missing_components": recon_meta["missing_components"],
        "confidence": recon_meta["confidence"],
        "confidence_label": recon_meta["confidence_label"],
        "confidence_rationale": recon_meta["confidence_rationale"],
        # STANDARD
        "segment": result.segment.value,
        "tariff_option": result.tariff_option.value,
        "energy_type": result.energy_type,
        "total_expected_ht": result.total_ht,
        "total_expected_ttc": result.total_ttc,
        "total_tva": result.total_tva,
        "total_tva_reduite": result.total_tva_reduite,
        "total_tva_normale": result.total_tva_normale,
        "total_invoice_ttc": supplier_ttc if supplier_ttc > 0 else None,
        "total_gap_eur": comparison["global_gap_eur"] if comparison else None,
        "total_gap_pct": comparison["global_gap_pct"] if comparison else None,
        "total_gap_status": comparison["global_status"] if comparison else "unknown",
        "components": components_out,
        "kwh": result.kwh_total,
        "kwh_by_period": result.kwh_by_period,
        "days_in_period": result.prorata_days,
        "prorata_factor": round(result.prorata_factor, 6),
        "subscribed_power_kva": result.subscribed_power_kva,
        "puissance_kva": result.subscribed_power_kva,
        "missing_inputs": result.missing_inputs,
        "assumptions": result.assumptions,
        "hypotheses": result.assumptions,
        "warnings": result.warnings,
        "catalog_version": result.catalog_version,
        "expert": {
            "engine": result.engine_version,
            "catalog": result.catalog_version,
            "segment": result.segment.value,
            "method": "billing_engine_v2",
            "tariff_source": "regulated_tariffs",
        },
    }


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
    reconcile_results = []
    for inv in invoices:
        r = audit_invoice_full(db, inv.id)
        results.append(
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "anomalies_count": r.get("anomalies_count", 0),
            }
        )
        # Auto-reconciliation compteur/facture (Step 9 B3)
        if inv.period_start and inv.period_end:
            rc = auto_reconcile_after_import(db, inv.site_id, inv.period_start, inv.period_end)
            if rc:
                reconcile_results.append(rc)
    if reconcile_results:
        db.commit()
    return {
        "status": "ok",
        "audited": len(results),
        "total_anomalies": sum(r["anomalies_count"] for r in results),
        "results": results,
        "reconciliation": reconcile_results,
    }


# ========================================
# Reconcile-all (Step 9 B3)
# ========================================


@router.post("/reconcile-all")
def reconcile_all_sites(
    request: Request,
    org_id: Optional[int] = Query(None),
    months: int = Query(12, ge=1, le=36),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Reconciliation compteur/facture pour tous les sites de l'org sur N mois."""
    check_rate_limit(request, key_prefix="billing_reconcile", max_requests=5, window_seconds=60)
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    site_ids = _get_org_site_ids(db, effective_org_id)

    end = date.today()
    start = date(end.year, end.month, 1) - timedelta(days=months * 30)

    results = []
    for sid in site_ids:
        r = auto_reconcile_after_import(db, sid, start, end)
        if r:
            results.append(r)

    db.commit()

    mismatches = [r for r in results if r.get("status") == "mismatch_created"]
    return {
        "status": "ok",
        "sites_checked": len(site_ids),
        "mismatches_created": len(mismatches),
        "results": results,
    }


# ========================================
# Read endpoints
# ========================================


@router.get("/summary", response_model=BillingSummaryResponse)
def billing_summary(
    request: Request,
    org_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Aggregate billing summary (invoices, insights, losses) — scoped to org, optionally to site."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    site_ids = [site_id] if site_id else _get_org_site_ids(db, effective_org_id)

    invoices = db.query(EnergyInvoice).filter(EnergyInvoice.site_id.in_(site_ids)).all() if site_ids else []

    insights = db.query(BillingInsight).filter(BillingInsight.site_id.in_(site_ids)).all() if site_ids else []

    total_eur = sum(i.total_eur or 0 for i in invoices)
    total_kwh = sum(i.energy_kwh or 0 for i in invoices)
    total_loss = sum(i.estimated_loss_eur or 0 for i in insights)
    by_type: dict = {}
    for i in insights:
        by_type[i.type] = by_type.get(i.type, 0) + 1
    by_severity: dict = {}
    for i in insights:
        by_severity[i.severity] = by_severity.get(i.severity, 0) + 1

    # Distinct months covered by invoices
    distinct_months = set()
    for inv in invoices:
        if inv.period_start:
            distinct_months.add((inv.period_start.year, inv.period_start.month))

    loss_rounded = round(total_loss, 2)

    return {
        "total_invoices": len(invoices),
        "total_eur": round(total_eur, 2),
        "total_kwh": round(total_kwh, 0),
        "total_insights": len(insights),
        "total_estimated_loss_eur": loss_rounded,
        "total_loss_eur": loss_rounded,
        "coverage_months": len(distinct_months),
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

    # Resolve action_id for each insight (batch query via source_id)
    insight_ids_str = [str(i.id) for i in insights]
    action_map = {}
    if insight_ids_str:
        actions = (
            db.query(ActionItem.source_id, ActionItem.id)
            .filter(
                ActionItem.source_type == ActionSourceType.BILLING,
                ActionItem.source_id.in_(insight_ids_str),
            )
            .all()
        )
        action_map = {a.source_id: a.id for a in actions}

    # P1.5: Resolve supplier name for each insight via invoice → contract
    supplier_map = {}
    invoice_ids = [i.invoice_id for i in insights if i.invoice_id]
    if invoice_ids:
        inv_rows = (
            db.query(EnergyInvoice.id, EnergyContract.supplier_name)
            .outerjoin(EnergyContract, EnergyInvoice.contract_id == EnergyContract.id)
            .filter(EnergyInvoice.id.in_(invoice_ids))
            .all()
        )
        supplier_map = {r[0]: r[1] for r in inv_rows if r[1]}

    return {
        "insights": [
            {
                "id": i.id,
                "site_id": i.site_id,
                "invoice_id": i.invoice_id,
                "type": i.type,
                "severity": i.severity,
                "message": i.message,
                "estimated_loss_eur": i.estimated_loss_eur,
                "insight_status": i.insight_status.value if i.insight_status else "open",
                "owner": i.owner,
                "notes": i.notes,
                "action_id": action_map.get(str(i.id)),
                "supplier": supplier_map.get(i.invoice_id),
            }
            for i in insights
        ],
        "count": len(insights),
    }


@router.get("/insights/{insight_id}")
def get_insight_detail(
    insight_id: int,
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'un insight avec metrics et recommended_actions."""
    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    insight = db.query(BillingInsight).filter(BillingInsight.id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")
    _check_site_belongs_to_org(db, insight.site_id, effective_org_id)
    # Resolve linked action
    action = (
        db.query(ActionItem)
        .filter(
            ActionItem.source_type == ActionSourceType.BILLING,
            ActionItem.source_id == str(insight.id),
        )
        .first()
    )

    metrics = json.loads(insight.metrics_json or "{}")

    # Recalcul V2 à la demande si breakdown absent (metrics peut être {} ou None-like)
    if metrics.get("expected_ttc") is None and metrics.get("expected_fourniture_ht") is None:
        try:
            from services.billing_shadow_v2 import shadow_billing_v2

            invoice = db.query(EnergyInvoice).filter(EnergyInvoice.id == insight.invoice_id).first()
            if invoice:
                lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == invoice.id).all()
                contract = None
                if invoice.contract_id:
                    contract = db.query(EnergyContract).filter(EnergyContract.id == invoice.contract_id).first()
                if lines:
                    v2 = shadow_billing_v2(invoice, lines, contract, db=db)
                    metrics.update(v2)
                    # Ajouter confidence/assumptions si absents
                    if "confidence" not in metrics:
                        metrics["confidence"] = "medium"
                    if "assumptions" not in metrics:
                        metrics["assumptions"] = [
                            "Tarifs POC simplifiés (CRE / DGFiP publique)",
                            "Calcul basé sur les lignes facture disponibles",
                        ]
                    # Persister pour éviter recalcul futur
                    insight.metrics_json = json.dumps(metrics)
                    db.commit()
        except Exception:
            pass  # Garder métriques originales

    # Invoice identification (P0.1)
    invoice_ident = {}
    inv = db.query(EnergyInvoice).filter(EnergyInvoice.id == insight.invoice_id).first() if insight.invoice_id else None
    if inv:
        from services.billing_shadow_v2 import _extract_pdl_prm, _resolve_segment

        inv_site, inv_contract = None, None
        if inv.site_id:
            try:
                from models.energy_models import Site

                inv_site = db.query(Site).filter(Site.id == inv.site_id).first()
            except Exception:
                pass
        if inv.contract_id:
            inv_contract = db.query(EnergyContract).filter(EnergyContract.id == inv.contract_id).first()
        p_s, p_e = inv.period_start, inv.period_end
        invoice_ident = {
            "invoice_number": inv.invoice_number,
            "period_start": str(p_s) if p_s else None,
            "period_end": str(p_e) if p_e else None,
            "period_days": (p_e - p_s).days if p_s and p_e else None,
            "pdl_prm": _extract_pdl_prm(inv, inv_site),
            "supplier": getattr(inv_contract, "supplier_name", None) if inv_contract else None,
            "segment": _resolve_segment(inv_contract, inv_site) if inv_contract else None,
            "puissance_kva": getattr(inv_contract, "subscribed_power_kva", None) if inv_contract else None,
            "kwh_total": inv.energy_kwh,
            "site_name": getattr(inv_site, "nom", None) or getattr(inv_site, "name", None) if inv_site else None,
        }

    return {
        "id": insight.id,
        "site_id": insight.site_id,
        "invoice_id": insight.invoice_id,
        "type": insight.type,
        "severity": insight.severity,
        "message": insight.message,
        "estimated_loss_eur": insight.estimated_loss_eur,
        "insight_status": insight.insight_status.value if insight.insight_status else "open",
        "owner": insight.owner,
        "notes": insight.notes,
        "action_id": action.id if action else None,
        "metrics": metrics,
        "invoice_identification": invoice_ident,
        "recommended_actions": json.loads(insight.recommended_actions_json or "[]"),
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
    insight = _org_sites_query(db, BillingInsight, effective_org_id).filter(BillingInsight.id == insight_id).first()
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
    insight = _org_sites_query(db, BillingInsight, effective_org_id).filter(BillingInsight.id == insight_id).first()
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


@router.get("/invoices/normalized")
def list_invoices_normalized(
    request: Request,
    site_id: Optional[int] = Query(None),
    month_key: Optional[str] = Query(None, description="Filtre YYYY-MM"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Factures normalisées (ht/tva/fournisseur calculés) — scoped to org."""
    from services.billing_normalization import normalize_invoice

    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    q = _org_sites_query(db, EnergyInvoice, effective_org_id)
    if site_id:
        q = q.filter(EnergyInvoice.site_id == site_id)
    invoices = q.order_by(EnergyInvoice.period_start.desc().nullslast()).all()

    # Filtre month_key (post-query, simple)
    if month_key:
        filtered = []
        for inv in invoices:
            mk = None
            if inv.period_start:
                mk = inv.period_start.strftime("%Y-%m")
            elif inv.issue_date:
                mk = inv.issue_date.strftime("%Y-%m")
            if mk == month_key:
                filtered.append(inv)
        invoices = filtered

    total = len(invoices)
    page = invoices[offset : offset + limit]

    normalized = []
    for inv in page:
        lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == inv.id).all()
        contract = (
            db.query(EnergyContract).filter(EnergyContract.id == inv.contract_id).first() if inv.contract_id else None
        )
        normalized.append(normalize_invoice(inv, lines, contract, effective_org_id).model_dump())

    return {
        "invoices": normalized,
        "total": total,
        "offset": offset,
        "limit": limit,
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
                "id": i.id,
                "site_id": i.site_id,
                "invoice_number": i.invoice_number,
                "period_start": str(i.period_start) if i.period_start else None,
                "period_end": str(i.period_end) if i.period_end else None,
                "total_eur": i.total_eur,
                "energy_kwh": i.energy_kwh,
                "status": i.status.value if i.status else None,
                "source": i.source,
                "energy_type": i.contract.energy_type.value.upper() if i.contract and i.contract.energy_type else None,
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
        "rules": [{"id": r[0], "name": r[1]} for r in BILLING_RULES],
        "count": len(BILLING_RULES),
    }


# ========================================
# PDF Import (V66 P2.2 / DoD P0-1)
# ========================================

# ComponentType.value (lowercase) → InvoiceLineType mapping for P0-1
_COMPONENT_TO_LINE_TYPE = {
    # Abonnement — fourniture (subscription part of energy supply)
    "abonnement": InvoiceLineType.ENERGY,
    # Energie / fourniture
    "conso_hp": InvoiceLineType.ENERGY,
    "conso_hc": InvoiceLineType.ENERGY,
    "conso_base": InvoiceLineType.ENERGY,
    "conso_pointe": InvoiceLineType.ENERGY,
    "conso_hph": InvoiceLineType.ENERGY,
    "conso_hch": InvoiceLineType.ENERGY,
    "conso_hpe": InvoiceLineType.ENERGY,
    "conso_hce": InvoiceLineType.ENERGY,
    "terme_variable": InvoiceLineType.ENERGY,
    # Réseau / acheminement
    "turpe_fixe": InvoiceLineType.NETWORK,
    "turpe_puissance": InvoiceLineType.NETWORK,
    "turpe_energie": InvoiceLineType.NETWORK,
    "terme_fixe": InvoiceLineType.NETWORK,
    # Capacité / dépassement
    "depassement_puissance": InvoiceLineType.NETWORK,
    "reactive": InvoiceLineType.NETWORK,
    # Taxes / contributions
    "cta": InvoiceLineType.TAX,
    "accise": InvoiceLineType.TAX,
    "tva_reduite": InvoiceLineType.TAX,
    "tva_normale": InvoiceLineType.TAX,
    "cee": InvoiceLineType.TAX,
    # Ajustements
    "regularisation": InvoiceLineType.OTHER,
    "prorata": InvoiceLineType.OTHER,
    "remise": InvoiceLineType.OTHER,
    "penalite": InvoiceLineType.OTHER,
}


def _component_to_line_type(comp_type) -> InvoiceLineType:
    """Mappe ComponentType.value (str lowercase) → InvoiceLineType. Fallback = OTHER."""
    key = comp_type.value if hasattr(comp_type, "value") else str(comp_type)
    return _COMPONENT_TO_LINE_TYPE.get(key, InvoiceLineType.OTHER)


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
    check_rate_limit(request, key_prefix="billing_import", max_requests=20, window_seconds=60)
    from app.bill_intelligence.parsers.pdf_parser import parse_pdf_bytes

    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    _check_site_belongs_to_org(db, site_id, effective_org_id)

    fname = (file.filename or "").lower()
    if not fname.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Le fichier doit etre un PDF")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF trop volumineux (max 20 Mo)")
    invoice_domain = parse_pdf_bytes(content, file.filename or "upload.pdf")

    confidence = getattr(invoice_domain, "parsing_confidence", 0) or 0
    if not invoice_domain or confidence < 0.5:
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
        energy_kwh=getattr(invoice_domain, "conso_kwh", None),  # P0-3: correct field name
        status=BillingInvoiceStatus.IMPORTED,
        source="pdf",
        raw_json=json.dumps(
            {
                "supplier": getattr(invoice_domain, "supplier", "") or "",
                "confidence": getattr(invoice_domain, "parsing_confidence", 0) or 0,
                "filename": file.filename or "",
                "pdl_prm": getattr(invoice_domain, "pdl_pce", None) or "",  # P0-3: store PDL
            }
        ),
    )
    db.add(db_invoice)
    db.flush()

    # P0-1: créer les lignes EnergyInvoiceLine depuis les composantes PDF
    for comp in getattr(invoice_domain, "components", None) or []:
        line_type = _component_to_line_type(comp.component_type)
        # Preserve tax_code and other metadata from parsed components
        comp_meta = getattr(comp, "metadata", None) or {}
        meta_str = json.dumps(comp_meta) if comp_meta else None
        db.add(
            EnergyInvoiceLine(
                invoice_id=db_invoice.id,
                line_type=line_type,
                label=getattr(comp, "label", "") or "",
                qty=getattr(comp, "quantity", None),
                unit=getattr(comp, "unit", None),
                unit_price=getattr(comp, "unit_price", None),
                amount_eur=(
                    comp.amount_ht
                    if getattr(comp, "amount_ht", None) is not None
                    else getattr(comp, "amount_ttc", None)
                ),
                meta_json=meta_str,
            )
        )

    anomalies_list = []
    if run_audit:
        result = audit_invoice_full(db, db_invoice.id)
        anomalies_list = result.get("anomalies", [])

    db.commit()

    # --- Auto-reconciliation compteur/facture (Step 9 B3) ---
    reconcile_result = None
    if db_invoice.period_start and db_invoice.period_end:
        reconcile_result = auto_reconcile_after_import(db, site_id, db_invoice.period_start, db_invoice.period_end)
        if reconcile_result:
            db.commit()

    return {
        "status": "imported",
        "invoice_id": db_invoice.id,
        "confidence": round(float(confidence), 2),
        "supplier": getattr(invoice_domain, "supplier", "") or "",
        "anomalies_count": len(anomalies_list),
        "kb_updated": run_audit,  # P0-5
        "kb_rules_applied": [a.get("rule_id") for a in anomalies_list],  # P0-5
        "reconciliation": reconcile_result,
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

    # Fix N+1 : charger tous les sites en une seule requête
    site_ids = list({i.site_id for i in insights})
    sites_map = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()} if site_ids else {}

    anomalies = []
    for i in insights:
        site = sites_map.get(i.site_id)
        anomalies.append(
            {
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
            }
        )

    return {"anomalies": anomalies, "count": len(anomalies)}


# ========================================
# V67 — Coverage endpoints
# ========================================


@router.get("/periods")
def get_billing_periods(
    request: Request,
    site_id: Optional[int] = Query(None),
    month_from: Optional[str] = Query(None, description="YYYY-MM"),
    month_to: Optional[str] = Query(None, description="YYYY-MM"),
    limit: int = Query(24, ge=1, le=120),
    offset: int = Query(0, ge=0),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Liste des périodes mensuelles avec statut de couverture (covered/partial/missing).
    Paginée (limit/offset). Tri: plus récent en premier.
    """
    from services.billing_coverage import compute_coverage, compute_range

    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    q = _org_sites_query(db, EnergyInvoice, effective_org_id)
    if site_id:
        site = _check_site_belongs_to_org(db, site_id, effective_org_id)
        q = q.filter(EnergyInvoice.site_id == site_id)
    invoices = q.all()

    range_start, range_end = compute_range(invoices)
    if not range_start or not range_end:
        return {"periods": [], "total": 0, "offset": offset, "limit": limit}

    # Appliquer filtres month_from / month_to
    if month_from:
        try:
            y, m = map(int, month_from.split("-"))
            from datetime import date as _date

            range_start = max(range_start, _date(y, m, 1))
        except (ValueError, TypeError):
            pass
    if month_to:
        try:
            y, m = map(int, month_to.split("-"))
            from calendar import monthrange as _mr
            from datetime import date as _date

            _, last = _mr(y, m)
            range_end = min(range_end, _date(y, m, last))  # type: ignore[type-var]
        except (ValueError, TypeError):
            pass

    all_months = compute_coverage(invoices, range_start, range_end)
    # Tri: plus récent en premier
    all_months.sort(key=lambda x: x.month_key, reverse=True)
    total = len(all_months)
    page = all_months[offset : offset + limit]

    return {
        "periods": [
            {
                "month_key": mc.month_key,
                "month_start": mc.month_start.isoformat(),
                "month_end": mc.month_end.isoformat(),
                "coverage_status": mc.coverage_status,
                "coverage_ratio": mc.coverage_ratio,
                "invoices_count": mc.invoices_count,
                "total_ttc": mc.total_ttc,
                "missing_reason": mc.missing_reason,
                "energy_kwh": mc.energy_kwh,  # P0-2
                "pdl_prm": mc.pdl_prm,  # P0-2
                "invoice_ids": mc.invoice_ids,  # V70
            }
            for mc in page
        ],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/coverage")
@router.get("/coverage-summary")
def get_coverage_summary(
    request: Request,
    site_id: Optional[int] = Query(None),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    KPIs globaux de couverture : range, mois couverts/partiels/manquants,
    liste des mois manquants (max 24), top sites avec le plus de trous.
    """
    from services.billing_coverage import compute_coverage, compute_range, compute_top_sites_missing

    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    q = _org_sites_query(db, EnergyInvoice, effective_org_id)
    if site_id:
        _check_site_belongs_to_org(db, site_id, effective_org_id)
        q = q.filter(EnergyInvoice.site_id == site_id)
    invoices = q.all()

    range_start, range_end = compute_range(invoices)
    if not range_start:
        return {
            "range": None,
            "months_total": 0,
            "covered": 0,
            "partial": 0,
            "missing": 0,
            "missing_months": [],
            "top_sites_missing": [],
        }

    months = compute_coverage(invoices, range_start, range_end)
    covered = sum(1 for mc in months if mc.coverage_status == "covered")
    partial = sum(1 for mc in months if mc.coverage_status == "partial")
    missing = sum(1 for mc in months if mc.coverage_status == "missing")
    missing_months = [
        mc.month_key
        for mc in sorted(months, key=lambda x: x.month_key, reverse=True)
        if mc.coverage_status != "covered"
    ][:24]

    top_sites = compute_top_sites_missing(db, effective_org_id, site_id_filter=site_id)

    return {
        "range": {
            "min_month": range_start.strftime("%Y-%m"),
            "max_month": range_end.strftime("%Y-%m"),
        },
        "months_total": len(months),
        "covered": covered,
        "partial": partial,
        "missing": missing,
        "missing_months": missing_months,
        "top_sites_missing": top_sites,
    }


@router.get("/missing-periods")
def get_missing_periods(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    org_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Liste paginée des mois manquants/partiels, format patrimoine-anomaly.
    Triée par gravité (missing avant partial) puis par mois décroissant.
    Compatible avec AnomaliesPage (framework FACTURATION).
    """
    from services.billing_coverage import compute_coverage, compute_range

    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    # Charger toutes les factures + sites en 2 requêtes
    q = _org_sites_query(db, EnergyInvoice, effective_org_id)
    if site_id:
        q = q.filter(EnergyInvoice.site_id == site_id)
    invoices_all = q.all()

    # Grouper par site
    by_site: dict[int, list] = {}
    for inv in invoices_all:
        by_site.setdefault(inv.site_id, []).append(inv)

    site_ids = list(by_site.keys())
    sites_map = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()} if site_ids else {}

    all_missing: list = []
    for site_id_key, invs in by_site.items():
        rs, re = compute_range(invs)
        if not rs:
            continue
        months = compute_coverage(invs, rs, re)
        site = sites_map.get(site_id_key)
        site_name = site.nom if site else f"Site {site_id_key}"
        for mc in months:
            if mc.coverage_status != "covered":
                all_missing.append(
                    {
                        "month_key": mc.month_key,
                        "site_id": site_id_key,
                        "site_name": site_name,
                        "coverage_status": mc.coverage_status,
                        "coverage_ratio": mc.coverage_ratio,
                        "missing_reason": mc.missing_reason,
                        "regulatory_impact": {"framework": "FACTURATION"},
                        "cta_url": f"/bill-intel?site_id={site_id_key}&month={mc.month_key}",
                    }
                )

    # Tri: missing avant partial, puis mois décroissant
    status_order = {"missing": 0, "partial": 1}
    all_missing.sort(key=lambda x: (status_order.get(x["coverage_status"], 2), x["month_key"]), reverse=False)
    all_missing.sort(key=lambda x: x["month_key"], reverse=True)
    all_missing.sort(key=lambda x: status_order.get(x["coverage_status"], 2))

    total = len(all_missing)
    page = all_missing[offset : offset + limit]

    return {"items": page, "total": total, "offset": offset, "limit": limit}


# ========================================
# Seed demo
# ========================================


@router.post("/seed-demo")
def seed_demo(
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin()),
):
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


_MONTH_LABELS_FR = [
    "",
    "Janv",
    "Fév",
    "Mars",
    "Avr",
    "Mai",
    "Juin",
    "Juil",
    "Août",
    "Sept",
    "Oct",
    "Nov",
    "Déc",
]


@router.get("/compare-monthly")
def compare_monthly(
    request: Request,
    org_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Comparaison mensuelle N vs N-1.
    Agrège total_eur et energy_kwh par mois pour l'année courante et l'année précédente.
    """
    from datetime import datetime as dt

    from sqlalchemy import func as sa_func

    effective_org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    site_ids = _get_org_site_ids(db, effective_org_id)

    current_year = year
    if not current_year and site_ids:
        # Auto-detect latest year with invoice data
        latest = (
            db.query(sa_func.max(sa_func.strftime("%Y", EnergyInvoice.period_start)))
            .filter(EnergyInvoice.site_id.in_(site_ids), EnergyInvoice.total_eur > 0)
            .scalar()
        )
        current_year = int(latest) if latest else dt.now().year
    elif not current_year:
        current_year = dt.now().year
    prev_year = current_year - 1

    # Fetch invoices for both years (positive amounts only — no avoirs)
    if not site_ids:
        invoices = []
    else:
        invoices = (
            db.query(EnergyInvoice)
            .filter(
                EnergyInvoice.site_id.in_(site_ids),
                EnergyInvoice.period_start.isnot(None),
                EnergyInvoice.total_eur > 0,
            )
            .all()
        )

    # Aggregate by month
    buckets = {}  # { (year, month): { total_eur, energy_kwh, count } }
    for inv in invoices:
        ps = inv.period_start
        y, m = ps.year, ps.month
        if y not in (current_year, prev_year):
            continue
        key = (y, m)
        if key not in buckets:
            buckets[key] = {"total_eur": 0.0, "energy_kwh": 0.0, "count": 0}
        buckets[key]["total_eur"] += inv.total_eur or 0
        buckets[key]["energy_kwh"] += inv.energy_kwh or 0
        buckets[key]["count"] += 1

    # Build response: 12 months
    months = []
    for m in range(1, 13):
        curr = buckets.get((current_year, m))
        prev = buckets.get((prev_year, m))
        curr_eur = round(curr["total_eur"], 2) if curr else None
        prev_eur = round(prev["total_eur"], 2) if prev else None
        curr_kwh = round(curr["energy_kwh"], 2) if curr else None
        prev_kwh = round(prev["energy_kwh"], 2) if prev else None

        delta_eur = None
        delta_pct = None
        if curr_eur is not None and prev_eur is not None and prev_eur > 0:
            delta_eur = round(curr_eur - prev_eur, 2)
            delta_pct = round((curr_eur - prev_eur) / prev_eur * 100, 1)

        months.append(
            {
                "month": m,
                "label": _MONTH_LABELS_FR[m],
                "current_eur": curr_eur,
                "previous_eur": prev_eur,
                "current_kwh": curr_kwh,
                "previous_kwh": prev_kwh,
                "delta_eur": delta_eur,
                "delta_pct": delta_pct,
            }
        )

    total_current = sum(x["current_eur"] for x in months if x["current_eur"] is not None)
    total_previous = sum(x["previous_eur"] for x in months if x["previous_eur"] is not None)

    return {
        "current_year": current_year,
        "previous_year": prev_year,
        "months": months,
        "total_current_eur": round(total_current, 2),
        "total_previous_eur": round(total_previous, 2),
    }


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
        cond1 = start_date is None or c.end_date is None or start_date <= c.end_date
        # startB <= endA  (if either is None, condition is True)
        cond2 = c.start_date is None or end_date is None or c.start_date <= end_date
        if cond1 and cond2:
            return c
    return None


# ========================================
# Canonical Validation & Perimeter Check
# ========================================


@router.post("/invoices/validate-canonical")
def validate_invoice_canonical_endpoint(body: dict = Body(...)):
    """Validate invoice data against the canonical billing schema."""
    from services.billing_canonical_service import validate_invoice_canonical, compute_gap_report

    invoice, errors = validate_invoice_canonical(body)
    gaps = compute_gap_report(body)
    missing_required = [g for g in gaps if g["status"] == "missing" and g["required"]]
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "gap_report": gaps,
        "missing_required_count": len(missing_required),
        "canonical_fields_present": sum(1 for g in gaps if g["status"] == "present"),
        "canonical_fields_total": len(gaps),
    }


@router.post("/perimeter/check")
def check_billing_perimeter(body: ContractPerimeter, db: Session = Depends(get_db)):
    """Check billing ↔ contract ↔ site consistency."""
    from services.perimeter_check import check_perimeter

    result = check_perimeter(db, body.site_id, body.contract_id, body.period_start, body.period_end)
    return result


@router.post("/invoices/shadow-billing-check")
def shadow_billing_check(body: dict = Body(...)):
    """Full shadow billing readiness check — fields + business consistency."""
    from services.billing_canonical_service import compute_shadow_billing_gaps

    return compute_shadow_billing_gaps(body)
