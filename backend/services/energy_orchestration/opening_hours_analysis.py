"""
PROMEOS — Service orchestration Analyse hors horaires (Sprint Énergie P3.2).

Compare les horaires d'ouverture déclarés (`SiteOperatingSchedule`) à la
consommation mesurée pour identifier les créneaux hors horaires + KPI
agrégés + recommandations FR métier.

Doctrine cardinale :
- Aucun calcul métier frontend : ranking, classification status, cost,
  recommended_action — tout vient d'ici.
- Provenance obligatoire sur chaque KPI, slot, recommandation.
- Timezone Europe/Paris stricte.
- Aucune économie présentée comme certaine : `estimated_cost_eur` reste
  null si aucun prix disponible ; sinon marqué « indicatif » via le
  champ `assumptions`.
- Aucun horaire inventé : si `SiteOperatingSchedule` manquant →
  `OpeningSchedule.source = "missing"` + `empty_state` explicite.
"""

from __future__ import annotations

import json
from datetime import datetime, time
from typing import Optional

from sqlalchemy.orm import Session

from schemas.energy_orchestration import (
    EnergyKpi,
    EnergyLoadCurvePoint,
    EnergyPeriod,
    EnergyProvenance,
    EnergyScope,
    OffHoursAnalysisResponse,
    OffHoursKpis,
    OffHoursRecommendation,
    OffHoursSlot,
    OffHoursStatus,
    OpeningDaySchedule,
    OpeningSchedule,
    OpeningSource,
    OpeningTimeRange,
)
from services.energy_orchestration.loadcurve import (
    LoadCurveError,
    TZ_PARIS,
    _aggregate_series,
    _localize_to_paris,
    validate_granularity_for_period,
)
from services.energy_orchestration.synthesis import _build_provenance, resolve_period


_WEEKDAY_LABELS_FR = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
_NIGHT_HOURS = set(range(0, 6))  # 00h-06h pour talon nuit
_DEFAULT_GRANULARITY = "hour"
_MAX_TOP_OFF_HOURS = 10
# Seuil anti-bruit : un point < 0.1 kWh est considéré comme bruit ; non comptabilisé.
_NOISE_KWH_THRESHOLD = 0.1


# ── Helpers schedule ────────────────────────────────────────────────────


def _parse_hhmm(value: Optional[str]) -> Optional[time]:
    if not value:
        return None
    try:
        hh, mm = value.split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError):
        return None


def _parse_intervals_json(raw: Optional[str]) -> dict[int, list[OpeningTimeRange]]:
    """Parse `SiteOperatingSchedule.intervals_json` en map jour → ranges."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
    out: dict[int, list[OpeningTimeRange]] = {}
    if not isinstance(data, dict):
        return out
    for day_key, intervals in data.items():
        try:
            day = int(day_key)
        except (TypeError, ValueError):
            continue
        ranges: list[OpeningTimeRange] = []
        if not isinstance(intervals, list):
            continue
        for it in intervals:
            if not isinstance(it, dict):
                continue
            s = it.get("start")
            e = it.get("end")
            if s and e:
                ranges.append(OpeningTimeRange(start_time=s, end_time=e))
        if ranges:
            out[day] = ranges
    return out


def _parse_exceptions_json(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(d) for d in data if isinstance(d, str)]


def _missing_schedule(period: EnergyPeriod) -> OpeningSchedule:
    """Construit un OpeningSchedule explicitement vide (source=missing)."""
    return OpeningSchedule(
        timezone="Europe/Paris",
        source="missing",
        weekly_schedule=[],
        exceptions=[],
        provenance=_build_provenance(
            service="energy_orchestration.opening_hours_analysis._missing_schedule",
            formula="aucun SiteOperatingSchedule en base — empty_state explicite",
            period=period,
            confidence=0.0,
            assumptions=["timezone Europe/Paris par défaut"],
        ),
    )


def _load_opening_schedule(db: Session, scope: EnergyScope, period: EnergyPeriod) -> OpeningSchedule:
    """Lit `SiteOperatingSchedule` ou retourne un schedule `source=missing`.

    Aucun horaire inventé : si le site n'a pas d'enregistrement, on
    retourne explicitement `source="missing"` ; le consommateur affiche
    l'empty_state correspondant.
    """
    if scope.kind != "site" or scope.id is None:
        return _missing_schedule(period)

    try:
        from models.site_operating_schedule import SiteOperatingSchedule
    except ImportError:
        return _missing_schedule(period)

    row = db.query(SiteOperatingSchedule).filter(SiteOperatingSchedule.site_id == scope.id).one_or_none()
    if row is None:
        return _missing_schedule(period)

    timezone = (row.timezone or "Europe/Paris").strip() or "Europe/Paris"
    intervals_map = _parse_intervals_json(row.intervals_json)
    exceptions = _parse_exceptions_json(row.exceptions_json)

    open_days: set[int] = set()
    if row.open_days:
        for token in str(row.open_days).split(","):
            token = token.strip()
            if token.isdigit():
                open_days.add(int(token))

    default_range: Optional[OpeningTimeRange] = None
    if row.is_24_7:
        default_range = OpeningTimeRange(start_time="00:00", end_time="23:59")
    else:
        open_t = (row.open_time or "").strip()
        close_t = (row.close_time or "").strip()
        if _parse_hhmm(open_t) and _parse_hhmm(close_t):
            default_range = OpeningTimeRange(start_time=open_t, end_time=close_t)

    weekly: list[OpeningDaySchedule] = []
    for day in range(7):
        ranges = intervals_map.get(day) or ([] if day not in open_days else ([default_range] if default_range else []))
        is_open = bool(ranges) if day in open_days or intervals_map.get(day) else bool(intervals_map.get(day))
        if row.is_24_7:
            is_open = True
            ranges = [OpeningTimeRange(start_time="00:00", end_time="23:59")]
        weekly.append(
            OpeningDaySchedule(
                day_of_week=day,
                label=_WEEKDAY_LABELS_FR[day],
                is_open=is_open,
                ranges=ranges,
            )
        )

    return OpeningSchedule(
        timezone=timezone,
        source="declared",
        weekly_schedule=weekly,
        exceptions=exceptions,
        provenance=_build_provenance(
            service="energy_orchestration.opening_hours_analysis._load_opening_schedule",
            formula=(
                "SiteOperatingSchedule.open_days + open_time/close_time + intervals_json "
                "fusionnés en grille hebdomadaire 7×N ranges"
            ),
            period=period,
            confidence=0.95,
            assumptions=[
                f"timezone {timezone}",
                "0=Lundi, 6=Dimanche",
                "is_24_7 force grille 00:00-23:59 sur les 7 jours",
            ],
        ),
    )


def _is_within_opening_hours(timestamp: datetime, schedule: OpeningSchedule) -> bool:
    """True si le timestamp tombe dans une plage déclarée (sinon hors horaires)."""
    if schedule.source == "missing" or not schedule.weekly_schedule:
        return False
    local = _localize_to_paris(timestamp)
    iso_date = local.date().isoformat()
    if iso_date in schedule.exceptions:
        return False  # fermeture exceptionnelle
    day_grid = next(
        (d for d in schedule.weekly_schedule if d.day_of_week == local.weekday()),
        None,
    )
    if day_grid is None or not day_grid.is_open or not day_grid.ranges:
        return False
    t = local.time()
    for r in day_grid.ranges:
        start = _parse_hhmm(r.start_time)
        end = _parse_hhmm(r.end_time)
        if start is None or end is None:
            continue
        if start <= t <= end:
            return True
    return False


# ── KPI helpers ────────────────────────────────────────────────────────


def _classify_off_hours_status(share_pct: Optional[float]) -> OffHoursStatus:
    if share_pct is None:
        return "sain"
    if share_pct >= 25.0:
        return "critique"
    if share_pct >= 10.0:
        return "vigilance"
    return "sain"


def _kpi(
    *,
    key: str,
    label: str,
    value: Optional[float],
    unit: str,
    state: str,
    service: str,
    formula: str,
    period: EnergyPeriod,
    scope: EnergyScope,
    confidence: float,
    assumptions: list[str],
) -> EnergyKpi:
    return EnergyKpi(
        key=key,
        label=label,
        value=value,
        unit=unit,
        state=state,
        period=period,
        scope=scope,
        provenance=_build_provenance(
            service=service,
            formula=formula,
            period=period,
            confidence=confidence,
            assumptions=assumptions,
        ),
    )


# ── Compute slots + KPI ───────────────────────────────────────────────


def _compute_slots(
    series: list[EnergyLoadCurvePoint],
    schedule: OpeningSchedule,
    period: EnergyPeriod,
) -> list[OffHoursSlot]:
    """Identifie chaque point hors horaires comme un slot annoté."""
    if not series or schedule.source == "missing":
        return []
    slots: list[OffHoursSlot] = []
    for point in series:
        if point.kwh is None or point.kwh < _NOISE_KWH_THRESHOLD:
            continue
        if _is_within_opening_hours(point.timestamp, schedule):
            continue
        local = _localize_to_paris(point.timestamp)
        day = local.weekday()
        # Justification reason FR métier
        if day in (5, 6):
            reason = "Week-end fermé selon horaires déclarés"
        else:
            day_grid = next(
                (d for d in schedule.weekly_schedule if d.day_of_week == day),
                None,
            )
            if day_grid and not day_grid.is_open:
                reason = "Jour déclaré fermé"
            else:
                reason = "Hors plage d'ouverture déclarée"
        # Provenance par slot
        prov = _build_provenance(
            service="energy_orchestration.opening_hours_analysis._compute_slots",
            formula=(f"point conservé si kwh ≥ {_NOISE_KWH_THRESHOLD} kWh ET timestamp hors plages déclarées"),
            period=period,
            confidence=0.85,
            assumptions=[
                "timezone Europe/Paris",
                f"seuil anti-bruit kwh < {_NOISE_KWH_THRESHOLD} ignoré",
            ],
        )
        # Status temporaire — réajusté dans top_off_hours (par rapport au total)
        status: OffHoursStatus = "vigilance"
        slots.append(
            OffHoursSlot(
                day_of_week=day,
                label=_WEEKDAY_LABELS_FR[day],
                hour=local.hour,
                kwh=round(point.kwh, 2),
                kw_avg=round(point.kw_avg, 2) if point.kw_avg is not None else None,
                status=status,
                reason=reason,
                provenance=prov,
            )
        )
    return slots


def _compute_top_off_hours(slots: list[OffHoursSlot], total_off_hours_kwh: float) -> list[OffHoursSlot]:
    """Top 10 par kwh desc avec statut recalculé contre le total off."""
    if not slots:
        return []
    sorted_slots = sorted(slots, key=lambda s: s.kwh if s.kwh is not None else 0.0, reverse=True)[:_MAX_TOP_OFF_HOURS]
    out: list[OffHoursSlot] = []
    for s in sorted_slots:
        share = (s.kwh / total_off_hours_kwh * 100.0) if (total_off_hours_kwh > 0 and s.kwh is not None) else None
        status = _classify_off_hours_status(share)
        out.append(
            OffHoursSlot(
                day_of_week=s.day_of_week,
                label=s.label,
                hour=s.hour,
                kwh=s.kwh,
                kw_avg=s.kw_avg,
                status=status,
                reason=s.reason,
                provenance=s.provenance,
            )
        )
    return out


def _compute_kpis(
    series: list[EnergyLoadCurvePoint],
    slots: list[OffHoursSlot],
    schedule: OpeningSchedule,
    period: EnergyPeriod,
    scope: EnergyScope,
) -> tuple[OffHoursKpis, float]:
    """Construit les 4 KPI off-hours + retourne le total off pour ranking."""
    total_kwh = sum(p.kwh for p in series if p.kwh is not None and p.kwh >= _NOISE_KWH_THRESHOLD)
    off_hours_kwh = sum(s.kwh for s in slots if s.kwh is not None)
    weekend_off_hours_kwh = sum(s.kwh for s in slots if s.kwh is not None and s.day_of_week in (5, 6))
    share_pct = (off_hours_kwh / total_kwh * 100.0) if total_kwh > 0 else None

    # Night baseload : moyenne kw_avg sur les heures 0-5 (talon nuit)
    night_kw_values = [
        p.kw_avg for p in series if p.kw_avg is not None and _localize_to_paris(p.timestamp).hour in _NIGHT_HOURS
    ]
    night_baseload_kw = round(sum(night_kw_values) / len(night_kw_values), 2) if night_kw_values else None

    base_assumptions = [
        "timezone Europe/Paris",
        f"seuil anti-bruit kwh < {_NOISE_KWH_THRESHOLD} ignoré",
    ]

    state_off = "inactif" if off_hours_kwh <= 0 else "sain"
    if share_pct is not None:
        if share_pct >= 25:
            state_off = "critique"
        elif share_pct >= 10:
            state_off = "vigilance"

    kpis = OffHoursKpis(
        off_hours_kwh=_kpi(
            key="off_hours_kwh",
            label="Conso hors horaires",
            value=round(off_hours_kwh, 2) if off_hours_kwh else None,
            unit="kWh",
            state=state_off,
            service="energy_orchestration.opening_hours_analysis._compute_kpis",
            formula="Σ kwh des points hors plages d'ouverture déclarées",
            period=period,
            scope=scope,
            confidence=0.9 if schedule.source == "declared" else 0.0,
            assumptions=base_assumptions,
        ),
        off_hours_share_pct=_kpi(
            key="off_hours_share_pct",
            label="Part hors horaires",
            value=round(share_pct, 1) if share_pct is not None else None,
            unit="%",
            state=state_off,
            service="energy_orchestration.opening_hours_analysis._compute_kpis",
            formula="off_hours_kwh / total_kwh × 100",
            period=period,
            scope=scope,
            confidence=0.9 if total_kwh > 0 else 0.0,
            assumptions=base_assumptions,
        ),
        weekend_off_hours_kwh=_kpi(
            key="weekend_off_hours_kwh",
            label="Week-end hors horaires",
            value=round(weekend_off_hours_kwh, 2) if weekend_off_hours_kwh else None,
            unit="kWh",
            state="inactif" if weekend_off_hours_kwh <= 0 else "vigilance",
            service="energy_orchestration.opening_hours_analysis._compute_kpis",
            formula="Σ kwh des points hors horaires dont weekday in (5, 6)",
            period=period,
            scope=scope,
            confidence=0.85,
            assumptions=base_assumptions,
        ),
        night_baseload_kw=_kpi(
            key="night_baseload_kw",
            label="Talon nuit",
            value=night_baseload_kw,
            unit="kW",
            state="inactif" if night_baseload_kw is None else "sain",
            service="energy_orchestration.opening_hours_analysis._compute_kpis",
            formula="moyenne kw_avg des points dont heure ∈ [0;5]",
            period=period,
            scope=scope,
            confidence=0.85 if night_baseload_kw else 0.0,
            assumptions=[
                *base_assumptions,
                "talon nuit = fenêtre 00h-05h",
            ],
        ),
        # estimated_cost_eur : MVP P3.2 — null tant qu'aucun prix branché.
        # Doctrine « pas d'économie certaine » ; le coût restera marqué
        # « indicatif » dès intégration price/tarif.
        estimated_cost_eur=None,
    )
    return kpis, off_hours_kwh


def _compute_recommendations(
    kpis: OffHoursKpis,
    top_slots: list[OffHoursSlot],
    schedule: OpeningSchedule,
    period: EnergyPeriod,
) -> list[OffHoursRecommendation]:
    """Recommandations FR métier — jamais « économie certaine »."""
    recs: list[OffHoursRecommendation] = []
    share = kpis.off_hours_share_pct.value if kpis.off_hours_share_pct else None
    if schedule.source == "missing":
        # Pas de recommandation si on n'a pas de référentiel horaire.
        return recs

    if share is None or share == 0:
        recs.append(
            OffHoursRecommendation(
                title="Aucun signal hors horaires détecté",
                description=(
                    "La consommation suit fidèlement vos horaires déclarés sur la période. Maintenir la surveillance."
                ),
                severity="info",
                cta_label=None,
                cta_to=None,
                provenance=_build_provenance(
                    service="energy_orchestration.opening_hours_analysis._compute_recommendations",
                    formula="off_hours_share_pct nul ou indéterminé",
                    period=period,
                    confidence=0.7,
                    assumptions=["timezone Europe/Paris"],
                ),
            )
        )
        return recs

    severity = "info" if share < 10 else ("warning" if share < 25 else "critical")
    title = (
        "Part hors horaires sous contrôle"
        if severity == "info"
        else (
            "Vigilance sur la consommation hors horaires"
            if severity == "warning"
            else "Consommation hors horaires critique"
        )
    )
    description = (
        f"Sur la période, {round(share, 1)} % de la consommation a lieu en dehors "
        "des horaires d'ouverture déclarés. "
        + (
            "Analyser les talons nuit et week-end pour identifier les postes pilotables."
            if severity != "info"
            else "Quelques points résiduels — comportement attendu."
        )
    )
    recs.append(
        OffHoursRecommendation(
            title=title,
            description=description,
            severity=severity,
            cta_label="Créer une action d'analyse" if severity != "info" else None,
            cta_to="/action-center-v4" if severity != "info" else None,
            provenance=_build_provenance(
                service="energy_orchestration.opening_hours_analysis._compute_recommendations",
                formula="seuils share_pct < 10 (info), [10;25[ (warning), ≥ 25 (critical)",
                period=period,
                confidence=0.8,
                assumptions=[
                    "timezone Europe/Paris",
                    "aucune économie chiffrée — seulement signal pilotable",
                ],
            ),
        )
    )

    # Talon nuit dominant ?
    night_kw = kpis.night_baseload_kw.value if kpis.night_baseload_kw else None
    if night_kw and night_kw >= 1.0:
        recs.append(
            OffHoursRecommendation(
                title="Talon nuit non négligeable",
                description=(
                    f"Le talon nuit (00h-05h) atteint {night_kw} kW en moyenne. "
                    "Identifier les usages permanents (CVC, éclairage, IT) pilotables."
                ),
                severity="warning",
                cta_label="Créer une action d'analyse",
                cta_to="/action-center-v4",
                provenance=_build_provenance(
                    service="energy_orchestration.opening_hours_analysis._compute_recommendations",
                    formula="night_baseload_kw ≥ 1 kW",
                    period=period,
                    confidence=0.8,
                    assumptions=["talon nuit = fenêtre 00h-05h"],
                ),
            )
        )

    return recs


# ── Entrée principale ─────────────────────────────────────────────────


def build_off_hours_analysis(
    db: Session,
    *,
    scope_kind: str,
    scope_id: Optional[int],
    org_id: Optional[int],
    from_dt: datetime,
    to_dt: datetime,
    granularity: str = _DEFAULT_GRANULARITY,
) -> OffHoursAnalysisResponse:
    """Compose l'analyse hors horaires pour un scope × période.

    Lève `LoadCurveError` si la fenêtre / la granularité sont invalides.
    """
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

    schedule = _load_opening_schedule(db, scope, period)

    if schedule.source == "missing":
        return OffHoursAnalysisResponse(
            scope=scope,
            period=period,
            schedule=schedule,
            kpis=OffHoursKpis(),
            slots=[],
            top_off_hours=[],
            recommendations=[],
            warnings=[],
            empty_state="Horaires d'ouverture non renseignés pour ce site.",
            provenance=_build_provenance(
                service="energy_orchestration.opening_hours_analysis.build_off_hours_analysis",
                formula="schedule.source == 'missing' → réponse empty_state",
                period=period,
                confidence=0.0,
                assumptions=[
                    "timezone Europe/Paris",
                    "aucune analyse calculée — horaires absents",
                ],
            ),
        )

    series, warnings = _aggregate_series(db, scope, from_dt, to_dt, granularity)

    if not series:
        return OffHoursAnalysisResponse(
            scope=scope,
            period=period,
            schedule=schedule,
            kpis=OffHoursKpis(),
            slots=[],
            top_off_hours=[],
            recommendations=[],
            warnings=warnings,
            empty_state=("Aucune mesure de consommation sur la période — analyse hors horaires indisponible."),
            provenance=_build_provenance(
                service="energy_orchestration.opening_hours_analysis.build_off_hours_analysis",
                formula="série vide → réponse empty_state",
                period=period,
                confidence=0.0,
                assumptions=["timezone Europe/Paris"],
            ),
        )

    slots = _compute_slots(series, schedule, period)
    kpis, total_off_kwh = _compute_kpis(series, slots, schedule, period, scope)
    top_slots = _compute_top_off_hours(slots, total_off_kwh)
    recommendations = _compute_recommendations(kpis, top_slots, schedule, period)

    return OffHoursAnalysisResponse(
        scope=scope,
        period=period,
        schedule=schedule,
        kpis=kpis,
        slots=slots,
        top_off_hours=top_slots,
        recommendations=recommendations,
        warnings=warnings,
        empty_state=None,
        provenance=_build_provenance(
            service="energy_orchestration.opening_hours_analysis.build_off_hours_analysis",
            formula=(
                "comparaison point timeseries vs SiteOperatingSchedule ; agrégation off_hours + top + recommandations"
            ),
            period=period,
            confidence=0.9,
            assumptions=[
                "timezone Europe/Paris",
                f"granularité '{granularity}'",
                "aucune économie certaine — coût indicatif uniquement",
                f"seuil anti-bruit kwh < {_NOISE_KWH_THRESHOLD} ignoré",
            ],
        ),
    )
