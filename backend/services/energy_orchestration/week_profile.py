"""
PROMEOS — Service orchestration Semaine type (Sprint P1.S2b).

Compose les SoT existants pour exposer une heatmap 7 × 24 cellules
représentant le profil de consommation hebdomadaire moyen sur une
fenêtre temporelle.

Doctrine :
- Timezone Europe/Paris stricte (cf. cdc_service).
- Pas de calcul métier FE : matrice + KPI + provenance pré-calculés.
- État cellule `status ∈ {normal, vigilance, critique, missing}` basé
  sur écart-type vs moyenne hebdomadaire (Tukey 3·IQR si dispo).
- KPI agrégés : highest_day, highest_hour, night_baseload_kw,
  weekend_consumption_pct.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session

from schemas.energy_orchestration import (
    EnergyKpi,
    EnergyPeriod,
    EnergyProvenance,
    EnergyScope,
    EnergyWeekProfileResponse,
    WeekProfileCell,
    WeekProfileKpis,
)
from services.energy_orchestration.synthesis import _build_provenance


TZ_PARIS = ZoneInfo("Europe/Paris")

# Jours de la semaine — convention Lun=0..Dim=6 (Python weekday()).
DAY_LABELS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

# Heures considérées "nuit" pour le talon (doctrine pilotage des usages).
NIGHT_HOURS = range(0, 6)
# Weekend = samedi + dimanche (Python weekday 5, 6).
WEEKEND_DAYS = {5, 6}


class WeekProfileError(Exception):
    """Erreur fonctionnelle week-profile (à mapper en HTTP 400)."""

    def __init__(self, message: str, hint: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


def build_week_profile(
    db: Session,
    *,
    scope_kind: str,
    scope_id: Optional[int],
    org_id: Optional[int],
    days: int = 90,
    now: Optional[datetime] = None,
) -> EnergyWeekProfileResponse:
    """Compose la semaine type 7×24 sur une fenêtre temporelle.

    Args:
        db : session SQLAlchemy.
        scope_kind : 'site' ou 'meter' (org/portfolio non supportés MVP).
        scope_id : id du site / compteur.
        org_id : id organisation pour scope_utils.
        days : fenêtre d'agrégation (défaut 90j).
        now : instant de référence (reproductibilité tests).

    Returns:
        EnergyWeekProfileResponse avec matrix 7×24 (potentiellement
        partielle si pas de données pour certaines cellules) + 4 KPI +
        provenance.

    Raises:
        WeekProfileError : scope invalide (cf. router → HTTP 400).
    """
    if scope_kind not in ("site", "meter"):
        raise WeekProfileError(
            f"scope_kind '{scope_kind}' non supporté pour week-profile",
            hint="utiliser scope='site' ou scope='meter' (org/portfolio à venir)",
        )
    if scope_id is None:
        raise WeekProfileError(
            "scope_id obligatoire pour week-profile",
            hint=f"fournir scope_id={scope_kind}_id pour cibler le profil",
        )

    if days < 7:
        raise WeekProfileError(
            f"days={days} insuffisant pour calculer une semaine type",
            hint="utiliser days >= 7 (idéalement 30+)",
        )

    if now is None:
        now = datetime.now(TZ_PARIS)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=TZ_PARIS)

    start = now - timedelta(days=days)
    period = EnergyPeriod(
        label="custom",
        start=start,
        end=now,
        days=days,
        timezone="Europe/Paris",
    )
    scope = EnergyScope(
        kind=scope_kind,  # type: ignore[arg-type]
        id=scope_id,
        org_id=org_id,
    )

    matrix, warnings = _aggregate_week_matrix(db, scope, start, now)
    kpis = _compute_week_kpis(matrix, scope, period)

    empty_state = None
    if not matrix or all(c.kwh is None for c in matrix):
        empty_state = (
            "Données insuffisantes pour afficher la semaine type. Élargir la fenêtre ou vérifier la connexion compteur."
        )

    provenance = _build_provenance(
        service="energy_orchestration.week_profile.build_week_profile",
        formula=(
            "Σ MeterReading.value_kwh groupé par (weekday, hour) sur la fenêtre, "
            "/ nb_occurrences pour moyenne hebdomadaire"
        ),
        period=period,
        confidence=0.85 if matrix else 0.0,
        assumptions=[
            "timezone Europe/Paris",
            "weekday=0=Lun .. 6=Dim",
            "fenêtre minimale 7 jours",
            f"days agrégation = {days}",
        ],
    )

    return EnergyWeekProfileResponse(
        scope=scope,
        period=period,
        matrix=matrix,
        kpis=kpis,
        provenance=provenance,
        warnings=warnings,
        empty_state=empty_state,
    )


def _aggregate_week_matrix(
    db: Session,
    scope: EnergyScope,
    start: datetime,
    end: datetime,
) -> tuple[list[WeekProfileCell], list[str]]:
    """Agrège MeterReading en 168 cellules (7 jours × 24 heures)."""
    warnings: list[str] = []
    cells: list[WeekProfileCell] = []

    try:
        from models import MeterReading

        # Récupération des meters pour le scope.
        meter_ids: list[int] = []
        if scope.kind == "meter" and scope.id is not None:
            meter_ids = [int(scope.id)]
        elif scope.kind == "site" and scope.id is not None:
            from models import Meter

            meter_q = db.query(Meter.id).filter(Meter.site_id == int(scope.id), Meter.is_active.is_(True))
            # Exclure sous-compteurs si modèle le supporte.
            if hasattr(Meter, "parent_meter_id"):
                meter_q = meter_q.filter(Meter.parent_meter_id.is_(None))
            meter_ids = [m.id for m in meter_q.all()]

        if not meter_ids:
            warnings.append("Aucun compteur actif sur ce scope.")
            return cells, warnings

        # Group by (weekday, hour) — SQLite-friendly via strftime.
        # Note : SQLAlchemy func.strftime fonctionne sur SQLite ; pour
        # Postgres on utiliserait extract('dow', ...).
        rows = (
            db.query(
                func.strftime("%w", MeterReading.timestamp).label("dow"),
                func.strftime("%H", MeterReading.timestamp).label("hour"),
                func.avg(MeterReading.value_kwh).label("avg_kwh"),
                func.count(MeterReading.id).label("n"),
            )
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.timestamp >= start.replace(tzinfo=None),
                MeterReading.timestamp < end.replace(tzinfo=None),
            )
            .group_by("dow", "hour")
            .all()
        )

        if not rows:
            warnings.append("Aucune lecture sur la fenêtre demandée.")
            return cells, warnings

        # SQLite strftime('%w', …) → 0=Dim .. 6=Sam. On normalise vers
        # convention Python weekday() : 0=Lun .. 6=Dim.
        # Mapping : sqlite_dow → python_weekday = (sqlite_dow - 1) % 7
        # (Dim 0→6, Lun 1→0, …, Sam 6→5).
        agg: dict[tuple[int, int], tuple[float, int]] = {}
        for r in rows:
            sqlite_dow = int(r.dow)
            python_dow = (sqlite_dow - 1) % 7
            hour = int(r.hour)
            agg[(python_dow, hour)] = (float(r.avg_kwh or 0.0), int(r.n or 0))

        # Construction matrix 7×24 (avec cellules missing si pas de données).
        for dow in range(7):
            for h in range(24):
                if (dow, h) in agg:
                    avg_kwh, n = agg[(dow, h)]
                    cells.append(
                        WeekProfileCell(
                            day_of_week=dow,
                            hour=h,
                            kwh=round(avg_kwh, 3),
                            kw_avg=round(avg_kwh, 3),  # 1 kWh sur 1h = 1 kW moyen
                            status=_classify_status(avg_kwh, agg),
                            quality_status="measured",
                        )
                    )
                else:
                    cells.append(
                        WeekProfileCell(
                            day_of_week=dow,
                            hour=h,
                            kwh=None,
                            kw_avg=None,
                            status="missing",
                            quality_status="missing",
                        )
                    )
    except Exception as exc:  # noqa: BLE001 — robustesse MVP
        warnings.append(f"Erreur agrégation matrix: {str(exc)[:120]}")

    return cells, warnings


def _classify_status(value: float, agg: dict[tuple[int, int], tuple[float, int]]) -> str:
    """Classifie une cellule {normal|vigilance|critique} via Tukey 3·IQR.

    Méthode : on calcule Q1/Q3 sur l'ensemble des cellules non-nulles
    et on flag celles au-dessus de Q3 + 1.5·IQR (vigilance) ou
    Q3 + 3·IQR (critique).
    """
    try:
        from services.consumption_granularity_service import compute_quantiles

        all_values = [v for (v, _n) in agg.values() if v > 0]
        if len(all_values) < 5:
            return "normal"
        qs = compute_quantiles(all_values, qs=[0.25, 0.75])
        q1 = qs.get("p25")
        q3 = qs.get("p75")
        iqr = qs.get("iqr") or 0.0
        if q1 is None or q3 is None or iqr <= 0:
            return "normal"
        upper_vigilance = q3 + 1.5 * iqr
        upper_critique = q3 + 3 * iqr
        if value > upper_critique:
            return "critique"
        if value > upper_vigilance:
            return "vigilance"
        return "normal"
    except Exception:  # noqa: BLE001
        return "normal"


def _compute_week_kpis(
    matrix: list[WeekProfileCell],
    scope: EnergyScope,
    period: EnergyPeriod,
) -> WeekProfileKpis:
    """Calcule les 4 KPI agrégés de la semaine type."""

    def _kpi(key: str, label: str, val, unit: str) -> EnergyKpi:
        return EnergyKpi(
            key=key,
            label=label,
            value=val,
            unit=unit,  # type: ignore[arg-type]
            state="inactif" if val is None else "sain",
            period=period,
            scope=scope,
            provenance=_build_provenance(
                service=f"energy_orchestration.week_profile._compute_week_kpis ({key})",
                formula={
                    "highest_day": "jour avec Σ(kwh) max sur la matrix",
                    "highest_hour": "heure (Lun-Dim) avec kwh max",
                    "night_baseload_kw": "moyenne kwh 0h-5h sur tous les jours",
                    "weekend_consumption_pct": "Σ kwh weekend / Σ kwh total × 100",
                }[key],
                period=period,
                confidence=0.9 if val is not None else 0.0,
                assumptions=["weekday=0=Lun..6=Dim", "weekend=5,6"],
            ),
        )

    # Agrégation par jour
    by_day: dict[int, float] = {d: 0.0 for d in range(7)}
    by_dh: dict[tuple[int, int], float] = {}
    night_values: list[float] = []
    weekend_total = 0.0
    total = 0.0

    for c in matrix:
        if c.kwh is None:
            continue
        by_day[c.day_of_week] += c.kwh
        by_dh[(c.day_of_week, c.hour)] = c.kwh
        total += c.kwh
        if c.hour in NIGHT_HOURS:
            night_values.append(c.kwh)
        if c.day_of_week in WEEKEND_DAYS:
            weekend_total += c.kwh

    # Highest day
    if any(v > 0 for v in by_day.values()):
        best_day = max(by_day.items(), key=lambda kv: kv[1])
        highest_day_label = f"{DAY_LABELS[best_day[0]]} ({round(best_day[1], 2)} kWh)"
        highest_day_kpi = _kpi("highest_day", "Jour le plus consommateur", highest_day_label, "kWh")
    else:
        highest_day_kpi = _kpi("highest_day", "Jour le plus consommateur", None, "kWh")

    # Highest hour
    if by_dh:
        (best_dh, best_kwh) = max(by_dh.items(), key=lambda kv: kv[1])
        highest_hour_label = f"{DAY_LABELS[best_dh[0]]} {best_dh[1]:02d}h ({round(best_kwh, 2)} kWh)"
        highest_hour_kpi = _kpi("highest_hour", "Heure la plus consommatrice", highest_hour_label, "kWh")
    else:
        highest_hour_kpi = _kpi("highest_hour", "Heure la plus consommatrice", None, "kWh")

    # Night baseload kW
    if night_values:
        night_avg = round(sum(night_values) / len(night_values), 3)
        night_kpi = _kpi("night_baseload_kw", "Talon nuit (0h-5h)", night_avg, "kW")
    else:
        night_kpi = _kpi("night_baseload_kw", "Talon nuit (0h-5h)", None, "kW")

    # Weekend consumption %
    if total > 0:
        weekend_pct = round(weekend_total / total * 100, 1)
        weekend_kpi = _kpi(
            "weekend_consumption_pct",
            "Part conso week-end",
            weekend_pct,
            "%",
        )
    else:
        weekend_kpi = _kpi("weekend_consumption_pct", "Part conso week-end", None, "%")

    return WeekProfileKpis(
        highest_day=highest_day_kpi,
        highest_hour=highest_hour_kpi,
        night_baseload_kw=night_kpi,
        weekend_consumption_pct=weekend_kpi,
    )
