"""
PROMEOS — Schémas Pydantic pour endpoints orchestration énergie.

Sprint Énergie P1.S2a (2026-05-29, brief P1).

Contrats API pour `/api/energy/synthesis` et `/api/energy/loadcurve`.
Chaque KPI exposé porte une `provenance` complète (source, service,
formula, period, confidence, assumptions) — obligation source-guard.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


KpiState = Literal["sain", "vigilance", "critique", "inactif"]
KpiUnit = Literal[
    "kWh",
    "MWh",
    "GWh",
    "€",
    "k€",
    "M€",
    "€/MWh",
    "€/kWh",
    "kW",
    "kVA",
    "kgCO₂eq",
    "tCO₂eq",
    "/100",
    "%",
    "count",
    "n/N",
]

ScopeKind = Literal["org", "portfolio", "site", "meter"]
PeriodLabel = Literal["7d", "30d", "90d", "12m", "ytd", "custom"]
CompareKind = Literal["none", "n-1", "baseline", "contract"]
Granularity = Literal["15min", "30min", "hour", "day", "week", "month", "year"]


class EnergyScope(BaseModel):
    """Périmètre d'application d'un payload énergétique."""

    kind: ScopeKind
    id: Optional[int | str] = None
    label: Optional[str] = None
    sites_count: Optional[int] = None
    org_id: Optional[int] = None


class EnergyPeriod(BaseModel):
    """Période temporelle d'analyse."""

    label: PeriodLabel = "30d"
    start: datetime
    end: datetime
    days: int = Field(..., ge=1, description="Nombre de jours dans la période")
    timezone: str = "Europe/Paris"


class EnergyProvenance(BaseModel):
    """Traçabilité d'un KPI ou d'un payload — obligation doctrine PROMEOS."""

    model_config = ConfigDict(extra="allow")

    source: str = Field(..., description="Source des données (ex: 'Enedis SGE', 'PROMEOS demo_seed')")
    service: str = Field(..., description="Service SoT backend (chemin module)")
    formula: str = Field(..., description="Formule de calcul (lecture humaine)")
    period: str = Field(..., description="Période ISO ou label")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confiance 0..1")
    assumptions: list[str] = Field(default_factory=list)
    doctrine_ref: Optional[str] = None


class EnergyKpi(BaseModel):
    """KPI normalisé pour exposition FE."""

    key: str
    label: str
    value: float | int | str | None
    unit: KpiUnit
    state: KpiState = "inactif"
    period: EnergyPeriod
    scope: EnergyScope
    provenance: EnergyProvenance
    delta_pct: Optional[float] = Field(None, description="Variation vs compare (si compare != none)")
    compare_ref: Optional[CompareKind] = None
    sub_metrics: dict[str, Any] = Field(default_factory=dict, description="Détails contextuels")


class EnergyRecommendation(BaseModel):
    """Action recommandée associée à une analyse."""

    id: str
    title: str
    description: str
    severity: Literal["info", "warning", "critical"] = "info"
    impact_kwh: Optional[float] = None
    impact_eur: Optional[float] = None
    related_action_id: Optional[int] = None  # lien Centre d'Action V4
    provenance: EnergyProvenance


# ── /api/energy/synthesis ──────────────────────────────────────────────


class EnergySynthesisResponse(BaseModel):
    """Payload réponse pour vue Synthèse 30 secondes."""

    scope: EnergyScope
    period: EnergyPeriod
    compare: CompareKind = "none"
    kpis: dict[str, EnergyKpi] = Field(..., description="Dictionnaire { kpi_key: EnergyKpi } — 10 KPI minimum")
    recommendations: list[EnergyRecommendation] = Field(default_factory=list)
    narrative: Optional[str] = Field(None, description="Briefing 2-3 phrases pour storytelling Sol §5")
    warnings: list[str] = Field(default_factory=list)
    provenance: EnergyProvenance


# ── /api/energy/loadcurve ──────────────────────────────────────────────


class LoadCurveQualityStatus(BaseModel):
    """Métadonnées qualité par point de la courbe."""

    status: Literal["measured", "estimated", "missing", "corrected"] = "measured"
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class EnergyLoadCurvePoint(BaseModel):
    """Un point de courbe de charge."""

    timestamp: datetime
    kwh: Optional[float] = None
    kw_avg: Optional[float] = None
    cost_eur: Optional[float] = None
    quality_status: Literal["measured", "estimated", "missing", "corrected"] = "measured"


class EnergyLoadCurveKpis(BaseModel):
    """KPI agrégés sur la courbe complète."""

    total_kwh: Optional[EnergyKpi] = None
    peak_kw: Optional[EnergyKpi] = None
    baseload_kw: Optional[EnergyKpi] = None
    average_kw: Optional[EnergyKpi] = None


class EnergyLoadCurveResponse(BaseModel):
    """Payload réponse pour vue Courbe de charge."""

    scope: EnergyScope
    period: EnergyPeriod
    granularity: Granularity
    compare: CompareKind = "none"
    series: list[EnergyLoadCurvePoint] = Field(default_factory=list)
    series_compare: list[EnergyLoadCurvePoint] = Field(default_factory=list)
    kpis: EnergyLoadCurveKpis = Field(default_factory=EnergyLoadCurveKpis)
    provenance: EnergyProvenance
    warnings: list[str] = Field(default_factory=list)
    empty_state: Optional[str] = None


# ── /api/energy/week-profile ───────────────────────────────────────────


CellStatus = Literal["normal", "vigilance", "critique", "missing"]


class WeekProfileCell(BaseModel):
    """Une cellule de la heatmap semaine type (7 × 24)."""

    day_of_week: int = Field(..., ge=0, le=6, description="0=Lun, 6=Dim")
    hour: int = Field(..., ge=0, le=23)
    kwh: Optional[float] = None
    kw_avg: Optional[float] = None
    status: CellStatus = "missing"
    quality_status: Literal["measured", "estimated", "missing"] = "measured"


class WeekProfileKpis(BaseModel):
    """KPI agrégés de la semaine type."""

    highest_day: Optional[EnergyKpi] = None
    highest_hour: Optional[EnergyKpi] = None
    night_baseload_kw: Optional[EnergyKpi] = None
    weekend_consumption_pct: Optional[EnergyKpi] = None


class EnergyWeekProfileResponse(BaseModel):
    """Payload réponse pour vue Semaine type — heatmap 7×24."""

    scope: EnergyScope
    period: EnergyPeriod
    matrix: list[WeekProfileCell] = Field(default_factory=list)
    kpis: WeekProfileKpis = Field(default_factory=WeekProfileKpis)
    provenance: EnergyProvenance
    warnings: list[str] = Field(default_factory=list)
    empty_state: Optional[str] = None


# ── Erreurs standardisées /api/energy/* ────────────────────────────────


class EnergyErrorPayload(BaseModel):
    """Erreur standardisée pour endpoints /api/energy/*.

    Sprint P1.S2b — uniformise code + message + hint + correlation_id
    (cf. middleware energy_orchestration ou UUID généré côté handler).
    """

    code: str = Field(..., description="Code erreur stable (ex: ENERGY_GRANULARITY_TOO_FINE)")
    message: str
    hint: Optional[str] = None
    correlation_id: str = Field(..., description="UUID corrélation pour logs / support")
