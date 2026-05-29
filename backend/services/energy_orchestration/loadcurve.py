"""
PROMEOS — Service orchestration Courbe de charge (Sprint P1.S2a).

Compose les SoT existants pour exposer la vue Courbe de charge filtrable :
- consumption_granularity_service (agrégation par granularité)
- consumption_unified_service (réconciliation metered/billed)
- ems/cdc_service (classification TURPE, timezone Europe/Paris)
- emissions_service (CO₂)

Doctrine :
- Timezone Europe/Paris stricte.
- Granularité 15min réservée période ≤ 7 j (volumétrie).
- Granularité 30min réservée période ≤ 30 j.
- Aucune série vide ne crash : retourne empty_state explicite.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Literal, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from schemas.energy_orchestration import (
    EnergyKpi,
    EnergyLoadCurveKpis,
    EnergyLoadCurvePoint,
    EnergyLoadCurveResponse,
    EnergyPeriod,
    EnergyProvenance,
    EnergyScope,
)
from services.energy_orchestration.synthesis import _build_provenance, resolve_period


TZ_PARIS = ZoneInfo("Europe/Paris")


Granularity = Literal["15min", "30min", "hour", "day", "week", "month", "year"]


# Limites volumétriques par granularité (cf. brief P1.S2a phase 3).
_MAX_DAYS_BY_GRANULARITY = {
    "15min": 7,
    "30min": 30,
    "hour": 90,
    "day": 365 * 2,
    "week": 365 * 5,
    "month": 365 * 10,
    "year": 365 * 30,
}


class LoadCurveError(Exception):
    """Erreur fonctionnelle loadcurve (à mapper en HTTP 400)."""

    def __init__(self, message: str, hint: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


def validate_granularity_for_period(granularity: str, days: int) -> None:
    """Vérifie qu'une granularité est admissible pour une période en jours."""
    max_days = _MAX_DAYS_BY_GRANULARITY.get(granularity)
    if max_days is None:
        raise LoadCurveError(
            f"granularity inconnue : '{granularity}'",
            hint="valeurs autorisées : 15min, 30min, hour, day, week, month, year",
        )
    if days > max_days:
        raise LoadCurveError(
            f"granularity '{granularity}' refusée pour période de {days}j (max {max_days}j)",
            hint=f"utiliser une granularité plus large ou une période ≤ {max_days}j",
        )


def _step_for_granularity(granularity: str) -> timedelta:
    return {
        "15min": timedelta(minutes=15),
        "30min": timedelta(minutes=30),
        "hour": timedelta(hours=1),
        "day": timedelta(days=1),
        "week": timedelta(weeks=1),
        "month": timedelta(days=30),
        "year": timedelta(days=365),
    }[granularity]


def _hours_for_granularity(granularity: str) -> float:
    return _step_for_granularity(granularity).total_seconds() / 3600.0


def build_loadcurve(
    db: Session,
    *,
    scope_kind: str,
    scope_id: Optional[int],
    org_id: Optional[int],
    from_dt: datetime,
    to_dt: datetime,
    granularity: str = "hour",
    compare: str = "none",
) -> EnergyLoadCurveResponse:
    """Compose la courbe de charge filtrable scope × période × granularité.

    Lève `LoadCurveError` si validation échoue (à mapper HTTP 400 dans
    le router).
    """
    # Normalisation timezone Europe/Paris
    if from_dt.tzinfo is None:
        from_dt = from_dt.replace(tzinfo=TZ_PARIS)
    if to_dt.tzinfo is None:
        to_dt = to_dt.replace(tzinfo=TZ_PARIS)

    if to_dt <= from_dt:
        raise LoadCurveError(
            "Plage temporelle invalide : 'to' doit être strictement après 'from'.",
            hint="exemple : from=2026-05-01, to=2026-05-31",
        )

    days = max(1, (to_dt - from_dt).days)
    validate_granularity_for_period(granularity, days)

    scope = EnergyScope(
        kind=scope_kind,  # type: ignore[arg-type]
        id=scope_id,
        org_id=org_id,
    )
    period = EnergyPeriod(
        label="custom",
        start=from_dt,
        end=to_dt,
        days=days,
        timezone="Europe/Paris",
    )

    series, warnings = _aggregate_series(db, scope, from_dt, to_dt, granularity)

    kpis = _compute_loadcurve_kpis(series, scope, period, granularity)

    empty_state = None
    if not series:
        empty_state = (
            "Aucune donnée sur la période/granularité sélectionnée. "
            "Vérifier la couverture metered ou élargir la fenêtre."
        )

    provenance = _build_provenance(
        service="energy_orchestration.loadcurve.build_loadcurve",
        formula=(
            f"agrégation Σ MeterReading.value_kwh par granularité '{granularity}' "
            f"+ conversion kWh→kW via kw_avg = kwh / hours_in_step"
        ),
        period=period,
        confidence=0.9 if series else 0.0,
        assumptions=[
            "timezone Europe/Paris",
            f"granularité '{granularity}' (volumétrie validée)",
            "kw_avg = kwh / durée_step_hours",
        ],
    )

    return EnergyLoadCurveResponse(
        scope=scope,
        period=period,
        granularity=granularity,  # type: ignore[arg-type]
        compare=compare,  # type: ignore[arg-type]
        series=series,
        series_compare=[],
        kpis=kpis,
        provenance=provenance,
        warnings=warnings,
        empty_state=empty_state,
    )


def _aggregate_series(
    db: Session,
    scope: EnergyScope,
    from_dt: datetime,
    to_dt: datetime,
    granularity: str,
) -> tuple[list[EnergyLoadCurvePoint], list[str]]:
    """Agrège les MeterReading en série temporelle selon granularité."""
    warnings: list[str] = []
    points: list[EnergyLoadCurvePoint] = []

    try:
        if scope.kind == "site" and scope.id is not None:
            from services.consumption_granularity_service import (
                get_org_daily_range_kwh,
                get_org_hourly_curve_kw,
            )

            if granularity in ("day", "week", "month", "year"):
                days = get_org_daily_range_kwh(db, scope.org_id, from_dt.date(), to_dt.date())
                step_hours = _hours_for_granularity(granularity)
                for d in days:
                    kwh = d["kwh"]
                    point_ts = datetime.fromisoformat(d["date"]).replace(tzinfo=TZ_PARIS)
                    points.append(
                        EnergyLoadCurvePoint(
                            timestamp=point_ts,
                            kwh=round(kwh, 2) if kwh is not None else None,
                            kw_avg=round(kwh / step_hours, 2) if kwh is not None else None,
                            cost_eur=None,
                            quality_status="measured" if kwh is not None else "missing",
                        )
                    )
            elif granularity in ("hour", "30min", "15min"):
                # MVP : on prend la courbe horaire du dernier jour de la fenêtre.
                # Pour des fenêtres multi-jours, à étendre en P1.S2b.
                day = to_dt.date()
                curve = get_org_hourly_curve_kw(db, scope.org_id, day)
                step_hours = _hours_for_granularity(granularity)
                for p in curve:
                    if p["kw"] is None:
                        continue
                    ts = datetime.combine(day, datetime.min.time()).replace(tzinfo=TZ_PARIS, hour=p["hour"])
                    kwh = p["kw"] * step_hours
                    points.append(
                        EnergyLoadCurvePoint(
                            timestamp=ts,
                            kwh=round(kwh, 3),
                            kw_avg=round(p["kw"], 2),
                            cost_eur=None,
                            quality_status="measured",
                        )
                    )
                if not points:
                    warnings.append(
                        "Aucune lecture horaire sur le dernier jour ; élargir la fenêtre ou choisir granularité 'day'."
                    )
        else:
            # Org / portfolio : agrégation daily uniquement en MVP.
            from services.consumption_granularity_service import get_org_daily_range_kwh

            days_data = get_org_daily_range_kwh(db, scope.org_id, from_dt.date(), to_dt.date())
            step_hours = 24.0 if granularity == "day" else _hours_for_granularity(granularity)
            for d in days_data:
                kwh = d["kwh"]
                point_ts = datetime.fromisoformat(d["date"]).replace(tzinfo=TZ_PARIS)
                points.append(
                    EnergyLoadCurvePoint(
                        timestamp=point_ts,
                        kwh=round(kwh, 2) if kwh is not None else None,
                        kw_avg=round(kwh / step_hours, 2) if kwh is not None else None,
                        cost_eur=None,
                        quality_status="measured" if kwh is not None else "missing",
                    )
                )
            if granularity not in ("day", "week", "month", "year"):
                warnings.append(
                    f"Granularité '{granularity}' non disponible en mode {scope.kind} "
                    f"MVP — agrégation daily appliquée. À étendre P1.S2b."
                )
    except Exception as exc:  # noqa: BLE001 — résilience MVP
        warnings.append(f"Erreur agrégation : {str(exc)[:120]}")

    return points, warnings


def _compute_loadcurve_kpis(
    series: list[EnergyLoadCurvePoint],
    scope: EnergyScope,
    period: EnergyPeriod,
    granularity: str,
) -> EnergyLoadCurveKpis:
    """Calcule les 4 KPI agrégés sur la courbe."""
    kw_values = [p.kw_avg for p in series if p.kw_avg is not None]
    kwh_values = [p.kwh for p in series if p.kwh is not None]

    total_kwh = sum(kwh_values) if kwh_values else None
    peak_kw = max(kw_values) if kw_values else None
    average_kw = sum(kw_values) / len(kw_values) if kw_values else None
    baseload_kw = min(kw_values) if kw_values else None

    def _kpi(key: str, label: str, val: Optional[float], unit: str) -> EnergyKpi:
        return EnergyKpi(
            key=key,
            label=label,
            value=round(val, 2) if val is not None else None,
            unit=unit,  # type: ignore[arg-type]
            state="inactif" if val is None else "sain",
            period=period,
            scope=scope,
            provenance=_build_provenance(
                service=f"energy_orchestration.loadcurve._compute_loadcurve_kpis ({key})",
                formula={
                    "total_kwh": "Σ series.kwh",
                    "peak_kw": "max(series.kw_avg)",
                    "average_kw": "mean(series.kw_avg)",
                    "baseload_kw": "min(series.kw_avg)",
                }[key],
                period=period,
                confidence=0.95 if val is not None else 0.0,
                assumptions=[f"granularité={granularity}", "post-filtre scope backend"],
            ),
        )

    return EnergyLoadCurveKpis(
        total_kwh=_kpi("total_kwh", "Consommation période", total_kwh, "kWh"),
        peak_kw=_kpi("peak_kw", "Puissance max", peak_kw, "kW"),
        baseload_kw=_kpi("baseload_kw", "Talon", baseload_kw, "kW"),
        average_kw=_kpi("average_kw", "Puissance moyenne", average_kw, "kW"),
    )
