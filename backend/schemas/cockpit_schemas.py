"""
PROMEOS — Schémas Pydantic pour les routes cockpit.

Couvre :
  - GET /api/cockpit (executive dashboard)
  - GET /api/cockpit/executive-v2 (V2 hero)
  - GET /api/portefeuilles
  - GET /api/kpi-catalog
  - GET /api/cockpit/benchmark
  - GET /api/cockpit/trajectory
  - GET /api/cockpit/conso-month
  - GET /api/cockpit/co2
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Cockpit Executive ────────────────────────────────────────────────────


class RisqueBreakdown(BaseModel):
    reglementaire_eur: float = 0
    billing_anomalies_eur: float = 0
    contract_risk_eur: float = 0
    total_eur: float = 0


class CockpitStats(BaseModel):
    total_sites: int = 0
    sites_actifs: int = 0
    avancement_decret_pct: float = 0
    risque_financier_euro: float = 0
    sites_tertiaire_ko: int = 0
    sites_bacs_ko: int = 0
    alertes_actives: int = 0
    compliance_score: Optional[float] = None
    compliance_confidence: Optional[str] = None
    compliance_source: Optional[str] = None
    compliance_computed_at: Optional[str] = None
    sites_evaluated: int = 0
    risque_breakdown: RisqueBreakdown = Field(default_factory=RisqueBreakdown)
    conso_kwh_total: float = 0
    conso_declared_kwh: float = 0
    conso_confidence: Optional[str] = None
    conso_sites_with_data: int = 0
    conso_source: Optional[str] = None
    contrats_expirant_90j: int = 0


class OrgSummary(BaseModel):
    nom: str
    type_client: Optional[str] = None


class ActionCenterSummary(BaseModel):
    total_issues: int = 0
    critical: int = 0
    high: int = 0
    domains: dict[str, Any] = Field(default_factory=dict)


class CockpitResponse(BaseModel):
    """GET /api/cockpit — Executive dashboard."""

    organisation: OrgSummary
    stats: CockpitStats
    kpi_details: list[dict[str, Any]] = Field(default_factory=list)
    action_center: ActionCenterSummary = Field(default_factory=ActionCenterSummary)
    echeance_prochaine: Optional[str] = None


# ─── Portefeuilles ─────────────────────────────────────────────────────────


class PortefeuilleItem(BaseModel):
    id: int
    nom: str
    description: Optional[str] = None
    nb_sites: int = 0


class PortefeuillesResponse(BaseModel):
    """GET /api/portefeuilles."""

    portefeuilles: list[PortefeuilleItem]
    total: int


# ─── KPI Catalog ───────────────────────────────────────────────────────────


class KpiCatalogResponse(BaseModel):
    """GET /api/kpi-catalog."""

    count: int
    kpis: list[dict[str, Any]]


# ─── Benchmark ─────────────────────────────────────────────────────────────


class BenchmarkSite(BaseModel):
    site_id: int
    site_nom: str
    usage: str
    surface_m2: float = 0
    conso_kwh_an: float = 0
    ipe_kwh_m2_an: Optional[float] = None
    benchmark: Optional[dict[str, Any]] = None
    position: Optional[str] = None


class BenchmarkResponse(BaseModel):
    """GET /api/cockpit/benchmark."""

    sites: list[BenchmarkSite]
    source: str = "ADEME Observatoire DPE 2024"
    unit: str = "kWh/m²/an"


# ─── Trajectory ────────────────────────────────────────────────────────────


class TrajectoryPoint(BaseModel):
    year: int
    target_kwh_m2: Optional[float] = None
    actual_kwh_m2: Optional[float] = None
    status: Optional[str] = None


class TrajectoryResponse(BaseModel):
    """GET /api/cockpit/trajectory."""

    org_id: Optional[int] = None
    reference_year: Optional[int] = None
    reference_kwh_m2: Optional[float] = None
    trajectory: list[TrajectoryPoint] = Field(default_factory=list)
    surface_m2_total: float = 0
    computed_at: Optional[str] = None
    # Error case (no targets)
    error: Optional[str] = None
    annees: Optional[list] = None
    reel_mwh: Optional[list] = None
    objectif_mwh: Optional[list] = None
    projection_mwh: Optional[list] = None
    jalons: Optional[list[dict[str, Any]]] = None


# ─── Conso Month ───────────────────────────────────────────────────────────


class ConsoMonthResponse(BaseModel):
    """GET /api/cockpit/conso-month."""

    year: int
    month: int
    actual_kwh: Optional[float] = None
    actual_mwh: Optional[float] = None
    target_kwh: Optional[float] = None
    delta_vs_prev_month_pct: Optional[float] = None
    sites_with_data: int = 0
    total_sites: int = 0
    source: str = "ConsumptionTarget.actual_kwh"


# ─── CO2 ───────────────────────────────────────────────────────────────────


class Co2Response(BaseModel):
    """GET /api/cockpit/co2."""

    total_co2_kg: float = 0
    total_co2_tonnes: float = 0
    elec_co2_kg: float = 0
    gaz_co2_kg: float = 0
    sites: list[dict[str, Any]] = Field(default_factory=list)
    facteurs: Optional[dict[str, float]] = None
    source: str = "ADEME Base Carbone 2024"
