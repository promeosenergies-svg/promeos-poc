"""
PROMEOS — Data Quality Service (Chantier 1)
Compute completeness per site × energy × source (meter readings, invoices).
Returns coverage_pct, freshness_days, cause, next_step for each row.
"""

from collections import defaultdict
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import (
    Site,
    Meter,
    MeterReading,
    EnergyInvoice,
    EnergyContract,
    Portefeuille,
    EntiteJuridique,
)
from models.energy_models import EnergyVector


# Expected months of data (trailing 12 months)
EXPECTED_MONTHS = 12

# Freshness thresholds (days)
FRESH_THRESHOLD = 45  # < 45 days = fresh
STALE_THRESHOLD = 90  # 45-90 days = stale
# > 90 days = outdated

# Cause / remediation mapping — 6 causes + ok
# Each entry: (cause_label, recommended_action, cta_route)
_CAUSES = {
    "no_meter": (
        "Aucun compteur rattache",
        "Rattacher un compteur au site",
        "/onboarding?step=step_meters_connected",
    ),
    "no_readings": (
        "Compteur sans releves",
        "Importer les donnees de consommation",
        "/onboarding?step=step_meters_connected",
    ),
    "sparse": (
        "Donnees partielles (<50%)",
        "Completer les releves manquants",
        "/onboarding?step=step_meters_connected",
    ),
    "stale": (
        "Donnees obsoletes (>{} jours)".format(STALE_THRESHOLD),
        "Mettre a jour les releves",
        "/onboarding?step=step_meters_connected",
    ),
    "no_invoices": (
        "Aucune facture importee",
        "Importer les factures du fournisseur",
        "/onboarding?step=step_invoices_imported",
    ),
    "sparse_inv": (
        "Factures partielles (<50%)",
        "Importer les factures manquantes",
        "/onboarding?step=step_invoices_imported",
    ),
    "stale_inv": (
        "Factures obsoletes (>{} jours)".format(STALE_THRESHOLD),
        "Relancer l'import factures",
        "/onboarding?step=step_invoices_imported",
    ),
    "mapping_missing": (
        "Compteur non associe a un site",
        "Verifier le rattachement des compteurs",
        "/onboarding?step=step_meters_connected",
    ),
    "api_error": (
        "Erreur de collecte API",
        "Verifier la connexion du compteur communicant",
        "/onboarding?step=step_meters_connected",
    ),
    "ok": (
        "Donnees completes",
        None,
        None,
    ),
}


def _months_in_range(start: date, end: date) -> int:
    """Count distinct months between start and end (inclusive)."""
    if start > end:
        return 0
    months = set()
    current = start.replace(day=1)
    end_month = end.replace(day=1)
    while current <= end_month:
        months.add((current.year, current.month))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return len(months)


def compute_site_completeness(
    db: Session,
    site_id: int,
    today: Optional[date] = None,
) -> list:
    """
    Compute data quality rows for a single site.
    Returns list of dicts: {site_id, energy_type, source, coverage_pct, freshness_days,
                            status, cause, next_step, readings_count, months_covered}
    """
    if today is None:
        today = date.today()

    window_start = today - timedelta(days=365)
    results = []

    # ── Meter readings ──
    meters = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active == True,
        )
        .all()
    )

    meters_by_energy = defaultdict(list)
    for m in meters:
        meters_by_energy[m.energy_vector.value].append(m)

    for energy_type, site_meters in meters_by_energy.items():
        meter_ids = [m.id for m in site_meters]

        # Count distinct months with readings
        month_counts = (
            db.query(
                func.strftime("%Y-%m", MeterReading.timestamp).label("ym"),
            )
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= window_start.isoformat(),
            )
            .group_by("ym")
            .all()
        )
        months_covered = len(month_counts)

        # Total readings count
        readings_count = (
            db.query(func.count(MeterReading.id))
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= window_start.isoformat(),
            )
            .scalar()
            or 0
        )

        # Last reading date
        last_ts = db.query(func.max(MeterReading.timestamp)).filter(MeterReading.meter_id.in_(meter_ids)).scalar()

        coverage_pct = round((months_covered / EXPECTED_MONTHS) * 100, 1) if EXPECTED_MONTHS else 0
        coverage_pct = min(coverage_pct, 100.0)

        if last_ts:
            last_date = last_ts if isinstance(last_ts, date) else last_ts.date() if hasattr(last_ts, "date") else today
            freshness_days = (today - last_date).days
        else:
            freshness_days = 999

        # Determine cause
        if readings_count == 0:
            cause_key = "no_readings"
        elif coverage_pct < 50:
            cause_key = "sparse"
        elif freshness_days > STALE_THRESHOLD:
            cause_key = "stale"
        else:
            cause_key = "ok"

        cause_label, recommended_action, cta_route = _CAUSES[cause_key]

        # Status: green / amber / red
        if coverage_pct >= 80 and freshness_days <= FRESH_THRESHOLD:
            status = "green"
        elif coverage_pct >= 50 or freshness_days <= STALE_THRESHOLD:
            status = "amber"
        else:
            status = "red"

        results.append(
            {
                "site_id": site_id,
                "energy_type": energy_type,
                "source": "meter",
                "coverage_pct": coverage_pct,
                "freshness_days": freshness_days,
                "status": status,
                "cause_code": cause_key,
                "cause": cause_label,
                "next_step": recommended_action,
                "cta_route": cta_route,
                "readings_count": readings_count,
                "months_covered": months_covered,
            }
        )

    # ── Check for energy types with no meter ──
    for ev in [EnergyVector.ELECTRICITY, EnergyVector.GAS]:
        if ev.value not in meters_by_energy:
            # Check if site has invoices for this energy type
            inv_count = (
                db.query(func.count(EnergyInvoice.id))
                .join(EnergyContract, EnergyInvoice.contract_id == EnergyContract.id, isouter=True)
                .filter(
                    EnergyInvoice.site_id == site_id,
                )
                .scalar()
                or 0
            )
            if inv_count > 0:
                # Has invoices but no meter — skip no_meter row, invoices cover it
                pass
            # Only add "no_meter" if site likely uses this energy
            # (we check for electricity always, gas only if site has gas contracts)
            elif ev == EnergyVector.ELECTRICITY:
                cause_label, recommended_action, cta_route = _CAUSES["no_meter"]
                results.append(
                    {
                        "site_id": site_id,
                        "energy_type": ev.value,
                        "source": "meter",
                        "coverage_pct": 0.0,
                        "freshness_days": 999,
                        "status": "red",
                        "cause_code": "no_meter",
                        "cause": cause_label,
                        "next_step": recommended_action,
                        "cta_route": cta_route,
                        "readings_count": 0,
                        "months_covered": 0,
                    }
                )

    # ── Invoices ──
    invoices = (
        db.query(EnergyInvoice)
        .filter(
            EnergyInvoice.site_id == site_id,
            EnergyInvoice.period_start >= window_start,
        )
        .all()
    )

    if invoices:
        inv_months = set()
        last_inv_date = None
        total_kwh = 0.0
        for inv in invoices:
            if inv.period_start:
                inv_months.add((inv.period_start.year, inv.period_start.month))
            if inv.period_end:
                inv_months.add((inv.period_end.year, inv.period_end.month))
            end = inv.period_end or inv.issue_date or inv.period_start
            if end and (last_inv_date is None or end > last_inv_date):
                last_inv_date = end
            total_kwh += inv.energy_kwh or 0

        months_covered_inv = len(inv_months)
        coverage_inv = round((months_covered_inv / EXPECTED_MONTHS) * 100, 1)
        coverage_inv = min(coverage_inv, 100.0)

        if last_inv_date:
            last_d = last_inv_date if isinstance(last_inv_date, date) else last_inv_date
            freshness_inv = (today - last_d).days
        else:
            freshness_inv = 999

        if months_covered_inv == 0:
            cause_key = "no_invoices"
        elif coverage_inv < 50:
            cause_key = "sparse_inv"
        elif freshness_inv > STALE_THRESHOLD:
            cause_key = "stale_inv"
        else:
            cause_key = "ok"

        cause_label, recommended_action, cta_route = _CAUSES[cause_key]

        if coverage_inv >= 80 and freshness_inv <= FRESH_THRESHOLD:
            status = "green"
        elif coverage_inv >= 50 or freshness_inv <= STALE_THRESHOLD:
            status = "amber"
        else:
            status = "red"

        results.append(
            {
                "site_id": site_id,
                "energy_type": "all",
                "source": "invoice",
                "coverage_pct": coverage_inv,
                "freshness_days": freshness_inv,
                "status": status,
                "cause_code": cause_key,
                "cause": cause_label,
                "next_step": recommended_action,
                "cta_route": cta_route,
                "readings_count": len(invoices),
                "months_covered": months_covered_inv,
            }
        )
    else:
        cause_label, recommended_action, cta_route = _CAUSES["no_invoices"]
        results.append(
            {
                "site_id": site_id,
                "energy_type": "all",
                "source": "invoice",
                "coverage_pct": 0.0,
                "freshness_days": 999,
                "status": "red",
                "cause_code": "no_invoices",
                "cause": cause_label,
                "next_step": recommended_action,
                "cta_route": cta_route,
                "readings_count": 0,
                "months_covered": 0,
            }
        )

    return results


def compute_org_completeness(
    db: Session,
    org_id: int,
    today: Optional[date] = None,
) -> dict:
    """
    Compute data quality for all sites in an organisation.
    Returns: {org_id, overall_coverage_pct, sites_count, green/amber/red counts,
              rows: [...per site × energy × source...]}
    """
    if today is None:
        today = date.today()

    site_ids = [
        row[0]
        for row in db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif == True)
        .all()
    ]

    all_rows = []
    for sid in site_ids:
        rows = compute_site_completeness(db, sid, today)
        all_rows.extend(rows)

    # Aggregate
    green = sum(1 for r in all_rows if r["status"] == "green")
    amber = sum(1 for r in all_rows if r["status"] == "amber")
    red = sum(1 for r in all_rows if r["status"] == "red")
    total = len(all_rows)

    coverages = [r["coverage_pct"] for r in all_rows if r["source"] == "meter"]
    overall_coverage = round(sum(coverages) / max(1, len(coverages)), 1) if coverages else 0.0

    return {
        "org_id": org_id,
        "sites_count": len(site_ids),
        "overall_coverage_pct": overall_coverage,
        "summary": {"green": green, "amber": amber, "red": red, "total": total},
        "rows": all_rows,
    }
