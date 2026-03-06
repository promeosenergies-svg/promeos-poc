"""
PROMEOS — Portfolio Consumption Endpoints (V2)
Aggregated multi-site view: summary + per-site table.
V2: patrimoine-first — all sites shown, data_status badge, coverage_pct per site,
    without_data filter, coverage sort.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_
from datetime import datetime, date as date_cls, timedelta
from typing import Optional, List

from database import get_db
from models import Site
from models.energy_models import Meter, MeterReading, EnergyVector
from models.consumption_insight import ConsumptionInsight
from models.action_item import ActionItem
from models.enums import ActionStatus
from services.billing_service import get_reference_price, DEFAULT_PRICE_ELEC
from config.emission_factors import get_emission_factor

router = APIRouter(prefix="/api/portfolio/consumption", tags=["Portfolio Consumption"])

CO2E_FACTOR = get_emission_factor("ELEC")  # ADEME Base Carbone 2024

# Expected readings per day by meter frequency
READINGS_PER_DAY = {
    "15min": 96, "30min": 48, "hourly": 24, "daily": 1, "monthly": 1 / 30,
}


def _parse_date_or_default(val: Optional[str], default_days_ago: int = 90) -> date_cls:
    if val:
        return date_cls.fromisoformat(val)
    return date_cls.today() - timedelta(days=default_days_ago)


def _site_consumption(db: Session, site_id: int, dt_from: datetime, dt_to: datetime):
    """Get aggregated consumption for a single site in the period."""
    row = (
        db.query(
            func.sum(MeterReading.value_kwh).label("kwh"),
            func.count(MeterReading.id).label("n_readings"),
            func.max(MeterReading.timestamp).label("last_reading"),
        )
        .join(Meter, MeterReading.meter_id == Meter.id)
        .filter(
            Meter.site_id == site_id,
            Meter.energy_vector == EnergyVector.ELECTRICITY,
            MeterReading.timestamp >= dt_from,
            MeterReading.timestamp < dt_to,
        )
        .first()
    )
    return row


def _site_peak_kw(db: Session, site_id: int, dt_from: datetime, dt_to: datetime):
    """P95 peak: 95th percentile of kWh readings (proxy for kW peak)."""
    readings = (
        db.query(MeterReading.value_kwh)
        .join(Meter, MeterReading.meter_id == Meter.id)
        .filter(
            Meter.site_id == site_id,
            Meter.energy_vector == EnergyVector.ELECTRICITY,
            MeterReading.timestamp >= dt_from,
            MeterReading.timestamp < dt_to,
            MeterReading.value_kwh.isnot(None),
        )
        .order_by(MeterReading.value_kwh.asc())
        .all()
    )
    if not readings:
        return None
    idx = min(int(len(readings) * 0.95), len(readings) - 1)
    return readings[idx].value_kwh


def _base_night_pct(db: Session, site_id: int, dt_from: datetime, dt_to: datetime):
    """Base nocturne %: part de la conso nuit (22h-6h) dans la conso totale.
    Fenêtre 22h-06h = standard tertiaire France (bureaux fermés).
    Résultat en % (0-100). Théorique si plat = 33% (8h/24h).
    """
    from sqlalchemy import extract

    night_kwh = (
        db.query(func.sum(MeterReading.value_kwh))
        .join(Meter, MeterReading.meter_id == Meter.id)
        .filter(
            Meter.site_id == site_id,
            Meter.energy_vector == EnergyVector.ELECTRICITY,
            MeterReading.timestamp >= dt_from,
            MeterReading.timestamp < dt_to,
            ((extract("hour", MeterReading.timestamp) < 6) | (extract("hour", MeterReading.timestamp) >= 22)),
        )
        .scalar()
    )

    total_kwh = (
        db.query(func.sum(MeterReading.value_kwh))
        .join(Meter, MeterReading.meter_id == Meter.id)
        .filter(
            Meter.site_id == site_id,
            Meter.energy_vector == EnergyVector.ELECTRICITY,
            MeterReading.timestamp >= dt_from,
            MeterReading.timestamp < dt_to,
        )
        .scalar()
    )

    if not total_kwh or total_kwh == 0:
        return None
    return round((night_kwh or 0) / total_kwh * 100)


def _confidence_for_readings(n_readings: int, days: int, frequency: str = "hourly") -> str:
    """Heuristic confidence from reading density, adapted to meter frequency."""
    rpd = READINGS_PER_DAY.get(frequency, 24)
    expected = days * rpd
    if expected <= 0:
        return "low"
    if n_readings >= expected * 0.8:
        return "high"
    if n_readings >= expected * 0.3:
        return "medium"
    return "low"


def _site_impact_eur(db: Session, site_id: int, dt_from: datetime) -> float:
    """Sum of estimated_loss_eur from consumption insights for a site."""
    total = (
        db.query(func.sum(ConsumptionInsight.estimated_loss_eur))
        .filter(
            ConsumptionInsight.site_id == site_id,
            ConsumptionInsight.period_start >= dt_from,
            ConsumptionInsight.estimated_loss_eur.isnot(None),
        )
        .scalar()
    )
    return round(total, 2) if total else 0.0


def _site_open_actions(db: Session, site_id: int) -> int:
    """Count of open/in_progress actions for a site."""
    return (
        db.query(func.count(ActionItem.id))
        .filter(
            ActionItem.site_id == site_id,
            ActionItem.status.in_([ActionStatus.OPEN, ActionStatus.IN_PROGRESS]),
        )
        .scalar()
        or 0
    )


def _build_site_row(db, site, dt_from, dt_to, days):
    """Build a single site row dict with all metrics (patrimoine-first)."""
    conso = _site_consumption(db, site.id, dt_from, dt_to)
    kwh = conso.kwh or 0
    n = conso.n_readings or 0
    last_reading = conso.last_reading
    has_data = kwh > 0

    # Dominant frequency for this site's meters
    dom_freq = (
        db.query(MeterReading.frequency)
        .join(Meter, MeterReading.meter_id == Meter.id)
        .filter(
            Meter.site_id == site.id,
            Meter.energy_vector == EnergyVector.ELECTRICITY,
            MeterReading.timestamp >= dt_from,
            MeterReading.timestamp < dt_to,
        )
        .group_by(MeterReading.frequency)
        .order_by(func.count(MeterReading.id).desc())
        .first()
    )
    freq_str = dom_freq[0].value if dom_freq and dom_freq[0] else "hourly"
    rpd = READINGS_PER_DAY.get(freq_str, 24)

    conf = _confidence_for_readings(n, days, freq_str) if has_data else "low"

    # V2: coverage_pct per site + data_status badge
    expected = days * rpd  # adapted to meter frequency
    coverage_pct = round(n / expected * 100) if expected > 0 else 0
    if coverage_pct > 100:
        coverage_pct = 100
    if not has_data:
        data_status = "none"  # Aucune donnee
    elif coverage_pct >= 80:
        data_status = "ok"  # Donnees completes
    else:
        data_status = "partial"  # Donnees partielles

    price, price_src = get_reference_price(db, site.id, "elec")
    eur = round(kwh * price, 2)
    co2 = round(kwh * CO2E_FACTOR, 1)

    diag_count = (
        db.query(func.count(ConsumptionInsight.id))
        .filter(
            ConsumptionInsight.site_id == site.id,
            ConsumptionInsight.period_start >= dt_from,
        )
        .scalar()
        or 0
    )

    peak_kw = _site_peak_kw(db, site.id, dt_from, dt_to) if has_data else None
    base_night = _base_night_pct(db, site.id, dt_from, dt_to) if has_data else None
    impact_eur = _site_impact_eur(db, site.id, dt_from)
    open_actions = _site_open_actions(db, site.id)

    return {
        "site_id": site.id,
        "site_name": site.nom,
        "kwh": round(kwh, 1),
        "eur": eur,
        "co2": co2,
        "base_night_pct": base_night,
        "peak_kw": round(peak_kw, 1) if peak_kw else None,
        "diagnostics_count": diag_count,
        "impact_eur_estimated": impact_eur,
        "open_actions_count": open_actions,
        "confidence": conf,
        "data_status": data_status,
        "coverage_pct": coverage_pct,
        "last_reading_date": last_reading.isoformat() if last_reading else None,
        "n_readings": n,
        "eur_source": price_src,
    }


# -------------------------------------------------------------------
# GET /api/portfolio/consumption/summary
# -------------------------------------------------------------------
@router.get("/summary")
def get_portfolio_summary(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    site_ids: Optional[str] = Query(None, description="Comma-separated site IDs"),
    db: Session = Depends(get_db),
):
    """
    Aggregated portfolio KPIs + top-lists for multi-site consumption view.
    """
    d_from = _parse_date_or_default(date_from, 90)
    d_to = _parse_date_or_default(date_to, 0) if date_to else date_cls.today()
    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to = datetime.combine(d_to + timedelta(days=1), datetime.min.time())
    days = (d_to - d_from).days or 1

    # Resolve sites
    q = db.query(Site).filter(Site.actif == True)
    if site_ids:
        ids = [int(x) for x in site_ids.split(",") if x.strip()]
        q = q.filter(Site.id.in_(ids))
    sites = q.all()

    kwh_total = 0.0
    sites_total = len(sites)
    sites_with_data = 0
    confidence_split = {"high": 0, "medium": 0, "low": 0}
    site_rows = []

    for site in sites:
        row = _build_site_row(db, site, dt_from, dt_to, days)
        if row["kwh"] > 0:
            sites_with_data += 1
        confidence_split[row["confidence"]] += 1
        kwh_total += row["kwh"]
        site_rows.append(row)

    eur_total = round(sum(r["eur"] for r in site_rows), 2)
    co2_total = round(kwh_total * CO2E_FACTOR, 1)
    impact_eur_total = round(sum(r["impact_eur_estimated"] for r in site_rows), 2)
    all_default = all(r.get("eur_source", "").startswith("default") for r in site_rows if r["kwh"] > 0)
    eur_source = "estime" if all_default else "mixte"

    # Build top-lists
    with_data = [r for r in site_rows if r["kwh"] > 0]

    top_drift = sorted(
        [r for r in with_data if r["diagnostics_count"] > 0],
        key=lambda r: r["diagnostics_count"],
        reverse=True,
    )[:5]

    top_base_night = sorted(
        [r for r in with_data if r["base_night_pct"] is not None],
        key=lambda r: r["base_night_pct"],
        reverse=True,
    )[:5]

    top_peaks = sorted(
        [r for r in with_data if r["peak_kw"] is not None],
        key=lambda r: r["peak_kw"],
        reverse=True,
    )[:5]

    # V1.1: Top impact — sites with highest estimated loss
    top_impact = sorted(
        [r for r in with_data if r["impact_eur_estimated"] > 0],
        key=lambda r: r["impact_eur_estimated"],
        reverse=True,
    )[:5]

    def _top_row(r, extra_keys):
        base = {"site_id": r["site_id"], "site_name": r["site_name"], "kwh": r["kwh"], "confidence": r["confidence"]}
        for k in extra_keys:
            base[k] = r[k]
        return base

    return {
        "period": {"from": d_from.isoformat(), "to": d_to.isoformat(), "days": days},
        "totals": {
            "kwh_total": round(kwh_total, 1),
            "eur_total": eur_total,
            "eur_source": eur_source,
            "co2_total": co2_total,
            "impact_eur_total": impact_eur_total,
        },
        "coverage": {
            "sites_total": sites_total,
            "sites_with_data": sites_with_data,
            "sites_without_data": sites_total - sites_with_data,
            "confidence_split": confidence_split,
        },
        "top_drift": [_top_row(r, ["diagnostics_count"]) for r in top_drift],
        "top_base_night": [_top_row(r, ["base_night_pct"]) for r in top_base_night],
        "top_peaks": [_top_row(r, ["peak_kw"]) for r in top_peaks],
        "top_impact": [_top_row(r, ["impact_eur_estimated"]) for r in top_impact],
    }


# -------------------------------------------------------------------
# GET /api/portfolio/consumption/sites
# -------------------------------------------------------------------
@router.get("/sites")
def get_portfolio_sites(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    sort: str = Query(
        "impact_desc", description="impact_desc|kwh_desc|kwh_asc|name|peak|base_night|diagnostics|coverage"
    ),
    confidence: Optional[str] = Query(None, description="high|medium|low"),
    with_anomalies: bool = Query(False),
    with_actions: Optional[str] = Query(None, description="with|without — filter by open actions"),
    without_data: bool = Query(False, description="Show only sites without consumption data"),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    site_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Paginated site-level consumption table for portfolio view.
    V1.1: impact_eur_estimated, open_actions_count, with_actions filter, impact sort.
    """
    d_from = _parse_date_or_default(date_from, 90)
    d_to = _parse_date_or_default(date_to, 0) if date_to else date_cls.today()
    dt_from = datetime.combine(d_from, datetime.min.time())
    dt_to = datetime.combine(d_to + timedelta(days=1), datetime.min.time())
    days = (d_to - d_from).days or 1

    q = db.query(Site).filter(Site.actif == True)
    if site_ids:
        ids = [int(x) for x in site_ids.split(",") if x.strip()]
        q = q.filter(Site.id.in_(ids))
    if search:
        q = q.filter(Site.nom.ilike(f"%{search}%"))
    all_sites = q.all()

    rows = [_build_site_row(db, site, dt_from, dt_to, days) for site in all_sites]

    # Filters
    if confidence:
        rows = [r for r in rows if r["confidence"] == confidence]
    if with_anomalies:
        rows = [r for r in rows if r["diagnostics_count"] > 0]
    if with_actions == "with":
        rows = [r for r in rows if r["open_actions_count"] > 0]
    elif with_actions == "without":
        rows = [r for r in rows if r["open_actions_count"] == 0]
    if without_data:
        rows = [r for r in rows if r["data_status"] == "none"]

    # Sort
    sort_key = {
        "impact_desc": lambda r: -(r["impact_eur_estimated"] or 0),
        "kwh_desc": lambda r: -(r["kwh"] or 0),
        "kwh_asc": lambda r: r["kwh"] or 0,
        "name": lambda r: (r["site_name"] or "").lower(),
        "peak": lambda r: -(r["peak_kw"] or 0),
        "base_night": lambda r: -(r["base_night_pct"] or 0),
        "diagnostics": lambda r: -(r["diagnostics_count"] or 0),
        "coverage": lambda r: -(r["coverage_pct"] or 0),
    }.get(sort, lambda r: -(r["impact_eur_estimated"] or 0))
    rows.sort(key=sort_key)

    total = len(rows)
    page = rows[offset : offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": page,
    }
