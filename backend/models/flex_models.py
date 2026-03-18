"""PROMEOS — Flex Foundation Models (Sprint 21)."""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from models.base import Base
import enum


class FlexAssetType(str, enum.Enum):
    HVAC = "hvac"
    IRVE = "irve"
    COLD_STORAGE = "cold_storage"
    THERMAL_STORAGE = "thermal_storage"
    BATTERY = "battery"
    PV = "pv"
    LIGHTING = "lighting"
    PROCESS = "process"
    OTHER = "other"


class ControlMethod(str, enum.Enum):
    GTB = "gtb"
    API = "api"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    UNKNOWN = "unknown"


class FlexAsset(Base):
    """Inventaire des assets pilotables par site/batiment."""

    __tablename__ = "flex_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    batiment_id = Column(Integer, ForeignKey("batiments.id"), nullable=True)
    bacs_cvc_system_id = Column(Integer, ForeignKey("bacs_cvc_systems.id"), nullable=True)

    asset_type = Column(SAEnum(FlexAssetType), nullable=False)
    label = Column(String(300), nullable=False)
    power_kw = Column(Float, nullable=True, comment="Puissance nominale kW")
    energy_kwh = Column(Float, nullable=True, comment="Capacite stockage kWh")
    is_controllable = Column(Boolean, nullable=False, default=False)
    control_method = Column(SAEnum(ControlMethod), nullable=True)
    gtb_class = Column(String(1), nullable=True, comment="Classe EN 15232 A/B/C/D")
    data_source = Column(String(50), nullable=True, comment="declaratif, inspection, import, bacs_sync")
    confidence = Column(String(20), nullable=False, default="unverified", comment="high, medium, low, unverified")
    status = Column(String(20), nullable=False, default="active", comment="active, inactive, decommissioned")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    site = relationship("Site")


class FlexAssessment(Base):
    """Evaluation du potentiel flex par site — lie a des FlexAssets."""

    __tablename__ = "flex_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)

    # Scoring
    flex_score = Column(Float, nullable=True, comment="Score 0-100")
    potential_kw = Column(Float, nullable=True, comment="Potentiel en kW")
    potential_kwh_year = Column(Float, nullable=True, comment="Potentiel annuel en kWh")

    # Sources
    source = Column(String(50), nullable=False, default="heuristic", comment="heuristic, asset_based, mixed")
    confidence = Column(String(20), nullable=False, default="low")

    # Levers (JSON array)
    levers_json = Column(Text, nullable=True, comment="JSON: [{lever, score, kw, kwh_year, source}]")

    # KPI metadata
    kpi_definition = Column(String(200), nullable=True, default="Potentiel de flexibilite estime par site")
    kpi_formula = Column(String(300), nullable=True, default="SUM(asset_power_kw * controllability_factor)")
    kpi_unit = Column(String(20), nullable=True, default="kW")
    kpi_period = Column(String(20), nullable=True, default="instantane")
    kpi_perimeter = Column(String(20), nullable=True, default="site")
    kpi_source = Column(String(100), nullable=True, default="services/flex_assessment_service.py")
    kpi_confidence = Column(String(20), nullable=True)

    # 4 dimensions
    technical_readiness_score = Column(Float, nullable=True, comment="0-100: assets controllables, connectes, testes")
    data_confidence_score = Column(Float, nullable=True, comment="0-100: qualite donnees, couverture, fraicheur")
    economic_relevance_score = Column(Float, nullable=True, comment="0-100: impact EUR potentiel vs effort")
    regulatory_alignment_status = Column(String(30), nullable=True, comment="aligned, partial, misaligned, unknown")

    assessed_at = Column(DateTime, server_default=func.now())

    site = relationship("Site")


class NebcoSignal(Base):
    """Signal marche NEBCO — structure sans moteur de valorisation."""

    __tablename__ = "nebco_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, index=True)
    bloc_type = Column(String(50), nullable=False, comment="effacement, consommation, mixte")
    direction = Column(String(10), nullable=False, comment="up (reduction), down (augmentation)")
    price_eur_mwh = Column(Float, nullable=True)
    volume_mw = Column(Float, nullable=True)
    source = Column(String(50), nullable=True, default="manual", comment="rte, epex_spot, manual, simulation")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class RegulatoryOpportunity(Base):
    """Opportunites reglementaires detectees par site — APER, CEE, flex."""

    __tablename__ = "regulatory_opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    regulation = Column(String(50), nullable=False, comment="aper, cee_p6, bacs_flex, nebco")

    # Obligation vs opportunity
    is_obligation = Column(Boolean, nullable=False, default=False)
    obligation_type = Column(String(100), nullable=True, comment="solarisation_ombriere, gtb_installation, etc.")

    # Opportunity details
    opportunity_type = Column(
        String(100), nullable=True, comment="autoconsommation, acc, stockage, revente_surplus, effacement"
    )
    # APER opportunity_types: "autoconsommation_individuelle", "acc", "stockage_batterie", "revente_surplus"

    # Eligibility
    eligible = Column(Boolean, nullable=True)
    eligibility_reason = Column(Text, nullable=True)
    eligibility_caveat = Column(Text, nullable=True)

    # APER-specific
    surface_m2 = Column(Float, nullable=True)
    surface_type = Column(String(50), nullable=True, comment="parking_exterieur, toiture, parking_couvert")
    threshold_m2 = Column(Float, nullable=True)

    # Deadlines
    deadline = Column(DateTime, nullable=True)
    deadline_source = Column(String(100), nullable=True)

    # CEE-specific
    cee_eligible = Column(Boolean, nullable=True)
    cee_caveat = Column(
        String(300),
        nullable=True,
        default="Eligibilite potentielle — volume et valorisation a confirmer par operateur CEE agree",
    )
    cee_tri_min_years = Column(Integer, nullable=True, default=3)

    # Source
    source_regulation = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    site = relationship("Site")


class TariffWindow(Base):
    """Fenetre tarifaire saisonnalisee — jamais de hardcode HC."""

    __tablename__ = "tariff_windows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    calendar_id = Column(Integer, ForeignKey("tariff_calendars.id"), nullable=True, index=True)
    name = Column(String(100), nullable=False, comment="Ex: TURPE7-C5-ETE")
    segment = Column(String(20), nullable=True, comment="C5, C4, C3, HTA, HTB")
    season = Column(String(20), nullable=False, comment="hiver, ete, mi_saison, toute_annee")
    months = Column(Text, nullable=False, comment="JSON array: [4,5,6,7,8,9,10]")
    period_type = Column(String(20), nullable=False, comment="HC_NUIT, HC_SOLAIRE, HP, POINTE, SUPER_POINTE")
    start_time = Column(String(5), nullable=False, comment="HH:MM")
    end_time = Column(String(5), nullable=False, comment="HH:MM")
    day_types = Column(Text, nullable=False, default='["all"]', comment="JSON: weekday, weekend, holiday, all")
    price_component_eur_kwh = Column(Float, nullable=True)
    effective_from = Column(String(10), nullable=True, comment="YYYY-MM-DD")
    effective_to = Column(String(10), nullable=True)
    source = Column(String(100), nullable=True, comment="CRE, Enedis, manual")
    source_ref = Column(String(300), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
