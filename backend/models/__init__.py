"""
PROMEOS - Models
"""
from .base import Base, TimestampMixin

# Enums (tous centralises)
from .enums import (
    TypeSite, TypeCompteur, SeveriteAlerte, TypeUsage,
    StatutConformite, TypeObligation,
    TypeEvidence, StatutEvidence,
    ParkingType, OperatStatus, EnergyVector, SourceType,
    JobType, JobStatus, RegStatus, Severity, Confidence,
    InsightType, RegulationType, Typologie,
)

# Hierarchie organisation
from .organisation import Organisation
from .entite_juridique import EntiteJuridique
from .portefeuille import Portefeuille

# Site (coeur)
from .site import Site
from .batiment import Batiment
from .usage import Usage

# Assets energie
from .compteur import Compteur
from .consommation import Consommation
from .alerte import Alerte

# Conformite
from .conformite import Obligation
from .evidence import Evidence

# Segmentation
from .segmentation import SegmentationProfile

# RegOps / Lifecycle
from .datapoint import DataPoint
from .reg_assessment import RegAssessment
from .job_outbox import JobOutbox
from .ai_insight import AiInsight
from .reg_source_event import RegSourceEvent

# KB (Knowledge Base)
from .kb_models import (
    KBVersion, KBArchetype, KBMappingCode, KBAnomalyRule, KBRecommendation, KBTaxonomy,
    KBConfidence, KBStatus
)

# Energy (Consumption & Analytics)
from .energy_models import (
    Meter, MeterReading, DataImportJob, UsageProfile, Anomaly, Recommendation,
    EnergyVector as EnergyVectorModel, FrequencyType, ImportStatus,
    AnomalySeverity, RecommendationStatus,
    MonitoringSnapshot, MonitoringAlert, AlertStatus, AlertSeverity,
)

__all__ = [
    "Base", "TimestampMixin",
    "Organisation", "EntiteJuridique", "Portefeuille",
    "Site", "Batiment", "Usage",
    "Compteur", "Consommation", "Alerte",
    "Obligation", "Evidence",
    "SegmentationProfile",
    "DataPoint", "RegAssessment", "JobOutbox", "AiInsight", "RegSourceEvent",
    # KB models
    "KBVersion", "KBArchetype", "KBMappingCode", "KBAnomalyRule", "KBRecommendation", "KBTaxonomy",
    # Energy models
    "Meter", "MeterReading", "DataImportJob", "UsageProfile", "Anomaly", "Recommendation",
    "MonitoringSnapshot", "MonitoringAlert",
    # Enums
    "TypeSite", "TypeCompteur", "SeveriteAlerte", "TypeUsage",
    "StatutConformite", "TypeObligation", "TypeEvidence", "StatutEvidence",
    "ParkingType", "OperatStatus", "EnergyVector", "SourceType",
    "JobType", "JobStatus", "RegStatus", "Severity", "Confidence",
    "InsightType", "RegulationType", "Typologie",
    "KBConfidence", "KBStatus", "EnergyVectorModel", "FrequencyType",
    "ImportStatus", "AnomalySeverity", "RecommendationStatus",
    "AlertStatus", "AlertSeverity",
]
