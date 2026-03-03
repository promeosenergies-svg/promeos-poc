"""
PROMEOS - Service Diagnostic Consommation V1.1
Detecte les defauts d'usage:
- hors_horaires: consommation en dehors des heures d'occupation (schedule-aware)
- base_load: talon de consommation anormalement eleve (robust: Q10 vs median heures ouvertes)
- pointe: jours avec consommation anormalement haute (robust: median + 3*MAD)
- derive: tendance a la hausse sur 30j (linear regression + fallback first/last week)
- data_gap: trous dans les donnees

V1.1 changes:
- Schedule-aware hors_horaires (SiteOperatingSchedule)
- Site-specific price ref (SiteTariffProfile) for loss EUR
- Robust statistics (median+MAD for pointe, linreg for derive)
- Recommended actions per insight
"""
import json
import math
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Site, Meter, MeterReading, ConsumptionInsight,
    Organisation, Portefeuille, EntiteJuridique,
)
from models.energy_models import FrequencyType

# Fallback price — used when no SiteTariffProfile exists
DEFAULT_PRICE_REF_KWH = 0.18


# ========================================
# Helpers
# ========================================

def _median(values: List[float]) -> float:
    """Calculate median of a sorted or unsorted list."""
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def _mad(values: List[float]) -> float:
    """Median Absolute Deviation."""
    med = _median(values)
    return _median([abs(v - med) for v in values])


def _linear_slope(values: List[float]) -> float:
    """Simple linear regression slope (y = a*x + b, returns a).
    x = 0..n-1, y = values.
    """
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den != 0 else 0.0


def _get_price_ref(db: Session, site_id: int) -> float:
    """Get site-specific price ref or fallback."""
    from routes.site_config import get_site_price_ref
    return get_site_price_ref(db, site_id)


def _get_schedule_params(db: Session, site_id: int) -> dict:
    """Get site-specific schedule or defaults."""
    from routes.site_config import get_site_schedule_params
    return get_site_schedule_params(db, site_id)


# ========================================
# Recommended actions templates
# ========================================

def _actions_hors_horaires(metrics: dict, price_ref: float) -> list:
    """Generate recommended actions for off-hours consumption."""
    loss_kwh = metrics.get("off_hours_kwh", 0) * 0.5 * 12
    actions = [
        {
            "title": "Programmer l'arret CVC hors horaires",
            "rationale": f"Consommation hors horaires = {metrics.get('off_hours_pct', 0):.0f}% du total. L'arret programme de la CVC la nuit/weekend reduirait la facture.",
            "expected_gain_kwh": round(loss_kwh * 0.6, 0),
            "expected_gain_eur": round(loss_kwh * 0.6 * price_ref, 0),
            "effort": "2j",
            "priority": "high",
        },
        {
            "title": "Installer une horloge / GTC pour pilotage horaire",
            "rationale": "Un systeme de gestion technique permet d'automatiser les coupures hors occupation.",
            "expected_gain_kwh": round(loss_kwh * 0.8, 0),
            "expected_gain_eur": round(loss_kwh * 0.8 * price_ref, 0),
            "effort": "5j",
            "priority": "medium",
        },
    ]
    return actions


def _actions_base_load(metrics: dict, price_ref: float) -> list:
    """Generate recommended actions for elevated base load."""
    excess_kw = max(0, metrics.get("base_load_kw", 0) - metrics.get("median_kw", 0) * 0.3)
    annual_excess = excess_kw * 8760 * 0.3
    actions = [
        {
            "title": "Audit du talon: identifier les equipements en fonctionnement permanent",
            "rationale": f"Talon a {metrics.get('base_ratio_pct', 0):.0f}% de la mediane. Verifier eclairage, serveurs, chauffage eau, VMC.",
            "expected_gain_kwh": round(annual_excess * 0.4, 0),
            "expected_gain_eur": round(annual_excess * 0.4 * price_ref, 0),
            "effort": "1j",
            "priority": "high",
        },
        {
            "title": "Couper les veilles et equipements non essentiels la nuit",
            "rationale": "Les equipements en veille representent souvent 10-15% du talon.",
            "expected_gain_kwh": round(annual_excess * 0.15, 0),
            "expected_gain_eur": round(annual_excess * 0.15 * price_ref, 0),
            "effort": "0.5j",
            "priority": "medium",
        },
    ]
    return actions


def _actions_pointe(metrics: dict, price_ref: float) -> list:
    """Generate recommended actions for peak anomalies."""
    excess_kwh = (metrics.get("max_daily_kwh", 0) - metrics.get("mean_daily_kwh", 0)) * 12
    actions = [
        {
            "title": "Analyser les jours de pointe pour identifier la cause",
            "rationale": f"{metrics.get('anomaly_days_count', 0)} jours anormaux detectes (pic {metrics.get('max_daily_kwh', 0):.0f} kWh). Verifier evenements, meteo, occupation.",
            "expected_gain_kwh": round(excess_kwh * 0.3, 0),
            "expected_gain_eur": round(excess_kwh * 0.3 * price_ref, 0),
            "effort": "1j",
            "priority": "medium",
        },
    ]
    return actions


def _actions_derive(metrics: dict, price_ref: float) -> list:
    """Generate recommended actions for upward drift."""
    drift_pct = metrics.get("drift_pct", 0)
    avg_last = metrics.get("avg_last_week_kw", 0)
    actions = [
        {
            "title": "Verifier les reglages CVC et la maintenance",
            "rationale": f"Derive de +{drift_pct:.1f}% detectee. Possible encrassement, fuite, ou dereglement.",
            "expected_gain_kwh": round(avg_last * 168 * drift_pct / 100 * 12, 0),
            "expected_gain_eur": round(avg_last * 168 * drift_pct / 100 * 12 * price_ref, 0),
            "effort": "2j",
            "priority": "high",
        },
        {
            "title": "Planifier une maintenance preventive",
            "rationale": "Un entretien regulier previent les derives de consommation.",
            "expected_gain_kwh": 0,
            "expected_gain_eur": 0,
            "effort": "3j",
            "priority": "low",
        },
    ]
    return actions


def _actions_data_gap(metrics: dict, price_ref: float) -> list:
    """Generate recommended actions for data gaps."""
    actions = [
        {
            "title": "Verifier la connexion du compteur communicant",
            "rationale": f"Couverture {metrics.get('coverage_pct', 0):.0f}% — {metrics.get('gaps_count', 0)} trou(s). Possible defaut telereleve.",
            "expected_gain_kwh": 0,
            "expected_gain_eur": 0,
            "effort": "0.5j",
            "priority": "medium",
        },
    ]
    return actions


ACTIONS_GENERATORS = {
    "hors_horaires": _actions_hors_horaires,
    "base_load": _actions_base_load,
    "pointe": _actions_pointe,
    "derive": _actions_derive,
    "data_gap": _actions_data_gap,
}


# ========================================
# Demo conso seed
# ========================================

def generate_demo_consumption(
    db: Session, site_id: int, days: int = 30, anomaly: bool = True
) -> dict:
    """Generate synthetic hourly consumption data for a site.

    Creates a Meter + MeterReadings with patterns:
    - Bureau: high 8h-19h weekdays, low nights/weekends
    - With optional anomaly: elevated night consumption on random days

    Returns: {meter_id, readings_count, period}
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {"error": "Site not found"}

    # Check if meter already exists
    existing = db.query(Meter).filter(Meter.site_id == site_id).first()
    if existing:
        meter = existing
    else:
        meter = Meter(
            meter_id=f"PRM-DEMO-{site_id:04d}",
            name=f"Compteur principal - {site.nom}",
            site_id=site_id,
            subscribed_power_kva=100.0,
            is_active=True,
        )
        db.add(meter)
        db.flush()

    # Delete existing readings for this meter
    db.query(MeterReading).filter(MeterReading.meter_id == meter.id).delete()

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)

    surface = site.surface_m2 or 1000
    # Base power proportional to surface (W/m2)
    base_power_kw = surface * 0.015  # ~15 W/m2 base (talon)
    peak_power_kw = surface * 0.060  # ~60 W/m2 peak

    # Anomaly days: random 3-5 days with elevated night consumption
    anomaly_days = set()
    if anomaly:
        nb_anomaly = random.randint(3, 5)
        all_days = list(range(days))
        anomaly_days = set(random.sample(all_days, min(nb_anomaly, len(all_days))))

    readings = []
    ts = start
    while ts < now:
        hour = ts.hour
        weekday = ts.weekday()  # 0=Mon, 6=Sun
        day_idx = (ts - start).days
        is_weekend = weekday >= 5

        # Base load (talon)
        power = base_power_kw

        # Business hours pattern (8-19 weekdays)
        if not is_weekend and 8 <= hour < 19:
            # Ramp up/down
            if hour < 10:
                factor = 0.5 + 0.5 * (hour - 8) / 2
            elif hour > 17:
                factor = 0.5 + 0.5 * (19 - hour) / 2
            else:
                factor = 1.0
            power = base_power_kw + (peak_power_kw - base_power_kw) * factor

        # Weekend: 20% of peak
        if is_weekend:
            power = base_power_kw * 1.2

        # Anomaly: elevated night consumption (HVAC left on)
        if day_idx in anomaly_days and (hour < 7 or hour >= 20):
            power = peak_power_kw * 0.6  # 60% of peak at night

        # Derive: slight upward trend (+0.5% per week)
        week_idx = day_idx / 7
        drift_factor = 1.0 + 0.005 * week_idx

        # Add noise (5%)
        noise = random.gauss(0, 0.05)
        kwh = max(0, power * (1 + noise) * drift_factor)

        readings.append(MeterReading(
            meter_id=meter.id,
            timestamp=ts,
            frequency=FrequencyType.HOURLY,
            value_kwh=round(kwh, 2),
            quality_score=0.95,
        ))

        ts += timedelta(hours=1)

    db.bulk_save_objects(readings)
    db.commit()

    return {
        "meter_id": meter.id,
        "meter_name": meter.name,
        "readings_count": len(readings),
        "period_start": start.isoformat(),
        "period_end": now.isoformat(),
        "anomaly_days": len(anomaly_days),
    }


def generate_demo_gas_consumption(
    db: Session, site_id: int, days: int = 90, anomaly: bool = True
) -> dict:
    """Generate synthetic daily gas consumption data for a site.

    Creates a gas Meter + MeterReadings with seasonal heating pattern:
    - Winter (Nov–Mar): high gas consumption (×1.8)
    - Summer (Jun–Aug): low gas consumption (~20% of base)
    - Base: 300 kWh/day (proportional to surface), ±15% noise

    Returns: {meter_id, readings_count, period_start, period_end, anomaly_days}
    """
    from models.energy_models import EnergyVector, FrequencyType

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        return {"error": "Site not found"}

    # Gas meter (per site, separate from electricity)
    existing = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.energy_vector == EnergyVector.GAS)
        .first()
    )
    if existing:
        meter = existing
    else:
        meter = Meter(
            meter_id=f"GAZ-DEMO-{site_id:04d}",
            name=f"Compteur Gaz - {site.nom}",
            site_id=site_id,
            energy_vector=EnergyVector.GAS,
            subscribed_power_kva=None,
            is_active=True,
        )
        db.add(meter)
        db.flush()

    # Delete existing gas readings for this meter
    db.query(MeterReading).filter(MeterReading.meter_id == meter.id).delete()

    now = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days)

    surface = site.surface_m2 or 1000
    # Base gas consumption proportional to surface (kWh/day)
    base_kwh_day = surface * 0.30  # ~300 kWh/day for 1000 m2

    # Anomaly days: unexpected high gas consumption
    anomaly_days = set()
    if anomaly:
        nb_anomaly = random.randint(2, 4)
        all_days = list(range(days))
        anomaly_days = set(random.sample(all_days, min(nb_anomaly, len(all_days))))

    readings = []
    for day_idx in range(days):
        ts = start + timedelta(days=day_idx)
        month = ts.month

        # Seasonal heating factor (sine-wave approximation)
        # Peak in Jan (month=1), trough in Jul (month=7)
        seasonal = 1.0 + 0.8 * math.cos(2 * math.pi * (month - 1) / 12)
        # Clamp: summer min = 0.2 × base, winter max = 1.8 × base
        seasonal = max(0.2, min(1.8, seasonal))

        # Anomaly: unexpected spike (equipment fault or heating override)
        anomaly_factor = 2.0 if day_idx in anomaly_days else 1.0

        noise = random.gauss(0, 0.07)  # ±7% noise
        kwh = max(0, base_kwh_day * seasonal * anomaly_factor * (1 + noise))

        readings.append(MeterReading(
            meter_id=meter.id,
            timestamp=ts,
            frequency=FrequencyType.DAILY,
            value_kwh=round(kwh, 1),
            quality_score=0.92,
        ))

    db.bulk_save_objects(readings)
    db.commit()

    return {
        "meter_id": meter.id,
        "meter_name": meter.name,
        "readings_count": len(readings),
        "period_start": start.isoformat(),
        "period_end": now.isoformat(),
        "anomaly_days": len(anomaly_days),
    }


# ========================================
# Diagnostic calculations (V1.1 — robust)
# ========================================

def _get_readings(db: Session, meter_id: int, days: int = 30) -> List[MeterReading]:
    """Get last N days of hourly readings for a meter."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    return (
        db.query(MeterReading)
        .filter(MeterReading.meter_id == meter_id, MeterReading.timestamp >= cutoff)
        .order_by(MeterReading.timestamp)
        .all()
    )


def _detect_hors_horaires(
    readings: List[MeterReading],
    schedule: dict = None,
) -> Optional[dict]:
    """Detect significant consumption outside business hours.

    V1.1: uses SiteOperatingSchedule (open_time, close_time, open_days, is_24_7, exceptions).
    """
    if len(readings) < 48:
        return None

    if schedule is None:
        schedule = {"open_time": 8, "close_time": 19, "open_days": {0, 1, 2, 3, 4}, "is_24_7": False, "exceptions": []}

    # If 24/7 site, no off-hours detection
    if schedule.get("is_24_7", False):
        return None

    biz_start = schedule["open_time"]
    biz_end = schedule["close_time"]
    open_days = schedule["open_days"]
    exceptions = set(schedule.get("exceptions", []))

    biz_kwh = 0
    off_kwh = 0
    off_readings = []

    for r in readings:
        hour = r.timestamp.hour
        weekday = r.timestamp.weekday()
        date_str = r.timestamp.strftime("%Y-%m-%d")

        # Exception days (holidays) count as off-hours
        if date_str in exceptions:
            off_kwh += r.value_kwh
            off_readings.append(r.value_kwh)
            continue

        is_biz = (weekday in open_days and biz_start <= hour < biz_end)
        if is_biz:
            biz_kwh += r.value_kwh
        else:
            off_kwh += r.value_kwh
            off_readings.append(r.value_kwh)

    total = biz_kwh + off_kwh
    if total == 0:
        return None

    off_pct = off_kwh / total * 100

    if off_pct < 35:
        return None

    avg_off = sum(off_readings) / len(off_readings) if off_readings else 0
    severity = "critical" if off_pct > 60 else "high" if off_pct > 45 else "medium"

    return {
        "type": "hors_horaires",
        "severity": severity,
        "message": f"{off_pct:.0f}% de la consommation hors horaires d'occupation ({biz_start}h-{biz_end}h) — potentiel de reduction significatif",
        "metrics": {
            "off_hours_pct": round(off_pct, 1),
            "off_hours_kwh": round(off_kwh, 1),
            "business_hours_kwh": round(biz_kwh, 1),
            "avg_off_hour_kw": round(avg_off, 2),
            "schedule_open": f"{biz_start}h-{biz_end}h",
            "schedule_source": "site" if schedule.get("_from_db") else "default",
        },
        "estimated_loss_kwh": round(off_kwh * 0.5 * 12, 0),
    }


def _detect_base_load(
    readings: List[MeterReading],
    schedule: dict = None,
) -> Optional[dict]:
    """Detect elevated base load (talon).

    V1.1: Q10 compared to median of business-hours readings only.
    """
    if len(readings) < 48:
        return None

    if schedule is None:
        schedule = {"open_time": 8, "close_time": 19, "open_days": {0, 1, 2, 3, 4}, "is_24_7": False}

    biz_start = schedule["open_time"]
    biz_end = schedule["close_time"]
    open_days = schedule["open_days"]

    # Separate business vs all readings
    all_values = sorted([r.value_kwh for r in readings])
    biz_values = []
    for r in readings:
        if r.timestamp.weekday() in open_days and biz_start <= r.timestamp.hour < biz_end:
            biz_values.append(r.value_kwh)

    q10_idx = max(0, int(len(all_values) * 0.10))
    q10 = all_values[q10_idx]

    # Use median of business hours (not global median)
    q50_biz = _median(biz_values) if biz_values else _median(all_values)

    if q50_biz == 0:
        return None

    base_ratio = q10 / q50_biz * 100

    if base_ratio < 40:
        return None

    severity = "high" if base_ratio > 60 else "medium"
    annual_excess_kwh = (q10 - q50_biz * 0.3) * len(readings) * (365 / 30)

    return {
        "type": "base_load",
        "severity": severity,
        "message": f"Talon de consommation eleve: {q10:.1f} kW (={base_ratio:.0f}% de la mediane heures ouvertes) — verifier les equipements en fonctionnement permanent",
        "metrics": {
            "base_load_kw": round(q10, 2),
            "median_kw": round(q50_biz, 2),
            "base_ratio_pct": round(base_ratio, 1),
        },
        "estimated_loss_kwh": round(max(0, annual_excess_kwh), 0),
    }


def _detect_pointe(readings: List[MeterReading]) -> Optional[dict]:
    """Detect abnormal peak days.

    V1.1: uses median + 3*MAD instead of mean + 2*std (more robust to outliers).
    """
    if len(readings) < 168:
        return None

    daily = {}
    for r in readings:
        day = r.timestamp.date()
        daily[day] = daily.get(day, 0) + r.value_kwh

    if len(daily) < 7:
        return None

    values = list(daily.values())
    med = _median(values)
    mad_val = _mad(values)

    if mad_val == 0:
        return None

    # 3*MAD threshold (1.4826 * MAD approximates stddev for normal distribution)
    threshold = med + 3 * 1.4826 * mad_val
    anomaly_days = [d for d, v in daily.items() if v > threshold]

    if len(anomaly_days) < 2:
        return None

    max_day = max(daily, key=daily.get)
    max_val = daily[max_day]
    excess_kwh = sum(daily[d] - med for d in anomaly_days)
    severity = "high" if len(anomaly_days) > 5 else "medium"

    return {
        "type": "pointe",
        "severity": severity,
        "message": f"{len(anomaly_days)} jour(s) avec consommation anormale (>{threshold:.0f} kWh/j vs mediane {med:.0f}) — pic le {max_day}: {max_val:.0f} kWh",
        "metrics": {
            "anomaly_days_count": len(anomaly_days),
            "median_daily_kwh": round(med, 1),
            "threshold_kwh": round(threshold, 1),
            "max_daily_kwh": round(max_val, 1),
            "max_day": max_day.isoformat(),
            "mad": round(mad_val, 1),
        },
        "estimated_loss_kwh": round(excess_kwh * 12, 0),
    }


def _detect_derive(readings: List[MeterReading]) -> Optional[dict]:
    """Detect upward trend (derive) over 30 days.

    V1.1: uses linear regression on daily averages.
    Fallback: first week vs last week comparison if < 14 days.
    """
    if len(readings) < 336:  # Need at least 14 days
        return None

    # Aggregate daily averages
    daily_avg = {}
    daily_count = {}
    for r in readings:
        day = r.timestamp.date()
        daily_avg[day] = daily_avg.get(day, 0) + r.value_kwh
        daily_count[day] = daily_count.get(day, 0) + 1

    days_sorted = sorted(daily_avg.keys())
    daily_means = [daily_avg[d] / daily_count[d] for d in days_sorted]

    if len(daily_means) < 14:
        return None

    # Linear regression on daily means
    slope = _linear_slope(daily_means)
    mean_val = sum(daily_means) / len(daily_means)

    if mean_val == 0:
        return None

    # slope is kW/day, convert to % over the period
    total_change = slope * len(daily_means)
    drift_pct = total_change / mean_val * 100

    # Fallback: first week vs last week (for validation)
    week_hours = 168
    first_week = readings[:week_hours]
    last_week = readings[-week_hours:]
    avg_first = sum(r.value_kwh for r in first_week) / len(first_week)
    avg_last = sum(r.value_kwh for r in last_week) / len(last_week)
    fallback_drift = (avg_last - avg_first) / avg_first * 100 if avg_first > 0 else 0

    # Use linreg drift if available, validate with fallback
    # If signs disagree, reduce confidence (use smaller absolute)
    if drift_pct > 0 and fallback_drift > 0:
        final_drift = min(drift_pct, fallback_drift * 1.5)
    elif drift_pct > 0:
        final_drift = drift_pct * 0.5  # linreg positive but fallback negative: halve it
    else:
        final_drift = fallback_drift  # linreg not positive, use fallback

    if final_drift < 5:
        return None

    severity = "high" if final_drift > 15 else "medium" if final_drift > 8 else "low"
    total_hours = len(readings)
    excess_kwh = (avg_last - avg_first) * total_hours if avg_last > avg_first else 0

    return {
        "type": "derive",
        "severity": severity,
        "message": f"Derive de +{final_drift:.1f}% sur la periode ({avg_first:.1f} → {avg_last:.1f} kW moyen) — verifier les reglages et la maintenance",
        "metrics": {
            "drift_pct": round(final_drift, 1),
            "drift_pct_linreg": round(drift_pct, 1),
            "drift_pct_fallback": round(fallback_drift, 1),
            "avg_first_week_kw": round(avg_first, 2),
            "avg_last_week_kw": round(avg_last, 2),
            "slope_kw_per_day": round(slope, 4),
        },
        "estimated_loss_kwh": round(max(0, excess_kwh * 12), 0),
    }


def _detect_data_gaps(readings: List[MeterReading]) -> Optional[dict]:
    """Detect significant data gaps (missing hours)."""
    if len(readings) < 24:
        return None

    gaps = 0
    max_gap_hours = 0

    for i in range(1, len(readings)):
        delta = (readings[i].timestamp - readings[i-1].timestamp).total_seconds() / 3600
        if delta > 1.5:
            gap_hours = int(delta)
            gaps += 1
            max_gap_hours = max(max_gap_hours, gap_hours)

    if gaps < 2 or max_gap_hours < 4:
        return None

    total_hours = (readings[-1].timestamp - readings[0].timestamp).total_seconds() / 3600
    coverage_pct = len(readings) / max(1, total_hours) * 100

    severity = "high" if coverage_pct < 80 else "medium" if coverage_pct < 90 else "low"

    return {
        "type": "data_gap",
        "severity": severity,
        "message": f"{gaps} trou(s) de donnees detecte(s) — couverture {coverage_pct:.0f}% (max gap: {max_gap_hours}h)",
        "metrics": {
            "gaps_count": gaps,
            "max_gap_hours": max_gap_hours,
            "coverage_pct": round(coverage_pct, 1),
            "total_readings": len(readings),
        },
        "estimated_loss_kwh": 0,
    }


# ========================================
# Main diagnostic + persistence
# ========================================

def run_diagnostic(
    db: Session, site_id: int,
    biz_start: int = None, biz_end: int = None,
    days: int = 30,
) -> List[ConsumptionInsight]:
    """Run all V1.1 diagnostics for a site and persist ConsumptionInsight rows.

    V1.1: reads SiteOperatingSchedule and SiteTariffProfile from DB.
    biz_start/biz_end are legacy overrides (if provided, override schedule).

    Returns list of created ConsumptionInsight objects.
    """
    meters = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).all()
    if not meters:
        return []

    # Load schedule + tariff
    schedule = _get_schedule_params(db, site_id)
    price_ref = _get_price_ref(db, site_id)

    # Legacy overrides
    if biz_start is not None:
        schedule["open_time"] = biz_start
    if biz_end is not None:
        schedule["close_time"] = biz_end

    # Delete existing insights for this site
    db.query(ConsumptionInsight).filter(ConsumptionInsight.site_id == site_id).delete()
    db.flush()

    result = []

    for meter in meters:
        readings = _get_readings(db, meter.id, days)
        if not readings:
            continue

        period_start = readings[0].timestamp
        period_end = readings[-1].timestamp

        detectors = [
            _detect_hors_horaires(readings, schedule),
            _detect_base_load(readings, schedule),
            _detect_pointe(readings),
            _detect_derive(readings),
            _detect_data_gaps(readings),
        ]

        for insight_data in detectors:
            if insight_data is None:
                continue

            # Compute estimated_loss_eur from kwh * price_ref
            loss_kwh = insight_data.get("estimated_loss_kwh", 0) or 0
            loss_eur = round(loss_kwh * price_ref, 0)

            # Add price_ref to metrics for transparency
            metrics = insight_data.get("metrics", {})
            metrics["price_ref_eur_kwh"] = price_ref

            # Generate recommended actions
            gen_fn = ACTIONS_GENERATORS.get(insight_data["type"])
            rec_actions = gen_fn(metrics, price_ref) if gen_fn else []

            ci = ConsumptionInsight(
                site_id=site_id,
                meter_id=meter.id,
                type=insight_data["type"],
                severity=insight_data["severity"],
                message=insight_data["message"],
                metrics_json=json.dumps(metrics, ensure_ascii=False),
                estimated_loss_kwh=loss_kwh,
                estimated_loss_eur=loss_eur,
                recommended_actions_json=json.dumps(rec_actions, ensure_ascii=False) if rec_actions else None,
                period_start=period_start,
                period_end=period_end,
            )
            db.add(ci)
            result.append(ci)

    db.flush()
    return result


def run_diagnostic_org(db: Session, org_id: int, days: int = 30) -> dict:
    """Run diagnostics for all sites of an organisation."""
    site_ids = [
        row[0] for row in
        db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    total_insights = 0
    sites_with_data = 0

    for sid in site_ids:
        insights = run_diagnostic(db, sid, days=days)
        if insights:
            sites_with_data += 1
            total_insights += len(insights)

    db.commit()

    return {
        "organisation_id": org_id,
        "sites_analyzed": len(site_ids),
        "sites_with_data": sites_with_data,
        "total_insights": total_insights,
    }


def get_insights_summary(db: Session, org_id: int) -> dict:
    """Aggregate consumption insights for an org."""
    site_ids = [
        row[0] for row in
        db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    if not site_ids:
        return {
            "total_insights": 0,
            "by_type": {},
            "total_loss_kwh": 0,
            "total_loss_eur": 0,
            "sites_with_insights": 0,
            "insights": [],
        }

    all_insights = (
        db.query(ConsumptionInsight)
        .filter(ConsumptionInsight.site_id.in_(site_ids))
        .all()
    )

    by_type = {}
    total_loss_kwh = 0
    total_loss_eur = 0
    sites_with = set()

    insight_list = []
    for ci in all_insights:
        by_type[ci.type] = by_type.get(ci.type, 0) + 1
        total_loss_kwh += ci.estimated_loss_kwh or 0
        total_loss_eur += ci.estimated_loss_eur or 0
        sites_with.add(ci.site_id)

        site = db.query(Site).filter(Site.id == ci.site_id).first()
        insight_list.append({
            "id": ci.id,
            "site_id": ci.site_id,
            "site_nom": site.nom if site else "?",
            "type": ci.type,
            "severity": ci.severity,
            "message": ci.message,
            "estimated_loss_kwh": ci.estimated_loss_kwh,
            "estimated_loss_eur": ci.estimated_loss_eur,
            "recommended_actions": json.loads(ci.recommended_actions_json) if ci.recommended_actions_json else [],
            "metrics": json.loads(ci.metrics_json) if ci.metrics_json else {},
            "period_start": ci.period_start.isoformat() if ci.period_start else None,
            "period_end": ci.period_end.isoformat() if ci.period_end else None,
            "insight_status": ci.insight_status.value if ci.insight_status else "open",
        })

    sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    insight_list.sort(key=lambda x: (sev_order.get(x["severity"], 0), x["estimated_loss_eur"] or 0), reverse=True)

    return {
        "total_insights": len(all_insights),
        "by_type": by_type,
        "total_loss_kwh": round(total_loss_kwh, 0),
        "total_loss_eur": round(total_loss_eur, 0),
        "sites_with_insights": len(sites_with),
        "insights": insight_list,
    }
