"""PROMEOS — Schemas Pydantic pour Billing (facturation, paiement, reconciliation)."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class InvoiceAuditRequest(BaseModel):
    invoice_id: int = Field(gt=0)
    force: bool = False


class BillingReconcileRequest(BaseModel):
    org_id: int = Field(gt=0)
    site_ids: Optional[List[int]] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None


class PaymentRuleCreate(BaseModel):
    site_id: int = Field(gt=0)
    rule_type: str = Field(min_length=1, max_length=100)
    amount: Optional[float] = Field(None, ge=0, le=10_000_000)
    currency: str = Field(default="EUR", max_length=3)
    description: Optional[str] = Field(None, max_length=500)
