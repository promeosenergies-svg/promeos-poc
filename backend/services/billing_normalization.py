"""
PROMEOS — Billing Normalization (V68)
InvoiceNormalized Pydantic schema + normalize_invoice() helper.
Calcule ht/tva/fournisseur/energie à la volée depuis lignes + contrat.
Pas de migration DB — view layer uniquement.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from pydantic import BaseModel


class InvoiceNormalized(BaseModel):
    id: int
    org_id: int
    site_id: int
    fournisseur: Optional[str]  # EnergyContract.supplier_name
    energie: Optional[str]  # "ELEC" | "GAZ"
    period_start: Optional[date]
    period_end: Optional[date]
    issue_date: Optional[date]
    month_key: Optional[str]  # YYYY-MM dérivé de period_start (ou issue_date)
    ttc: Optional[float]  # = total_eur
    ht: Optional[float]  # sum(ENERGY + NETWORK lines)
    tva: Optional[float]  # sum(TAX lines)
    ht_fourniture: Optional[float]  # sum(ENERGY lines)
    ht_reseau: Optional[float]  # sum(NETWORK lines)
    kwh: Optional[float]
    invoice_number: str
    status: str
    pdf_doc_id: Optional[str]


def normalize_invoice(inv, lines: list, contract, org_id: int) -> InvoiceNormalized:
    """
    Construit InvoiceNormalized depuis un EnergyInvoice + ses lignes + contrat.
    org_id doit être résolu en amont via _resolve_invoice_org_id ou effective_org_id.
    """
    ht_fourniture = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "energy")
    ht_reseau = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "network")
    tva = sum(l.amount_eur or 0 for l in lines if l.line_type.value == "tax")

    month_key = None
    if inv.period_start:
        month_key = inv.period_start.strftime("%Y-%m")
    elif inv.issue_date:
        month_key = inv.issue_date.strftime("%Y-%m")

    raw: dict = {}
    try:
        raw = json.loads(inv.raw_json or "{}")
    except Exception:
        pass

    return InvoiceNormalized(
        id=inv.id,
        org_id=org_id,
        site_id=inv.site_id,
        fournisseur=getattr(contract, "supplier_name", None),
        energie=contract.energy_type.value.upper() if contract else None,
        period_start=inv.period_start,
        period_end=inv.period_end,
        issue_date=inv.issue_date,
        month_key=month_key,
        ttc=inv.total_eur,
        ht=round(ht_fourniture + ht_reseau, 2),
        tva=round(tva, 2),
        ht_fourniture=round(ht_fourniture, 2),
        ht_reseau=round(ht_reseau, 2),
        kwh=inv.energy_kwh,
        invoice_number=inv.invoice_number,
        status=inv.status.value if inv.status else "imported",
        pdf_doc_id=raw.get("pdf_doc_id"),
    )
