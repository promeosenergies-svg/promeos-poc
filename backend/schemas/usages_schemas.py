"""
PROMEOS — Schemas Pydantic pour Usages Energetiques.
"""

from typing import Any, Optional

from pydantic import BaseModel


# === Dashboard ===


class ScopedDashboardResponse(BaseModel):
    """Dashboard usages multi-niveaux."""

    scope: Optional[dict[str, Any]] = None
    readiness: Optional[dict[str, Any]] = None
    top_usages: Optional[list[dict[str, Any]]] = None
    cost_breakdown: Optional[dict[str, Any]] = None
    baselines: Optional[dict[str, Any]] = None
    compliance: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class UsageDashboardResponse(BaseModel):
    """Dashboard usages mono-site (legacy)."""

    readiness: Optional[dict[str, Any]] = None
    metering_plan: Optional[dict[str, Any]] = None
    top_ues: Optional[list[dict[str, Any]]] = None
    cost_breakdown: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


# === Timeline ===


class TimelineResponse(BaseModel):
    """Timeline usages mensuelle."""

    months: Optional[list[dict[str, Any]]] = None
    usages: Optional[list[str]] = None
    site_id: Optional[int] = None

    model_config = {"from_attributes": True}


# === Archetypes ===


class ArchetypeItem(BaseModel):
    """Un archetype dans le scope."""

    code: str
    label: str
    count: int


class ArchetypesResponse(BaseModel):
    """Distribution des archetypes."""

    archetypes: list[ArchetypeItem]


# === Flex ===


class FlexPotentialResponse(BaseModel):
    """Scoring flex NEBCO + lien BACS pour un site."""

    site_id: Optional[int] = None
    eligible: Optional[bool] = None
    score: Optional[float] = None
    potential_kw: Optional[float] = None
    details: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class FlexPortfolioUsagesResponse(BaseModel):
    """Agregation flex du perimetre."""

    total_sites: Optional[int] = None
    eligible_sites: Optional[int] = None
    total_potential_kw: Optional[float] = None
    sites: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Cost ===


class CostByPeriodResponse(BaseModel):
    """Ventilation cout par usage x periode tarifaire."""

    site_id: Optional[int] = None
    periods: Optional[list[dict[str, Any]]] = None
    usages: Optional[list[dict[str, Any]]] = None
    total_eur: Optional[float] = None

    model_config = {"from_attributes": True}


class CostBreakdownResponse(BaseModel):
    """Ventilation du cout energetique par usage."""

    site_id: Optional[int] = None
    total_eur: Optional[float] = None
    usages: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Readiness ===


class ReadinessResponse(BaseModel):
    """Score de readiness usage d'un site."""

    site_id: Optional[int] = None
    score: Optional[float] = None
    details: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


# === Metering Plan ===


class MeteringPlanResponse(BaseModel):
    """Plan de comptage dynamique."""

    site_id: Optional[int] = None
    meters: Optional[list[dict[str, Any]]] = None
    coverage_pct: Optional[float] = None

    model_config = {"from_attributes": True}


# === Top UES ===


class TopUesResponse(BaseModel):
    """Top usages energetiques significatifs."""

    site_id: Optional[int] = None
    usages: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Taxonomy ===


class UsageTaxonomyResponse(BaseModel):
    """Taxonomie des usages energetiques."""

    families: list[dict[str, Any]]
    data_sources: list[dict[str, Any]]


# === Baselines ===


class BaselinesResponse(BaseModel):
    """Baselines auto-calculees avec comparaison."""

    site_id: Optional[int] = None
    baselines: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Compliance ===


class UsageComplianceResponse(BaseModel):
    """Widget conformite par usage."""

    site_id: Optional[int] = None
    compliance: Optional[dict[str, Any]] = None
    rules: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Billing Links ===


class BillingLinksResponse(BaseModel):
    """Liens usage -> facture -> contrat -> achat."""

    site_id: Optional[int] = None
    links: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Usage Item ===


class UsageItemResponse(BaseModel):
    """Un usage declare pour un site."""

    id: int
    batiment_id: Optional[int] = None
    type: str
    label: Optional[str] = None
    family: Optional[str] = None
    description: Optional[str] = None
    surface_m2: Optional[float] = None
    data_source: Optional[str] = None
    is_significant: Optional[bool] = None
    pct_of_total: Optional[float] = None


# === Portfolio Compare ===


class PortfolioCompareResponse(BaseModel):
    """Comparaison inter-sites des IPE par usage."""

    sites: Optional[list[dict[str, Any]]] = None
    usages: Optional[list[str]] = None

    model_config = {"from_attributes": True}


# === Meter Readings ===


class MeterReadingsResponse(BaseModel):
    """Releves recents d'un compteur."""

    meter_id: Optional[int] = None
    readings: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Energy Signature ===


class EnergySignatureResponse(BaseModel):
    """Signature energetique E = a x DJU + b."""

    site_id: Optional[int] = None
    baseload_kwh: Optional[float] = None
    thermosensitivity: Optional[float] = None
    r_squared: Optional[float] = None
    benchmark: Optional[dict[str, Any]] = None
    savings_potential: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


# === Power Optimization ===


class PowerOptimizationResponse(BaseModel):
    """Recommandation d'optimisation de puissance souscrite."""

    site_id: Optional[int] = None
    current_ps_kva: Optional[float] = None
    recommended_ps_kva: Optional[float] = None
    savings_eur: Optional[float] = None
    details: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}
