"""Service to validate and normalize billing data against the canonical schema."""

from typing import List, Optional, Tuple
from schemas.billing_canonical import BillingInvoiceCanonical, BillingGapReport
from pydantic import ValidationError


def validate_invoice_canonical(data: dict) -> Tuple[Optional[BillingInvoiceCanonical], List[str]]:
    """Validate invoice data against the canonical schema.
    Returns (validated_invoice, errors).
    """
    errors = []
    try:
        invoice = BillingInvoiceCanonical(**data)
        return invoice, []
    except ValidationError as e:
        for err in e.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            errors.append(f"{field}: {err['msg']}")
        return None, errors


def compute_gap_report(data: dict) -> List[dict]:
    """Compute which canonical fields are present, missing, or derivable."""
    REQUIRED_FIELDS = {
        "site_id": "Identifiant site",
        "supplier_name": "Fournisseur",
        "amount_ht": "Montant HT",
        "period_start": "Début période",
        "period_end": "Fin période",
    }
    OPTIONAL_FIELDS = {
        "contract_id": "Contrat associé",
        "amount_ttc": "Montant TTC",
        "energy_total": "Énergie totale",
        "energy_unit": "Unité énergie",
        "currency": "Devise",
        "invoice_ref": "Référence facture",
        "pricing_effective_date": "Date tarif effectif",
    }

    gaps = []
    for field, label in REQUIRED_FIELDS.items():
        val = data.get(field)
        status = "present" if val is not None and val != "" else "missing"
        gaps.append({"field": field, "label": label, "status": status, "required": True})

    for field, label in OPTIONAL_FIELDS.items():
        val = data.get(field)
        if val is not None and val != "":
            status = "present"
        elif field == "amount_ttc" and data.get("amount_ht"):
            status = "derivable"
        elif field == "currency":
            status = "present"  # defaults to EUR
        else:
            status = "missing"
        gaps.append({"field": field, "label": label, "status": status, "required": False})

    return gaps


def normalize_invoice_for_import(raw: dict) -> dict:
    """Normalize raw import data to canonical field names."""
    # Map common import field names to canonical names
    FIELD_MAP = {
        "montant_ht": "amount_ht",
        "montant_ttc": "amount_ttc",
        "fournisseur": "supplier_name",
        "debut_periode": "period_start",
        "fin_periode": "period_end",
        "reference": "invoice_ref",
        "energie_kwh": "energy_total",
    }
    result = {}
    for k, v in raw.items():
        canonical_key = FIELD_MAP.get(k, k)
        result[canonical_key] = v
    if "currency" not in result:
        result["currency"] = "EUR"
    if "energy_unit" not in result:
        result["energy_unit"] = "kWh"
    return result
