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


# ── Sprint Énergie P3.1 : top_peaks + weekday_overlay ────────────────


class EnergyTopPeak(BaseModel):
    """Un pic de puissance classé sur la période (P3.1)."""

    rank: int = Field(..., ge=1, description="1 = pic le plus critique")
    timestamp: datetime
    kwh: Optional[float] = None
    kw_avg: Optional[float] = None
    period_label: str = Field(..., description="ex: 'Mardi 14h'")
    context: Optional[str] = Field(None, description="ex: 'Pic récurrent sur plage active'")
    recommended_action: str = Field(..., description="action conseillée FR backend")
    quality_status: Literal["measured", "estimated", "missing", "corrected"] = "measured"
    provenance: EnergyProvenance


class EnergyWeekdayPoint(BaseModel):
    """Un point horaire d'une courbe moyenne par jour de semaine (P3.1)."""

    hour: int = Field(..., ge=0, le=23)
    avg_kwh: Optional[float] = None
    avg_kw: Optional[float] = None
    n_points: int = Field(0, ge=0, description="nombre de jours agrégés pour ce point")
    quality_status: Literal["measured", "estimated", "missing"] = "measured"


class EnergyWeekdayCurve(BaseModel):
    """Courbe moyenne pour un jour de semaine (P3.1) : 24 points horaires."""

    day_of_week: int = Field(..., ge=0, le=6, description="0=Lun, 6=Dim")
    label: str = Field(..., description="ex: 'Lundi'")
    points: list[EnergyWeekdayPoint] = Field(default_factory=list)
    provenance: EnergyProvenance


WeekdayState = Literal["sain", "vigilance", "critique", "inactif"]


class EnergyWeekdayDecomposition(BaseModel):
    """Décomposition de la consommation par jour de semaine (P3.1)."""

    day_of_week: int = Field(..., ge=0, le=6)
    label: str
    total_kwh: Optional[float] = None
    avg_kwh_per_day: Optional[float] = None
    share_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    n_days: int = Field(0, ge=0)
    state: WeekdayState = "inactif"
    provenance: EnergyProvenance


class EnergyWeekdayWeekendComparison(BaseModel):
    """Comparaison jours ouvrés vs week-end (P3.1)."""

    weekday_kwh: Optional[float] = None
    weekend_kwh: Optional[float] = None
    weekend_share_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    provenance: EnergyProvenance


class EnergyLoadCurveResponse(BaseModel):
    """Payload réponse pour vue Courbe de charge."""

    scope: EnergyScope
    period: EnergyPeriod
    granularity: Granularity
    compare: CompareKind = "none"
    series: list[EnergyLoadCurvePoint] = Field(default_factory=list)
    series_compare: list[EnergyLoadCurvePoint] = Field(default_factory=list)
    kpis: EnergyLoadCurveKpis = Field(default_factory=EnergyLoadCurveKpis)
    # Sprint Énergie P3.1 — pics de puissance + profil moyen par jour
    top_peaks: list[EnergyTopPeak] = Field(default_factory=list)
    weekday_overlay: list[EnergyWeekdayCurve] = Field(default_factory=list)
    weekday_decomposition: list[EnergyWeekdayDecomposition] = Field(default_factory=list)
    weekday_weekend_comparison: Optional[EnergyWeekdayWeekendComparison] = None
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


# ── /api/energy/cost-vs-contract ───────────────────────────────────────


ContractType = Literal["fixed", "indexed", "mixed", "ths", "unknown"]
RiskLevel = Literal["faible", "modéré", "élevé"]
ScenarioStatus = Literal["current", "simulation"]
PriceComponentKey = Literal["supply", "network", "taxes", "capacity", "other"]


class EnergyContractSummary(BaseModel):
    """Résumé du contrat actif d'un site (ContratCadre v2 + Annexe)."""

    contract_id: Optional[str] = None
    supplier_name: Optional[str] = None
    contract_type: ContractType = "unknown"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    subscribed_power_kva: Optional[float] = None
    provenance: EnergyProvenance


class EnergyPriceComponent(BaseModel):
    """Une composante de prix de la facture (fourniture / TURPE / taxes / capacité)."""

    key: PriceComponentKey
    label: str
    amount_eur: Optional[float] = None
    price_eur_mwh: Optional[float] = None
    share_pct: Optional[float] = Field(None, ge=0.0, le=100.0)
    provenance: EnergyProvenance


class EnergyContractScenario(BaseModel):
    """Un scénario contractuel simulé (cdc_contract_simulator)."""

    key: str = Field(..., description="ex: fixed_12m, indexed_spot, mixed_50_50, ths")
    label: str
    estimated_cost_eur: Optional[float] = None
    weighted_price_eur_mwh: Optional[float] = None
    risk_level: RiskLevel = "modéré"
    status: ScenarioStatus = "simulation"
    delta_vs_current_eur: Optional[float] = Field(
        None, description="Différentiel coût annuel vs contrat actuel (signe négatif = économie)"
    )
    provenance: EnergyProvenance
    assumptions: list[str] = Field(default_factory=list)


class EnergyContractRecommendation(BaseModel):
    """Recommandation contractuelle non-engageante issue de la simulation.

    Doctrine : `warning` OBLIGATOIRE — toute reco PROMEOS est indicative,
    aucune économie n'est promise comme certaine.
    """

    recommended_scenario: Optional[str] = Field(None, description="Clé du scénario recommandé (cf. scenarios[].key)")
    message: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    warning: str = "Simulation indicative — ne constitue pas une promesse d'économie."
    provenance: EnergyProvenance


class EnergyCostAssumptions(BaseModel):
    """Hypothèses globales utilisées dans la simulation coût/contrat."""

    spot_price_source: Optional[str] = None
    spot_year_reference: Optional[int] = None
    turpe_version: Optional[str] = None
    fallback_price_used: bool = False
    notes: list[str] = Field(default_factory=list)


class EnergyCostContractKpis(BaseModel):
    """KPI agrégés Coût & contrat."""

    total_cost_eur: Optional[EnergyKpi] = None
    consumption_kwh: Optional[EnergyKpi] = None
    weighted_price_eur_mwh: Optional[EnergyKpi] = None
    supply_cost_eur: Optional[EnergyKpi] = None
    network_cost_eur: Optional[EnergyKpi] = None
    taxes_cost_eur: Optional[EnergyKpi] = None


class EnergyCostContractResponse(BaseModel):
    """Payload réponse `/api/energy/cost-vs-contract`."""

    scope: EnergyScope
    period: EnergyPeriod
    active_contract: Optional[EnergyContractSummary] = None
    kpis: EnergyCostContractKpis = Field(default_factory=EnergyCostContractKpis)
    price_decomposition: list[EnergyPriceComponent] = Field(default_factory=list)
    scenarios: list[EnergyContractScenario] = Field(default_factory=list)
    recommendation: Optional[EnergyContractRecommendation] = None
    assumptions: EnergyCostAssumptions = Field(default_factory=EnergyCostAssumptions)
    warnings: list[str] = Field(default_factory=list)
    empty_state: Optional[str] = None
    provenance: EnergyProvenance


# ── /api/energy/market-exposure ────────────────────────────────────────


MarketType = Literal["day_ahead", "intraday", "future_baseload", "future_peakload"]
MarketZone = Literal["FR", "DE_LU", "BE", "ES", "NL", "GB", "CH", "IT_NORTH"]
ExposureScoreState = Literal["sain", "vigilance", "critique", "inactif"]
FavorableHourReason = Literal["prix bas", "prix négatif", "heure solaire"]


class EnergyMarketContext(BaseModel):
    """Contexte marché du payload (type, zone, source)."""

    type: MarketType = "day_ahead"
    zone: MarketZone = "FR"
    source: str = Field(..., description="Source données prix (ex: 'MktPrice canonique')")
    price_unit: str = "€/MWh"
    provenance: EnergyProvenance


class EnergyMarketExposurePoint(BaseModel):
    """Un point de la série superposée consommation × prix spot."""

    timestamp: datetime
    kwh: Optional[float] = None
    kw_avg: Optional[float] = None
    spot_price_eur_mwh: Optional[float] = None
    spot_cost_eur: Optional[float] = None
    is_top_expensive_hour: bool = False
    is_negative_price: bool = False
    quality_status: Literal["measured", "estimated", "missing", "corrected"] = "measured"


class EnergyExpensiveHour(BaseModel):
    """Une heure parmi les top 10% les plus coûteuses."""

    timestamp: datetime
    spot_price_eur_mwh: float
    kwh: float
    cost_eur: float
    rank: int = Field(..., ge=1, description="1 = la plus coûteuse")
    recommended_action: str
    provenance: EnergyProvenance


class EnergyFavorableHour(BaseModel):
    """Une heure favorable au déplacement (prix bas / négatif / solaire)."""

    timestamp: datetime
    spot_price_eur_mwh: float
    kwh: Optional[float] = None
    reason: FavorableHourReason
    provenance: EnergyProvenance


class EnergyBaseloadComparison(BaseModel):
    """Comparaison profil réel vs ruban baseload théorique."""

    real_profile_cost_eur: Optional[float] = None
    baseload_cost_eur: Optional[float] = None
    delta_eur: Optional[float] = Field(
        None, description="real_profile_cost_eur - baseload_cost_eur (>0 = profil plus coûteux)"
    )
    delta_eur_mwh: Optional[float] = None
    formula: str = "comparaison coût spot pondéré réel vs consommation plate équivalente"
    provenance: EnergyProvenance


class EnergyDisplacementSimulation(BaseModel):
    """Simulation indicative d'un déplacement de charge.

    Doctrine : `warning` obligatoire — toute simulation est indicative,
    aucune économie n'est promise comme certaine.
    """

    label: str = "Déplacement indicatif"
    flexible_share_pct: float = Field(20.0, ge=0.0, le=100.0)
    estimated_delta_eur: Optional[float] = None
    warning: str = "Simulation indicative — ne constitue pas une promesse d'économie."
    provenance: EnergyProvenance


class EnergyMarketExposureKpis(BaseModel):
    """KPI agrégés marché & exposition."""

    spot_cost_theoretical_eur: Optional[EnergyKpi] = None
    spot_avg_simple_eur_mwh: Optional[EnergyKpi] = None
    spot_avg_weighted_eur_mwh: Optional[EnergyKpi] = None
    baseload_cost_eur: Optional[EnergyKpi] = None
    delta_vs_baseload_eur: Optional[EnergyKpi] = None
    top_10pct_expensive_hours_cost_pct: Optional[EnergyKpi] = None
    negative_price_consumption_pct: Optional[EnergyKpi] = None
    exposure_score: Optional[EnergyKpi] = None


class EnergyMarketExposureResponse(BaseModel):
    """Payload réponse `/api/energy/market-exposure`."""

    scope: EnergyScope
    period: EnergyPeriod
    market: EnergyMarketContext
    kpis: EnergyMarketExposureKpis = Field(default_factory=EnergyMarketExposureKpis)
    series: list[EnergyMarketExposurePoint] = Field(default_factory=list)
    top_expensive_hours: list[EnergyExpensiveHour] = Field(default_factory=list)
    favorable_hours: list[EnergyFavorableHour] = Field(default_factory=list)
    baseload_comparison: Optional[EnergyBaseloadComparison] = None
    simulation: Optional[EnergyDisplacementSimulation] = None
    warnings: list[str] = Field(default_factory=list)
    empty_state: Optional[str] = None
    provenance: EnergyProvenance


# ── Sprint Énergie P3.2 : /api/energy/off-hours-analysis ──────────────


OpeningSource = Literal["declared", "default", "missing"]
OffHoursStatus = Literal["sain", "vigilance", "critique"]


class OpeningTimeRange(BaseModel):
    """Plage horaire d'ouverture (HH:MM → HH:MM, tz Europe/Paris)."""

    start_time: str = Field(..., description="Heure début (HH:MM)")
    end_time: str = Field(..., description="Heure fin (HH:MM)")


class OpeningDaySchedule(BaseModel):
    """Grille d'ouverture d'un jour de semaine (0=Lundi, 6=Dimanche)."""

    day_of_week: int = Field(..., ge=0, le=6)
    label: str = Field(..., description="Libellé FR (Lundi, Mardi…)")
    is_open: bool
    ranges: list[OpeningTimeRange] = Field(default_factory=list)


class OpeningSchedule(BaseModel):
    """Horaires d'ouverture déclarés du site.

    `source = "missing"` → aucun horaire renseigné → `weekly_schedule` vide,
    consommateur doit afficher empty_state explicite.
    """

    timezone: str = Field(default="Europe/Paris")
    source: OpeningSource = Field(default="missing")
    weekly_schedule: list[OpeningDaySchedule] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list, description="Jours fériés / fermetures (YYYY-MM-DD)")
    provenance: EnergyProvenance


class OffHoursSlot(BaseModel):
    """Créneau hors horaires détecté (jour×heure, conso, status, raison)."""

    day_of_week: int = Field(..., ge=0, le=6)
    label: str
    hour: int = Field(..., ge=0, le=23)
    kwh: Optional[float] = None
    kw_avg: Optional[float] = None
    status: OffHoursStatus
    reason: str = Field(..., description="Pourquoi ce créneau est hors horaires (FR métier)")
    provenance: EnergyProvenance


class OffHoursKpis(BaseModel):
    """KPI agrégés analyse hors horaires."""

    off_hours_kwh: Optional[EnergyKpi] = None
    off_hours_share_pct: Optional[EnergyKpi] = None
    weekend_off_hours_kwh: Optional[EnergyKpi] = None
    night_baseload_kw: Optional[EnergyKpi] = None
    estimated_cost_eur: Optional[EnergyKpi] = Field(
        default=None,
        description="Coût indicatif ; null si aucun prix disponible (jamais inventé)",
    )


class OffHoursRecommendation(BaseModel):
    """Recommandation FR métier générée backend (jamais frontend)."""

    title: str
    description: str
    severity: Literal["info", "warning", "critical"] = "info"
    cta_label: Optional[str] = None
    cta_to: Optional[str] = None
    provenance: EnergyProvenance


class OffHoursAnalysisResponse(BaseModel):
    """Payload réponse `/api/energy/off-hours-analysis`.

    Doctrine P3.2 :
    - timezone Europe/Paris stricte
    - aucune économie certaine — coût toujours indicatif
    - empty_state explicite si horaires manquants ou série vide
    - provenance racine + provenance par KPI + provenance par slot
    """

    scope: EnergyScope
    period: EnergyPeriod
    schedule: OpeningSchedule
    kpis: OffHoursKpis = Field(default_factory=OffHoursKpis)
    slots: list[OffHoursSlot] = Field(default_factory=list)
    top_off_hours: list[OffHoursSlot] = Field(default_factory=list)
    recommendations: list[OffHoursRecommendation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    empty_state: Optional[str] = None
    provenance: EnergyProvenance


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
