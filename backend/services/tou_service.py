"""
PROMEOS - TOU Service (HP/HC Schedule Management)
CRUD + versioned TOU schedules + HP/HC ratio calculation.
"""

import json
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.tou_schedule import TOUSchedule
from models import Meter, MeterReading, Site
from models.energy_models import EnergyVector
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_HC_EUR_KWH
from services.ems.timeseries_service import resolve_best_freq


# Default TURPE-like schedule (HP 6h-22h weekday, HC rest)
DEFAULT_WINDOWS = [
    {
        "day_types": ["weekday"],
        "start": "06:00",
        "end": "22:00",
        "period": "HP",
        "price_eur_kwh": DEFAULT_PRICE_ELEC_EUR_KWH,
    },
    {
        "day_types": ["weekday"],
        "start": "22:00",
        "end": "06:00",
        "period": "HC",
        "price_eur_kwh": DEFAULT_PRICE_HC_EUR_KWH,
    },
    {
        "day_types": ["weekend", "holiday"],
        "start": "00:00",
        "end": "24:00",
        "period": "HC",
        "price_eur_kwh": DEFAULT_PRICE_HC_EUR_KWH,
    },
]


def get_schedules(
    db: Session,
    site_id: Optional[int] = None,
    meter_id: Optional[int] = None,
    active_only: bool = True,
) -> List[Dict[str, Any]]:
    """List TOU schedules for a site or meter."""
    query = db.query(TOUSchedule)
    if site_id:
        query = query.filter(TOUSchedule.site_id == site_id)
    if meter_id:
        query = query.filter(TOUSchedule.meter_id == meter_id)
    if active_only:
        query = query.filter(TOUSchedule.is_active == True)
    query = query.order_by(TOUSchedule.effective_from.desc())
    return [_serialize_schedule(s) for s in query.all()]


def get_active_schedule(
    db: Session,
    site_id: int,
    meter_id: Optional[int] = None,
    ref_date: Optional[date] = None,
) -> Optional[Dict[str, Any]]:
    """Get the active TOU schedule for a site/meter at a given date."""
    if ref_date is None:
        ref_date = date.today()

    query = db.query(TOUSchedule).filter(
        TOUSchedule.is_active == True,
        TOUSchedule.effective_from <= ref_date,
        or_(TOUSchedule.effective_to.is_(None), TOUSchedule.effective_to >= ref_date),
    )

    # Prefer meter-level, then site-level
    if meter_id:
        meter_sched = query.filter(TOUSchedule.meter_id == meter_id).first()
        if meter_sched:
            return _serialize_schedule(meter_sched)

    site_sched = query.filter(TOUSchedule.site_id == site_id).first()
    if site_sched:
        return _serialize_schedule(site_sched)

    # Return default
    return {
        "id": None,
        "name": "HC/HP Standard (defaut)",
        "site_id": site_id,
        "meter_id": meter_id,
        "effective_from": "2024-01-01",
        "effective_to": None,
        "is_active": True,
        "windows": DEFAULT_WINDOWS,
        "source": "default",
        "source_ref": None,
        "price_hp_eur_kwh": DEFAULT_PRICE_ELEC_EUR_KWH,
        "price_hc_eur_kwh": DEFAULT_PRICE_HC_EUR_KWH,
        "is_default": True,
    }


def create_schedule(
    db: Session,
    site_id: Optional[int],
    meter_id: Optional[int],
    name: str,
    effective_from: date,
    effective_to: Optional[date],
    windows: List[Dict],
    source: str = "manual",
    source_ref: Optional[str] = None,
    price_hp_eur_kwh: Optional[float] = None,
    price_hc_eur_kwh: Optional[float] = None,
) -> Dict[str, Any]:
    """Create a new TOU schedule version. Deactivates overlapping schedules."""
    # Deactivate existing overlapping schedules
    existing_query = db.query(TOUSchedule).filter(TOUSchedule.is_active == True)
    if meter_id:
        existing_query = existing_query.filter(TOUSchedule.meter_id == meter_id)
    elif site_id:
        existing_query = existing_query.filter(
            TOUSchedule.site_id == site_id,
            TOUSchedule.meter_id.is_(None),
        )

    for existing in existing_query.all():
        if effective_to is None or (existing.effective_from <= effective_from):
            existing.effective_to = effective_from - timedelta(days=1)
            if existing.effective_to < existing.effective_from:
                existing.is_active = False

    schedule = TOUSchedule(
        site_id=site_id,
        meter_id=meter_id,
        name=name,
        effective_from=effective_from,
        effective_to=effective_to,
        is_active=True,
        windows_json=json.dumps(windows, ensure_ascii=False),
        source=source,
        source_ref=source_ref,
        price_hp_eur_kwh=price_hp_eur_kwh,
        price_hc_eur_kwh=price_hc_eur_kwh,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _serialize_schedule(schedule)


def update_schedule(
    db: Session,
    schedule_id: int,
    **kwargs,
) -> Optional[Dict[str, Any]]:
    """Update a TOU schedule."""
    sched = db.query(TOUSchedule).filter(TOUSchedule.id == schedule_id).first()
    if not sched:
        return None

    allowed = {"name", "effective_to", "is_active", "source", "source_ref", "price_hp_eur_kwh", "price_hc_eur_kwh"}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            setattr(sched, k, v)

    if "windows" in kwargs and kwargs["windows"] is not None:
        sched.windows_json = json.dumps(kwargs["windows"], ensure_ascii=False)

    db.commit()
    db.refresh(sched)
    return _serialize_schedule(sched)


def delete_schedule(db: Session, schedule_id: int) -> bool:
    """Delete (deactivate) a TOU schedule."""
    sched = db.query(TOUSchedule).filter(TOUSchedule.id == schedule_id).first()
    if not sched:
        return False
    sched.is_active = False
    db.commit()
    return True


def compute_hp_hc_ratio(
    db: Session,
    site_id: int,
    meter_id: Optional[int] = None,
    days: int = 30,
) -> Dict[str, Any]:
    """
    Compute HP/HC consumption ratio using TOU schedule + meter readings.

    Returns:
        {
            "site_id": int,
            "hp_kwh": float,
            "hc_kwh": float,
            "total_kwh": float,
            "hp_ratio": float,  # 0-1
            "hp_cost_eur": float,
            "hc_cost_eur": float,
            "total_cost_eur": float,
            "schedule_name": str,
            "confidence": str,
        }
    """
    active = get_active_schedule(db, site_id, meter_id)
    if not active:
        return _empty_hp_hc(site_id)

    windows = active.get("windows", DEFAULT_WINDOWS)
    price_hp = active.get("price_hp_eur_kwh") or DEFAULT_PRICE_ELEC_EUR_KWH
    price_hc = active.get("price_hc_eur_kwh") or DEFAULT_PRICE_HC_EUR_KWH

    # Fetch readings
    end_date = datetime.now(timezone.utc).replace(tzinfo=None)
    start_date = end_date - timedelta(days=days)

    meters_query = db.query(Meter).filter(
        Meter.site_id == site_id,
        Meter.is_active == True,
        Meter.energy_vector == EnergyVector.ELECTRICITY,
    )
    if meter_id:
        meters_query = meters_query.filter(Meter.id == meter_id)

    meter_ids = [m.id for m in meters_query.all()]
    if not meter_ids:
        return _empty_hp_hc(site_id)

    best = resolve_best_freq(db, meter_ids, start_date, end_date)

    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_date,
            MeterReading.timestamp <= end_date,
            MeterReading.frequency.in_(best),
        )
        .all()
    )

    if not readings:
        return _empty_hp_hc(site_id)

    hp_kwh = 0.0
    hc_kwh = 0.0

    for r in readings:
        period = _classify_period(r.timestamp, windows)
        if period == "HP":
            hp_kwh += r.value_kwh
        else:
            hc_kwh += r.value_kwh

    total_kwh = hp_kwh + hc_kwh
    hp_ratio = hp_kwh / total_kwh if total_kwh > 0 else 0

    confidence = "high" if len(readings) >= days * 20 else ("medium" if len(readings) >= days * 10 else "low")

    return {
        "site_id": site_id,
        "hp_kwh": round(hp_kwh, 1),
        "hc_kwh": round(hc_kwh, 1),
        "total_kwh": round(total_kwh, 1),
        "hp_ratio": round(hp_ratio, 4),
        "hp_cost_eur": round(hp_kwh * price_hp, 2),
        "hc_cost_eur": round(hc_kwh * price_hc, 2),
        "total_cost_eur": round(hp_kwh * price_hp + hc_kwh * price_hc, 2),
        "schedule_name": active.get("name", "?"),
        "confidence": confidence,
    }


def _classify_period(ts: datetime, windows: List[Dict]) -> str:
    """Classify a timestamp as HP or HC based on TOU windows."""
    is_weekend = ts.weekday() >= 5
    day_type = "weekend" if is_weekend else "weekday"
    hour_str = f"{ts.hour:02d}:{ts.minute:02d}"

    for w in windows:
        day_types = w.get("day_types", [])
        if day_type not in day_types:
            continue
        start = w.get("start", "00:00")
        end = w.get("end", "24:00")

        if start <= end:
            if start <= hour_str < end:
                return w.get("period", "HP")
        else:
            # Wraps midnight: e.g., 22:00-06:00
            if hour_str >= start or hour_str < end:
                return w.get("period", "HC")

    return "HC"  # default


def _empty_hp_hc(site_id: int) -> Dict:
    return {
        "site_id": site_id,
        "hp_kwh": 0,
        "hc_kwh": 0,
        "total_kwh": 0,
        "hp_ratio": 0,
        "hp_cost_eur": 0,
        "hc_cost_eur": 0,
        "total_cost_eur": 0,
        "schedule_name": "N/A",
        "confidence": "low",
    }


def compute_hphc_breakdown_v2(
    db: Session,
    site_id: int,
    days: int = 30,
    calendar_id: Optional[int] = None,
    simulate: bool = False,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    HP/HC V2: breakdown + heatmap + opportunity + optional simulation.

    calendar_id: use a TariffCalendar instead of the site's TOUSchedule.
    simulate: if True, also compute with alternate calendar and return comparison.
    """
    from collections import defaultdict

    # Resolve windows
    if calendar_id:
        from models.tariff_calendar import TariffCalendar

        cal = db.query(TariffCalendar).filter(TariffCalendar.id == calendar_id).first()
        if cal:
            windows = json.loads(cal.ruleset_json) if cal.ruleset_json else DEFAULT_WINDOWS
            cal_name = cal.name
            price_hp = DEFAULT_PRICE_ELEC_EUR_KWH
            price_hc = DEFAULT_PRICE_HC_EUR_KWH
            # Try to extract prices from windows
            for w in windows:
                if w.get("period") == "HP" and w.get("price_eur_kwh"):
                    price_hp = w["price_eur_kwh"]
                if w.get("period") == "HC" and w.get("price_eur_kwh"):
                    price_hc = w["price_eur_kwh"]
        else:
            windows = DEFAULT_WINDOWS
            cal_name = "Defaut"
            price_hp, price_hc = DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_HC_EUR_KWH
    else:
        active = get_active_schedule(db, site_id)
        if active:
            windows = active.get("windows", DEFAULT_WINDOWS)
            cal_name = active.get("name", "Defaut")
            price_hp = active.get("price_hp_eur_kwh") or DEFAULT_PRICE_ELEC_EUR_KWH
            price_hc = active.get("price_hc_eur_kwh") or DEFAULT_PRICE_HC_EUR_KWH
        else:
            windows = DEFAULT_WINDOWS
            cal_name = "TURPE standard"
            price_hp, price_hc = DEFAULT_PRICE_ELEC_EUR_KWH, DEFAULT_PRICE_HC_EUR_KWH

    # Fetch readings
    if start_date and end_date:
        start_date = start_date.replace(tzinfo=None) if start_date.tzinfo else start_date
        end_date = end_date.replace(tzinfo=None) if end_date.tzinfo else end_date
    else:
        end_date = datetime.now(timezone.utc).replace(tzinfo=None)
        start_date = end_date - timedelta(days=days)

    meters = (
        db.query(Meter)
        .filter(
            Meter.site_id == site_id,
            Meter.is_active == True,
            Meter.energy_vector == EnergyVector.ELECTRICITY,
        )
        .all()
    )

    if not meters:
        return _empty_hphc_v2(site_id, cal_name)

    meter_ids = [m.id for m in meters]
    best = resolve_best_freq(db, meter_ids, start_date, end_date)

    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_date,
            MeterReading.timestamp <= end_date,
            MeterReading.frequency.in_(best),
        )
        .all()
    )

    if not readings:
        return _empty_hphc_v2(site_id, cal_name)

    # Classify + build heatmap
    hp_kwh = 0.0
    hc_kwh = 0.0
    heatmap_data = defaultdict(lambda: {"sum_kwh": 0.0, "count": 0, "period": "HC"})

    for r in readings:
        period = _classify_period(r.timestamp, windows)
        if period == "HP":
            hp_kwh += r.value_kwh
        else:
            hc_kwh += r.value_kwh

        # Heatmap: day_of_week (0=Mon) x hour
        dow = r.timestamp.weekday()
        hour = r.timestamp.hour
        key = (dow, hour)
        heatmap_data[key]["sum_kwh"] += r.value_kwh
        heatmap_data[key]["count"] += 1
        heatmap_data[key]["period"] = period

    total_kwh = hp_kwh + hc_kwh
    hp_ratio = hp_kwh / total_kwh if total_kwh > 0 else 0

    # Build 7x24 heatmap
    DAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    heatmap = []
    for dow in range(7):
        for hour in range(24):
            cell = heatmap_data.get((dow, hour), {"sum_kwh": 0, "count": 0, "period": "HC"})
            avg = cell["sum_kwh"] / max(cell["count"], 1)
            heatmap.append(
                {
                    "day": dow,
                    "day_label": DAY_LABELS[dow],
                    "hour": hour,
                    "avg_kwh": round(avg, 2),
                    "period": cell["period"],
                }
            )

    # Opportunity: ~15% of HP kWh shiftable
    shiftable_kwh = round(hp_kwh * 0.15, 1)
    savings_eur = round(shiftable_kwh * (price_hp - price_hc), 2)

    confidence = "high" if len(readings) >= days * 20 else ("medium" if len(readings) >= days * 10 else "low")

    result = {
        "site_id": site_id,
        "calendar_name": cal_name,
        "days": days,
        "hp_kwh": round(hp_kwh, 1),
        "hc_kwh": round(hc_kwh, 1),
        "total_kwh": round(total_kwh, 1),
        "hp_ratio": round(hp_ratio, 4),
        "hp_cost_eur": round(hp_kwh * price_hp, 2),
        "hc_cost_eur": round(hc_kwh * price_hc, 2),
        "total_cost_eur": round(hp_kwh * price_hp + hc_kwh * price_hc, 2),
        "heatmap": heatmap,
        "opportunity": {
            "shiftable_kwh": shiftable_kwh,
            "savings_eur": savings_eur,
            "price_hp": price_hp,
            "price_hc": price_hc,
        },
        "confidence": confidence,
        "readings_count": len(readings),
    }

    # Simulation: compare with default schedule if calendar_id was used
    if simulate and calendar_id:
        base = compute_hphc_breakdown_v2(
            db, site_id, days=days, calendar_id=None, simulate=False, start_date=start_date, end_date=end_date
        )
        result["simulation"] = {
            "base_calendar": base.get("calendar_name", "Defaut"),
            "base_cost_eur": base.get("total_cost_eur", 0),
            "alt_cost_eur": result["total_cost_eur"],
            "delta_eur": round(result["total_cost_eur"] - base.get("total_cost_eur", 0), 2),
        }

    return result


def _empty_hphc_v2(site_id, cal_name):
    DAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    return {
        "site_id": site_id,
        "calendar_name": cal_name,
        "days": 0,
        "hp_kwh": 0,
        "hc_kwh": 0,
        "total_kwh": 0,
        "hp_ratio": 0,
        "hp_cost_eur": 0,
        "hc_cost_eur": 0,
        "total_cost_eur": 0,
        "heatmap": [
            {"day": d, "day_label": DAY_LABELS[d], "hour": h, "avg_kwh": 0, "period": "HC"}
            for d in range(7)
            for h in range(24)
        ],
        "opportunity": {
            "shiftable_kwh": 0,
            "savings_eur": 0,
            "price_hp": DEFAULT_PRICE_ELEC_EUR_KWH,
            "price_hc": DEFAULT_PRICE_HC_EUR_KWH,
        },
        "confidence": "low",
        "readings_count": 0,
    }


def _serialize_schedule(s: TOUSchedule) -> Dict[str, Any]:
    try:
        windows = json.loads(s.windows_json) if s.windows_json else []
    except (json.JSONDecodeError, TypeError):
        windows = []

    return {
        "id": s.id,
        "site_id": s.site_id,
        "meter_id": s.meter_id,
        "name": s.name,
        "effective_from": s.effective_from.isoformat() if s.effective_from else None,
        "effective_to": s.effective_to.isoformat() if s.effective_to else None,
        "is_active": s.is_active,
        "windows": windows,
        "source": s.source,
        "source_ref": s.source_ref,
        "price_hp_eur_kwh": s.price_hp_eur_kwh,
        "price_hc_eur_kwh": s.price_hc_eur_kwh,
        "is_default": False,
    }
