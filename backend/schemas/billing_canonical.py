"""Canonical billing data contract for PROMEOS invoices/line items."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class BillingLineItem(BaseModel):
    """Canonical representation of an invoice line item."""

    description: str = Field(min_length=1, max_length=500)
    amount_ht: float = Field(ge=0, le=100_000_000, description="Montant HT en EUR")
    amount_ttc: Optional[float] = Field(None, ge=0, le=100_000_000, description="Montant TTC en EUR")
    energy_kwh: Optional[float] = Field(None, ge=0, description="Quantité énergie en kWh")
    unit_price: Optional[float] = Field(None, ge=0, description="Prix unitaire EUR/kWh")


class BillingInvoiceCanonical(BaseModel):
    """Canonical invoice representation for shadow billing / reconciliation."""

    invoice_id: Optional[int] = None
    site_id: int = Field(gt=0)
    contract_id: Optional[int] = Field(None, gt=0)
    supplier_name: str = Field(min_length=1, max_length=300)
    invoice_ref: Optional[str] = Field(None, max_length=100)
    currency: str = Field(default="EUR", max_length=3)
    amount_ht: float = Field(ge=0, le=100_000_000)
    amount_ttc: Optional[float] = Field(None, ge=0, le=100_000_000)
    energy_unit: str = Field(default="kWh", max_length=10)
    energy_total: Optional[float] = Field(None, ge=0)
    period_start: date
    period_end: date
    pricing_effective_date: Optional[date] = None
    line_items: List[BillingLineItem] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "site_id": 1,
                    "supplier_name": "EDF",
                    "currency": "EUR",
                    "amount_ht": 12500.0,
                    "period_start": "2025-01-01",
                    "period_end": "2025-03-31",
                }
            ]
        }
    }


class BillingGapReport(BaseModel):
    """Documents which canonical fields exist vs missing in current data."""

    field: str
    status: str  # "present", "missing", "derivable", "not_applicable"
    source: Optional[str] = None
    notes: Optional[str] = None
