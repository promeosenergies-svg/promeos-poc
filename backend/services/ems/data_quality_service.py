"""
PROMEOS — Data Quality Service (EMS Tier 1)
Évalue la qualité / fraîcheur des données par compteur pour un site.

Score = 100 - max(0, delay_days - 2) * 10 - gaps_count * 5, clamped [0, 100]
Statut : ok >= 80, warning >= 50, critical < 50
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any

from sqlalchemy.orm import Session


def _score_to_status(score: float) -> str:
    """Convertit un score qualité en statut."""
    if score >= 80:
        return "ok"
    if score >= 50:
        return "warning"
    return "critical"


def compute_data_quality(db: Session, site_id: int) -> dict:
    """
    Calcule le score de qualité données pour chaque compteur actif d'un site.

    Retourne :
      - site_id
      - score_global : moyenne pondérée des scores compteurs
      - status_global : ok | warning | critical
      - meters : [{meter_id, name, last_reading, delay_days, gaps, completeness_pct, score, status}]
    """
    from models import Meter, MeterReading
    from models.power import PowerReading

    meters = (
        db.query(Meter)
        .filter(Meter.site_id == site_id, Meter.is_active == True)  # noqa: E712
        .all()
    )

    if not meters:
        return {
            "site_id": site_id,
            "score_global": 0,
            "status_global": "critical",
            "meters": [],
        }

    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    meter_results: List[Dict[str, Any]] = []

    for m in meters:
        # Déterminer la dernière relève
        last_reading_dt = m.date_derniere_releve

        # Si pas renseigné, chercher dans PowerReading puis MeterReading
        if not last_reading_dt:
            last_pr = (
                db.query(PowerReading.ts_debut)
                .filter(PowerReading.meter_id == m.id)
                .order_by(PowerReading.ts_debut.desc())
                .first()
            )
            if last_pr:
                last_reading_dt = last_pr[0]
            else:
                last_mr = (
                    db.query(MeterReading.timestamp)
                    .filter(MeterReading.meter_id == m.id)
                    .order_by(MeterReading.timestamp.desc())
                    .first()
                )
                if last_mr:
                    last_reading_dt = last_mr[0]

        # Calcul retard
        if last_reading_dt:
            delay_days = max(0, (now - last_reading_dt).days)
        else:
            delay_days = 999  # Aucune donnée

        # Compter les trous sur 30 jours (PowerReading)
        # Un trou = delta entre 2 points consécutifs > 1.5 * pas attendu
        gaps_count = 0
        readings_30d = (
            db.query(PowerReading.ts_debut, PowerReading.pas_minutes)
            .filter(
                PowerReading.meter_id == m.id,
                PowerReading.ts_debut >= thirty_days_ago,
            )
            .order_by(PowerReading.ts_debut)
            .all()
        )

        if len(readings_30d) >= 2:
            for i in range(1, len(readings_30d)):
                prev_ts = readings_30d[i - 1][0]
                curr_ts = readings_30d[i][0]
                expected_min = readings_30d[i - 1][1] or 30
                delta_min = (curr_ts - prev_ts).total_seconds() / 60
                if delta_min > expected_min * 1.5:
                    gaps_count += 1

        # Complétude sur 30 jours
        expected_points_30d = 30 * 24 * 2  # 48 points/jour pour 30min
        actual_points = len(readings_30d)

        # Fallback MeterReading si pas de PowerReading
        if actual_points == 0:
            mr_count = (
                db.query(MeterReading)
                .filter(
                    MeterReading.meter_id == m.id,
                    MeterReading.timestamp >= thirty_days_ago,
                )
                .count()
            )
            actual_points = mr_count
            expected_points_30d = 30 * 24  # hourly

        completeness_pct = round(min(100, (actual_points / max(1, expected_points_30d)) * 100), 1)

        # Score
        score = max(0, min(100, 100 - max(0, delay_days - 2) * 10 - gaps_count * 5))
        status = _score_to_status(score)

        meter_results.append(
            {
                "meter_id": m.id,
                "meter_ref": m.meter_id,
                "name": m.name,
                "last_reading": last_reading_dt.isoformat() if last_reading_dt else None,
                "delay_days": delay_days,
                "gaps": gaps_count,
                "completeness_pct": completeness_pct,
                "score": score,
                "status": status,
            }
        )

    # Score global = moyenne des scores
    scores = [mr["score"] for mr in meter_results]
    score_global = round(sum(scores) / len(scores), 1) if scores else 0
    status_global = _score_to_status(score_global)

    return {
        "site_id": site_id,
        "score_global": score_global,
        "status_global": status_global,
        "meters": meter_results,
    }
