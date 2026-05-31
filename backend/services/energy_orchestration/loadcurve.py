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
    # Sprint Énergie P3.1 — pics + profil moyen par jour
    EnergyTopPeak,
    EnergyWeekdayCurve,
    EnergyWeekdayDecomposition,
    EnergyWeekdayPoint,
    EnergyWeekdayWeekendComparison,
)
from services.energy_orchestration.synthesis import _build_provenance, resolve_period


# Sprint Énergie P3.1 — labels FR canoniques jours de semaine.
_WEEKDAY_LABELS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
_HOUR_LABELS_FR = [f"{h:02d}h" for h in range(24)]
_MAX_TOP_PEAKS = 5


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

    # Sprint Énergie P3.1 — pics + profil moyen par jour
    top_peaks = _compute_top_peaks(series, period)
    weekday_overlay = _compute_weekday_overlay(series, period, granularity)
    weekday_decomposition = _compute_weekday_decomposition(series, period)
    weekday_weekend_comparison = _compute_weekday_weekend_comparison(series, period)

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
        top_peaks=top_peaks,
        weekday_overlay=weekday_overlay,
        weekday_decomposition=weekday_decomposition,
        weekday_weekend_comparison=weekday_weekend_comparison,
        provenance=provenance,
        warnings=warnings,
        empty_state=empty_state,
    )


# ── Sprint Énergie P3.1 helpers ──────────────────────────────────────


def _classify_weekday_state(share_pct: Optional[float]) -> str:
    """Classifie un jour par sa part dans la consommation totale.

    Doctrine zéro calcul métier : la borne est un seuil cosmétique
    d'affichage (pas un KPI métier).
    """
    if share_pct is None:
        return "inactif"
    if share_pct >= 25.0:
        return "critique"
    if share_pct >= 18.0:
        return "vigilance"
    return "sain"


def _localize_to_paris(dt: datetime) -> datetime:
    """Convertit un timestamp en Europe/Paris (préserve la valeur s'il y est déjà)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=TZ_PARIS)
    return dt.astimezone(TZ_PARIS)


def _compute_top_peaks(
    series: list[EnergyLoadCurvePoint],
    period: EnergyPeriod,
) -> list[EnergyTopPeak]:
    """Classement des pics de puissance par kw_avg décroissant.

    Doctrine : tri pur sans calcul métier neuf. Top 5 maximum.
    """
    valid = [p for p in series if p.kw_avg is not None]
    if not valid:
        return []
    sorted_pts = sorted(valid, key=lambda p: p.kw_avg or 0.0, reverse=True)
    peaks: list[EnergyTopPeak] = []
    for rank, point in enumerate(sorted_pts[:_MAX_TOP_PEAKS], start=1):
        local = _localize_to_paris(point.timestamp)
        weekday_label = _WEEKDAY_LABELS_FR[local.weekday()]
        hour_label = _HOUR_LABELS_FR[local.hour]
        period_label = f"{weekday_label} {hour_label}"
        # Action conseillée : contexte d'analyse, non engageant
        if rank == 1:
            recommended_action = "Analyser l'usage pilotable sur cette plage : déplacement ou lissage potentiel."
        else:
            recommended_action = "Vérifier la récurrence et identifier le poste de consommation."
        # Contexte : pic récurrent si même créneau jour+heure dans autres top
        context: Optional[str] = None
        same_slot = sum(
            1
            for p in sorted_pts[:_MAX_TOP_PEAKS]
            if _localize_to_paris(p.timestamp).weekday() == local.weekday()
            and _localize_to_paris(p.timestamp).hour == local.hour
        )
        if same_slot >= 2:
            context = "Pic récurrent sur plage active"
        peaks.append(
            EnergyTopPeak(
                rank=rank,
                timestamp=point.timestamp,
                kwh=point.kwh,
                kw_avg=point.kw_avg,
                period_label=period_label,
                context=context,
                recommended_action=recommended_action,
                quality_status=point.quality_status,
                provenance=_build_provenance(
                    service="energy_orchestration.loadcurve._compute_top_peaks",
                    formula=("classement des points de la série par kw_avg décroissant ; top 5 retenus"),
                    period=period,
                    confidence=0.85,
                    assumptions=[
                        "timezone Europe/Paris",
                        "kw_avg fourni par _aggregate_series (kWh / durée_step_hours)",
                    ],
                ),
            )
        )
    return peaks


def _compute_weekday_overlay(
    series: list[EnergyLoadCurvePoint],
    period: EnergyPeriod,
    granularity: str = "hour",
) -> list[EnergyWeekdayCurve]:
    """Profil moyen par jour de semaine — 7 courbes × 24 heures.

    Pour chaque (jour_de_semaine, heure), moyenne arithmétique des
    valeurs des points correspondants dans la série.

    Hotfix P3.1 : pour les granularités ≥ jour (day/week/month/year),
    chaque point timeseries représente un step >= 24h et est indexé à
    minuit Europe/Paris. On étale alors `kw_avg` du point sur toutes les
    heures couvertes (sinon 23h sont vides et les courbes Recharts sont
    invisibles). `avg_kwh` du bucket horaire est ramené à `kwh / step_h`
    (kWh par heure cohérent avec puissance moyenne du step).
    """
    if not series:
        return []

    step_hours = _hours_for_granularity(granularity)
    # Au-delà du step horaire, on étale chaque point sur toutes les
    # heures du step (cas day/week/month/year — point indexé minuit).
    spread_over_step = step_hours >= 24.0
    hours_to_spread = int(min(24, max(1, round(step_hours)))) if spread_over_step else 1

    # Bucket : (day_of_week, hour) → list of (kwh_h, kw_avg, quality_status)
    buckets: dict[tuple[int, int], list[tuple[Optional[float], Optional[float], str]]] = {}
    for point in series:
        local = _localize_to_paris(point.timestamp)
        weekday = local.weekday()
        if spread_over_step:
            # kWh par heure pour rester cohérent avec une lecture horaire.
            kwh_h = (point.kwh / hours_to_spread) if point.kwh is not None else None
            for h in range(hours_to_spread):
                buckets.setdefault((weekday, h), []).append((kwh_h, point.kw_avg, point.quality_status))
        else:
            buckets.setdefault((weekday, local.hour), []).append((point.kwh, point.kw_avg, point.quality_status))

    curves: list[EnergyWeekdayCurve] = []
    for day_of_week in range(7):
        label = _WEEKDAY_LABELS_FR[day_of_week]
        points: list[EnergyWeekdayPoint] = []
        for hour in range(24):
            entries = buckets.get((day_of_week, hour), [])
            kwh_vals = [e[0] for e in entries if e[0] is not None]
            kw_vals = [e[1] for e in entries if e[1] is not None]
            statuses = [e[2] for e in entries]
            avg_kwh = sum(kwh_vals) / len(kwh_vals) if kwh_vals else None
            avg_kw = sum(kw_vals) / len(kw_vals) if kw_vals else None
            # quality_status majoritaire
            if not statuses:
                q = "missing"
            else:
                if all(s == "measured" for s in statuses):
                    q = "measured"
                elif any(s == "missing" for s in statuses):
                    q = "missing"
                else:
                    q = "estimated"
            points.append(
                EnergyWeekdayPoint(
                    hour=hour,
                    avg_kwh=avg_kwh,
                    avg_kw=avg_kw,
                    n_points=len(entries),
                    quality_status=q,  # type: ignore[arg-type]
                )
            )
        curves.append(
            EnergyWeekdayCurve(
                day_of_week=day_of_week,
                label=label,
                points=points,
                provenance=_build_provenance(
                    service="energy_orchestration.loadcurve._compute_weekday_overlay",
                    formula=(
                        f"moyenne arithmétique kwh/kw_avg par (jour_semaine={label}, "
                        "heure) sur la période ; n_points = nombre d'occurrences "
                        "agrégées ; pour granularité ≥ jour, kw_avg du point est "
                        "étalé sur les 24h du step (kWh/h = kwh_step / 24)"
                    ),
                    period=period,
                    confidence=0.85,
                    assumptions=[
                        "timezone Europe/Paris",
                        "0=Lundi, 6=Dimanche",
                        "axe heure local 0h-23h",
                    ],
                ),
            )
        )
    return curves


def _compute_weekday_decomposition(
    series: list[EnergyLoadCurvePoint],
    period: EnergyPeriod,
) -> list[EnergyWeekdayDecomposition]:
    """Décomposition de la consommation totale par jour de semaine."""
    if not series:
        return []

    # totaux par day_of_week + ensemble des dates uniques
    totals: dict[int, float] = {i: 0.0 for i in range(7)}
    unique_dates: dict[int, set[date]] = {i: set() for i in range(7)}
    grand_total = 0.0
    for point in series:
        local = _localize_to_paris(point.timestamp)
        dow = local.weekday()
        if point.kwh is not None:
            totals[dow] += point.kwh
            grand_total += point.kwh
            unique_dates[dow].add(local.date())

    decomposition: list[EnergyWeekdayDecomposition] = []
    for day_of_week in range(7):
        total_kwh = totals[day_of_week]
        n_days = len(unique_dates[day_of_week])
        avg_kwh = total_kwh / n_days if n_days > 0 else None
        share_pct = (total_kwh / grand_total * 100.0) if grand_total > 0 else None
        state = _classify_weekday_state(share_pct)
        decomposition.append(
            EnergyWeekdayDecomposition(
                day_of_week=day_of_week,
                label=_WEEKDAY_LABELS_FR[day_of_week],
                total_kwh=total_kwh if total_kwh > 0 else None,
                avg_kwh_per_day=avg_kwh,
                share_pct=share_pct,
                n_days=n_days,
                state=state,  # type: ignore[arg-type]
                provenance=_build_provenance(
                    service="energy_orchestration.loadcurve._compute_weekday_decomposition",
                    formula=(
                        f"total_kwh = Σ kwh sur {_WEEKDAY_LABELS_FR[day_of_week]}s ; "
                        "share_pct = total_kwh / total_global × 100 ; "
                        "avg_kwh_per_day = total_kwh / n_days"
                    ),
                    period=period,
                    confidence=0.85 if grand_total > 0 else 0.0,
                    assumptions=[
                        "timezone Europe/Paris",
                        "n_days = nombre de dates distinctes observées",
                    ],
                ),
            )
        )
    return decomposition


def _compute_weekday_weekend_comparison(
    series: list[EnergyLoadCurvePoint],
    period: EnergyPeriod,
) -> Optional[EnergyWeekdayWeekendComparison]:
    """Comparaison jours ouvrés (Lun-Ven) vs week-end (Sam-Dim)."""
    if not series:
        return None
    weekday_kwh = 0.0
    weekend_kwh = 0.0
    for point in series:
        if point.kwh is None:
            continue
        local = _localize_to_paris(point.timestamp)
        if local.weekday() >= 5:
            weekend_kwh += point.kwh
        else:
            weekday_kwh += point.kwh
    total = weekday_kwh + weekend_kwh
    weekend_share_pct = (weekend_kwh / total * 100.0) if total > 0 else None
    return EnergyWeekdayWeekendComparison(
        weekday_kwh=weekday_kwh if weekday_kwh > 0 else None,
        weekend_kwh=weekend_kwh if weekend_kwh > 0 else None,
        weekend_share_pct=weekend_share_pct,
        provenance=_build_provenance(
            service="energy_orchestration.loadcurve._compute_weekday_weekend_comparison",
            formula=("Lun-Ven Σ kwh vs Sam-Dim Σ kwh ; weekend_share_pct = weekend_kwh / total × 100"),
            period=period,
            confidence=0.85 if total > 0 else 0.0,
            assumptions=[
                "timezone Europe/Paris",
                "weekday = 0..4 (Lun-Ven), weekend = 5..6 (Sam-Dim)",
            ],
        ),
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
