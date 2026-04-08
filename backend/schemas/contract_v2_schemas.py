"""
PROMEOS ��� Schemas Pydantic pour Contrats V2 (Cadre + Annexes).
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

ENERGY_TYPES = ("elec", "gaz")

# === Referentiels ===

# Fournisseurs par categorie (source: CRE, observatoire marche detail T4 2025)
SUPPLIERS_BY_CATEGORY = {
    "Historiques": [
        {"name": "EDF Entreprises", "energy": ["elec", "gaz"], "hint": "Fournisseur historique, elec + gaz B2B"},
        {"name": "ENGIE Pro", "energy": ["elec", "gaz"], "hint": "Fournisseur historique gaz"},
        {"name": "TotalEnergies", "energy": ["elec", "gaz"], "hint": "Multi-energie, grands comptes"},
    ],
    "Alternatifs majeurs": [
        {"name": "Vattenfall", "energy": ["elec"], "hint": "Suedois, elec verte"},
        {"name": "Alpiq", "energy": ["elec"], "hint": "Suisse, trading + fourniture"},
        {"name": "Eni", "energy": ["elec", "gaz"], "hint": "Italien, gaz naturel"},
        {"name": "Iberdrola", "energy": ["elec"], "hint": "Espagnol, renouvelable"},
        {"name": "Axpo", "energy": ["elec"], "hint": "Suisse, trading B2B"},
        {"name": "Gazel Energie", "energy": ["elec", "gaz"], "hint": "Groupe EPH, ex-Uniper France"},
    ],
    "Alternatifs verts": [
        {"name": "Ekwateur", "energy": ["elec", "gaz"], "hint": "100% renouvelable"},
        {"name": "ilek", "energy": ["elec", "gaz"], "hint": "Producteur local, circuit court"},
        {"name": "Mint Energie", "energy": ["elec", "gaz"], "hint": "Offres vertes competitives"},
        {"name": "La Bellenergie", "energy": ["elec"], "hint": "Cooperatif, prix coutant"},
        {"name": "Octopus Energy", "energy": ["elec"], "hint": "UK, tech + vert"},
        {"name": "GreenYellow", "energy": ["elec"], "hint": "Groupe Casino, PV + fourniture"},
        {"name": "Planete Oui", "energy": ["elec"], "hint": "BSM Energie, petit pro"},
        {"name": "Plum Energie", "energy": ["elec"], "hint": "Autoconso collective"},
    ],
    "Specialistes B2B": [
        {"name": "OHM Energie", "energy": ["elec", "gaz"], "hint": "PME, offres simplifiees"},
        {"name": "Alterna", "energy": ["elec", "gaz"], "hint": "ELD, territoires"},
        {"name": "Elmy", "energy": ["elec"], "hint": "Ex-Chezswitch, renouvelable B2B"},
        {"name": "Primeo Energie", "energy": ["elec", "gaz"], "hint": "Suisse, B2B France"},
        {"name": "Mega Energie", "energy": ["elec", "gaz"], "hint": "Belge, prix bas"},
        {"name": "Proxelia", "energy": ["elec", "gaz"], "hint": "ELD Picardie"},
        {"name": "Energem", "energy": ["elec", "gaz"], "hint": "ELD Metz"},
        {"name": "Lucia Energie", "energy": ["elec", "gaz"], "hint": "B2B ETI-PME"},
    ],
    "Gaz specialises": [
        {"name": "Endesa", "energy": ["elec", "gaz"], "hint": "Groupe Enel, elec + gaz B2B"},
        {"name": "Antargaz", "energy": ["gaz"], "hint": "UGI, propane + gaz naturel"},
        {"name": "Gaz de Bordeaux", "energy": ["gaz"], "hint": "ELD Bordeaux"},
        {"name": "Save Energies", "energy": ["gaz"], "hint": "PME, gaz naturel"},
        {"name": "Gaz Europeen", "energy": ["gaz"], "hint": "Grands comptes gaz"},
    ],
}

SUPPLIERS_CRE = [s["name"] for items in SUPPLIERS_BY_CATEGORY.values() for s in items]

# Modeles de prix par type d'energie
PRICING_MODELS_ELEC = [
    {"value": "FIXE", "label": "Prix fixe", "hint": "Prix bloque sur toute la duree"},
    {"value": "FIXE_HORS_ACHEMINEMENT", "label": "Fixe hors acheminement", "hint": "Fourniture fixe, TURPE variable"},
    {"value": "INDEXE_TRVE", "label": "Indexe TRVE", "hint": "Indexe sur le tarif reglemente (% TRVE)"},
    {"value": "INDEXE_SPOT", "label": "Indexe spot", "hint": "Prix marche EPEX Spot J-1"},
    {"value": "VARIABLE_AUTRE", "label": "Variable autre", "hint": "Formule specifique (click, tunnel, ...)"},
]
PRICING_MODELS_GAZ = [
    {"value": "FIXE", "label": "Prix fixe", "hint": "Prix bloque sur toute la duree"},
    {"value": "INDEXE_PEG", "label": "Indexe PEG", "hint": "Indexe sur le PEG (point echange gaz)"},
    {"value": "INDEXE_SPOT", "label": "Indexe spot", "hint": "Prix marche spot gaz"},
    {"value": "VARIABLE_AUTRE", "label": "Variable autre", "hint": "Formule specifique"},
]

PRICING_MODELS = [
    "FIXE",
    "FIXE_HORS_ACHEMINEMENT",
    "INDEXE_TRVE",
    "INDEXE_PEG",
    "INDEXE_SPOT",
    "VARIABLE_AUTRE",
]

# Options tarifaires par segment Enedis
TARIFF_OPTIONS_BY_SEGMENT = {
    "C5": [
        {"value": "base", "label": "Base", "hint": "Tarif unique, <=36 kVA"},
        {"value": "hp_hc", "label": "HP/HC", "hint": "Heures pleines / creuses"},
    ],
    "C4": [
        {"value": "cu4", "label": "CU 4 postes", "hint": "Courte utilisation saisonnalisee"},
        {"value": "mu4", "label": "MU 4 postes", "hint": "Moyenne utilisation saisonnalisee"},
        {"value": "lu", "label": "LU", "hint": "Longue utilisation, >5000h/an"},
    ],
    "C3": [
        {"value": "lu", "label": "LU", "hint": "Longue utilisation HTA"},
        {"value": "cu", "label": "CU", "hint": "Courte utilisation HTA"},
    ],
    "C2": [{"value": "lu", "label": "LU", "hint": "HTA poste-source"}],
    "C1": [{"value": "lu", "label": "LU", "hint": "HTB"}],
}

_GRID_4POSTES = [
    {"period_code": "HPH", "season": "HIVER"},
    {"period_code": "HCH", "season": "HIVER"},
    {"period_code": "HPB", "season": "ETE"},
    {"period_code": "HCB", "season": "ETE"},
]
_GRID_5POSTES = _GRID_4POSTES + [{"period_code": "POINTE", "season": "HIVER"}]

PRICING_GRID_BY_TARIFF = {
    "base": [{"period_code": "BASE", "season": "ANNUEL"}],
    "hp_hc": [
        {"period_code": "HP", "season": "ANNUEL"},
        {"period_code": "HC", "season": "ANNUEL"},
    ],
    "cu4": _GRID_4POSTES,
    "mu4": _GRID_4POSTES,
    "cu": _GRID_5POSTES,
    "lu": _GRID_5POSTES,
}

# Durees typiques de contrat
CONTRACT_DURATIONS = [
    {"months": 12, "label": "1 an"},
    {"months": 24, "label": "2 ans"},
    {"months": 36, "label": "3 ans"},
    {"months": 48, "label": "4 ans"},
    {"months": 60, "label": "5 ans"},
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
    segment_enedis: Optional[str] = None
    annual_consumption_kwh: Optional[float] = Field(None, gt=0)
    indexation_formula: Optional[str] = Field(None, max_length=200)
    indexation_reference: Optional[str] = Field(None, max_length=100)
    indexation_spread_eur_mwh: Optional[float] = None
    price_revision_clause: Optional[str] = Field(None, description="NONE/CAP/FLOOR/TUNNEL/ANNUAL_REVIEW")
    price_cap_eur_mwh: Optional[float] = Field(None, ge=0)
    price_floor_eur_mwh: Optional[float] = Field(None, ge=0)
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

    @field_validator("segment_enedis")
    @classmethod
    def validate_segment_cadre(cls, v):
        if v is not None and v.upper() not in SEGMENTS_ENEDIS:
            raise ValueError(f"segment invalide: {v}. Valeurs: {SEGMENTS_ENEDIS}")
        return v.upper() if v else v

    @field_validator("price_revision_clause")
    @classmethod
    def validate_revision_clause(cls, v):
        if v is not None and v.upper() not in REVISION_CLAUSES:
            raise ValueError(f"price_revision_clause invalide: {v}. Valeurs: {REVISION_CLAUSES}")
        return v.upper() if v else v

    @field_validator("energy_type")
    @classmethod
    def validate_energy(cls, v):
        if v.lower() not in ENERGY_TYPES:
            raise ValueError(f"energy_type doit etre l'un de {ENERGY_TYPES}")
        return v.lower()


REVISION_CLAUSES = ("NONE", "CAP", "FLOOR", "TUNNEL", "ANNUAL_REVIEW")
INDEXATION_REFERENCES = ("TRVE", "EPEX_SPOT_FR", "PEG_DA", "PEG_M+1", "TTF_DA")


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
    segment_enedis: Optional[str] = None
    annual_consumption_kwh: Optional[float] = None
    indexation_formula: Optional[str] = None
    indexation_reference: Optional[str] = None
    indexation_spread_eur_mwh: Optional[float] = None
    price_revision_clause: Optional[str] = None
    price_cap_eur_mwh: Optional[float] = None
    price_floor_eur_mwh: Optional[float] = None
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


class AnnexeResponse(BaseModel):
    """Reponse annexe serialisee."""

    id: Optional[int] = None
    contrat_cadre_id: Optional[int] = None
    cadre_id: Optional[int] = None
    site_id: Optional[int] = None
    annexe_ref: Optional[str] = None
    tariff_option: Optional[str] = None
    subscribed_power_kva: Optional[float] = None
    segment_enedis: Optional[str] = None
    has_price_override: Optional[bool] = None
    override_pricing_model: Optional[str] = None
    status: Optional[str] = None
    pricing: Optional[list] = None
    volume_commitment: Optional[dict] = None
    start_date_override: Optional[str] = None
    end_date_override: Optional[str] = None

    model_config = {"from_attributes": True}


class CadreResponse(BaseModel):
    """Reponse cadre serialisee (detail + annexes)."""

    id: Optional[int] = None
    supplier_name: Optional[str] = None
    energy_type: Optional[str] = None
    contract_ref: Optional[str] = None
    contract_type: Optional[str] = None
    pricing_model: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    tacit_renewal: Optional[bool] = None
    notice_period_months: Optional[int] = None
    is_green: Optional[bool] = None
    green_percentage: Optional[float] = None
    segment_enedis: Optional[str] = None
    annual_consumption_kwh: Optional[float] = None
    nb_annexes: Optional[int] = None
    annexes: Optional[list] = None
    pricing: Optional[list] = None
    kpis: Optional[dict] = None
    coherence: Optional[list] = None
    events: Optional[list] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class SuppliersResponse(BaseModel):
    """Referentiels fournisseurs."""

    suppliers: list[str]
    suppliers_by_category: dict
    pricing_models: list[str]
    pricing_models_elec: list
    pricing_models_gaz: list
    tariff_options_by_segment: dict
    pricing_grid_by_tariff: dict
    contract_durations: list


class DeleteResponse(BaseModel):
    """Reponse suppression."""

    status: str
    cadre_id: Optional[int] = None
    annexe_id: Optional[int] = None


class EventResponse(BaseModel):
    """Reponse creation evenement."""

    id: int
    event_type: str
    event_date: str


class CoherenceCheckResponse(BaseModel):
    """Resultat check coherence."""

    cadre_id: int
    rules: list[CoherenceResult]
    total: int


class ShadowGapResponse(BaseModel):
    """Ecart shadow billing pour une annexe."""

    annexe_id: Optional[int] = None
    gap_eur: Optional[float] = None
    details: Optional[dict] = None

    model_config = {"from_attributes": True}


class ImportCsvResponse(BaseModel):
    """Resultat import CSV."""

    cadres_created: Optional[int] = None
    annexes_created: Optional[int] = None
    errors: Optional[list] = None
