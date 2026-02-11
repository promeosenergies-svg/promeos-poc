"""
PROMEOS - Service Diagnostic Consommation V1
Detecte les defauts d'usage sans complexite:
- hors_horaires: consommation en dehors des heures d'occupation
- base_load: talon de consommation (quantile bas) anormalement eleve
- pointe: jours avec consommation anormalement haute
- derive: tendance a la hausse sur 30j
- data_gap: trous dans les donnees
"""
import json
import math
import random
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from models import (
    Site, Meter, MeterReading, ConsumptionInsight,
    Organisation, Portefeuille, EntiteJuridique,
)
from models.energy_models import FrequencyType

# Prix de reference kWh (EUR HT)
PRIX_REF_KWH = 0.15


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

    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
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


# ========================================
# Diagnostic calculations
# ========================================

def _get_readings(db: Session, meter_id: int, days: int = 30) -> List[MeterReading]:
    """Get last N days of hourly readings for a meter."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(MeterReading)
        .filter(MeterReading.meter_id == meter_id, MeterReading.timestamp >= cutoff)
        .order_by(MeterReading.timestamp)
        .all()
    )


def _detect_hors_horaires(
    readings: List[MeterReading],
    biz_start: int = 8, biz_end: int = 19,
) -> Optional[dict]:
    """Detect significant consumption outside business hours.

    Returns insight dict or None.
    """
    if len(readings) < 48:  # Need at least 2 days
        return None

    biz_kwh = 0
    off_kwh = 0
    off_readings = []

    for r in readings:
        hour = r.timestamp.hour
        weekday = r.timestamp.weekday()
        is_biz = (weekday < 5 and biz_start <= hour < biz_end)
        if is_biz:
            biz_kwh += r.value_kwh
        else:
            off_kwh += r.value_kwh
            off_readings.append(r.value_kwh)

    total = biz_kwh + off_kwh
    if total == 0:
        return None

    off_pct = off_kwh / total * 100

    # Alert if > 35% of consumption is outside business hours
    if off_pct < 35:
        return None

    avg_off = sum(off_readings) / len(off_readings) if off_readings else 0
    annual_loss_kwh = avg_off * len(off_readings) * (365 / 30)  # Extrapolate
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
        },
        "estimated_loss_kwh": round(off_kwh * 0.5 * 12, 0),  # 50% recoverable, annualized
        "estimated_loss_eur": round(off_kwh * 0.5 * 12 * PRIX_REF_KWH, 0),
    }


def _detect_base_load(readings: List[MeterReading]) -> Optional[dict]:
    """Detect elevated base load (talon).

    Uses Q10 (10th percentile) as proxy for base load.
    """
    if len(readings) < 48:
        return None

    values = sorted([r.value_kwh for r in readings])
    q10_idx = max(0, int(len(values) * 0.10))
    q50_idx = int(len(values) * 0.50)
    q10 = values[q10_idx]
    q50 = values[q50_idx]

    if q50 == 0:
        return None

    base_ratio = q10 / q50 * 100

    # Alert if base load > 40% of median
    if base_ratio < 40:
        return None

    severity = "high" if base_ratio > 60 else "medium"
    annual_excess_kwh = (q10 - q50 * 0.3) * len(readings) * (365 / 30)

    return {
        "type": "base_load",
        "severity": severity,
        "message": f"Talon de consommation eleve: {q10:.1f} kW (={base_ratio:.0f}% de la mediane) — verifier les equipements en fonctionnement permanent",
        "metrics": {
            "base_load_kw": round(q10, 2),
            "median_kw": round(q50, 2),
            "base_ratio_pct": round(base_ratio, 1),
        },
        "estimated_loss_kwh": round(max(0, annual_excess_kwh), 0),
        "estimated_loss_eur": round(max(0, annual_excess_kwh) * PRIX_REF_KWH, 0),
    }


def _detect_pointe(readings: List[MeterReading]) -> Optional[dict]:
    """Detect abnormal peak days.

    Flags days where daily total > mean + 2*std.
    """
    if len(readings) < 168:  # Need at least 1 week
        return None

    # Aggregate by day
    daily = {}
    for r in readings:
        day = r.timestamp.date()
        daily[day] = daily.get(day, 0) + r.value_kwh

    if len(daily) < 7:
        return None

    values = list(daily.values())
    mean_daily = sum(values) / len(values)
    std_daily = math.sqrt(sum((v - mean_daily) ** 2 for v in values) / len(values))

    if std_daily == 0:
        return None

    threshold = mean_daily + 2 * std_daily
    anomaly_days = [d for d, v in daily.items() if v > threshold]

    if len(anomaly_days) < 2:
        return None

    max_day = max(daily, key=daily.get)
    max_val = daily[max_day]
    excess_kwh = sum(daily[d] - mean_daily for d in anomaly_days)
    severity = "high" if len(anomaly_days) > 5 else "medium"

    return {
        "type": "pointe",
        "severity": severity,
        "message": f"{len(anomaly_days)} jour(s) avec consommation anormale (>{threshold:.0f} kWh/j vs moyenne {mean_daily:.0f}) — pic le {max_day}: {max_val:.0f} kWh",
        "metrics": {
            "anomaly_days_count": len(anomaly_days),
            "mean_daily_kwh": round(mean_daily, 1),
            "threshold_kwh": round(threshold, 1),
            "max_daily_kwh": round(max_val, 1),
            "max_day": max_day.isoformat(),
        },
        "estimated_loss_kwh": round(excess_kwh * 12, 0),
        "estimated_loss_eur": round(excess_kwh * 12 * PRIX_REF_KWH, 0),
    }


def _detect_derive(readings: List[MeterReading]) -> Optional[dict]:
    """Detect upward trend (derive) over 30 days.

    Compares average of first week vs last week.
    """
    if len(readings) < 336:  # Need at least 14 days
        return None

    # Split into first week and last week
    total_hours = len(readings)
    week_hours = 168  # 7 * 24

    first_week = readings[:week_hours]
    last_week = readings[-week_hours:]

    avg_first = sum(r.value_kwh for r in first_week) / len(first_week)
    avg_last = sum(r.value_kwh for r in last_week) / len(last_week)

    if avg_first == 0:
        return None

    drift_pct = (avg_last - avg_first) / avg_first * 100

    # Alert if > 5% increase
    if drift_pct < 5:
        return None

    severity = "high" if drift_pct > 15 else "medium" if drift_pct > 8 else "low"
    excess_kwh = (avg_last - avg_first) * total_hours

    return {
        "type": "derive",
        "severity": severity,
        "message": f"Derive de +{drift_pct:.1f}% sur la periode ({avg_first:.1f} → {avg_last:.1f} kW moyen) — verifier les reglages et la maintenance",
        "metrics": {
            "drift_pct": round(drift_pct, 1),
            "avg_first_week_kw": round(avg_first, 2),
            "avg_last_week_kw": round(avg_last, 2),
        },
        "estimated_loss_kwh": round(max(0, excess_kwh * 12), 0),
        "estimated_loss_eur": round(max(0, excess_kwh * 12) * PRIX_REF_KWH, 0),
    }


def _detect_data_gaps(readings: List[MeterReading]) -> Optional[dict]:
    """Detect significant data gaps (missing hours)."""
    if len(readings) < 24:
        return None

    gaps = 0
    max_gap_hours = 0
    current_gap = 0

    for i in range(1, len(readings)):
        delta = (readings[i].timestamp - readings[i-1].timestamp).total_seconds() / 3600
        if delta > 1.5:  # More than 1.5h between hourly readings = gap
            gap_hours = int(delta)
            gaps += 1
            current_gap = gap_hours
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
        "estimated_loss_eur": 0,
    }


# ========================================
# Main diagnostic + persistence
# ========================================

def run_diagnostic(
    db: Session, site_id: int,
    biz_start: int = 8, biz_end: int = 19,
    days: int = 30,
) -> List[ConsumptionInsight]:
    """Run all V1 diagnostics for a site and persist ConsumptionInsight rows.

    Args:
        biz_start, biz_end: business hours (from questionnaire or default)
        days: lookback period

    Returns list of created ConsumptionInsight objects.
    """
    # Get all meters for site
    meters = db.query(Meter).filter(Meter.site_id == site_id, Meter.is_active == True).all()
    if not meters:
        return []

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
            _detect_hors_horaires(readings, biz_start, biz_end),
            _detect_base_load(readings),
            _detect_pointe(readings),
            _detect_derive(readings),
            _detect_data_gaps(readings),
        ]

        for insight_data in detectors:
            if insight_data is None:
                continue

            ci = ConsumptionInsight(
                site_id=site_id,
                meter_id=meter.id,
                type=insight_data["type"],
                severity=insight_data["severity"],
                message=insight_data["message"],
                metrics_json=json.dumps(insight_data.get("metrics", {}), ensure_ascii=False),
                estimated_loss_kwh=insight_data.get("estimated_loss_kwh"),
                estimated_loss_eur=insight_data.get("estimated_loss_eur"),
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
            "metrics": json.loads(ci.metrics_json) if ci.metrics_json else {},
            "period_start": ci.period_start.isoformat() if ci.period_start else None,
            "period_end": ci.period_end.isoformat() if ci.period_end else None,
        })

    # Sort by severity then loss
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
