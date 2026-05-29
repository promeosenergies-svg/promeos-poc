"""
PROMEOS — Data Freshness Service (Sprint Énergie P0.S1b, brief P4).

SoT canonique du score de fraîcheur des relevés énergétiques. Remplace
le calcul `computeConfidence` qui vivait dans `frontend/src/pages/
MonitoringPage.jsx:202-217` (violation doctrine « zéro calcul métier
frontend » — formule pénalité cumulative côté JS).

Doctrine
────────
- Timezone canonique : Europe/Paris (cf. source-guard
  `test_cdc_timezone_paris_source_guards.py`).
- Score borné [0, 100] : utilise `score_utils.clamp_score_0_100` pour
  garantir l'invariant en sortie.
- Provenance obligatoire : source, période, formule, hypothèses.
- Skill `promeos-energy-fundamentals` pour seuils canoniques métier.

Méthode
───────
Score = (40 × score_délai) + (40 × score_couverture) + (20 × score_qualité)

avec :
  score_délai     = max(0, 1 - delay_hours / threshold_delay_hours)
  score_couverture = readings_count / readings_expected (clamped [0, 1])
  score_qualité   = avg(MeterReading.quality_score) ∈ [0, 1]

Status discret :
  - fresh    : freshness_score ≥ 80 ET delay_hours ≤ 6
  - warning  : 60 ≤ freshness_score < 80
  - stale    : 30 ≤ freshness_score < 60
  - missing  : freshness_score < 30 OU 0 reading
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import MeterReading
from models.energy_models import FrequencyType
from services.electric_monitoring.score_utils import clamp_score_0_100


TZ_PARIS = ZoneInfo("Europe/Paris")


# Seuils canoniques (skill `promeos-energy-fundamentals` + doctrine pilotage usages).
# Délai au-delà duquel on considère les données « stale » par défaut, par fréquence.
# Source : retour terrain Enedis SGE — un Linky C5 (30 min) qui n'a pas remonté
# de relevé depuis 12 h indique un problème de remontée. Un C1-C4 industriel
# (10 min) déclenche l'alerte plus tôt (4 h).
_DELAY_THRESHOLD_HOURS_BY_FREQ = {
    FrequencyType.MIN_15: 4.0,
    FrequencyType.MIN_30: 12.0,
    FrequencyType.HOURLY: 24.0,
    FrequencyType.DAILY: 72.0,
    FrequencyType.MONTHLY: 720.0,  # 30 j
}
_DEFAULT_DELAY_THRESHOLD_HOURS = 24.0


# Statuts discrets — bornes (cf. doctrine PROMEOS RAG conformité).
_STATUS_FRESH_MIN_SCORE = 80
_STATUS_WARNING_MIN_SCORE = 60
_STATUS_STALE_MIN_SCORE = 30
_STATUS_FRESH_MAX_DELAY_HOURS = 6.0


@dataclass
class FreshnessResult:
    """Résultat du calcul de fraîcheur, prêt à exposer au FE."""

    freshness_score: Optional[int]  # 0..100 ou None si aucune donnée
    status: str  # fresh | warning | stale | missing
    delay_hours: Optional[float]  # heures depuis la dernière lecture
    last_read_at: Optional[str]  # ISO 8601 Europe/Paris ou None
    expected_frequency: Optional[str]  # ex "30min", "hourly"
    coverage_pct: Optional[float]  # 0..100, % couverture vs attendu
    readings_count: int  # taille de l'échantillon analysé
    avg_quality: Optional[float]  # MeterReading.quality_score moyen ∈ [0, 1]
    provenance: dict


def compute_meter_freshness(
    db: Session,
    meter_id: int,
    *,
    window_hours: int = 168,  # 7 jours par défaut
    now: Optional[datetime] = None,
) -> FreshnessResult:
    """Calcule la fraîcheur des relevés d'un compteur sur une fenêtre.

    Args:
        meter_id : id Meter (ou Compteur sur le bridge).
        window_hours : taille de la fenêtre d'évaluation, en heures.
        now : instant de référence (pour reproductibilité tests).
            Si None, utilise `datetime.now(TZ_PARIS)`.

    Returns:
        FreshnessResult prêt à exposer au FE.
    """
    if now is None:
        now = datetime.now(TZ_PARIS)
    elif now.tzinfo is None:
        # On force la timezone Paris pour les comparaisons MeterReading.
        now = now.replace(tzinfo=TZ_PARIS)

    window_start = now - timedelta(hours=window_hours)

    # Lecture brute des relevés sur la fenêtre.
    readings = (
        db.query(
            MeterReading.timestamp,
            MeterReading.frequency,
            MeterReading.quality_score,
        )
        .filter(
            MeterReading.meter_id == meter_id,
            MeterReading.timestamp >= window_start.replace(tzinfo=None),
            MeterReading.timestamp <= now.replace(tzinfo=None),
        )
        .order_by(MeterReading.timestamp.desc())
        .all()
    )

    readings_count = len(readings)

    if readings_count == 0:
        return FreshnessResult(
            freshness_score=None,
            status="missing",
            delay_hours=None,
            last_read_at=None,
            expected_frequency=None,
            coverage_pct=None,
            readings_count=0,
            avg_quality=None,
            provenance=_build_provenance(
                meter_id=meter_id,
                window_hours=window_hours,
                now=now,
                reason="no_reading_in_window",
            ),
        )

    last_ts = readings[0].timestamp  # naïf UTC selon convention DB
    # Reconstitution timezone (cf. doctrine cdc_service : storage UTC).
    last_ts_paris = last_ts.replace(tzinfo=TZ_PARIS)
    delay_hours = max(0.0, (now - last_ts_paris).total_seconds() / 3600.0)

    # Fréquence dominante (la plus fréquente sur la fenêtre).
    freq_counts: dict[FrequencyType, int] = {}
    for r in readings:
        freq_counts[r.frequency] = freq_counts.get(r.frequency, 0) + 1
    expected_freq = max(freq_counts.items(), key=lambda kv: kv[1])[0]
    threshold_delay = _DELAY_THRESHOLD_HOURS_BY_FREQ.get(expected_freq, _DEFAULT_DELAY_THRESHOLD_HOURS)

    # Couverture : ratio relevés observés / relevés attendus sur la fenêtre.
    expected_readings = _expected_readings_per_window(expected_freq, window_hours)
    coverage_ratio = readings_count / expected_readings if expected_readings > 0 else 0.0
    coverage_ratio = min(1.0, max(0.0, coverage_ratio))

    # Score qualité (moyenne MeterReading.quality_score si renseigné).
    quality_scores = [r.quality_score for r in readings if r.quality_score is not None]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    # Formule : 40 × délai + 40 × couverture + 20 × qualité (cf. doctrine).
    delay_subscore = max(0.0, 1.0 - delay_hours / threshold_delay)
    quality_subscore = avg_quality if avg_quality is not None else 1.0

    raw_score = 40.0 * delay_subscore + 40.0 * coverage_ratio + 20.0 * quality_subscore
    freshness_score = clamp_score_0_100(raw_score, preserve_none=False)

    # Status discret.
    if freshness_score >= _STATUS_FRESH_MIN_SCORE and delay_hours <= _STATUS_FRESH_MAX_DELAY_HOURS:
        status = "fresh"
    elif freshness_score >= _STATUS_WARNING_MIN_SCORE:
        status = "warning"
    elif freshness_score >= _STATUS_STALE_MIN_SCORE:
        status = "stale"
    else:
        status = "missing"

    return FreshnessResult(
        freshness_score=freshness_score,
        status=status,
        delay_hours=round(delay_hours, 2),
        last_read_at=last_ts_paris.isoformat(),
        expected_frequency=expected_freq.value if hasattr(expected_freq, "value") else str(expected_freq),
        coverage_pct=round(coverage_ratio * 100, 1),
        readings_count=readings_count,
        avg_quality=round(avg_quality, 3) if avg_quality is not None else None,
        provenance=_build_provenance(
            meter_id=meter_id,
            window_hours=window_hours,
            now=now,
            threshold_delay_hours=threshold_delay,
            expected_readings=expected_readings,
        ),
    )


def _expected_readings_per_window(freq: FrequencyType, window_hours: int) -> int:
    """Nombre de relevés attendus sur une fenêtre pour une fréquence."""
    if freq == FrequencyType.MIN_15:
        return window_hours * 4
    if freq == FrequencyType.MIN_30:
        return window_hours * 2
    if freq == FrequencyType.HOURLY:
        return window_hours
    if freq == FrequencyType.DAILY:
        return max(1, window_hours // 24)
    if freq == FrequencyType.MONTHLY:
        return max(1, window_hours // (24 * 30))
    return max(1, window_hours)  # défaut conservateur


def _build_provenance(
    *,
    meter_id: int,
    window_hours: int,
    now: datetime,
    threshold_delay_hours: Optional[float] = None,
    expected_readings: Optional[int] = None,
    reason: Optional[str] = None,
) -> dict:
    """Provenance compatible doctrine traçabilité KPI."""
    return {
        "source": "PROMEOS data_freshness_service",
        "computed_at": now.isoformat(),
        "timezone": "Europe/Paris",
        "meter_id": meter_id,
        "window_hours": window_hours,
        "formula": "40 × delay_subscore + 40 × coverage + 20 × quality",
        "threshold_delay_hours": threshold_delay_hours,
        "expected_readings_in_window": expected_readings,
        "reason": reason,
        "doctrine_ref": "promeos-energy-fundamentals + ADR-cdc Europe/Paris",
    }
