"""
PROMEOS — Data Quality Service (Chantier 1)
Compute completeness per site × energy × source (meter readings, invoices).
Returns coverage_pct, freshness_days, cause, next_step for each row.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
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
from models.energy_models import EnergyVector, Anomaly


def _to_date(val, fallback=None):
    """Convert datetime/date/string to a plain date, avoiding date-datetime comparison errors."""
    if val is None:
        return fallback
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str) and len(val) >= 10:
        try:
            return date.fromisoformat(val[:10])
        except ValueError:
            return fallback
    return fallback


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
            last_date = _to_date(last_ts, today)
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


# ══════════════════════════════════════════════════════════════════
# D.1 — Score qualité données 0-100 (4 dimensions pondérées)
# ══════════════════════════════════════════════════════════════════

# Grade boundaries
DQ_GRADES = {"A": 85, "B": 70, "C": 50, "D": 30}

# Dimension weights
DQ_WEIGHTS = {
    "completeness": 0.35,
    "freshness": 0.25,
    "accuracy": 0.25,
    "consistency": 0.15,
}


def _grade(score: float) -> str:
    if score >= DQ_GRADES["A"]:
        return "A"
    if score >= DQ_GRADES["B"]:
        return "B"
    if score >= DQ_GRADES["C"]:
        return "C"
    if score >= DQ_GRADES["D"]:
        return "D"
    return "F"


def _dim_completeness(db: Session, site_id: int, window_start: date, today: date) -> dict:
    """COMPLETENESS (35%) — months with readings / 12."""
    meter_ids = [r[0] for r in db.query(Meter.id).filter(Meter.site_id == site_id, Meter.is_active == True).all()]

    if meter_ids:
        month_rows = (
            db.query(func.strftime("%Y-%m", MeterReading.timestamp))
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= window_start.isoformat(),
            )
            .group_by(func.strftime("%Y-%m", MeterReading.timestamp))
            .all()
        )
        months_with_readings = len(month_rows)
        score = round(min((months_with_readings / 12) * 100, 100), 1)
        detail = f"{months_with_readings} mois sur 12 avec lectures"
    else:
        # No meter readings — check invoices as fallback
        inv_count = (
            db.query(func.count(EnergyInvoice.id))
            .filter(EnergyInvoice.site_id == site_id, EnergyInvoice.period_start >= window_start)
            .scalar()
            or 0
        )
        if inv_count > 0:
            score = 40.0
            detail = f"Pas de compteur — {inv_count} factures disponibles"
        else:
            score = 0.0
            detail = "Aucune donnée de consommation"

    rec = "Importer les relevés de compteur manquants" if score < 70 else None
    return {"score": score, "weight": DQ_WEIGHTS["completeness"], "detail": detail, "recommendation": rec}


def _dim_freshness(db: Session, site_id: int, today: date) -> dict:
    """FRESHNESS (25%) — recency of last reading."""
    meter_ids = [r[0] for r in db.query(Meter.id).filter(Meter.site_id == site_id, Meter.is_active == True).all()]

    last_ts = None
    if meter_ids:
        last_ts = db.query(func.max(MeterReading.timestamp)).filter(MeterReading.meter_id.in_(meter_ids)).scalar()

    if last_ts:
        last_date = _to_date(last_ts, today)
        days_since = (today - last_date).days
        score = round(max(0, 100 - days_since * 2), 1)
        detail = f"Dernière lecture il y a {days_since} jour{'s' if days_since != 1 else ''}"
    else:
        days_since = 999
        score = 0.0
        detail = "Aucun relevé de compteur"

    rec = "Mettre à jour les relevés de consommation" if score < 70 else None
    return {"score": score, "weight": DQ_WEIGHTS["freshness"], "detail": detail, "recommendation": rec}


def _dim_accuracy(db: Session, site_id: int, window_start: date) -> dict:
    """ACCURACY (25%) — anomaly ratio over readings."""
    meter_ids = [r[0] for r in db.query(Meter.id).filter(Meter.site_id == site_id, Meter.is_active == True).all()]

    if not meter_ids:
        return {
            "score": 50.0,
            "weight": DQ_WEIGHTS["accuracy"],
            "detail": "Pas de compteur — score neutre",
            "recommendation": None,
        }

    nb_readings = (
        db.query(func.count(MeterReading.id))
        .filter(MeterReading.meter_id.in_(meter_ids), MeterReading.timestamp >= window_start.isoformat())
        .scalar()
        or 0
    )

    nb_anomalies = (
        db.query(func.count(Anomaly.id))
        .filter(
            Anomaly.meter_id.in_(meter_ids),
            Anomaly.detected_at >= window_start.isoformat(),
            Anomaly.is_active == True,
        )
        .scalar()
        or 0
    )

    ratio = nb_anomalies / max(nb_readings, 1)
    score = round(max(0, 100 - ratio * 1000), 1)

    if nb_anomalies > 0:
        detail = f"{nb_anomalies} anomalie{'s' if nb_anomalies > 1 else ''} détectée{'s' if nb_anomalies > 1 else ''} sur {nb_readings:,} lectures"
    else:
        detail = f"Aucune anomalie sur {nb_readings:,} lectures"

    rec = "Vérifier les pics de consommation anormaux" if score < 70 else None
    return {"score": score, "weight": DQ_WEIGHTS["accuracy"], "detail": detail, "recommendation": rec}


def _dim_consistency(db: Session, site_id: int, window_start: date, today: date) -> dict:
    """CONSISTENCY (15%) — metered vs billed delta."""
    try:
        from services.consumption_unified_service import reconcile_metered_billed

        result = reconcile_metered_billed(db, site_id, window_start, today)
        if result.get("status") == "insufficient_data":
            return {
                "score": 50.0,
                "weight": DQ_WEIGHTS["consistency"],
                "detail": "Données insuffisantes pour la réconciliation",
                "recommendation": None,
            }

        delta_pct = abs(result.get("delta_pct") or 0)
        score = round(max(0, 100 - delta_pct * 5), 1)
        detail = f"Écart compteur/facture : {delta_pct:.1f}%"
        rec = "Rapprocher les relevés compteur des factures" if score < 70 else None
        return {"score": score, "weight": DQ_WEIGHTS["consistency"], "detail": detail, "recommendation": rec}
    except Exception:
        return {
            "score": 50.0,
            "weight": DQ_WEIGHTS["consistency"],
            "detail": "Réconciliation non disponible",
            "recommendation": None,
        }


def compute_site_data_quality(
    db: Session,
    site_id: int,
    today: Optional[date] = None,
) -> dict:
    """
    Score qualité données 0-100 basé sur 4 dimensions pondérées.
    Retourne score, grade, dimensions, recommendations.
    """
    if today is None:
        today = date.today()

    window_start = today - timedelta(days=365)

    dims = {
        "completeness": _dim_completeness(db, site_id, window_start, today),
        "freshness": _dim_freshness(db, site_id, today),
        "accuracy": _dim_accuracy(db, site_id, window_start),
        "consistency": _dim_consistency(db, site_id, window_start, today),
    }

    global_score = sum(d["score"] * d["weight"] for d in dims.values())
    global_score = round(min(global_score, 100), 1)

    # Build recommendations for dimensions with score < 70
    recommendations = []
    priority_map = {0: "high", 1: "high", 2: "medium", 3: "low"}
    sorted_dims = sorted(
        [(k, v) for k, v in dims.items() if v["recommendation"]],
        key=lambda x: x[1]["score"],
    )
    for idx, (dim_key, dim) in enumerate(sorted_dims):
        cta_map = {
            "completeness": f"/consommations/import?site_id={site_id}",
            "freshness": f"/consommations/import?site_id={site_id}",
            "accuracy": f"/monitoring?site_id={site_id}",
            "consistency": f"/billing?site_id={site_id}",
        }
        recommendations.append(
            {
                "priority": priority_map.get(idx, "low"),
                "message": dim["recommendation"],
                "cta_route": cta_map.get(dim_key, f"/sites/{site_id}"),
            }
        )

    from datetime import datetime

    return {
        "site_id": site_id,
        "score": global_score,
        "grade": _grade(global_score),
        "dimensions": dims,
        "recommendations": recommendations,
        "computed_at": datetime.utcnow().isoformat(),
    }


def compute_site_freshness(
    db: Session,
    site_id: int,
    today: Optional[date] = None,
) -> dict:
    """
    D.2 — Fraîcheur des données pour un site.
    Retourne last_reading, last_invoice, staleness_days, status, label_fr, recommendations.
    Status: "fresh" (<48h), "recent" (2-7j), "stale" (7-30j), "expired" (>30j), "no_data".
    """
    if today is None:
        today = date.today()

    # Last meter reading
    meter_ids = [r[0] for r in db.query(Meter.id).filter(Meter.site_id == site_id, Meter.is_active == True).all()]

    last_reading_date = None
    if meter_ids:
        last_ts = db.query(func.max(MeterReading.timestamp)).filter(MeterReading.meter_id.in_(meter_ids)).scalar()
        if last_ts:
            last_reading_date = _to_date(last_ts)

    # Last invoice
    last_inv = db.query(func.max(EnergyInvoice.period_end)).filter(EnergyInvoice.site_id == site_id).scalar()
    last_invoice_date = None
    if last_inv:
        last_invoice_date = _to_date(last_inv)

    # Compute staleness from most recent data source
    most_recent = None
    if last_reading_date and last_invoice_date:
        most_recent = max(last_reading_date, last_invoice_date)
    elif last_reading_date:
        most_recent = last_reading_date
    elif last_invoice_date:
        most_recent = last_invoice_date

    if most_recent is None:
        staleness_days = 999
        status = "no_data"
        label_fr = "Aucune donnée"
    else:
        staleness_days = (today - most_recent).days
        if staleness_days <= 2:
            status = "fresh"
            label_fr = "À jour"
        elif staleness_days <= 7:
            status = "recent"
            label_fr = "Récent"
        elif staleness_days <= 30:
            status = "stale"
            label_fr = "En retard"
        else:
            status = "expired"
            label_fr = "Périmées"

    recommendations = []
    if status == "stale":
        recommendations.append("Mettre à jour les relevés de consommation")
    elif status == "expired":
        recommendations.append("Importer les données récentes — les KPIs sont obsolètes")
        if not last_reading_date:
            recommendations.append("Rattacher un compteur communicant pour des données automatiques")
        if not last_invoice_date:
            recommendations.append("Importer les dernières factures du fournisseur")
    elif status == "no_data":
        recommendations.append("Importer des données de consommation (compteur ou facture)")

    return {
        "site_id": site_id,
        "last_reading": last_reading_date.isoformat() if last_reading_date else None,
        "last_invoice": last_invoice_date.isoformat() if last_invoice_date else None,
        "staleness_days": staleness_days,
        "status": status,
        "label_fr": label_fr,
        "recommendations": recommendations,
    }


def compute_portfolio_data_quality(
    db: Session,
    org_id: int,
    today: Optional[date] = None,
) -> dict:
    """
    Agrège les scores data quality de tous les sites d'une organisation.
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

    sites = []
    for sid in site_ids:
        sq = compute_site_data_quality(db, sid, today)
        sites.append(sq)

    scores = [s["score"] for s in sites]
    avg_score = round(sum(scores) / max(len(scores), 1), 1) if scores else 0

    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for s in sites:
        grade_dist[s["grade"]] = grade_dist.get(s["grade"], 0) + 1

    worst = sorted(sites, key=lambda s: s["score"])[:3]

    return {
        "org_id": org_id,
        "avg_score": avg_score,
        "grade": _grade(avg_score),
        "grade_distribution": grade_dist,
        "worst_sites": worst,
        "sites": sites,
    }
