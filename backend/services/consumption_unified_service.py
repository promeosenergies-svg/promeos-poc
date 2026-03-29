"""
PROMEOS — A.1 Unified Consumption Service
Source unique pour toute consommation (metered vs billed vs reconciled).

Fonctions principales :
- get_consumption_summary(db, site_id, start, end, source) -> ConsumptionResult
- get_portfolio_consumption(db, org_id, start, end, source) -> list[SiteConsumption]
- reconcile_metered_billed(db, site_id, start, end) -> ReconciliationResult
"""

import logging
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    Site,
    Meter,
    MeterReading,
    EnergyInvoice,
    Portefeuille,
    EntiteJuridique,
)
from models.energy_models import EnergyVector
from services.ems.timeseries_service import resolve_best_freq, get_site_meter_ids

logger = logging.getLogger(__name__)


class ConsumptionSource(str, Enum):
    METERED = "metered"
    BILLED = "billed"
    RECONCILED = "reconciled"


# Coverage threshold: metered must cover >= 80% of the period to be preferred
METERED_COVERAGE_THRESHOLD = 0.80

# Reconciliation alert threshold: delta > 10% between metered and billed
RECONCILIATION_ALERT_THRESHOLD = 0.10


def _get_meter_ids(db: Session, site_id: int, energy_vector: EnergyVector = EnergyVector.ELECTRICITY):
    """Return active meter IDs for a site, excluding sub-meters whose parent is in the list."""
    return get_site_meter_ids(db, site_id, energy_vector)


def _metered_kwh(db: Session, meter_ids: list, start: date, end: date):
    """SUM(value_kwh) from MeterReading for given meters and period."""
    if not meter_ids:
        return 0.0, 0, 0

    start_dt = datetime(start.year, start.month, start.day)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59)

    best = resolve_best_freq(db, meter_ids, start_dt, end_dt)

    result = (
        db.query(
            func.coalesce(func.sum(MeterReading.value_kwh), 0.0),
            func.count(MeterReading.id),
        )
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_dt,
            MeterReading.timestamp <= end_dt,
            MeterReading.frequency.in_(best),
        )
        .first()
    )
    total_kwh = float(result[0])
    readings_count = int(result[1])

    # Coverage: how many days have at least one reading
    days_with_data = (
        db.query(func.count(func.distinct(func.date(MeterReading.timestamp))))
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_dt,
            MeterReading.timestamp <= end_dt,
            MeterReading.frequency.in_(best),
        )
        .scalar()
    ) or 0

    return total_kwh, readings_count, days_with_data


def _billed_kwh(db: Session, site_id: int, start: date, end: date):
    """SUM(energy_kwh) from EnergyInvoice for given site and period."""
    result = (
        db.query(
            func.coalesce(func.sum(EnergyInvoice.energy_kwh), 0.0),
            func.count(EnergyInvoice.id),
        )
        .filter(
            EnergyInvoice.site_id == site_id,
            EnergyInvoice.period_start >= start,
            EnergyInvoice.period_end <= end,
        )
        .first()
    )
    total_kwh = float(result[0])
    invoice_count = int(result[1])

    # Coverage: count months with invoices
    months_with_invoices = (
        db.query(func.count(func.distinct(func.strftime("%Y-%m", EnergyInvoice.period_start))))
        .filter(
            EnergyInvoice.site_id == site_id,
            EnergyInvoice.period_start >= start,
            EnergyInvoice.period_end <= end,
        )
        .scalar()
    ) or 0

    return total_kwh, invoice_count, months_with_invoices


def get_consumption_summary(
    db: Session,
    site_id: int,
    start: date,
    end: date,
    source: ConsumptionSource = ConsumptionSource.RECONCILED,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> dict:
    """
    Source unique pour la consommation d'un site sur une periode.

    Returns:
        {
            value_kwh: float,
            source_used: "metered" | "billed" | "estimated",
            coverage_pct: float (0-100),
            confidence: "high" | "medium" | "low" | "none",
            period: { start, end, days },
            details: { metered_kwh, metered_readings, billed_kwh, billed_invoices }
        }
    """
    period_days = max(1, (end - start).days)

    meter_ids = _get_meter_ids(db, site_id, energy_vector)
    metered_kwh, metered_readings, metered_days = _metered_kwh(db, meter_ids, start, end)
    billed_kwh, billed_invoices, billed_months = _billed_kwh(db, site_id, start, end)

    metered_coverage = metered_days / period_days if period_days > 0 else 0
    # Estimate billed coverage: each invoice covers ~30 days
    expected_months = max(1, period_days / 30)
    billed_coverage = min(1.0, billed_months / expected_months)

    details = {
        "metered_kwh": round(metered_kwh, 2),
        "metered_readings": metered_readings,
        "metered_days": metered_days,
        "metered_coverage_pct": round(metered_coverage * 100, 1),
        "billed_kwh": round(billed_kwh, 2),
        "billed_invoices": billed_invoices,
        "billed_months": billed_months,
        "billed_coverage_pct": round(billed_coverage * 100, 1),
    }

    # Source selection logic
    if source == ConsumptionSource.METERED:
        value_kwh = metered_kwh
        source_used = "metered"
        coverage = metered_coverage
    elif source == ConsumptionSource.BILLED:
        value_kwh = billed_kwh
        source_used = "billed"
        coverage = billed_coverage
    else:
        # RECONCILED: prefer metered if coverage >= 80%, else billed, else estimated
        if metered_coverage >= METERED_COVERAGE_THRESHOLD and metered_kwh > 0:
            value_kwh = metered_kwh
            source_used = "metered"
            coverage = metered_coverage
        elif billed_kwh > 0:
            value_kwh = billed_kwh
            source_used = "billed"
            coverage = billed_coverage
        elif metered_kwh > 0:
            # Metered data exists but coverage < threshold — use it with low confidence
            value_kwh = metered_kwh
            source_used = "metered"
            coverage = metered_coverage
        else:
            # Fallback: use site.annual_kwh_total as estimate
            site = db.query(Site).filter(Site.id == site_id).first()
            annual = site.annual_kwh_total if site and site.annual_kwh_total else 0
            value_kwh = round(annual * period_days / 365, 2) if annual else 0
            source_used = "estimated"
            coverage = 0

    # Confidence
    if source_used == "metered" and coverage >= METERED_COVERAGE_THRESHOLD:
        confidence = "high"
    elif source_used == "billed" and billed_coverage >= 0.5:
        confidence = "medium"
    elif source_used == "estimated" and value_kwh > 0:
        confidence = "low"
    elif value_kwh == 0:
        confidence = "none"
    else:
        confidence = "low"

    return {
        "site_id": site_id,
        "value_kwh": round(value_kwh, 2),
        "source_used": source_used,
        "coverage_pct": round(coverage * 100, 1),
        "confidence": confidence,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": period_days,
        },
        "details": details,
    }


def get_portfolio_consumption(
    db: Session,
    org_id: int,
    start: date,
    end: date,
    source: ConsumptionSource = ConsumptionSource.RECONCILED,
) -> dict:
    """
    Aggrege la consommation pour tous les sites de l'org.

    Returns:
        {
            org_id, period, total_kwh, sites_count, sites_with_data,
            confidence, sites: [ { site_id, nom, value_kwh, source_used, ... } ]
        }
    """
    sites = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif == True)
        .all()
    )

    results = []
    total_kwh = 0.0
    sites_with_data = 0

    for site in sites:
        summary = get_consumption_summary(db, site.id, start, end, source)
        row = {
            "site_id": site.id,
            "nom": site.nom,
            "value_kwh": summary["value_kwh"],
            "source_used": summary["source_used"],
            "coverage_pct": summary["coverage_pct"],
            "confidence": summary["confidence"],
        }
        results.append(row)
        total_kwh += summary["value_kwh"]
        if summary["value_kwh"] > 0:
            sites_with_data += 1

    # Portfolio confidence
    if not sites:
        confidence = "none"
    elif sites_with_data >= len(sites) * 0.8:
        confidence = "high"
    elif sites_with_data >= len(sites) * 0.5:
        confidence = "medium"
    elif sites_with_data > 0:
        confidence = "low"
    else:
        confidence = "none"

    return {
        "org_id": org_id,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": max(1, (end - start).days),
        },
        "total_kwh": round(total_kwh, 2),
        "sites_count": len(sites),
        "sites_with_data": sites_with_data,
        "confidence": confidence,
        "sites": results,
    }


def reconcile_metered_billed(
    db: Session,
    site_id: int,
    start: date,
    end: date,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> dict:
    """
    Compare metered vs billed. Retourne delta_pct et alerte si > 10%.

    Returns:
        {
            site_id, period,
            metered_kwh, billed_kwh,
            delta_kwh, delta_pct,
            status: "aligned" | "divergent" | "insufficient_data",
            alert: bool,
            recommendation
        }
    """
    period_days = max(1, (end - start).days)

    meter_ids = _get_meter_ids(db, site_id, energy_vector)
    metered_kwh, metered_readings, metered_days = _metered_kwh(db, meter_ids, start, end)
    billed_kwh, billed_invoices, billed_months = _billed_kwh(db, site_id, start, end)

    metered_coverage = metered_days / period_days if period_days > 0 else 0

    result = {
        "site_id": site_id,
        "period": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "days": period_days,
        },
        "metered_kwh": round(metered_kwh, 2),
        "metered_readings": metered_readings,
        "metered_coverage_pct": round(metered_coverage * 100, 1),
        "billed_kwh": round(billed_kwh, 2),
        "billed_invoices": billed_invoices,
    }

    # Need both sources with meaningful data
    if metered_kwh <= 0 or billed_kwh <= 0:
        result.update(
            {
                "delta_kwh": None,
                "delta_pct": None,
                "status": "insufficient_data",
                "alert": False,
                "recommendation": (
                    "Donnees insuffisantes pour la reconciliation. "
                    "Verifiez que des releves compteur ET des factures couvrent la periode."
                ),
            }
        )
        return result

    delta_kwh = metered_kwh - billed_kwh
    ref = max(metered_kwh, billed_kwh)
    delta_pct = round(delta_kwh / ref * 100, 2) if ref > 0 else 0

    is_divergent = abs(delta_pct) > RECONCILIATION_ALERT_THRESHOLD * 100

    if is_divergent:
        if delta_kwh > 0:
            recommendation = (
                f"Ecart de {abs(delta_pct):.1f}% : compteur > facture. "
                "Verifiez si des consommations ne sont pas facturees."
            )
        else:
            recommendation = (
                f"Ecart de {abs(delta_pct):.1f}% : facture > compteur. "
                "Verifiez le compteur ou les estimations fournisseur."
            )
    else:
        recommendation = "Les sources metered et billed sont coherentes."

    result.update(
        {
            "delta_kwh": round(delta_kwh, 2),
            "delta_pct": delta_pct,
            "status": "divergent" if is_divergent else "aligned",
            "alert": is_divergent,
            "recommendation": recommendation,
        }
    )
    return result


def check_reconciliation_alert(
    db: Session,
    site_id: int,
    start: date,
    end: date,
    energy_vector: EnergyVector = EnergyVector.ELECTRICITY,
) -> Optional[dict]:
    """
    Cree un BillingInsight si l'ecart metered/billed depasse le seuil.
    Idempotent : ne cree pas de doublon pour le meme site + periode.
    """
    period_days = max(1, (end - start).days)

    meter_ids = _get_meter_ids(db, site_id, energy_vector)
    metered_kwh, _, metered_days = _metered_kwh(db, meter_ids, start, end)
    billed_kwh, _, _ = _billed_kwh(db, site_id, start, end)

    if metered_kwh <= 0 or billed_kwh <= 0:
        return None

    delta_pct = abs(metered_kwh - billed_kwh) / max(metered_kwh, billed_kwh) * 100

    if delta_pct <= RECONCILIATION_ALERT_THRESHOLD * 100:
        return None

    try:
        from models.billing_models import BillingInsight
        from models.enums import InsightStatus

        # Dedup : check for existing open insight of same type for this site
        existing = (
            db.query(BillingInsight)
            .filter(
                BillingInsight.site_id == site_id,
                BillingInsight.type == "reconciliation_metered_billed",
                BillingInsight.insight_status.in_([InsightStatus.OPEN, InsightStatus.ACK]),
            )
            .first()
        )
        if existing:
            return {"insight_id": existing.id, "status": "already_exists"}

        severity = "high" if delta_pct > 20 else "medium"
        message = (
            f"Ecart compteur/facture = {delta_pct:.1f}% sur {start} - {end}. "
            f"Metered={metered_kwh:.0f} kWh, Billed={billed_kwh:.0f} kWh."
        )

        import json

        insight = BillingInsight(
            site_id=site_id,
            type="reconciliation_metered_billed",
            severity=severity,
            message=message,
            metrics_json=json.dumps(
                {
                    "period_start": start.isoformat(),
                    "period_end": end.isoformat(),
                    "metered_kwh": round(metered_kwh, 2),
                    "billed_kwh": round(billed_kwh, 2),
                    "delta_pct": round(delta_pct, 1),
                }
            ),
            estimated_loss_eur=None,
        )
        db.add(insight)
        db.commit()

        logger.info(
            "Reconciliation alert created for site %d: delta=%.1f%%",
            site_id,
            delta_pct,
        )
        return {"insight_id": insight.id, "status": "created", "delta_pct": round(delta_pct, 1)}

    except Exception as e:
        logger.warning("Failed to create reconciliation alert for site %d: %s", site_id, e)
        db.rollback()
        return None
