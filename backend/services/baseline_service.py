"""Service baseline PROMEOS — 3 méthodes canoniques A/B/C (décisions B+D §0.D).

Méthodes :
  A_HISTORICAL   : moyenne 4 mêmes jours de semaine sur 12 semaines glissantes
  B_DJU_ADJUSTED : régression linéaire E = a×DJU + b, calibration depuis BaselineCalibration
  C_REGULATORY_DT: conso année référence DT (ref_year depuis DT_REF_YEAR_DEFAULT)

Aucune exception levée : si données insuffisantes → value=0, confidence='faible'.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §2.B Phase 1.2
Doctrine : §0.D décisions B+D — 3 baselines + historisation calibration r²
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from doctrine.constants import DT_REF_YEAR_DEFAULT
from models.baseline_calibration import BaselineCalibration, BaselineMethod
from models.energy_models import Meter, MeterReading

# ─── Seuils confidence ──────────────────────────────────────────────────────

_CONFIDENCE_HAUTE = "haute"
_CONFIDENCE_MOYENNE = "moyenne"
_CONFIDENCE_FAIBLE = "faible"

_BASELINE_A_WINDOW_WEEKS = 12
_BASELINE_B_MIN_DAYS = 90
_BASELINE_B_R2_THRESHOLD = 0.7


def _confidence_from_points(data_points: int) -> str:
    """Retourne le niveau de confiance selon le nombre de points."""
    if data_points >= 4:
        return _CONFIDENCE_HAUTE
    if data_points >= 2:
        return _CONFIDENCE_MOYENNE
    return _CONFIDENCE_FAIBLE


def _get_meter_ids_for_site(db: Session, site_id: int) -> list[int]:
    """Retourne la liste des meter.id associés à un site."""
    rows = db.query(Meter.id).filter(Meter.site_id == site_id).all()
    return [r[0] for r in rows]


# ─── Méthode A ───────────────────────────────────────────────────────────────


def get_baseline_a(db: Session, site_id: int, target_date: date) -> dict:
    """Baseline A : moyenne 4 mêmes jours de semaine sur 12 semaines glissantes.

    Lit MeterReading sur la fenêtre [target_date - 12 semaines, target_date].
    Filtre par jour de semaine identique à target_date.
    Confidence : 'haute' si ≥4 points, 'moyenne' si 2-3, 'faible' si <2.

    Returns:
        {
            "value_kwh": float,
            "calibration_date": str (ISO),
            "confidence": "haute"|"moyenne"|"faible",
            "method": "a_historical",
            "data_points": int,
        }
    """
    meter_ids = _get_meter_ids_for_site(db, site_id)
    now_iso = datetime.utcnow().isoformat()

    if not meter_ids:
        return {
            "value_kwh": 0.0,
            "calibration_date": now_iso,
            "confidence": _CONFIDENCE_FAIBLE,
            "method": BaselineMethod.A_HISTORICAL.value,
            "data_points": 0,
        }

    window_start = datetime.combine(target_date - timedelta(weeks=_BASELINE_A_WINDOW_WEEKS), datetime.min.time())
    window_end = datetime.combine(target_date, datetime.max.time())

    # Jour de semaine cible (0=lundi … 6=dimanche)
    target_weekday = target_date.weekday()

    rows = (
        db.query(MeterReading.timestamp, MeterReading.value_kwh)
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= window_start,
            MeterReading.timestamp <= window_end,
        )
        .all()
    )

    # Grouper par jour (sommer les lectures du même jour, multi-compteurs)
    daily: dict[date, float] = {}
    for ts, kwh in rows:
        if ts.weekday() == target_weekday:
            d = ts.date()
            daily[d] = daily.get(d, 0.0) + kwh

    data_points = len(daily)
    value_kwh = sum(daily.values()) / data_points if data_points > 0 else 0.0
    confidence = _confidence_from_points(data_points)

    return {
        "value_kwh": round(value_kwh, 3),
        "calibration_date": now_iso,
        "confidence": confidence,
        "method": BaselineMethod.A_HISTORICAL.value,
        "data_points": data_points,
    }


# ─── Méthode B ───────────────────────────────────────────────────────────────


def get_baseline_b(db: Session, site_id: int, target_date: date, dju: float) -> dict:
    """Baseline B : E = a×DJU + b calibré sur 12 mois glissants.

    La calibration coefficients (a, b, r²) est lue depuis la DERNIÈRE
    BaselineCalibration enregistrée pour (site_id, method=B).

    Fallback → get_baseline_a dans les cas suivants :
      - moins de 90 jours de MeterReading disponibles pour le site
      - aucune calibration B enregistrée

    Si r² < 0.7 : confidence='faible' mais retourne résultat méthode B.

    Returns:
        {
            "value_kwh": float,
            "calibration_date": str (ISO),
            "confidence": "haute"|"moyenne"|"faible",
            "r_squared": float|None,
            "a": float|None,
            "b": float|None,
            "method": "b_dju_adjusted"|"a_historical",
        }
    """
    meter_ids = _get_meter_ids_for_site(db, site_id)
    now_iso = datetime.utcnow().isoformat()

    # Vérifier couverture données (≥90 jours)
    if meter_ids:
        window_90d = datetime.utcnow() - timedelta(days=_BASELINE_B_MIN_DAYS)
        count = (
            db.query(func.count(MeterReading.id))
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= window_90d,
            )
            .scalar()
        ) or 0
    else:
        count = 0

    if count < _BASELINE_B_MIN_DAYS or not meter_ids:
        # Fallback A
        result_a = get_baseline_a(db, site_id, target_date)
        return {
            "value_kwh": result_a["value_kwh"],
            "calibration_date": result_a["calibration_date"],
            "confidence": result_a["confidence"],
            "r_squared": None,
            "a": None,
            "b": None,
            "method": BaselineMethod.A_HISTORICAL.value,
        }

    # Lire la dernière calibration B pour ce site
    calib: Optional[BaselineCalibration] = (
        db.query(BaselineCalibration)
        .filter(
            BaselineCalibration.site_id == site_id,
            BaselineCalibration.method == BaselineMethod.B_DJU_ADJUSTED.value,
        )
        .order_by(BaselineCalibration.calibration_date.desc())
        .first()
    )

    if calib is None:
        # Pas de calibration enregistrée → fallback A
        result_a = get_baseline_a(db, site_id, target_date)
        return {
            "value_kwh": result_a["value_kwh"],
            "calibration_date": result_a["calibration_date"],
            "confidence": result_a["confidence"],
            "r_squared": None,
            "a": None,
            "b": None,
            "method": BaselineMethod.A_HISTORICAL.value,
        }

    # Appliquer la régression
    a = calib.coefficient_a or 0.0
    b = calib.coefficient_b or 0.0
    value_kwh = a * dju + b

    r2 = calib.r_squared
    if r2 is None or r2 < _BASELINE_B_R2_THRESHOLD:
        confidence = _CONFIDENCE_FAIBLE
    elif r2 >= 0.85:
        confidence = _CONFIDENCE_HAUTE
    else:
        confidence = _CONFIDENCE_MOYENNE

    return {
        "value_kwh": round(max(value_kwh, 0.0), 3),
        "calibration_date": calib.calibration_date.isoformat(),
        "confidence": confidence,
        "r_squared": r2,
        "a": a,
        "b": b,
        "method": BaselineMethod.B_DJU_ADJUSTED.value,
    }


# ─── Méthode C ───────────────────────────────────────────────────────────────


def get_baseline_c(db: Session, site_id: int, year: int = DT_REF_YEAR_DEFAULT) -> dict:
    """Baseline C : conso année référence DT (ref_year=DT_REF_YEAR_DEFAULT).

    Lit la dernière BaselineCalibration (site_id, method=C, ref_year=year).
    Si absente, agrège MeterReading sur l'année `year` en kWh.
    Si aucune donnée → value_kwh_year=0, confidence='faible'.

    Returns:
        {
            "value_kwh_year": float,
            "ref_year": int,
            "method": "c_regulatory_dt",
            "calibration_date": str (ISO),
            "confidence": "haute"|"moyenne"|"faible",
        }
    """
    now_iso = datetime.utcnow().isoformat()

    # Lire la dernière calibration C pour ce site + année
    calib: Optional[BaselineCalibration] = (
        db.query(BaselineCalibration)
        .filter(
            BaselineCalibration.site_id == site_id,
            BaselineCalibration.method == BaselineMethod.C_REGULATORY_DT.value,
            BaselineCalibration.ref_year == year,
        )
        .order_by(BaselineCalibration.calibration_date.desc())
        .first()
    )

    if calib is not None:
        # La calibration stocke la valeur dans coefficient_a (conso annuelle kWh)
        value_kwh_year = calib.coefficient_a or 0.0
        return {
            "value_kwh_year": round(value_kwh_year, 3),
            "ref_year": year,
            "method": BaselineMethod.C_REGULATORY_DT.value,
            "calibration_date": calib.calibration_date.isoformat(),
            "confidence": _CONFIDENCE_HAUTE,
        }

    # Fallback : agréger les MeterReadings de l'année ref
    meter_ids = _get_meter_ids_for_site(db, site_id)

    if not meter_ids:
        return {
            "value_kwh_year": 0.0,
            "ref_year": year,
            "method": BaselineMethod.C_REGULATORY_DT.value,
            "calibration_date": now_iso,
            "confidence": _CONFIDENCE_FAIBLE,
        }

    year_start = datetime(year, 1, 1)
    year_end = datetime(year, 12, 31, 23, 59, 59)

    total = (
        db.query(func.sum(MeterReading.value_kwh))
        .filter(
            MeterReading.meter_id.in_(meter_ids),
            MeterReading.timestamp >= year_start,
            MeterReading.timestamp <= year_end,
        )
        .scalar()
    ) or 0.0

    confidence = _CONFIDENCE_MOYENNE if total > 0 else _CONFIDENCE_FAIBLE

    return {
        "value_kwh_year": round(float(total), 3),
        "ref_year": year,
        "method": BaselineMethod.C_REGULATORY_DT.value,
        "calibration_date": now_iso,
        "confidence": confidence,
    }
