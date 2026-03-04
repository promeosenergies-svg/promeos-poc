"""
PROMEOS - Demo Seed: Monitoring Generator (V108)
Creates monthly rolling monitoring snapshots, alerts, and consumption insights.
6 monthly snapshots per site for realistic trend dashboards.
"""

import random
from datetime import datetime, timedelta, timezone

from models import (
    MonitoringSnapshot,
    MonitoringAlert,
    ConsumptionInsight,
    AlertStatus,
    AlertSeverity,
    InsightStatus,
    FrequencyType,
)


# Number of monthly rolling snapshots per site
_NUM_MONTHLY_SNAPSHOTS = 6


def generate_monitoring(db, sites: list, meters: list, site_profiles: dict, rng: random.Random) -> dict:
    """
    Generate 6 monthly monitoring snapshots per site + alerts + insights.
    Uses the real KPI/power/quality engines for consistency.
    """
    from services.electric_monitoring.kpi_engine import KPIEngine
    from services.electric_monitoring.power_engine import PowerEngine
    from services.electric_monitoring.data_quality import DataQualityEngine
    from models import MeterReading, SiteOperatingSchedule
    from models.energy_models import EnergyVector

    kpi_engine = KPIEngine()
    power_engine = PowerEngine()
    quality_engine = DataQualityEngine()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    snapshots_count = 0
    alerts_count = 0
    insights_count = 0

    # Only use electricity meters for monitoring
    meter_by_site = {}
    for m in meters:
        if m.energy_vector == EnergyVector.ELECTRICITY and m.site_id not in meter_by_site:
            meter_by_site[m.site_id] = m

    for site in sites:
        meter = meter_by_site.get(site.id)
        if not meter:
            continue

        # Fetch schedule once for the site
        schedule = None
        sched = db.query(SiteOperatingSchedule).filter_by(site_id=site.id).first()
        if sched:
            schedule = {
                "open_days": sched.open_days,
                "open_time": sched.open_time,
                "close_time": sched.close_time,
                "is_24_7": sched.is_24_7,
            }

        # Generate 6 monthly snapshots (most recent first)
        for month_offset in range(_NUM_MONTHLY_SNAPSHOTS):
            period_end = now - timedelta(days=30 * month_offset)
            period_start = period_end - timedelta(days=30)

            # Fetch readings for this period — filter by frequency (prefer 15min > hourly)
            best_freq = None
            for freq in [FrequencyType.MIN_15, FrequencyType.HOURLY]:
                cnt = (
                    db.query(MeterReading)
                    .filter(
                        MeterReading.meter_id == meter.id,
                        MeterReading.frequency == freq,
                        MeterReading.timestamp >= period_start,
                        MeterReading.timestamp < period_end,
                    )
                    .count()
                )
                if cnt >= 48:
                    best_freq = freq
                    break
            freq_filter = [best_freq] if best_freq else [FrequencyType.MIN_15, FrequencyType.HOURLY]
            readings_orm = (
                db.query(MeterReading)
                .filter(
                    MeterReading.meter_id == meter.id,
                    MeterReading.frequency.in_(freq_filter),
                    MeterReading.timestamp >= period_start,
                    MeterReading.timestamp < period_end,
                )
                .order_by(MeterReading.timestamp)
                .all()
            )

            if len(readings_orm) < 48:
                continue

            readings = [{"timestamp": r.timestamp, "value_kwh": r.value_kwh} for r in readings_orm]

            # Auto-detect interval
            interval = 15 if best_freq == FrequencyType.MIN_15 else 60

            # Compute KPIs with real engine
            kpis = kpi_engine.compute(readings, interval_minutes=interval, schedule=schedule)
            quality = quality_engine.compute(
                readings,
                interval,
                period_start=period_start,
                period_end=period_end,
            )
            power_risk = power_engine.compute(
                kpis,
                readings,
                subscribed_power_kva=meter.subscribed_power_kva or 0,
                interval_minutes=interval,
            )

            snapshot = MonitoringSnapshot(
                site_id=site.id,
                meter_id=meter.id,
                period_start=period_start,
                period_end=period_end,
                kpis_json=kpis,
                data_quality_score=quality.get("quality_score", 0),
                risk_power_score=power_risk.get("risk_score", 0),
                data_quality_details_json=quality,
                risk_power_details_json=power_risk,
                engine_version="demo_seed_v108",
            )
            db.add(snapshot)
            db.flush()
            snapshots_count += 1

            # Alerts only on the most recent snapshot (month_offset == 0)
            if month_offset == 0:
                site_alerts = _generate_alerts(
                    site,
                    meter,
                    kpis,
                    power_risk,
                    quality,
                    snapshot.id,
                    rng,
                )
                db.add_all(site_alerts)
                alerts_count += len(site_alerts)

            # Insights on every snapshot for trend analysis
            site_insights = _generate_insights(site, meter, kpis, rng, month_offset)
            db.add_all(site_insights)
            insights_count += len(site_insights)

    db.flush()

    return {
        "snapshots_count": snapshots_count,
        "alerts_count": alerts_count,
        "insights_count": insights_count,
    }


def _generate_alerts(site, meter, kpis, power_risk, quality, snapshot_id: int, rng: random.Random) -> list:
    """Generate realistic alerts based on actual KPI values."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    alerts = []

    # High night base alert
    if kpis.get("night_ratio", 0) > 0.35:
        alerts.append(
            MonitoringAlert(
                site_id=site.id,
                meter_id=meter.id,
                alert_type="high_night_base",
                severity=AlertSeverity.WARNING,
                explanation=f"Consommation nocturne elevee : {kpis['night_ratio']:.0%} de la conso totale.",
                recommended_action="Verifier les equipements fonctionnant la nuit (CVC, eclairage, process).",
                estimated_impact_kwh=round(kpis.get("total_kwh", 0) * kpis.get("night_ratio", 0) * 0.3, 0),
                estimated_impact_eur=round(kpis.get("total_kwh", 0) * kpis.get("night_ratio", 0) * 0.3 * 0.15, 0),
                evidence_json={"night_ratio": kpis.get("night_ratio"), "threshold": 0.35},
                status=AlertStatus.OPEN,
                snapshot_id=snapshot_id,
                start_ts=now - timedelta(days=7),
            )
        )

    # Power risk alert
    risk_score = power_risk.get("risk_score", 0)
    if risk_score > 60:
        sev = AlertSeverity.CRITICAL if risk_score > 80 else AlertSeverity.HIGH
        alerts.append(
            MonitoringAlert(
                site_id=site.id,
                meter_id=meter.id,
                alert_type="power_risk",
                severity=sev,
                explanation=f"Risque de depassement de puissance souscrite (score {risk_score}/100).",
                recommended_action="Evaluer un ajustement de la puissance souscrite ou un effacement de pointe.",
                estimated_impact_eur=round(risk_score * 50, 0),
                evidence_json={"risk_score": risk_score},
                status=AlertStatus.OPEN,
                snapshot_id=snapshot_id,
                start_ts=now - timedelta(days=3),
            )
        )

    # Data quality alert
    q_score = quality.get("quality_score", 100)
    if q_score < 80:
        alerts.append(
            MonitoringAlert(
                site_id=site.id,
                meter_id=meter.id,
                alert_type="data_quality",
                severity=AlertSeverity.INFO,
                explanation=f"Qualite des donnees insuffisante (score {q_score}/100).",
                recommended_action="Verifier la connexion du compteur et l'import des donnees.",
                evidence_json={"quality_score": q_score},
                status=AlertStatus.OPEN,
                snapshot_id=snapshot_id,
                start_ts=now - timedelta(days=14),
            )
        )

    # Off-hours consumption alert
    off_ratio = kpis.get("off_hours_ratio", 0)
    if off_ratio > 0.4:
        alerts.append(
            MonitoringAlert(
                site_id=site.id,
                meter_id=meter.id,
                alert_type="off_hours_consumption",
                severity=AlertSeverity.WARNING,
                explanation=f"Consommation hors horaires elevee : {off_ratio:.0%} du total.",
                recommended_action="Programmer l'extinction des equipements en dehors des heures d'ouverture.",
                estimated_impact_kwh=round(kpis.get("off_hours_kwh", 0) * 0.5, 0),
                estimated_impact_eur=round(kpis.get("off_hours_kwh", 0) * 0.5 * 0.15, 0),
                evidence_json={"off_hours_ratio": off_ratio, "off_hours_kwh": kpis.get("off_hours_kwh", 0)},
                status=AlertStatus.OPEN,
                snapshot_id=snapshot_id,
                start_ts=now - timedelta(days=5),
            )
        )

    # Weekend ratio anomaly
    we_ratio = kpis.get("weekend_ratio", 0)
    if we_ratio > 0.8 and kpis.get("total_kwh", 0) > 1000:
        alerts.append(
            MonitoringAlert(
                site_id=site.id,
                meter_id=meter.id,
                alert_type="weekend_anomaly",
                severity=AlertSeverity.INFO,
                explanation=f"Ratio weekend/semaine eleve ({we_ratio:.2f}). Consommation similaire 7j/7.",
                evidence_json={"weekend_ratio": we_ratio},
                status=AlertStatus.OPEN,
                snapshot_id=snapshot_id,
                start_ts=now - timedelta(days=10),
            )
        )

    # Load factor alert (new V108)
    load_factor = kpis.get("load_factor", 0)
    if 0 < load_factor < 0.3:
        alerts.append(
            MonitoringAlert(
                site_id=site.id,
                meter_id=meter.id,
                alert_type="low_load_factor",
                severity=AlertSeverity.WARNING,
                explanation=f"Facteur de charge faible ({load_factor:.0%}). La puissance souscrite semble surdimensionnee.",
                recommended_action="Etudier un abaissement de la puissance souscrite pour reduire l'abonnement.",
                estimated_impact_eur=round((1 - load_factor) * 500, 0),
                evidence_json={"load_factor": load_factor},
                status=AlertStatus.OPEN,
                snapshot_id=snapshot_id,
                start_ts=now - timedelta(days=2),
            )
        )

    return alerts


def _generate_insights(site, meter, kpis, rng: random.Random, month_offset: int = 0) -> list:
    """Generate consumption insights based on KPIs."""
    insights = []

    # Status varies: older insights are RESOLVED, recent are OPEN
    status = InsightStatus.RESOLVED if month_offset >= 3 else InsightStatus.OPEN

    # Off-hours insight
    off_kwh = kpis.get("off_hours_kwh", 0)
    if off_kwh > 500:
        insights.append(
            ConsumptionInsight(
                site_id=site.id,
                meter_id=meter.id,
                type="hors_horaires",
                severity="medium",
                message=f"Consommation hors horaires de {off_kwh:.0f} kWh sur la periode.",
                estimated_loss_kwh=round(off_kwh * 0.4, 0),
                estimated_loss_eur=round(off_kwh * 0.4 * 0.15, 0),
                insight_status=status,
            )
        )

    # Base load insight
    pbase = kpis.get("pbase_kw", 0)
    pmean = kpis.get("pmean_kw", 0)
    if pbase > 0 and pmean > 0 and pbase / pmean > 0.5:
        insights.append(
            ConsumptionInsight(
                site_id=site.id,
                meter_id=meter.id,
                type="base_load",
                severity="high",
                message=f"Talon de puissance eleve : {pbase:.1f} kW ({pbase / pmean:.0%} de Pmoy).",
                estimated_loss_kwh=round(pbase * 8760 * 0.2, 0),
                estimated_loss_eur=round(pbase * 8760 * 0.2 * 0.15, 0),
                insight_status=status,
            )
        )

    # Peak insight
    pmax = kpis.get("pmax_kw", 0)
    p95 = kpis.get("p95_kw", 0)
    if pmax > 0 and p95 > 0 and pmax / p95 > 1.5:
        insights.append(
            ConsumptionInsight(
                site_id=site.id,
                meter_id=meter.id,
                type="pointe",
                severity="medium",
                message=f"Pointe de puissance anormale : Pmax={pmax:.1f} kW vs P95={p95:.1f} kW.",
                insight_status=status,
            )
        )

    # Weekend ratio insight (new V108)
    we_ratio = kpis.get("weekend_ratio", 0)
    if we_ratio > 0.7 and kpis.get("total_kwh", 0) > 1000:
        insights.append(
            ConsumptionInsight(
                site_id=site.id,
                meter_id=meter.id,
                type="weekend_ratio",
                severity="medium",
                message=f"Ratio weekend/semaine eleve ({we_ratio:.0%}). Equipements probablement non programmes.",
                estimated_loss_kwh=round(kpis.get("total_kwh", 0) * 0.1, 0),
                estimated_loss_eur=round(kpis.get("total_kwh", 0) * 0.1 * 0.15, 0),
                insight_status=status,
            )
        )

    # Load factor insight (new V108)
    load_factor = kpis.get("load_factor", 0)
    if 0 < load_factor < 0.35:
        insights.append(
            ConsumptionInsight(
                site_id=site.id,
                meter_id=meter.id,
                type="load_factor",
                severity="low",
                message=f"Facteur de charge {load_factor:.0%} — abonnement potentiellement surdimensionne.",
                insight_status=status,
            )
        )

    return insights
