"""
PROMEOS — Offer ↔ Invoice Reconciliation V1 (Sprint V2)
Compares an offer quote to the shadow billing of an invoice.
Produces per-component deltas, explanations, and confidence assessment.
"""

import logging
from datetime import date
from typing import Optional, List

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def reconcile_offer_vs_invoice(
    db: Session,
    invoice_id: int,
    strategy: str = "fixe",
    price_ref_eur_per_kwh: Optional[float] = None,
    fixed_fee_eur_per_month: float = 0.0,
    use_actual_kwh: bool = True,
) -> dict:
    """
    Compare an offer quote to the shadow billing of a real invoice.

    Process:
    1. Load invoice + lines + contract
    2. Compute shadow_billing_v2 (what the invoice *should* be)
    3. Compute offer_quote_v1 with same period/kwh (what the offer *would* cost)
    4. Compare component by component

    Returns:
        ReconcileResult: { invoice, offer_quote, delta, explanations, confidence, missing_data }
    """
    from models import EnergyInvoice, EnergyInvoiceLine, EnergyContract
    from services.billing_shadow_v2 import shadow_billing_v2
    from services.offer_pricing_v1 import compute_offer_quote

    # ── Load invoice ─────────────────────────────────────────────
    invoice = db.query(EnergyInvoice).filter(EnergyInvoice.id == invoice_id).first()
    if not invoice:
        return {"error": "invoice_not_found", "invoice_id": invoice_id}

    lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == invoice_id).all()

    contract = None
    if invoice.contract_id:
        contract = db.query(EnergyContract).filter(EnergyContract.id == invoice.contract_id).first()
        if not contract:
            logger.warning(
                "Invoice %d references missing contract %d",
                invoice_id,
                invoice.contract_id,
            )

    # ── Determine energy type & kwh ──────────────────────────────
    is_elec = True
    if contract and hasattr(contract, "energy_type") and contract.energy_type:
        is_elec = contract.energy_type.value == "elec"
    energy_type = "elec" if is_elec else "gaz"

    kwh = invoice.energy_kwh or 0.0
    period_start = getattr(invoice, "period_start", None)
    period_end = getattr(invoice, "period_end", None)

    # ── Resolve price reference ──────────────────────────────────
    ref_price = price_ref_eur_per_kwh
    if not ref_price and contract and contract.price_ref_eur_per_kwh:
        ref_price = contract.price_ref_eur_per_kwh

    fixed_fee = fixed_fee_eur_per_month
    if not fixed_fee and contract:
        fixed_fee = getattr(contract, "fixed_fee_eur_per_month", None) or 0.0

    # ── Compute shadow billing (what invoice should be) ──────────
    shadow = shadow_billing_v2(invoice, lines, contract, db=db)

    # ── Compute offer quote (what offer would cost) ──────────────
    offer = compute_offer_quote(
        strategy=strategy,
        energy_type=energy_type,
        consumption_kwh=kwh,
        period_start=period_start,
        period_end=period_end,
        price_ref_eur_per_kwh=ref_price,
        fixed_fee_eur_per_month=fixed_fee,
        invoice_date=period_start,
    )

    # ── Compute deltas (offer vs shadow) ─────────────────────────
    delta_by_component = _compute_component_deltas(offer, shadow)

    delta_totals = {
        "ht": round(offer["totals"]["ht"] - shadow["totals"]["ht"], 2),
        "tva": round(offer["totals"]["tva"] - shadow["totals"]["tva"], 2),
        "ttc": round(offer["totals"]["ttc"] - shadow["totals"]["ttc"], 2),
    }

    delta_vs_actual = {
        "ttc": round(offer["totals"]["ttc"] - (invoice.total_eur or 0), 2),
    }

    # ── Assess confidence ────────────────────────────────────────
    missing_data = []
    if not ref_price:
        missing_data.append("price_ref_eur_per_kwh")
    if not period_start or not period_end:
        missing_data.append("period_dates")
    if not kwh or kwh <= 0:
        missing_data.append("energy_kwh")
    if not contract:
        missing_data.append("contract")
    if not lines:
        missing_data.append("invoice_lines")

    confidence = "HIGH"
    if len(missing_data) >= 3:
        confidence = "LOW"
    elif len(missing_data) >= 1:
        confidence = "MED"

    # ── Build explanations ───────────────────────────────────────
    explanations = _build_explanations(delta_by_component, delta_totals, missing_data, strategy, shadow, offer)

    return {
        "invoice_id": invoice_id,
        "invoice_total_eur": invoice.total_eur,
        "invoice_kwh": kwh,
        "invoice_period": {
            "start": str(period_start) if period_start else None,
            "end": str(period_end) if period_end else None,
        },
        "shadow": {
            "totals": shadow["totals"],
            "method": shadow.get("method"),
        },
        "offer_quote": {
            "totals": offer["totals"],
            "components": offer["components"],
            "meta": offer["meta"],
        },
        "delta": {
            "by_component": delta_by_component,
            "totals": delta_totals,
            "vs_actual_invoice": delta_vs_actual,
        },
        "explanations": explanations,
        "confidence": confidence,
        "missing_data": missing_data,
    }


def reconcile_offer_vs_shadow(
    strategy: str,
    energy_type: str = "elec",
    consumption_kwh: float = 0.0,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    price_ref_eur_per_kwh: Optional[float] = None,
    fixed_fee_eur_per_month: float = 0.0,
    shadow_result: Optional[dict] = None,
) -> dict:
    """
    Lightweight reconcile: compare offer quote to a pre-computed shadow result.
    No DB needed. Useful for frontend preview.
    """
    from services.offer_pricing_v1 import compute_offer_quote

    offer = compute_offer_quote(
        strategy=strategy,
        energy_type=energy_type,
        consumption_kwh=consumption_kwh,
        period_start=period_start,
        period_end=period_end,
        price_ref_eur_per_kwh=price_ref_eur_per_kwh,
        fixed_fee_eur_per_month=fixed_fee_eur_per_month,
        invoice_date=period_start,
    )

    if not shadow_result or "totals" not in shadow_result:
        return {
            "offer_quote": offer,
            "delta": None,
            "explanations": ["Pas de facture shadow disponible pour comparaison."],
            "confidence": "LOW",
        }

    delta_by_component = _compute_component_deltas(offer, shadow_result)
    delta_totals = {
        "ht": round(offer["totals"]["ht"] - shadow_result["totals"]["ht"], 2),
        "tva": round(offer["totals"]["tva"] - shadow_result["totals"]["tva"], 2),
        "ttc": round(offer["totals"]["ttc"] - shadow_result["totals"]["ttc"], 2),
    }

    return {
        "offer_quote": offer,
        "shadow": {"totals": shadow_result["totals"]},
        "delta": {
            "by_component": delta_by_component,
            "totals": delta_totals,
        },
        "explanations": _build_explanations(delta_by_component, delta_totals, [], strategy, shadow_result, offer),
        "confidence": "HIGH",
    }


# ── Internal helpers ─────────────────────────────────────────────────


def _compute_component_deltas(offer: dict, shadow: dict) -> list:
    """Compare offer components to shadow components by code."""
    shadow_by_code = {}
    for comp in shadow.get("components", []):
        shadow_by_code[comp["code"]] = comp

    deltas = []
    for comp in offer.get("components", []):
        code = comp["code"]
        shadow_comp = shadow_by_code.get(code, {})
        shadow_ht = shadow_comp.get("ht", 0)
        delta_ht = round(comp["ht"] - shadow_ht, 2)
        delta_pct = round(delta_ht / shadow_ht * 100, 1) if shadow_ht else 0.0
        deltas.append(
            {
                "code": code,
                "label": comp["label"],
                "offer_ht": comp["ht"],
                "shadow_ht": shadow_ht,
                "delta_ht": delta_ht,
                "delta_pct": delta_pct,
            }
        )
    return deltas


def _build_explanations(
    delta_by_component: list,
    delta_totals: dict,
    missing_data: list,
    strategy: str,
    shadow: dict,
    offer: dict,
) -> List[str]:
    """Build human-readable explanations for the reconciliation."""
    explanations = []

    # Overall delta
    ttc_delta = delta_totals.get("ttc", 0)
    if ttc_delta > 0:
        explanations.append(
            f"L'offre {strategy.upper()} coûterait {ttc_delta:+.2f} € TTC de plus que la facture attendue."
        )
    elif ttc_delta < 0:
        explanations.append(
            f"L'offre {strategy.upper()} économiserait {abs(ttc_delta):.2f} € TTC par rapport à la facture attendue."
        )
    else:
        explanations.append(f"L'offre {strategy.upper()} est alignée avec la facture attendue.")

    # Component-level explanations for significant deltas
    for delta in delta_by_component:
        if abs(delta["delta_pct"]) > 5 and abs(delta["delta_ht"]) > 1:
            direction = "supérieur" if delta["delta_ht"] > 0 else "inférieur"
            explanations.append(
                f"{delta['label']} : {delta['delta_ht']:+.2f} € HT ({delta['delta_pct']:+.1f}%, {direction} au shadow)."
            )

    # Missing data warnings
    if "price_ref_eur_per_kwh" in missing_data:
        explanations.append("Prix de référence non fourni : valeur par défaut utilisée.")
    if "contract" in missing_data:
        explanations.append("Contrat non associé : segment C5 par défaut utilisé.")
    if "period_dates" in missing_data:
        explanations.append("Dates de période manquantes : prorata 30 jours par défaut.")

    return explanations
