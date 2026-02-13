"""
PROMEOS — Bill Intelligence Service (Sprint 7.1)
Shadow billing simplifie + anomaly engine (10 regles) + summary.
V1.1: get_reference_price (contract > site_tariff > fallback),
      proof/explainability (inputs+threshold in metrics),
      cross-link R9 -> diagnostic-conso,
      insight workflow defaults.
"""
import json
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Site, EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight,
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus,
    SiteTariffProfile, InsightStatus,
)


# ========================================
# Price reference resolution (V1.1)
# ========================================

DEFAULT_PRICE_ELEC = 0.18
DEFAULT_PRICE_GAZ = 0.09


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
      2. SiteTariffProfile for the site
      3. Config fallback (0.18 elec, 0.09 gaz)
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

    # Priority 2: SiteTariffProfile
    tariff = db.query(SiteTariffProfile).filter(
        SiteTariffProfile.site_id == site_id
    ).first()
    if tariff and tariff.price_ref_eur_per_kwh:
        return (tariff.price_ref_eur_per_kwh, "site_tariff_profile")

    # Priority 3: Default fallback
    if energy_type == "gaz":
        return (DEFAULT_PRICE_GAZ, "default_gaz")
    return (DEFAULT_PRICE_ELEC, "default_elec")


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
            db, invoice.site_id, energy_type_str,
            invoice.period_start, invoice.period_end,
        )
    elif contract and contract.price_ref_eur_per_kwh:
        price_ref = contract.price_ref_eur_per_kwh
        ref_source = f"contract:{contract.id}"

    if price_ref is None:
        price_ref = DEFAULT_PRICE_ELEC
        ref_source = "default_elec"

    shadow_total = round(invoice.energy_kwh * price_ref, 2)
    actual_total = invoice.total_eur or 0
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

def _rule_shadow_gap(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]) -> Optional[Dict]:
    """R1: Ecart shadow billing > 10%."""
    shadow = shadow_billing_simple(invoice, contract)
    if shadow["delta_pct"] is not None and abs(shadow["delta_pct"]) > 10:
        return {
            "type": "shadow_gap",
            "severity": "high" if abs(shadow["delta_pct"]) > 20 else "medium",
            "message": f"Ecart shadow billing de {shadow['delta_pct']:+.1f}% ({shadow['delta_eur']:+.2f} EUR)",
            "metrics": {
                **shadow,
                "inputs": _build_inputs(invoice, shadow.get("price_ref_eur_kwh")),
                "threshold_pct": 10,
                "delta_calculated_pct": shadow["delta_pct"],
            },
            "estimated_loss_eur": abs(shadow["delta_eur"]) if shadow["delta_eur"] and shadow["delta_eur"] > 0 else 0,
        }
    return None


def _rule_unit_price_high(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]) -> Optional[Dict]:
    """R2: Prix unitaire anormalement eleve (> 0.30 EUR/kWh elec, > 0.15 EUR/kWh gaz)."""
    if not invoice.energy_kwh or invoice.energy_kwh <= 0 or not invoice.total_eur:
        return None
    unit_price = invoice.total_eur / invoice.energy_kwh
    threshold = 0.30 if _energy_type(invoice, contract) == "elec" else 0.15
    if unit_price > threshold:
        return {
            "type": "unit_price_high",
            "severity": "high",
            "message": f"Prix unitaire eleve: {unit_price:.4f} EUR/kWh (seuil: {threshold})",
            "metrics": {
                "unit_price": round(unit_price, 4),
                "threshold": threshold,
                "inputs": _build_inputs(invoice, threshold),
                "delta_calculated": round(unit_price - threshold, 4),
            },
            "estimated_loss_eur": round((unit_price - threshold) * invoice.energy_kwh, 2),
        }
    return None


def _rule_duplicate_invoice(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine], db: Session = None) -> Optional[Dict]:
    """R3: Doublon de facture (meme site, meme periode, meme montant)."""
    if db is None or not invoice.period_start or not invoice.period_end:
        return None
    dupes = db.query(EnergyInvoice).filter(
        EnergyInvoice.site_id == invoice.site_id,
        EnergyInvoice.period_start == invoice.period_start,
        EnergyInvoice.period_end == invoice.period_end,
        EnergyInvoice.total_eur == invoice.total_eur,
        EnergyInvoice.id != invoice.id,
    ).count()
    if dupes > 0:
        return {
            "type": "duplicate_invoice",
            "severity": "critical",
            "message": f"Facture en doublon ({dupes} autre(s) avec meme periode et montant)",
            "metrics": {
                "duplicates_count": dupes,
                "inputs": _build_inputs(invoice),
            },
            "estimated_loss_eur": invoice.total_eur or 0,
        }
    return None


def _rule_missing_period(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]) -> Optional[Dict]:
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
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_period_too_long(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]) -> Optional[Dict]:
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
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_negative_kwh(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]) -> Optional[Dict]:
    """R6: Consommation negative."""
    if invoice.energy_kwh is not None and invoice.energy_kwh < 0:
        return {
            "type": "negative_kwh",
            "severity": "high",
            "message": f"Consommation negative: {invoice.energy_kwh} kWh",
            "metrics": {
                "energy_kwh": invoice.energy_kwh,
                "inputs": _build_inputs(invoice),
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_zero_amount(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]) -> Optional[Dict]:
    """R7: Montant total = 0 mais consommation > 0."""
    if (invoice.total_eur is not None and invoice.total_eur == 0
            and invoice.energy_kwh is not None and invoice.energy_kwh > 0):
        return {
            "type": "zero_amount",
            "severity": "high",
            "message": f"Montant = 0 EUR pour {invoice.energy_kwh} kWh consommes",
            "metrics": {
                "total_eur": invoice.total_eur,
                "energy_kwh": invoice.energy_kwh,
                "inputs": _build_inputs(invoice),
            },
            "estimated_loss_eur": 0,
        }
    return None


def _rule_lines_sum_mismatch(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine]) -> Optional[Dict]:
    """R8: Somme des lignes != total facture (tolerance 2%)."""
    if not lines or not invoice.total_eur:
        return None
    lines_sum = sum(l.amount_eur or 0 for l in lines)
    if lines_sum == 0:
        return None
    diff = abs(invoice.total_eur - lines_sum)
    pct = diff / invoice.total_eur * 100 if invoice.total_eur else 0
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
            },
            "estimated_loss_eur": round(diff, 2) if diff > 1 else 0,
        }
    return None


def _rule_consumption_spike(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine], db: Session = None) -> Optional[Dict]:
    """R9: Pic de consommation (> 2x la moyenne des 6 derniers mois)."""
    if db is None or not invoice.energy_kwh or not invoice.site_id:
        return None
    avg_result = db.query(func.avg(EnergyInvoice.energy_kwh)).filter(
        EnergyInvoice.site_id == invoice.site_id,
        EnergyInvoice.id != invoice.id,
        EnergyInvoice.energy_kwh > 0,
    ).scalar()
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


def _rule_price_drift(invoice: EnergyInvoice, contract: Optional[EnergyContract], lines: List[EnergyInvoiceLine], db: Session = None) -> Optional[Dict]:
    """R10: Derive de prix unitaire par rapport au contrat (> 15%)."""
    if not contract or not contract.price_ref_eur_per_kwh:
        return None
    if not invoice.energy_kwh or invoice.energy_kwh <= 0 or not invoice.total_eur:
        return None
    actual_unit = invoice.total_eur / invoice.energy_kwh
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
                "threshold_pct": 15,
                "delta_calculated_pct": round(drift_pct, 1),
                "inputs": _build_inputs(invoice, ref),
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
]


def run_anomaly_engine(
    invoice: EnergyInvoice,
    lines: List[EnergyInvoiceLine],
    contract: Optional[EnergyContract],
    db: Session,
) -> List[Dict[str, Any]]:
    """Run all billing rules on an invoice. Returns list of anomaly dicts."""
    anomalies = []
    for rule_id, rule_name, rule_fn in BILLING_RULES:
        try:
            import inspect
            params = inspect.signature(rule_fn).parameters
            if "db" in params:
                result = rule_fn(invoice, contract, lines, db=db)
            else:
                result = rule_fn(invoice, contract, lines)
            if result:
                result["rule_id"] = rule_id
                result["rule_name"] = rule_name
                anomalies.append(result)
        except Exception:
            pass
    return anomalies


def persist_insights(
    db: Session,
    invoice: EnergyInvoice,
    anomalies: List[Dict[str, Any]],
) -> List[BillingInsight]:
    """Persist anomaly results as BillingInsight rows."""
    db.query(BillingInsight).filter(BillingInsight.invoice_id == invoice.id).delete()

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

    invoices = db.query(EnergyInvoice).filter(EnergyInvoice.site_id == site_id).order_by(EnergyInvoice.period_start).all()
    contracts = db.query(EnergyContract).filter(EnergyContract.site_id == site_id).all()
    insights = db.query(BillingInsight).filter(BillingInsight.site_id == site_id).all()

    return {
        "site_id": site_id,
        "site_nom": site.nom,
        "contracts": [
            {
                "id": c.id, "supplier": c.supplier_name,
                "energy_type": c.energy_type.value,
                "price_ref": c.price_ref_eur_per_kwh,
                "start": str(c.start_date) if c.start_date else None,
                "end": str(c.end_date) if c.end_date else None,
            }
            for c in contracts
        ],
        "invoices": [
            {
                "id": i.id, "number": i.invoice_number,
                "period_start": str(i.period_start) if i.period_start else None,
                "period_end": str(i.period_end) if i.period_end else None,
                "total_eur": i.total_eur, "energy_kwh": i.energy_kwh,
                "status": i.status.value if i.status else None,
            }
            for i in invoices
        ],
        "insights": [
            {
                "id": ins.id, "type": ins.type, "severity": ins.severity,
                "message": ins.message,
                "estimated_loss_eur": ins.estimated_loss_eur,
            }
            for ins in insights
        ],
        "total_eur": round(sum(i.total_eur or 0 for i in invoices), 2),
        "total_kwh": round(sum(i.energy_kwh or 0 for i in invoices), 0),
        "total_loss_eur": round(sum(i.estimated_loss_eur or 0 for i in insights), 2),
    }
