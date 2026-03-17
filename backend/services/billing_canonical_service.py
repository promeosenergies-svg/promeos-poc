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


def compute_shadow_billing_gaps(data: dict) -> dict:
    """Extended gap report for shadow billing / reconciliation.
    Checks field presence + business consistency.
    """
    field_gaps = compute_gap_report(data)

    business_checks = []

    # 1. HT/TTC mismatch
    ht = data.get("amount_ht")
    ttc = data.get("amount_ttc")
    if ht is not None and ttc is not None:
        if ttc < ht:
            business_checks.append(
                {
                    "check": "ht_ttc_mismatch",
                    "status": "warning",
                    "message": f"TTC ({ttc}) < HT ({ht}) — incohérent",
                }
            )
        elif ht > 0:
            tva_rate = round((ttc - ht) / ht * 100, 1)
            if tva_rate < 0 or tva_rate > 30:
                business_checks.append(
                    {
                        "check": "tva_rate_suspect",
                        "status": "warning",
                        "message": f"Taux TVA implicite = {tva_rate}% — vérifier",
                    }
                )

    # 2. Currency mismatch
    currency = data.get("currency", "EUR")
    if currency and currency != "EUR":
        business_checks.append(
            {
                "check": "currency_non_eur",
                "status": "info",
                "message": f"Devise = {currency} (non EUR) — vérifier la conversion",
            }
        )

    # 3. Energy unit
    unit = data.get("energy_unit", "kWh")
    if unit and unit not in ("kWh", "MWh", "GWh"):
        business_checks.append(
            {
                "check": "energy_unit_non_standard",
                "status": "warning",
                "message": f"Unité énergie = {unit} — conversion requise",
            }
        )

    # 4. Period consistency
    ps = data.get("period_start")
    pe = data.get("period_end")
    if ps and pe:
        from datetime import date

        try:
            start = date.fromisoformat(str(ps)) if isinstance(ps, str) else ps
            end = date.fromisoformat(str(pe)) if isinstance(pe, str) else pe
            if end < start:
                business_checks.append(
                    {
                        "check": "period_inverted",
                        "status": "error",
                        "message": "Fin de période antérieure au début",
                    }
                )
            days = (end - start).days
            if days > 366:
                business_checks.append(
                    {
                        "check": "period_too_long",
                        "status": "warning",
                        "message": f"Période de {days} jours — vérifier",
                    }
                )
        except (ValueError, TypeError):
            business_checks.append(
                {
                    "check": "period_parse_error",
                    "status": "error",
                    "message": "Dates de période non parsables",
                }
            )

    # 5. Pricing date
    if not data.get("pricing_effective_date"):
        business_checks.append(
            {
                "check": "pricing_date_missing",
                "status": "info",
                "message": "Date tarif effectif absente — comparaison marché limitée",
            }
        )

    missing_required = [g for g in field_gaps if g["status"] == "missing" and g["required"]]

    return {
        "field_gaps": field_gaps,
        "business_checks": business_checks,
        "missing_required_count": len(missing_required),
        "warnings_count": sum(1 for c in business_checks if c["status"] == "warning"),
        "errors_count": sum(1 for c in business_checks if c["status"] == "error"),
        "shadow_billing_ready": len(missing_required) == 0
        and sum(1 for c in business_checks if c["status"] == "error") == 0,
    }
