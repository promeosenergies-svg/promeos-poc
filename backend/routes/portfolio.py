"""
PROMEOS — Portfolio Consumption Endpoints (V1)
Aggregated multi-site view: summary + per-site table.
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

router = APIRouter(prefix="/api/portfolio/consumption", tags=["Portfolio Consumption"])

# Default kWh→EUR estimation (used when no contract price available)
DEFAULT_EUR_KWH = 0.18
CO2E_FACTOR = 0.052  # kgCO2e/kWh ADEME 2024


def _parse_date_or_default(val: Optional[str], default_days_ago: int = 90) -> date_cls:
    if val:
        return date_cls.fromisoformat(val)
    return date_cls.today() - timedelta(days=default_days_ago)


def _site_consumption(db: Session, site_id: int, dt_from: datetime, dt_to: datetime):
    """Get aggregated consumption for a single site in the period."""
    row = db.query(
        func.sum(MeterReading.value_kwh).label("kwh"),
        func.count(MeterReading.id).label("n_readings"),
        func.max(MeterReading.timestamp).label("last_reading"),
    ).join(Meter, MeterReading.meter_id == Meter.id).filter(
        Meter.site_id == site_id,
        Meter.energy_vector == EnergyVector.ELECTRICITY,
        MeterReading.timestamp >= dt_from,
        MeterReading.timestamp < dt_to,
    ).first()
    return row


def _site_peak_kw(db: Session, site_id: int, dt_from: datetime, dt_to: datetime):
    """P95 approximation: max hourly kWh reading (proxy for kW peak)."""
    row = db.query(
        func.max(MeterReading.value_kwh).label("peak"),
    ).join(Meter, MeterReading.meter_id == Meter.id).filter(
        Meter.site_id == site_id,
        Meter.energy_vector == EnergyVector.ELECTRICITY,
        MeterReading.timestamp >= dt_from,
        MeterReading.timestamp < dt_to,
    ).first()
    return row.peak if row and row.peak else None


def _base_night_pct(db: Session, site_id: int, dt_from: datetime, dt_to: datetime):
    """Base nocturne %: ratio night (22h-6h) vs day (6h-22h) avg kWh."""
    from sqlalchemy import extract
    night_avg = db.query(func.avg(MeterReading.value_kwh)).join(
        Meter, MeterReading.meter_id == Meter.id
    ).filter(
        Meter.site_id == site_id,
        Meter.energy_vector == EnergyVector.ELECTRICITY,
        MeterReading.timestamp >= dt_from,
        MeterReading.timestamp < dt_to,
        ((extract("hour", MeterReading.timestamp) < 6) |
         (extract("hour", MeterReading.timestamp) >= 22)),
    ).scalar()

    day_avg = db.query(func.avg(MeterReading.value_kwh)).join(
        Meter, MeterReading.meter_id == Meter.id
    ).filter(
        Meter.site_id == site_id,
        Meter.energy_vector == EnergyVector.ELECTRICITY,
        MeterReading.timestamp >= dt_from,
        MeterReading.timestamp < dt_to,
        extract("hour", MeterReading.timestamp) >= 6,
        extract("hour", MeterReading.timestamp) < 22,
    ).scalar()

    if not day_avg or day_avg == 0:
        return None
    return round((night_avg or 0) / day_avg * 100)


def _confidence_for_readings(n_readings: int, days: int) -> str:
    """Heuristic confidence from reading density."""
    expected = days * 24  # hourly
    if n_readings >= expected * 0.8:
        return "high"
    if n_readings >= expected * 0.3:
        return "medium"
    return "low"


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
        conso = _site_consumption(db, site.id, dt_from, dt_to)
        kwh = conso.kwh or 0
        n = conso.n_readings or 0
        last_reading = conso.last_reading

        has_data = kwh > 0
        if has_data:
            sites_with_data += 1

        conf = _confidence_for_readings(n, days) if has_data else "low"
        confidence_split[conf] += 1

        eur = round(kwh * DEFAULT_EUR_KWH, 2)
        co2 = round(kwh * CO2E_FACTOR, 1)

        # Diagnostics count
        diag_count = db.query(func.count(ConsumptionInsight.id)).filter(
            ConsumptionInsight.site_id == site.id,
            ConsumptionInsight.period_start >= dt_from,
        ).scalar() or 0

        # Peak & base night (only if data)
        peak_kw = _site_peak_kw(db, site.id, dt_from, dt_to) if has_data else None
        base_night = _base_night_pct(db, site.id, dt_from, dt_to) if has_data else None

        kwh_total += kwh

        site_rows.append({
            "site_id": site.id,
            "site_name": site.nom,
            "kwh": round(kwh, 1),
            "eur": eur,
            "co2": co2,
            "base_night_pct": base_night,
            "peak_kw": round(peak_kw, 1) if peak_kw else None,
            "diagnostics_count": diag_count,
            "confidence": conf,
            "last_reading_date": last_reading.isoformat() if last_reading else None,
            "n_readings": n,
        })

    eur_total = round(kwh_total * DEFAULT_EUR_KWH, 2)
    co2_total = round(kwh_total * CO2E_FACTOR, 1)

    # Build top-lists
    with_data = [r for r in site_rows if r["kwh"] > 0]

    # Top drift: sites with most diagnostics of type "derive"
    top_drift = sorted(
        [r for r in with_data if r["diagnostics_count"] > 0],
        key=lambda r: r["diagnostics_count"],
        reverse=True,
    )[:5]

    # Top base nocturne: highest night/day ratio
    top_base_night = sorted(
        [r for r in with_data if r["base_night_pct"] is not None],
        key=lambda r: r["base_night_pct"],
        reverse=True,
    )[:5]

    # Top peaks: highest peak_kw
    top_peaks = sorted(
        [r for r in with_data if r["peak_kw"] is not None],
        key=lambda r: r["peak_kw"],
        reverse=True,
    )[:5]

    return {
        "period": {"from": d_from.isoformat(), "to": d_to.isoformat(), "days": days},
        "totals": {
            "kwh_total": round(kwh_total, 1),
            "eur_total": eur_total,
            "eur_source": "estime",
            "co2_total": co2_total,
        },
        "coverage": {
            "sites_total": sites_total,
            "sites_with_data": sites_with_data,
            "confidence_split": confidence_split,
        },
        "top_drift": [{"site_id": r["site_id"], "site_name": r["site_name"], "diagnostics_count": r["diagnostics_count"], "kwh": r["kwh"], "confidence": r["confidence"]} for r in top_drift],
        "top_base_night": [{"site_id": r["site_id"], "site_name": r["site_name"], "base_night_pct": r["base_night_pct"], "kwh": r["kwh"], "confidence": r["confidence"]} for r in top_base_night],
        "top_peaks": [{"site_id": r["site_id"], "site_name": r["site_name"], "peak_kw": r["peak_kw"], "kwh": r["kwh"], "confidence": r["confidence"]} for r in top_peaks],
    }


# -------------------------------------------------------------------
# GET /api/portfolio/consumption/sites
# -------------------------------------------------------------------
@router.get("/sites")
def get_portfolio_sites(
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    sort: str = Query("kwh_desc", description="kwh_desc|kwh_asc|name|peak|base_night|diagnostics"),
    confidence: Optional[str] = Query(None, description="high|medium|low"),
    with_anomalies: bool = Query(False),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    site_ids: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Paginated site-level consumption table for portfolio view.
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

    rows = []
    for site in all_sites:
        conso = _site_consumption(db, site.id, dt_from, dt_to)
        kwh = conso.kwh or 0
        n = conso.n_readings or 0
        last_reading = conso.last_reading
        has_data = kwh > 0
        conf = _confidence_for_readings(n, days) if has_data else "low"

        eur = round(kwh * DEFAULT_EUR_KWH, 2)
        co2 = round(kwh * CO2E_FACTOR, 1)

        diag_count = db.query(func.count(ConsumptionInsight.id)).filter(
            ConsumptionInsight.site_id == site.id,
            ConsumptionInsight.period_start >= dt_from,
        ).scalar() or 0

        peak_kw = _site_peak_kw(db, site.id, dt_from, dt_to) if has_data else None
        base_night = _base_night_pct(db, site.id, dt_from, dt_to) if has_data else None

        rows.append({
            "site_id": site.id,
            "site_name": site.nom,
            "kwh": round(kwh, 1),
            "eur": eur,
            "co2": co2,
            "base_night_pct": base_night,
            "peak_kw": round(peak_kw, 1) if peak_kw else None,
            "diagnostics_count": diag_count,
            "confidence": conf,
            "last_reading_date": last_reading.isoformat() if last_reading else None,
        })

    # Filters
    if confidence:
        rows = [r for r in rows if r["confidence"] == confidence]
    if with_anomalies:
        rows = [r for r in rows if r["diagnostics_count"] > 0]

    # Sort
    sort_key = {
        "kwh_desc": lambda r: -(r["kwh"] or 0),
        "kwh_asc": lambda r: r["kwh"] or 0,
        "name": lambda r: (r["site_name"] or "").lower(),
        "peak": lambda r: -(r["peak_kw"] or 0),
        "base_night": lambda r: -(r["base_night_pct"] or 0),
        "diagnostics": lambda r: -(r["diagnostics_count"] or 0),
    }.get(sort, lambda r: -(r["kwh"] or 0))
    rows.sort(key=sort_key)

    total = len(rows)
    page = rows[offset:offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "rows": page,
    }
