"""
PROMEOS ��� Schemas Pydantic pour Contrats V2 (Cadre + Annexes).
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# === Referentiels ===

SUPPLIERS_CRE = [
    "EDF Entreprises",
    "ENGIE Pro",
    "TotalEnergies",
    "Alpiq",
    "OHM Energie",
    "Vattenfall",
    "Mint Energie",
    "Ekwateur",
    "La Bellenergie",
    "Alterna",
    "Octopus Energy",
    "ilek",
    "Dyneff",
    "GreenYellow",
    "jpme",
]

PRICING_MODELS = [
    "FIXE",
    "FIXE_HORS_ACHEMINEMENT",
    "INDEXE_TRVE",
    "INDEXE_PEG",
    "INDEXE_SPOT",
    "VARIABLE_AUTRE",
]

PERIOD_CODES = ["BASE", "HP", "HC", "HPH", "HCH", "HPB", "HCB", "POINTE"]
SEASONS = ["ANNUEL", "HIVER", "ETE"]
SEGMENTS_ENEDIS = ["C5", "C4", "C3", "C2", "C1"]
EVENT_TYPES = [
    "CREATION",
    "AVENANT",
    "REVISION",
    "RESILIATION",
    "CESSION",
    "TRANSFER",
    "RENOUVELLEMENT",
]


# === Sous-schemas ===


class PricingLineSchema(BaseModel):
    period_code: str = Field(..., description="BASE/HP/HC/HPH/HCH/HPB/HCB/POINTE")
    season: str = Field("ANNUEL", description="ANNUEL/HIVER/ETE")
    unit_price_eur_kwh: Optional[float] = Field(None, ge=0, le=1.0)
    subscription_eur_month: Optional[float] = Field(None, ge=0, le=100000)

    @field_validator("period_code")
    @classmethod
    def validate_period(cls, v):
        if v.upper() not in PERIOD_CODES:
            raise ValueError(f"period_code invalide: {v}. Valeurs: {PERIOD_CODES}")
        return v.upper()

    @field_validator("season")
    @classmethod
    def validate_season(cls, v):
        if v.upper() not in SEASONS:
            raise ValueError(f"season invalide: {v}. Valeurs: {SEASONS}")
        return v.upper()


class VolumeSchema(BaseModel):
    annual_kwh: float = Field(..., gt=0, description="Volume engage kWh/an")
    tolerance_pct_up: float = Field(10.0, ge=0, le=100)
    tolerance_pct_down: float = Field(10.0, ge=0, le=100)
    penalty_eur_kwh_above: Optional[float] = Field(None, ge=0)
    penalty_eur_kwh_below: Optional[float] = Field(None, ge=0)


class EventSchema(BaseModel):
    event_type: str = Field(..., description="Type d'evenement")
    event_date: date
    description: Optional[str] = Field(None, max_length=500)
    meta_json: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v):
        if v.upper() not in EVENT_TYPES:
            raise ValueError(f"event_type invalide: {v}. Valeurs: {EVENT_TYPES}")
        return v.upper()


# === Annexe ===


class AnnexeCreateSchema(BaseModel):
    site_id: int = Field(..., gt=0)
    delivery_point_id: Optional[int] = None
    annexe_ref: Optional[str] = Field(None, max_length=100)
    tariff_option: Optional[str] = None
    subscribed_power_kva: Optional[float] = Field(None, ge=0, le=100000)
    segment_enedis: Optional[str] = None
    has_price_override: bool = False
    pricing_overrides: List[PricingLineSchema] = []
    volume_commitment: Optional[VolumeSchema] = None

    @field_validator("segment_enedis")
    @classmethod
    def validate_segment(cls, v):
        if v is not None and v.upper() not in SEGMENTS_ENEDIS:
            raise ValueError(f"segment invalide: {v}. Valeurs: {SEGMENTS_ENEDIS}")
        return v.upper() if v else v


class AnnexeUpdateSchema(BaseModel):
    delivery_point_id: Optional[int] = None
    annexe_ref: Optional[str] = None
    tariff_option: Optional[str] = None
    subscribed_power_kva: Optional[float] = None
    segment_enedis: Optional[str] = None
    has_price_override: Optional[bool] = None
    override_pricing_model: Optional[str] = None
    start_date_override: Optional[date] = None
    end_date_override: Optional[date] = None
    pricing_overrides: Optional[List[PricingLineSchema]] = None
    volume_commitment: Optional[VolumeSchema] = None


# === Cadre ===


class CadreCreateSchema(BaseModel):
    entite_juridique_id: Optional[int] = None
    supplier_name: str = Field(..., min_length=1, max_length=200)
    energy_type: str = Field(..., description="elec ou gaz")
    contract_ref: Optional[str] = Field(None, max_length=100)
    contract_type: str = Field("UNIQUE", description="UNIQUE ou CADRE")
    pricing_model: Optional[str] = None
    start_date: date
    end_date: date
    tacit_renewal: bool = False
    notice_period_months: int = Field(3, ge=0, le=60)
    is_green: bool = False
    green_percentage: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    pricing: List[PricingLineSchema] = []
    annexes: List[AnnexeCreateSchema] = []

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        start = info.data.get("start_date")
        if start and v <= start:
            raise ValueError("Date fin doit etre apres date debut")
        return v

    @field_validator("annexes")
    @classmethod
    def at_least_one_annexe(cls, v):
        if len(v) < 1:
            raise ValueError("Au moins une annexe site requise")
        return v

    @field_validator("energy_type")
    @classmethod
    def validate_energy(cls, v):
        if v.lower() not in ("elec", "gaz"):
            raise ValueError("energy_type doit etre 'elec' ou 'gaz'")
        return v.lower()


class CadreUpdateSchema(BaseModel):
    supplier_name: Optional[str] = None
    contract_ref: Optional[str] = None
    pricing_model: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tacit_renewal: Optional[bool] = None
    notice_period_months: Optional[int] = None
    is_green: Optional[bool] = None
    green_percentage: Optional[float] = None
    notes: Optional[str] = None
    pricing: Optional[List[PricingLineSchema]] = None


# === Reponses ===


class PricingLineResponse(BaseModel):
    period_code: str
    season: str
    unit_price_eur_kwh: Optional[float] = None
    subscription_eur_month: Optional[float] = None
    source: str = "cadre"  # "cadre" ou "override"


class CoherenceResult(BaseModel):
    rule_id: str
    level: str  # "error", "warning", "info"
    message: str


class CadreKpisResponse(BaseModel):
    total_cadres: int = 0
    active_cadres: int = 0
    expiring_90d: int = 0
    total_volume_mwh: float = 0
    total_budget_eur: float = 0
    total_shadow_gap_eur: float = 0
