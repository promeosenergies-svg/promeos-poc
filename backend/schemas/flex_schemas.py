"""
PROMEOS — Schemas Pydantic pour Flex (Assets, Assessment, Regulatory, Tariff).
"""

from typing import Any, Optional

from pydantic import BaseModel


# === Flex Asset ===


class FlexAssetResponse(BaseModel):
    """Reponse serialisee d'un FlexAsset."""

    id: int
    site_id: int
    batiment_id: Optional[int] = None
    bacs_cvc_system_id: Optional[int] = None
    asset_type: str
    label: str
    power_kw: Optional[float] = None
    energy_kwh: Optional[float] = None
    is_controllable: bool = False
    control_method: Optional[str] = None
    gtb_class: Optional[str] = None
    data_source: Optional[str] = None
    confidence: str = "unverified"
    status: str = "active"
    notes: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class FlexAssetListResponse(BaseModel):
    """Liste d'assets flex."""

    total: int
    assets: list[FlexAssetResponse]


# === Flex Mini ===


class FlexMiniResponse(BaseModel):
    """Score flex mini (0-100) + leviers."""

    site_id: Optional[int] = None
    flex_score: Optional[float] = None
    levers: Optional[list[dict[str, Any]]] = None
    source: Optional[str] = None
    confidence: Optional[str] = None

    model_config = {"from_attributes": True}


# === Flex Assessment ===


class FlexAssessmentResponse(BaseModel):
    """Evaluation du potentiel flex d'un site."""

    site_id: Optional[int] = None
    flex_score: Optional[float] = None
    potential_kw: Optional[float] = None
    source: Optional[str] = None
    confidence: Optional[str] = None
    dimensions: Optional[dict[str, Any]] = None
    assets: Optional[list[dict[str, Any]]] = None

    model_config = {"from_attributes": True}


# === Regulatory Opportunities ===


class RegOppResponse(BaseModel):
    """Opportunite reglementaire serialisee."""

    id: int
    site_id: int
    regulation: str
    is_obligation: Optional[bool] = False
    obligation_type: Optional[str] = None
    opportunity_type: Optional[str] = None
    eligible: Optional[bool] = None
    eligibility_reason: Optional[str] = None
    eligibility_caveat: Optional[str] = None
    surface_m2: Optional[float] = None
    surface_type: Optional[str] = None
    threshold_m2: Optional[float] = None
    deadline: Optional[str] = None
    deadline_source: Optional[str] = None
    cee_eligible: Optional[bool] = None
    cee_caveat: Optional[str] = None
    cee_tri_min_years: Optional[int] = None
    source_regulation: Optional[str] = None
    notes: Optional[str] = None


class RegOppListResponse(BaseModel):
    """Liste d'opportunites reglementaires."""

    total: int
    opportunities: list[RegOppResponse]


# === Tariff Windows ===


class TariffWindowResponse(BaseModel):
    """Fenetre tarifaire."""

    id: int
    name: str
    segment: Optional[str] = None
    season: Optional[str] = None
    months: Optional[str] = None
    period_type: str
    start_time: str
    end_time: str
    day_types: Optional[str] = None
    price_component_eur_kwh: Optional[float] = None
    effective_from: Optional[str] = None
    source: Optional[str] = None


class TariffWindowListResponse(BaseModel):
    """Liste de fenetres tarifaires."""

    total: int
    windows: list[TariffWindowResponse]


class TariffWindowCreateResponse(BaseModel):
    """Reponse creation fenetre tarifaire."""

    id: int
    name: str
    period_type: str


# === BACS Sync ===


class BacsSyncResponse(BaseModel):
    """Resultat sync BACS → FlexAsset."""

    created: Optional[int] = 0
    updated: Optional[int] = 0
    skipped: Optional[int] = 0
    errors: Optional[list[str]] = None


# === Portfolio / Prioritization ===


class FlexSiteRanking(BaseModel):
    """Classement flex d'un site."""

    site_id: int
    site_name: Optional[str] = None
    flex_score: Optional[float] = 0
    potential_kw: Optional[float] = 0
    source: Optional[str] = "unknown"
    confidence: Optional[str] = "low"
    asset_count: Optional[int] = 0
    dimensions: Optional[dict[str, Any]] = None


class FlexPrioritizationResponse(BaseModel):
    """Priorisation flex par portefeuille."""

    portfolio_id: int
    portfolio_name: Optional[str] = None
    total_sites: int
    total_potential_kw: float
    avg_flex_score: float
    rankings: list[FlexSiteRanking]


class FlexPortfolioResponse(BaseModel):
    """Vue portefeuille flex."""

    total_sites: int
    total_potential_kw: float
    avg_flex_score: float
    rankings: list[FlexSiteRanking]


# === Generiques ===


class StatusResponse(BaseModel):
    """Reponse simple statut."""

    status: str
    detail: Optional[str] = None
