"""
PROMEOS — Bill Intelligence Service (Sprint 7.1)
Shadow billing simplifie + anomaly engine (10 regles) + summary.
V1.1: get_reference_price (contract > site_tariff > fallback),
      proof/explainability (inputs+threshold in metrics),
      cross-link R9 -> diagnostic-conso,
      insight workflow defaults.
"""

import inspect
import json
import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)

from models import (
    Site,
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    BillingInsight,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
    SiteTariffProfile,
    InsightStatus,
    ActionItem,
    Portefeuille,
    EntiteJuridique,
)
from models.enums import ActionSourceType, ActionStatus
from config.default_prices import (
    DEFAULT_PRICE_ELEC_EUR_KWH,
    DEFAULT_PRICE_GAZ_EUR_KWH,
    get_default_price,
)


# ========================================
# Price reference resolution (V1.1)
# Source unique : config/default_prices.py
# ========================================


def get_reference_price(
    db: Session,
    site_id: int,
    energy_type: str = "elec",
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> Tuple[float, str]:
    """
    Resolve the reference price for a site, with clear priority:
      1. Active EnergyContract covering the invoice period
      2. MarketPrice moyenne 30 jours (EPEX Spot FR)
      3. SiteTariffProfile for the site
      4. Config fallback (0.068 elec, 0.045 gaz)
    Returns: (price_eur_per_kwh, source_label)
    """
    # Priority 1: Active contract
    q = db.query(EnergyContract).filter(
        EnergyContract.site_id == site_id,
        EnergyContract.price_ref_eur_per_kwh.isnot(None),
    )
    if energy_type:
        try:
            q = q.filter(EnergyContract.energy_type == BillingEnergyType(energy_type))
        except ValueError:
            pass
    contracts = q.all()
    for c in contracts:
        if c.price_ref_eur_per_kwh is None:
            continue
        # Check period overlap if dates available
        if period_start and period_end and c.start_date and c.end_date:
            if c.start_date <= period_end and c.end_date >= period_start:
                return (c.price_ref_eur_per_kwh, f"contract:{c.id}")
        elif c.start_date is None and c.end_date is None:
            # Contract without dates = always valid
            return (c.price_ref_eur_per_kwh, f"contract:{c.id}")

    # Priority 2: MktPrice — moyenne spot 30 jours (mkt_prices V2)
    try:
        from datetime import datetime as _dt, timezone as _tz
        from models.market_models import MktPrice, MarketType, PriceZone

        if energy_type != "gaz":
            ref_date = period_end or period_start or date.today()
            ref_dt = _dt(ref_date.year, ref_date.month, ref_date.day, tzinfo=_tz.utc)
            avg_price = (
                db.query(func.avg(MktPrice.price_eur_mwh))
                .filter(
                    MktPrice.zone == PriceZone.FR,
                    MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
                    MktPrice.delivery_start >= ref_dt - timedelta(days=30),
                    MktPrice.delivery_start <= ref_dt,
                )
                .scalar()
            )
            if avg_price and avg_price > 0:
                return (round(avg_price / 1000, 6), "market_epex_spot_30d")
    except Exception:
        pass  # mkt_prices table may not exist yet

    # Priority 3: SiteTariffProfile
    tariff = db.query(SiteTariffProfile).filter(SiteTariffProfile.site_id == site_id).first()
    if tariff and tariff.price_ref_eur_per_kwh:
        return (tariff.price_ref_eur_per_kwh, "site_tariff_profile")

    # Priority 4: Default fallback (source unique: config/default_prices.py)
    if energy_type == "gaz":
        return (DEFAULT_PRICE_GAZ_EUR_KWH, "default_gaz")
    return (DEFAULT_PRICE_ELEC_EUR_KWH, "default_elec")


# ========================================
# Shadow billing simplifie
# ========================================


def shadow_billing_simple(
    invoice: EnergyInvoice,
    contract: Optional[EnergyContract] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Shadow billing simplifie: energy_kwh * price_ref.
    V1.1: uses get_reference_price when db is provided.
    """
    if not invoice.energy_kwh or invoice.energy_kwh <= 0:
        return {
            "shadow_total_eur": None,
            "delta_eur": None,
            "delta_pct": None,
            "method": "skip",
            "reason": "energy_kwh manquant ou <= 0",
        }

    # Resolve price reference
    price_ref = None
    ref_source = "fallback"

    if db:
        energy_type_str = _energy_type(invoice, contract)
        price_ref, ref_source = get_reference_price(
            db,
            invoice.site_id,
            energy_type_str,
            invoice.period_start,
            invoice.period_end,
        )
    elif contract and contract.price_ref_eur_per_kwh:
        price_ref = contract.price_ref_eur_per_kwh
        ref_source = f"contract:{contract.id}"

    if price_ref is None:
        price_ref = DEFAULT_PRICE_ELEC_EUR_KWH
        ref_source = "default_elec"

    shadow_total = round(invoice.energy_kwh * price_ref, 2)
    # Compare against energy line when available (avoids comparing energy-only vs TTC all-in)
    actual_total = invoice.total_eur or 0
    if db:
        energy_line_total = (
            db.query(func.sum(EnergyInvoiceLine.amount_eur))
            .filter(
                EnergyInvoiceLine.invoice_id == invoice.id,
                EnergyInvoiceLine.line_type == InvoiceLineType.ENERGY,
            )
            .scalar()
        )
        if energy_line_total and energy_line_total > 0:
            actual_total = float(energy_line_total)
    delta = round(actual_total - shadow_total, 2)
    delta_pct = round(delta / shadow_total * 100, 2) if shadow_total > 0 else None

    return {
        "shadow_total_eur": shadow_total,
        "actual_total_eur": actual_total,
        "delta_eur": delta,
        "delta_pct": delta_pct,
        "price_ref_eur_kwh": price_ref,
        "ref_price_source": ref_source,
        "energy_kwh": invoice.energy_kwh,
        "method": "simple",
    }


# ========================================
# Proof helper (V1.1)
# ========================================


def _build_inputs(invoice: EnergyInvoice, ref_price: Optional[float] = None) -> Dict:
    """Build standardized inputs dict for proof/explainability."""
    implied = None
    if invoice.energy_kwh and invoice.energy_kwh > 0 and invoice.total_eur:
        implied = round(invoice.total_eur / invoice.energy_kwh, 4)
    return {
        "period_start": str(invoice.period_start) if invoice.period_start else None,
        "period_end": str(invoice.period_end) if invoice.period_end else None,
        "energy_kwh": invoice.energy_kwh,
        "total_eur": invoice.total_eur,
        "implied_price": implied,
        "ref_price": ref_price,
    }


# ========================================
# Anomaly engine (10 rules)
# ========================================


def _rule_shadow_gap(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine], db: Session = None
) -> Optional[Dict]:
    """R1: Ecart shadow billing > 20%."""
    shadow = shadow_billing_simple(invoice, contract, db=db)
    if shadow["delta_pct"] is not None and abs(shadow["delta_pct"]) > 20:
        metrics = {
            **shadow,
            "inputs": _build_inputs(invoice, shadow.get("price_ref_eur_kwh")),
            "threshold_pct": 20,
            "delta_calculated_pct": shadow["delta_pct"],
            "confidence": "medium",
            "assumptions": [
                f"Prix ref: {shadow.get('ref_price_source', 'défaut')}",
                "Tarifs réseau/taxes POC 2025 simplifiés",
            ],
        }
        # Enrich with V2 4-component breakdown when lines available
        if lines:
            try:
                from services.billing_shadow_v2 import shadow_billing_v2

                v2 = shadow_billing_v2(invoice, lines, contract, db=db)
                metrics.update(v2)
                # Phase 2: top contributors explainability
                from services.billing_explainability import compute_contributors

                metrics["top_contributors"] = compute_contributors(metrics)
            except Exception as exc:
                import logging

                logging.getLogger("promeos.billing").debug(f"shadow_billing_v2 failed: {exc}")
        return {
            "type": "shadow_gap",
            "severity": "high" if abs(shadow["delta_pct"]) > 20 else "medium",
            "message": f"Ecart shadow billing de {shadow['delta_pct']:+.1f}% ({shadow['delta_eur']:+.2f} EUR)",
            "metrics": metrics,
            "estimated_loss_eur": abs(shadow["delta_eur"]) if shadow["delta_eur"] and shadow["delta_eur"] > 0 else 0,
        }
    return None


def _rule_unit_price_high(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R2: Prix unitaire anormalement élevé (> 0.30 EUR/kWh elec, > 0.15 EUR/kWh gaz)."""
    if not invoice.energy_kwh or invoice.energy_kwh <= 0 or not invoice.total_eur:
        return None
    unit_price = invoice.total_eur / invoice.energy_kwh
    threshold = 0.30 if _energy_type(invoice, contract) == "elec" else 0.15
    if unit_price > threshold:
        return {
            "type": "unit_price_high",
            "severity": "high",
            "message": f"Prix unitaire élevé : {unit_price:.4f} EUR/kWh (seuil : {threshold})",
            "metrics": {
                "unit_price": round(unit_price, 4),
                "threshold": threshold,
                "inputs": _build_inputs(invoice, threshold),
                "delta_calculated": round(unit_price - threshold, 4),
                "confidence": "high",
                "assumptions": [f"Seuil: {threshold} €/kWh"],
            },
            "estimated_loss_eur": round((unit_price - threshold) * invoice.energy_kwh, 2),
        }
    return None


def _rule_duplicate_invoice(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine], db: Session = None
) -> Optional[Dict]:
    """R3: Doublon de facture (même site, même période, même montant)."""
    if db is None or not invoice.period_start or not invoice.period_end:
        return None
    dupes = (
        db.query(EnergyInvoice)
        .filter(
            EnergyInvoice.site_id == invoice.site_id,
            EnergyInvoice.period_start == invoice.period_start,
            EnergyInvoice.period_end == invoice.period_end,
            EnergyInvoice.total_eur == invoice.total_eur,
            EnergyInvoice.id != invoice.id,
        )
        .count()
    )
    if dupes > 0:
        return {
            "type": "duplicate_invoice",
            "severity": "critical",
            "message": f"Facture en doublon ({dupes} autre(s) avec même période et montant)",
            "metrics": {
                "duplicates_count": dupes,
                "inputs": _build_inputs(invoice),
                "confidence": "high",
                "assumptions": ["Même site, période et montant"],
            },
            "estimated_loss_eur": invoice.total_eur or 0,
        }
    return None


def _rule_missing_period(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R4: Periode manquante sur la facture."""
    if not invoice.period_start or not invoice.period_end:
        return {
            "type": "missing_period",
            "severity": "medium",
            "message": "Periode de facturation manquante (debut ou fin)",
            "metrics": {
                "has_start": invoice.period_start is not None,
                "has_end": invoice.period_end is not None,
                "inputs": _build_inputs(invoice),
                "confidence": "high",
                "assumptions": ["Champs période absents"],
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_period_too_long(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R5: Periode de facturation > 62 jours (suspect)."""
    if not invoice.period_start or not invoice.period_end:
        return None
    days = (invoice.period_end - invoice.period_start).days
    if days > 62:
        return {
            "type": "period_too_long",
            "severity": "medium",
            "message": f"Periode de facturation anormalement longue: {days} jours",
            "metrics": {
                "days": days,
                "threshold_days": 62,
                "delta_calculated_days": days - 62,
                "inputs": _build_inputs(invoice),
                "confidence": "high",
                "assumptions": ["Seuil: 62 jours"],
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_negative_kwh(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R6: Consommation negative."""
    if invoice.energy_kwh is not None and invoice.energy_kwh < 0:
        return {
            "type": "negative_kwh",
            "severity": "high",
            "message": f"Consommation negative: {invoice.energy_kwh} kWh",
            "metrics": {
                "energy_kwh": invoice.energy_kwh,
                "inputs": _build_inputs(invoice),
                "confidence": "high",
                "assumptions": ["Relevé négatif"],
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_zero_amount(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R7: Montant total = 0 mais consommation > 0."""
    if (
        invoice.total_eur is not None
        and invoice.total_eur == 0
        and invoice.energy_kwh is not None
        and invoice.energy_kwh > 0
    ):
        return {
            "type": "zero_amount",
            "severity": "high",
            "message": f"Montant = 0 EUR pour {invoice.energy_kwh} kWh consommes",
            "metrics": {
                "total_eur": invoice.total_eur,
                "energy_kwh": invoice.energy_kwh,
                "inputs": _build_inputs(invoice),
                "confidence": "high",
                "assumptions": ["Montant nul avec consommation > 0"],
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_lines_sum_mismatch(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R8: Somme des lignes != total facture (tolerance 2%)."""
    if not lines or not invoice.total_eur:
        return None
    lines_sum = sum(l.amount_eur or 0 for l in lines)
    if lines_sum == 0:
        return None
    diff = abs(invoice.total_eur - lines_sum)
    pct = diff / abs(invoice.total_eur) * 100 if invoice.total_eur else 0
    if pct > 2:
        return {
            "type": "lines_sum_mismatch",
            "severity": "high" if pct > 10 else "medium",
            "message": f"Ecart lignes vs total: {diff:.2f} EUR ({pct:.1f}%)",
            "metrics": {
                "lines_sum": round(lines_sum, 2),
                "total_eur": invoice.total_eur,
                "diff": round(diff, 2),
                "pct": round(pct, 1),
                "threshold_pct": 2,
                "delta_calculated_pct": round(pct, 1),
                "inputs": _build_inputs(invoice),
                "confidence": "high",
                "assumptions": ["Tolérance: 2%"],
            },
            "estimated_loss_eur": round(diff, 2) if diff > 1 else 0,
        }
    return None


def _rule_consumption_spike(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine], db: Session = None
) -> Optional[Dict]:
    """R9: Pic de consommation (> 2x la moyenne des 6 derniers mois)."""
    if db is None or not invoice.energy_kwh or not invoice.site_id:
        return None
    avg_result = (
        db.query(func.avg(EnergyInvoice.energy_kwh))
        .filter(
            EnergyInvoice.site_id == invoice.site_id,
            EnergyInvoice.id != invoice.id,
            EnergyInvoice.energy_kwh > 0,
        )
        .scalar()
    )
    if avg_result and avg_result > 0 and invoice.energy_kwh > 2 * avg_result:
        ratio = round(invoice.energy_kwh / avg_result, 1)
        return {
            "type": "consumption_spike",
            "severity": "high",
            "message": f"Pic de consommation: {invoice.energy_kwh:.0f} kWh vs moyenne {avg_result:.0f} kWh (x{ratio})",
            "metrics": {
                "energy_kwh": invoice.energy_kwh,
                "avg_kwh": round(avg_result, 0),
                "ratio": ratio,
                "threshold_ratio": 2.0,
                "delta_calculated_ratio": ratio,
                "inputs": _build_inputs(invoice),
                "confidence": "medium",
                "consumption_source": "billed",
                "assumptions": ["Moyenne 6 mois glissants", "Seuil: ×2", "Source: factures (billed)"],
                "cross_link": {
                    "module": "diagnostic-conso",
                    "site_id": invoice.site_id,
                    "date_range": {
                        "from": str(invoice.period_start) if invoice.period_start else None,
                        "to": str(invoice.period_end) if invoice.period_end else None,
                    },
                },
            },
            "estimated_loss_eur": 0,
            "recommended_actions": [
                {
                    "action": "Verifier le diagnostic consommation",
                    "link": f"/diagnostic-conso?site_id={invoice.site_id}&from={invoice.period_start}&to={invoice.period_end}",
                    "reason": "Pic de consommation detecte sur la facture",
                }
            ],
        }
    return None


def _rule_price_drift(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine], db: Session = None
) -> Optional[Dict]:
    """R10: Derive de prix unitaire par rapport au contrat (> 15%)."""
    if not contract or not contract.price_ref_eur_per_kwh:
        return None
    if not invoice.energy_kwh or invoice.energy_kwh <= 0 or not invoice.total_eur:
        return None
    # Use energy line amount when available (avoids comparing TTC vs energy-only ref)
    energy_total = invoice.total_eur
    if db:
        energy_line = (
            db.query(func.sum(EnergyInvoiceLine.amount_eur))
            .filter(
                EnergyInvoiceLine.invoice_id == invoice.id,
                EnergyInvoiceLine.line_type == InvoiceLineType.ENERGY,
            )
            .scalar()
        )
        if energy_line and energy_line > 0:
            energy_total = float(energy_line)
    actual_unit = energy_total / invoice.energy_kwh
    ref = contract.price_ref_eur_per_kwh
    drift_pct = (actual_unit - ref) / ref * 100
    if abs(drift_pct) > 15:
        loss = max(0, round((actual_unit - ref) * invoice.energy_kwh, 2))
        return {
            "type": "price_drift",
            "severity": "high" if abs(drift_pct) > 30 else "medium",
            "message": f"Derive de prix: {actual_unit:.4f} vs contrat {ref:.4f} EUR/kWh ({drift_pct:+.1f}%)",
            "metrics": {
                "actual_unit_price": round(actual_unit, 4),
                "contract_ref": ref,
                "drift_pct": round(drift_pct, 1),
                "threshold_pct": 20,
                "delta_calculated_pct": round(drift_pct, 1),
                "inputs": _build_inputs(invoice, ref),
                "confidence": "high",
                "assumptions": ["Comparaison avec prix contrat"],
            },
            "estimated_loss_eur": loss,
        }
    return None


# Helper
def _energy_type(invoice: EnergyInvoice, contract: Optional[EnergyContract]) -> str:
    """Determine energy type from contract or fallback."""
    if contract and contract.energy_type:
        return contract.energy_type.value
    return "elec"  # default


# ========================================
# R11 — TTC Coherence (V66)
# ========================================


def _rule_ttc_coherence(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R11: TTC facturé incohérent avec HT+TVA (tolérance 2%)."""
    if not invoice.total_eur or not lines:
        return None
    sum_ht = sum(l.amount_eur or 0 for l in lines if l.line_type != InvoiceLineType.TAX)
    sum_tva = sum(l.amount_eur or 0 for l in lines if l.line_type == InvoiceLineType.TAX)
    expected = sum_ht + sum_tva
    if expected == 0:
        return None
    delta = abs(expected - invoice.total_eur)
    if delta / max(abs(invoice.total_eur), 1) > 0.02 and delta > 5.0:
        return {
            "type": "ttc_mismatch",
            "severity": "high",
            "message": f"TTC facturé {invoice.total_eur:.2f}€ ≠ HT+TVA {expected:.2f}€ (écart {delta:.2f}€)",
            "metrics": {
                "total_eur_facture": invoice.total_eur,
                "total_eur_calcule": round(expected, 2),
                "delta_eur": round(delta, 2),
                "tolerance_pct": 2,
                "confidence": "high",
                "assumptions": ["Tolérance: 2%"],
            },
            "estimated_loss_eur": round(delta, 2),
        }
    return None


# ========================================
# R12 — Contract Expiry (V66)
# ========================================


def _rule_contract_expiry(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R12: Contrat expiré ou expire bientôt (< 90 jours)."""
    if not contract or not contract.end_date:
        return None
    days_left = (contract.end_date - date.today()).days
    if days_left < 0:
        return {
            "type": "contract_expired",
            "severity": "critical",
            "message": f"Contrat {contract.supplier_name} expiré le {contract.end_date} ({abs(days_left)}j)",
            "metrics": {
                "end_date": str(contract.end_date),
                "days_overdue": abs(days_left),
                "supplier": contract.supplier_name,
                "confidence": "high",
                "assumptions": [f"Date fin contrat: {contract.end_date}"],
            },
            "estimated_loss_eur": round((invoice.total_eur or 0) * 0.1, 2),
        }
    elif days_left <= 90:
        return {
            "type": "contract_expiry_soon",
            "severity": "high",
            "message": f"Contrat {contract.supplier_name} expire dans {days_left}j (le {contract.end_date})",
            "metrics": {
                "end_date": str(contract.end_date),
                "days_left": days_left,
                "supplier": contract.supplier_name,
                "confidence": "high",
                "assumptions": [f"Date fin contrat: {contract.end_date}"],
            },
            "estimated_loss_eur": 0,
        }
    return None


# ========================================
# R13 — Réseau / TURPE mismatch (V68)
# ========================================


def _rule_reseau_mismatch(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R13: Coût réseau/TURPE facturé ≠ attendu > 15%."""
    if not lines:
        return None
    from services.billing_shadow_v2 import shadow_billing_v2

    res = shadow_billing_v2(invoice, lines, contract)
    if res["expected_reseau_ht"] == 0:
        return None
    pct = abs(res["delta_reseau"] / res["expected_reseau_ht"] * 100)
    if pct > 15:
        sev = "high" if pct > 20 else "medium"
        return {
            "type": "reseau_mismatch",
            "severity": sev,
            "message": (
                f"Coût réseau {res['actual_reseau_ht']:.2f}€ vs attendu {res['expected_reseau_ht']:.2f}€ (Δ {pct:.0f}%)"
            ),
            "metrics": {
                **res,
                "delta_pct": round(pct, 1),
                "confidence": "medium",
                "assumptions": ["Tarif TURPE simplifié (C5 BT ≤ 36kVA)"],
            },
            "estimated_loss_eur": round(abs(res["delta_reseau"]), 2),
        }
    return None


# ========================================
# R14 — Taxes / CSPE mismatch (V68)
# ========================================


def _rule_taxes_mismatch(
    invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]
) -> Optional[Dict]:
    """R14: Taxes (CSPE/TICGN) facturées ≠ attendu > 10%."""
    if not lines:
        return None
    from services.billing_shadow_v2 import shadow_billing_v2

    res = shadow_billing_v2(invoice, lines, contract)
    if res["expected_taxes_ht"] == 0:
        return None
    pct = abs(res["delta_taxes"] / res["expected_taxes_ht"] * 100)
    if pct > 10:
        return {
            "type": "taxes_mismatch",
            "severity": "medium",
            "message": (
                f"Taxes {res['actual_taxes_ht']:.2f}€ vs attendu {res['expected_taxes_ht']:.2f}€ (Δ {pct:.0f}%)"
            ),
            "metrics": {
                **res,
                "delta_pct": round(pct, 1),
                "confidence": "medium",
                "assumptions": ["Taux CSPE/TICGN 2025 simplifiés"],
            },
            "estimated_loss_eur": round(abs(res["delta_taxes"]), 2),
        }
    return None


# All rules
BILLING_RULES = [
    ("R1", "Shadow gap", _rule_shadow_gap),
    ("R2", "Unit price high", _rule_unit_price_high),
    ("R3", "Duplicate invoice", _rule_duplicate_invoice),
    ("R4", "Missing period", _rule_missing_period),
    ("R5", "Period too long", _rule_period_too_long),
    ("R6", "Negative kWh", _rule_negative_kwh),
    ("R7", "Zero amount", _rule_zero_amount),
    ("R8", "Lines sum mismatch", _rule_lines_sum_mismatch),
    ("R9", "Consumption spike", _rule_consumption_spike),
    ("R10", "Price drift", _rule_price_drift),
    ("R11", "TTC coherence", _rule_ttc_coherence),
    ("R12", "Contract expiry", _rule_contract_expiry),
    ("R13", "Réseau / TURPE mismatch", _rule_reseau_mismatch),
    ("R14", "Taxes / CSPE mismatch", _rule_taxes_mismatch),
]

# Pre-compute which rules accept a `db` parameter (avoids inspect per invocation)
_RULES_ACCEPT_DB = frozenset(
    rule_id for rule_id, _, rule_fn in BILLING_RULES if "db" in inspect.signature(rule_fn).parameters
)


def run_anomaly_engine(
    invoice: EnergyInvoice,
    lines: List[EnergyInvoiceLine],
    contract: Optional[EnergyContract],
    db: Session,
) -> List[Dict[str, Any]]:
    """Run all billing rules on an invoice. Returns list of anomaly dicts.

    When R1 (shadow_gap) fires, skip sub-component rules (R13 reseau, R14 taxes)
    to avoid stacking 4 anomalies on the same invoice — shadow_gap already covers them.
    """
    anomalies = []
    shadow_gap_fired = False
    for rule_id, rule_name, rule_fn in BILLING_RULES:
        # Skip sub-component rules when shadow_gap already explains the deviation
        if shadow_gap_fired and rule_id in ("R10", "R13", "R14"):
            continue
        try:
            if rule_id in _RULES_ACCEPT_DB:
                result = rule_fn(invoice, contract, lines, db=db)
            else:
                result = rule_fn(invoice, contract, lines)
            if result:
                result["rule_id"] = rule_id
                result["rule_name"] = rule_name
                if "metrics" in result:
                    result["metrics"]["rule_id"] = rule_id
                    result["metrics"]["rule_name"] = rule_name
                anomalies.append(result)
                if rule_id == "R1":
                    shadow_gap_fired = True
        except Exception as e:
            logger.warning("Billing rule %s failed for invoice %s: %s", rule_id, getattr(invoice, "id", "?"), e)
    return anomalies


def _resolve_invoice_org_id(db: Session, invoice: EnergyInvoice) -> Optional[int]:
    """Walk site→portefeuille→entite_juridique→org to resolve org_id for an invoice."""
    try:
        site = db.query(Site).filter(Site.id == invoice.site_id).first()
        if not site or not site.portefeuille_id:
            return None
        port = db.query(Portefeuille).filter(Portefeuille.id == site.portefeuille_id).first()
        if not port or not port.entite_juridique_id:
            return None
        entite = db.query(EntiteJuridique).filter(EntiteJuridique.id == port.entite_juridique_id).first()
        return entite.organisation_id if entite else None
    except Exception:
        return None


def persist_insights(
    db: Session,
    invoice: EnergyInvoice,
    anomalies: List[Dict[str, Any]],
) -> List[BillingInsight]:
    """Persist anomaly results as BillingInsight rows + idempotent ActionItem bridge."""
    db.query(BillingInsight).filter(BillingInsight.invoice_id == invoice.id).delete()

    org_id = _resolve_invoice_org_id(db, invoice)
    insights = []
    for a in anomalies:
        insight = BillingInsight(
            site_id=invoice.site_id,
            invoice_id=invoice.id,
            type=a["type"],
            severity=a["severity"],
            message=a["message"],
            metrics_json=json.dumps(a.get("metrics", {})),
            estimated_loss_eur=a.get("estimated_loss_eur"),
            recommended_actions_json=json.dumps(a.get("recommended_actions", [])),
            insight_status=InsightStatus.OPEN,
        )
        db.add(insight)
        db.flush()  # get insight.id

        # NOTE: ActionItem creation for billing insights is handled by sync_actions
        # (build_actions_from_billing) with per-source capping, not here.

        insights.append(insight)

    if anomalies:
        invoice.status = BillingInvoiceStatus.ANOMALY
    else:
        invoice.status = BillingInvoiceStatus.AUDITED

    db.commit()
    return insights


def audit_invoice_full(db: Session, invoice_id: int) -> Dict[str, Any]:
    """Full audit pipeline for a persisted invoice: shadow + anomaly engine + persist."""
    invoice = db.query(EnergyInvoice).filter(EnergyInvoice.id == invoice_id).first()
    if not invoice:
        return {"error": "Invoice not found"}

    lines = db.query(EnergyInvoiceLine).filter(EnergyInvoiceLine.invoice_id == invoice_id).all()
    contract = None
    if invoice.contract_id:
        contract = db.query(EnergyContract).filter(EnergyContract.id == invoice.contract_id).first()

    shadow = shadow_billing_simple(invoice, contract, db=db)
    anomalies = run_anomaly_engine(invoice, lines, contract, db)
    insights = persist_insights(db, invoice, anomalies)

    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "shadow": shadow,
        "anomalies_count": len(anomalies),
        "anomalies": anomalies,
        "insights_persisted": len(insights),
    }


# ========================================
# Summary / read helpers
# ========================================


def get_billing_summary(db: Session, org_id: Optional[int] = None) -> Dict[str, Any]:
    """Aggregate billing summary for the organisation."""
    q = db.query(EnergyInvoice)
    if org_id:
        site_ids = [s.id for s in db.query(Site.id).filter(Site.portefeuille_id.isnot(None)).all()]
        if site_ids:
            q = q.filter(EnergyInvoice.site_id.in_(site_ids))

    invoices = q.all()
    total_eur = sum(i.total_eur or 0 for i in invoices)
    total_kwh = sum(i.energy_kwh or 0 for i in invoices)
    distinct_months = len({(i.period_start.year, i.period_start.month) for i in invoices if i.period_start})

    insights = db.query(BillingInsight).all()
    total_loss = sum(i.estimated_loss_eur or 0 for i in insights)
    by_type = {}
    for i in insights:
        by_type[i.type] = by_type.get(i.type, 0) + 1
    by_severity = {}
    for i in insights:
        by_severity[i.severity] = by_severity.get(i.severity, 0) + 1

    return {
        "total_invoices": len(invoices),
        "total_eur": round(total_eur, 2),
        "total_kwh": round(total_kwh, 0),
        "distinct_months": distinct_months,
        "total_insights": len(insights),
        "total_estimated_loss_eur": round(total_loss, 2),
        "insights_by_type": by_type,
        "insights_by_severity": by_severity,
        "invoices_with_anomalies": len([i for i in invoices if i.status == BillingInvoiceStatus.ANOMALY]),
        "invoices_clean": len([i for i in invoices if i.status == BillingInvoiceStatus.AUDITED]),
    }


def get_site_billing(db: Session, site_id: int) -> Dict[str, Any]:
    """Get billing data for a specific site."""
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {"error": "Site not found"}

    invoices = (
        db.query(EnergyInvoice).filter(EnergyInvoice.site_id == site_id).order_by(EnergyInvoice.period_start).all()
    )
    contracts = db.query(EnergyContract).filter(EnergyContract.site_id == site_id).all()
    insights = db.query(BillingInsight).filter(BillingInsight.site_id == site_id).all()

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "contracts": [
            {
                "id": c.id,
                "supplier": c.supplier_name,
                "energy_type": c.energy_type.value,
                "price_ref": c.price_ref_eur_per_kwh,
                "start": str(c.start_date) if c.start_date else None,
                "end": str(c.end_date) if c.end_date else None,
            }
            for c in contracts
        ],
        "invoices": [
            {
                "id": i.id,
                "number": i.invoice_number,
                "period_start": str(i.period_start) if i.period_start else None,
                "period_end": str(i.period_end) if i.period_end else None,
                "total_eur": i.total_eur,
                "energy_kwh": i.energy_kwh,
                "status": i.status.value if i.status else None,
            }
            for i in invoices
        ],
        "insights": [
            {
                "id": ins.id,
                "type": ins.type,
                "severity": ins.severity,
                "message": ins.message,
                "estimated_loss_eur": ins.estimated_loss_eur,
            }
            for ins in insights
        ],
        "total_eur": round(sum(i.total_eur or 0 for i in invoices), 2),
        "total_kwh": round(sum(i.energy_kwh or 0 for i in invoices), 0),
        "total_loss_eur": round(sum(i.estimated_loss_eur or 0 for i in insights), 2),
    }
