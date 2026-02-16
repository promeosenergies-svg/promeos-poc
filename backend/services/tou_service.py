"""
PROMEOS - TOU Service (HP/HC Schedule Management)
CRUD + versioned TOU schedules + HP/HC ratio calculation.
"""
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.tou_schedule import TOUSchedule
from models import Meter, MeterReading, Site
from models.energy_models import EnergyVector


# Default TURPE-like schedule (HP 6h-22h weekday, HC rest)
DEFAULT_WINDOWS = [
    {"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP", "price_eur_kwh": 0.18},
    {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC", "price_eur_kwh": 0.13},
    {"day_types": ["weekend", "holiday"], "start": "00:00", "end": "24:00", "period": "HC", "price_eur_kwh": 0.13},
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
        "price_hp_eur_kwh": 0.18,
        "price_hc_eur_kwh": 0.13,
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
    price_hp = active.get("price_hp_eur_kwh") or 0.18
    price_hc = active.get("price_hc_eur_kwh") or 0.13

    # Fetch readings
    end_date = datetime.utcnow()
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

    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_date,
            MeterReading.timestamp <= end_date,
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
        "hp_kwh": 0, "hc_kwh": 0, "total_kwh": 0,
        "hp_ratio": 0, "hp_cost_eur": 0, "hc_cost_eur": 0, "total_cost_eur": 0,
        "schedule_name": "N/A", "confidence": "low",
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
