"""
PROMEOS — Gas Weather Service (DJU model + alerts)
Weather-normalized gas consumption analysis.
Uses mock DJU (deterministic seasonal formula) for POC scope.
"""
import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session

from models import Meter, MeterReading, Site
from models.energy_models import EnergyVector


def _mock_dju(doy: int) -> float:
    """Generate mock DJU (Degree-Day Unit) from day of year.
    T_avg = 12 + 10*sin(2*pi*(doy-80)/365) + noise
    DJU = max(0, 18 - T_avg)
    """
    t_avg = 12 + 10 * math.sin(2 * math.pi * (doy - 80) / 365)
    # Deterministic noise based on doy (reproducible)
    noise = math.sin(doy * 17.3) * 2
    t_avg += noise
    return round(max(0, 18 - t_avg), 2)


def _linear_regression(x_vals, y_vals):
    """Simple linear regression: y = a*x + b. Returns (a, b, r_squared)."""
    n = len(x_vals)
    if n < 3:
        return 0, 0, 0

    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(xi * yi for xi, yi in zip(x_vals, y_vals))
    sum_x2 = sum(xi ** 2 for xi in x_vals)
    sum_y2 = sum(yi ** 2 for yi in y_vals)

    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-10:
        return 0, sum_y / n, 0

    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n

    # R²
    ss_res = sum((yi - (a * xi + b)) ** 2 for xi, yi in zip(x_vals, y_vals))
    y_mean = sum_y / n
    ss_tot = sum((yi - y_mean) ** 2 for yi in y_vals)
    r2 = 1 - ss_res / max(ss_tot, 1e-10)

    return round(a, 4), round(b, 2), round(max(0, r2), 4)


def compute_weather_normalized(
    db: Session,
    site_id: int,
    days: int = 90,
) -> Dict[str, Any]:
    """
    Gas weather normalization using DJU model.

    Returns:
        model: { slope, intercept, r_squared, base_kwh_day, heating_sensitivity }
        dju_data: [{ date, dju, kwh, normalized_kwh }]
        decomposition: { base_pct, heating_pct }
        alerts: [{ type, severity, message }]
        confidence: str
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    meters = db.query(Meter).filter(
        Meter.site_id == site_id,
        Meter.is_active == True,
        Meter.energy_vector == EnergyVector.GAS,
    ).all()

    if not meters:
        return _empty_gas_weather(site_id, days, reason="no_gas_meters")

    meter_ids = [m.id for m in meters]
    readings = (
        db.query(MeterReading)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= start_date,
            MeterReading.timestamp <= end_date,
        )
        .order_by(MeterReading.timestamp)
        .all()
    )

    if len(readings) < 48:
        return _empty_gas_weather(site_id, days, reason="insufficient_data",
                                  readings_count=len(readings))

    # Aggregate by day
    daily = defaultdict(float)
    for r in readings:
        day_key = r.timestamp.strftime("%Y-%m-%d")
        daily[day_key] += r.value_kwh

    if len(daily) < 7:
        return _empty_gas_weather(site_id, days, reason="insufficient_data",
                                  readings_count=len(readings))

    # Build DJU data
    dju_data = []
    x_vals = []
    y_vals = []

    for date_str, kwh in sorted(daily.items()):
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        doy = dt.timetuple().tm_yday
        dju = _mock_dju(doy)
        dju_data.append({"date": date_str, "dju": dju, "kwh": round(kwh, 1)})
        x_vals.append(dju)
        y_vals.append(kwh)

    # Linear regression: kwh = slope * dju + intercept
    slope, intercept, r2 = _linear_regression(x_vals, y_vals)
    base_kwh_day = max(0, intercept)
    heating_sensitivity = max(0, slope)

    # Normalized values
    for d in dju_data:
        expected = slope * d["dju"] + intercept
        d["normalized_kwh"] = round(expected, 1)

    # Decomposition
    total_kwh = sum(y_vals)
    base_total = base_kwh_day * len(daily)
    heating_total = max(0, total_kwh - base_total)
    base_pct = round(base_total / max(total_kwh, 1) * 100, 1)
    heating_pct = round(100 - base_pct, 1)

    # Alerts
    alerts = []

    # Alert: probable leak (summer base > expected * 1.5)
    summer_days = [d for d in dju_data if d["date"][5:7] in ("06", "07", "08", "09")]
    if summer_days:
        summer_avg = sum(d["kwh"] for d in summer_days) / len(summer_days)
        if summer_avg > base_kwh_day * 1.5 and base_kwh_day > 0:
            alerts.append({
                "type": "probable_leak",
                "severity": "high",
                "message": f"Consommation estivale anormalement elevee ({round(summer_avg, 1)} kWh/j vs base {round(base_kwh_day, 1)} kWh/j)",
            })

    # Alert: early heating (heating in months 5-9)
    warm_months = [d for d in dju_data if d["date"][5:7] in ("05", "06", "07", "08", "09") and d["dju"] > 2]
    if warm_months:
        alerts.append({
            "type": "early_heating",
            "severity": "medium",
            "message": f"Chauffage detecte en saison chaude ({len(warm_months)} jours avec DJU > 2)",
        })

    # Alert: base drift (last 30d base vs overall base > 10%)
    recent_days = sorted(dju_data, key=lambda d: d["date"])[-30:]
    if len(recent_days) >= 10:
        low_dju_recent = [d for d in recent_days if d["dju"] < 1]
        if low_dju_recent:
            recent_base = sum(d["kwh"] for d in low_dju_recent) / len(low_dju_recent)
            if base_kwh_day > 0 and (recent_base - base_kwh_day) / base_kwh_day > 0.10:
                alerts.append({
                    "type": "base_drift",
                    "severity": "medium",
                    "message": f"Derive du talon de base detectee (+{round((recent_base - base_kwh_day) / base_kwh_day * 100, 0)}% sur 30j)",
                })

    confidence = "high" if r2 > 0.7 and len(daily) > 60 else ("medium" if r2 > 0.4 else "low")

    return {
        "site_id": site_id,
        "days": days,
        "readings_count": len(readings),
        "model": {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r2,
            "base_kwh_day": round(base_kwh_day, 1),
            "heating_sensitivity": round(heating_sensitivity, 2),
        },
        "dju_data": dju_data,
        "decomposition": {
            "base_pct": base_pct,
            "heating_pct": heating_pct,
            "base_total_kwh": round(base_total, 1),
            "heating_total_kwh": round(heating_total, 1),
        },
        "alerts": alerts,
        "confidence": confidence,
    }


def _empty_gas_weather(site_id, days, reason="no_gas_meters", readings_count=0):
    return {
        "site_id": site_id, "days": days, "readings_count": readings_count,
        "model": {"slope": 0, "intercept": 0, "r_squared": 0, "base_kwh_day": 0, "heating_sensitivity": 0},
        "dju_data": [], "decomposition": {"base_pct": 0, "heating_pct": 0, "base_total_kwh": 0, "heating_total_kwh": 0},
        "alerts": [], "confidence": "low", "reason": reason,
    }
