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
    BillingEnergyType, InvoiceLineType, BillingInvoiceStatus, InsightStatus,
    PurchaseStrategy, PurchaseRecoStatus,
    ActionSourceType, ActionStatus,
    NotificationSeverity, NotificationStatus, NotificationSourceType,
    UserRole, ScopeLevel, PermissionAction,
    StagingStatus, ImportSourceType, QualityRuleSeverity,
    IntakeSessionStatus, IntakeMode, IntakeSource,
    WatcherEventStatus,
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
from .compliance_run_batch import ComplianceRunBatch
from .compliance_finding import ComplianceFinding

# Consumption diagnostics
from .consumption_insight import ConsumptionInsight
from .site_operating_schedule import SiteOperatingSchedule
from .site_tariff_profile import SiteTariffProfile

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

# Bill Intelligence (persisted)
from .billing_models import (
    EnergyContract, EnergyInvoice, EnergyInvoiceLine, BillingInsight,
    BillingImportBatch, ConceptAllocation,
)

# Achat Energie
from .purchase_models import (
    PurchaseAssumptionSet, PurchasePreference, PurchaseScenarioResult,
)

# Action Hub (Sprint 10)
from .action_item import ActionItem, ActionSyncBatch

# Notifications (Sprint 10.2)
from .notification import NotificationEvent, NotificationBatch, NotificationPreference

# IAM (Users / Roles / Scopes)
from .iam import User, UserOrgRole, UserScope, AuditLog

# Patrimoine / Staging (DIAMANT)
from .patrimoine import (
    OrgEntiteLink, PortfolioEntiteLink,
    StagingBatch, StagingSite, StagingCompteur, QualityFinding,
)

# Smart Intake (DIAMANT)
from .intake import IntakeSession, IntakeAnswer, IntakeFieldOverride

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
    "Obligation", "Evidence", "ComplianceRunBatch", "ComplianceFinding", "ConsumptionInsight",
    "SiteOperatingSchedule", "SiteTariffProfile",
    "SegmentationProfile",
    "DataPoint", "RegAssessment", "JobOutbox", "AiInsight", "RegSourceEvent",
    # KB models
    "KBVersion", "KBArchetype", "KBMappingCode", "KBAnomalyRule", "KBRecommendation", "KBTaxonomy",
    # Energy models
    "Meter", "MeterReading", "DataImportJob", "UsageProfile", "Anomaly", "Recommendation",
    "MonitoringSnapshot", "MonitoringAlert",
    # Bill Intelligence models
    "EnergyContract", "EnergyInvoice", "EnergyInvoiceLine", "BillingInsight",
    "BillingImportBatch", "ConceptAllocation",
    # Enums
    "TypeSite", "TypeCompteur", "SeveriteAlerte", "TypeUsage",
    "StatutConformite", "TypeObligation", "TypeEvidence", "StatutEvidence",
    "ParkingType", "OperatStatus", "EnergyVector", "SourceType",
    "JobType", "JobStatus", "RegStatus", "Severity", "Confidence",
    "InsightType", "RegulationType", "Typologie",
    "KBConfidence", "KBStatus", "EnergyVectorModel", "FrequencyType",
    "ImportStatus", "AnomalySeverity", "RecommendationStatus",
    "AlertStatus", "AlertSeverity",
    "BillingEnergyType", "InvoiceLineType", "BillingInvoiceStatus", "InsightStatus",
    # Achat Energie models
    "PurchaseAssumptionSet", "PurchasePreference", "PurchaseScenarioResult",
    "PurchaseStrategy", "PurchaseRecoStatus",
    # Action Hub (Sprint 10)
    "ActionItem", "ActionSyncBatch", "ActionSourceType", "ActionStatus",
    # Notifications (Sprint 10.2)
    "NotificationEvent", "NotificationBatch", "NotificationPreference",
    "NotificationSeverity", "NotificationStatus", "NotificationSourceType",
    # IAM (Users / Roles / Scopes)
    "User", "UserOrgRole", "UserScope", "AuditLog",
    "UserRole", "ScopeLevel", "PermissionAction",
    # Patrimoine / Staging (DIAMANT)
    "OrgEntiteLink", "PortfolioEntiteLink",
    "StagingBatch", "StagingSite", "StagingCompteur", "QualityFinding",
    "StagingStatus", "ImportSourceType", "QualityRuleSeverity",
    # Smart Intake (DIAMANT)
    "IntakeSession", "IntakeAnswer", "IntakeFieldOverride",
    "IntakeSessionStatus", "IntakeMode", "IntakeSource",
    # Watchers
    "WatcherEventStatus",
]
