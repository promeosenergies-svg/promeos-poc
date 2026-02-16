"""
PROMEOS - Targets Service (Objectifs & Budgets)
CRUD + progression tracking + forecast for consumption targets.
"""
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.consumption_target import ConsumptionTarget
from models import Meter, MeterReading, Site
from models.energy_models import EnergyVector


def get_targets(
    db: Session,
    site_id: int,
    energy_type: str = "electricity",
    year: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List consumption targets for a site, optionally filtered by year."""
    query = db.query(ConsumptionTarget).filter(
        ConsumptionTarget.site_id == site_id,
        ConsumptionTarget.energy_type == energy_type,
    )
    if year:
        query = query.filter(ConsumptionTarget.year == year)
    query = query.order_by(ConsumptionTarget.year, ConsumptionTarget.month)

    return [_serialize_target(t) for t in query.all()]


def create_target(
    db: Session,
    site_id: int,
    energy_type: str,
    period: str,
    year: int,
    month: Optional[int],
    target_kwh: Optional[float] = None,
    target_eur: Optional[float] = None,
    target_co2e_kg: Optional[float] = None,
    source: str = "manual",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a consumption target."""
    # Check for duplicate
    existing = db.query(ConsumptionTarget).filter(
        ConsumptionTarget.site_id == site_id,
        ConsumptionTarget.energy_type == energy_type,
        ConsumptionTarget.year == year,
        ConsumptionTarget.month == month if month else ConsumptionTarget.month.is_(None),
    ).first()

    if existing:
        # Update existing
        if target_kwh is not None:
            existing.target_kwh = target_kwh
        if target_eur is not None:
            existing.target_eur = target_eur
        if target_co2e_kg is not None:
            existing.target_co2e_kg = target_co2e_kg
        existing.source = source
        if notes:
            existing.notes = notes
        db.commit()
        db.refresh(existing)
        return _serialize_target(existing)

    target = ConsumptionTarget(
        site_id=site_id,
        energy_type=energy_type,
        period=period,
        year=year,
        month=month,
        target_kwh=target_kwh,
        target_eur=target_eur,
        target_co2e_kg=target_co2e_kg,
        source=source,
        notes=notes,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return _serialize_target(target)


def update_target(
    db: Session,
    target_id: int,
    **kwargs,
) -> Optional[Dict[str, Any]]:
    """Update a consumption target (target or actual values)."""
    target = db.query(ConsumptionTarget).filter(ConsumptionTarget.id == target_id).first()
    if not target:
        return None

    allowed = {"target_kwh", "target_eur", "target_co2e_kg", "actual_kwh", "actual_eur", "actual_co2e_kg", "notes", "source"}
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            setattr(target, k, v)

    db.commit()
    db.refresh(target)
    return _serialize_target(target)


def delete_target(db: Session, target_id: int) -> bool:
    """Delete a consumption target."""
    target = db.query(ConsumptionTarget).filter(ConsumptionTarget.id == target_id).first()
    if not target:
        return False
    db.delete(target)
    db.commit()
    return True


def get_progression(
    db: Session,
    site_id: int,
    energy_type: str = "electricity",
    year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compute target progression: actual vs target with forecast.

    Returns:
        {
            "site_id": int,
            "energy_type": str,
            "year": int,
            "yearly_target_kwh": float,
            "ytd_actual_kwh": float,
            "ytd_target_kwh": float,
            "progress_pct": float,
            "forecast_year_kwh": float,
            "forecast_vs_target_pct": float,
            "months": [...],
            "alert": str or None,  # "on_track", "at_risk", "over_budget"
        }
    """
    if year is None:
        year = datetime.utcnow().year

    current_month = datetime.utcnow().month

    # Get all monthly targets for the year
    targets = (
        db.query(ConsumptionTarget)
        .filter(
            ConsumptionTarget.site_id == site_id,
            ConsumptionTarget.energy_type == energy_type,
            ConsumptionTarget.year == year,
            ConsumptionTarget.period == "monthly",
        )
        .order_by(ConsumptionTarget.month)
        .all()
    )

    # Get yearly target
    yearly = (
        db.query(ConsumptionTarget)
        .filter(
            ConsumptionTarget.site_id == site_id,
            ConsumptionTarget.energy_type == energy_type,
            ConsumptionTarget.year == year,
            ConsumptionTarget.period == "yearly",
        )
        .first()
    )

    yearly_target_kwh = yearly.target_kwh if yearly and yearly.target_kwh else 0
    if not yearly_target_kwh and targets:
        yearly_target_kwh = sum(t.target_kwh or 0 for t in targets)

    # Build month-by-month
    months = []
    ytd_actual = 0
    ytd_target = 0

    target_by_month = {t.month: t for t in targets}

    for m in range(1, 13):
        t = target_by_month.get(m)
        t_kwh = t.target_kwh if t and t.target_kwh else (yearly_target_kwh / 12 if yearly_target_kwh else 0)
        a_kwh = t.actual_kwh if t and t.actual_kwh else None

        if m <= current_month:
            ytd_target += t_kwh
            if a_kwh is not None:
                ytd_actual += a_kwh

        months.append({
            "month": m,
            "target_kwh": round(t_kwh, 1),
            "actual_kwh": round(a_kwh, 1) if a_kwh is not None else None,
            "delta_pct": round((a_kwh - t_kwh) / max(t_kwh, 1) * 100, 1) if a_kwh is not None and t_kwh else None,
        })

    # Forecast: linear extrapolation of YTD actual
    if current_month > 0 and ytd_actual > 0:
        forecast_year_kwh = round(ytd_actual / current_month * 12, 1)
    else:
        forecast_year_kwh = 0

    forecast_vs_target_pct = round(
        (forecast_year_kwh - yearly_target_kwh) / max(yearly_target_kwh, 1) * 100, 1
    ) if yearly_target_kwh else 0

    progress_pct = round(ytd_actual / max(ytd_target, 1) * 100, 1) if ytd_target else 0

    # Alert level
    if forecast_vs_target_pct <= 0:
        alert = "on_track"
    elif forecast_vs_target_pct <= 10:
        alert = "at_risk"
    else:
        alert = "over_budget"

    return {
        "site_id": site_id,
        "energy_type": energy_type,
        "year": year,
        "yearly_target_kwh": round(yearly_target_kwh, 1),
        "ytd_actual_kwh": round(ytd_actual, 1),
        "ytd_target_kwh": round(ytd_target, 1),
        "progress_pct": progress_pct,
        "forecast_year_kwh": forecast_year_kwh,
        "forecast_vs_target_pct": forecast_vs_target_pct,
        "months": months,
        "alert": alert,
    }


def _serialize_target(t: ConsumptionTarget) -> Dict[str, Any]:
    return {
        "id": t.id,
        "site_id": t.site_id,
        "energy_type": t.energy_type,
        "period": t.period,
        "year": t.year,
        "month": t.month,
        "target_kwh": t.target_kwh,
        "target_eur": t.target_eur,
        "target_co2e_kg": t.target_co2e_kg,
        "actual_kwh": t.actual_kwh,
        "actual_eur": t.actual_eur,
        "actual_co2e_kg": t.actual_co2e_kg,
        "source": t.source,
        "notes": t.notes,
    }
