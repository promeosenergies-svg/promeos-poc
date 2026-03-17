"""
PROMEOS - Models
"""

from .base import Base, TimestampMixin, SoftDeleteMixin, not_deleted

# Enums (tous centralises)
from .enums import (
    TypeSite,
    TypeCompteur,
    SeveriteAlerte,
    TypeUsage,
    StatutConformite,
    TypeObligation,
    TypeEvidence,
    StatutEvidence,
    ParkingType,
    OperatStatus,
    EnergyVector,
    SourceType,
    JobType,
    JobStatus,
    RegStatus,
    Severity,
    Confidence,
    InsightType,
    RegulationType,
    Typologie,
    BillingEnergyType,
    InvoiceLineType,
    BillingInvoiceStatus,
    InsightStatus,
    PurchaseStrategy,
    PurchaseRecoStatus,
    ActionSourceType,
    ActionStatus,
    NotificationSeverity,
    NotificationStatus,
    NotificationSourceType,
    UserRole,
    ScopeLevel,
    PermissionAction,
    StagingStatus,
    ImportSourceType,
    QualityRuleSeverity,
    ActivationLogStatus,
    DeliveryPointStatus,
    DeliveryPointEnergyType,
    IntakeSessionStatus,
    IntakeMode,
    IntakeSource,
    WatcherEventStatus,
    CvcSystemType,
    CvcArchitecture,
    BacsTriggerReason,
    InspectionStatus,
    EfaStatut,
    EfaRole,
    DeclarationStatus,
    PerimeterEventType,
    DataQualityIssueSeverity,
    DataQualityIssueStatus,
    WorkPackageSize,
    CeeDossierStep,
    CeeStatus,
    MVAlertType,
    PaymentRuleLevel,
    ContractIndexation,
    ContractStatus,
    ReconciliationStatus,
    AnomalyStatus,
    DismissReason,
    TariffOptionEnum,
    InvoiceTypeEnum,
    ReconstitutionStatusEnum,
    # V1.1 Usage
    UsageFamily,
    DataSourceType,
    USAGE_FAMILY_MAP,
    USAGE_LABELS_FR,
)

# Hierarchie organisation
from .organisation import Organisation
from .entite_juridique import EntiteJuridique
from .portefeuille import Portefeuille

# Site (coeur)
from .site import Site
from .batiment import Batiment
from .usage import Usage, UsageBaseline

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
from .segmentation import SegmentationProfile, SegmentationAnswer

# RegOps / Lifecycle
from .datapoint import DataPoint
from .reg_assessment import RegAssessment
from .job_outbox import JobOutbox
from .ai_insight import AiInsight
from .reg_source_event import RegSourceEvent

# KB (Knowledge Base)
from .kb_models import (
    KBVersion,
    KBArchetype,
    KBMappingCode,
    KBAnomalyRule,
    KBRecommendation,
    KBTaxonomy,
    KBConfidence,
    KBStatus,
)

# Bill Intelligence (persisted)
from .billing_models import (
    EnergyContract,
    EnergyInvoice,
    EnergyInvoiceLine,
    BillingInsight,
    BillingImportBatch,
    ConceptAllocation,
)

# Achat Energie
from .purchase_models import (
    PurchaseAssumptionSet,
    PurchasePreference,
    PurchaseScenarioResult,
)

# Action Hub (Sprint 10)
from .action_item import ActionItem, ActionSyncBatch

# Action Detail (Sprint V5.0)
from .action_detail_models import ActionEvent, ActionComment, ActionEvidence, AnomalyActionLink, AnomalyDismissal

# Notifications (Sprint 10.2)
from .notification import (
    NotificationEvent,
    NotificationBatch,
    NotificationPreference,
    WebhookSubscription,
    DigestPreference,
)

# IAM (Users / Roles / Scopes)
from .iam import User, UserOrgRole, UserScope, AuditLog

# Patrimoine / Staging (DIAMANT)
from .patrimoine import (
    OrgEntiteLink,
    PortfolioEntiteLink,
    ContractDeliveryPoint,
    StagingBatch,
    StagingSite,
    StagingCompteur,
    QualityFinding,
    ActivationLog,
    DeliveryPoint,
)

# Smart Intake (DIAMANT)
from .intake import IntakeSession, IntakeAnswer, IntakeFieldOverride

# Consumption World-Class (V10)
from .consumption_target import ConsumptionTarget
from .tou_schedule import TOUSchedule
from .tariff_calendar import TariffCalendar

# BACS Expert (Decret n°2020-887)
from .bacs_models import BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection

# EMS Consumption Explorer
from .ems_models import EmsWeatherCache, EmsSavedView, EmsCollection

# Emission Factors (Sprint V9 Decarbonation)
from .emission_factor import EmissionFactor

# Tertiaire / OPERAT (V39)
from .tertiaire import (
    TertiaireEfa,
    TertiaireEfaLink,
    TertiaireEfaBuilding,
    TertiaireResponsibility,
    TertiairePerimeterEvent,
    TertiaireDeclaration,
    TertiaireProofArtifact,
    TertiaireDataQualityIssue,
    TertiaireEfaConsumption,
)
from .compliance_event_log import ComplianceEventLog
from .operat_export_manifest import OperatExportManifest
from .bacs_regulatory import BacsFunctionalRequirement, BacsExploitationStatus, BacsProofDocument
from .bacs_remediation import BacsRemediationAction

# V96: Payment Rules
from .payment_rule import PaymentRule

# V97: Reconciliation Fix Log
from .reconciliation_fix_log import ReconciliationFixLog

# V69: CEE Pipeline + M&V
from .cee_models import WorkPackage, CeeDossier, CeeDossierEvidence

# Energy (Consumption & Analytics)
from .energy_models import (
    Meter,
    MeterReading,
    DataImportJob,
    UsageProfile,
    Anomaly,
    Recommendation,
    EnergyVector as EnergyVectorModel,
    FrequencyType,
    ImportStatus,
    AnomalySeverity,
    RecommendationStatus,
    MonitoringSnapshot,
    MonitoringAlert,
    AlertStatus,
    AlertSeverity,
)

# Energy Copilot (V113)
from .copilot_models import CopilotAction, CopilotActionStatus

# Action Templates (V113)
from .action_template import ActionTemplate

# Onboarding Progress (V113)
from .onboarding_progress import OnboardingProgress

# Market Prices (Step 17)
from .market_price import MarketPrice

# Compliance Score History (Step 33)
from .compliance_score_history import ComplianceScoreHistory

# Action Plan Items (Workflow)
from .action_plan_item import ActionPlanItem

__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "not_deleted",
    "Organisation",
    "EntiteJuridique",
    "Portefeuille",
    "Site",
    "Batiment",
    "Usage",
    "Compteur",
    "Consommation",
    "Alerte",
    "Obligation",
    "Evidence",
    "ComplianceRunBatch",
    "ComplianceFinding",
    "ConsumptionInsight",
    "SiteOperatingSchedule",
    "SiteTariffProfile",
    "SegmentationProfile",
    "SegmentationAnswer",
    "DataPoint",
    "RegAssessment",
    "JobOutbox",
    "AiInsight",
    "RegSourceEvent",
    # KB models
    "KBVersion",
    "KBArchetype",
    "KBMappingCode",
    "KBAnomalyRule",
    "KBRecommendation",
    "KBTaxonomy",
    # Energy models
    "Meter",
    "MeterReading",
    "DataImportJob",
    "UsageProfile",
    "Anomaly",
    "Recommendation",
    "MonitoringSnapshot",
    "MonitoringAlert",
    # Bill Intelligence models
    "EnergyContract",
    "EnergyInvoice",
    "EnergyInvoiceLine",
    "BillingInsight",
    "BillingImportBatch",
    "ConceptAllocation",
    # Enums
    "TypeSite",
    "TypeCompteur",
    "SeveriteAlerte",
    "TypeUsage",
    "StatutConformite",
    "TypeObligation",
    "TypeEvidence",
    "StatutEvidence",
    "ParkingType",
    "OperatStatus",
    "EnergyVector",
    "SourceType",
    "JobType",
    "JobStatus",
    "RegStatus",
    "Severity",
    "Confidence",
    "InsightType",
    "RegulationType",
    "Typologie",
    "KBConfidence",
    "KBStatus",
    "EnergyVectorModel",
    "FrequencyType",
    "ImportStatus",
    "AnomalySeverity",
    "RecommendationStatus",
    "AlertStatus",
    "AlertSeverity",
    "BillingEnergyType",
    "InvoiceLineType",
    "BillingInvoiceStatus",
    "InsightStatus",
    # Achat Energie models
    "PurchaseAssumptionSet",
    "PurchasePreference",
    "PurchaseScenarioResult",
    "PurchaseStrategy",
    "PurchaseRecoStatus",
    # Action Hub (Sprint 10)
    "ActionItem",
    "ActionSyncBatch",
    "ActionSourceType",
    "ActionStatus",
    # Action Detail (Sprint V5.0)
    "ActionEvent",
    "ActionComment",
    "ActionEvidence",
    "AnomalyActionLink",
    "AnomalyDismissal",
    # Notifications (Sprint 10.2)
    "NotificationEvent",
    "NotificationBatch",
    "NotificationPreference",
    "WebhookSubscription",
    "DigestPreference",
    "NotificationSeverity",
    "NotificationStatus",
    "NotificationSourceType",
    # IAM (Users / Roles / Scopes)
    "User",
    "UserOrgRole",
    "UserScope",
    "AuditLog",
    "UserRole",
    "ScopeLevel",
    "PermissionAction",
    # Patrimoine / Staging (DIAMANT)
    "OrgEntiteLink",
    "PortfolioEntiteLink",
    "StagingBatch",
    "StagingSite",
    "StagingCompteur",
    "QualityFinding",
    "StagingStatus",
    "ImportSourceType",
    "QualityRuleSeverity",
    "ContractDeliveryPoint",
    "DeliveryPoint",
    "DeliveryPointStatus",
    "DeliveryPointEnergyType",
    # Smart Intake (DIAMANT)
    "IntakeSession",
    "IntakeAnswer",
    "IntakeFieldOverride",
    "IntakeSessionStatus",
    "IntakeMode",
    "IntakeSource",
    # Watchers
    "WatcherEventStatus",
    # Consumption World-Class (V10)
    "ConsumptionTarget",
    "TOUSchedule",
    # BACS Expert (Decret n°2020-887)
    "BacsAsset",
    "BacsCvcSystem",
    "BacsAssessment",
    "BacsInspection",
    "CvcSystemType",
    "CvcArchitecture",
    "BacsTriggerReason",
    "InspectionStatus",
    # EMS Consumption Explorer
    "EmsWeatherCache",
    "EmsSavedView",
    "EmsCollection",
    # Emission Factors (Sprint V9 Decarbonation)
    "EmissionFactor",
    # Tertiaire / OPERAT (V39)
    "TertiaireEfa",
    "TertiaireEfaLink",
    "TertiaireEfaBuilding",
    "TertiaireResponsibility",
    "TertiairePerimeterEvent",
    "TertiaireDeclaration",
    "TertiaireProofArtifact",
    "TertiaireDataQualityIssue",
    "TertiaireEfaConsumption",
    "EfaStatut",
    "EfaRole",
    "DeclarationStatus",
    "PerimeterEventType",
    "DataQualityIssueSeverity",
    "DataQualityIssueStatus",
    # V69: CEE Pipeline + M&V
    "WorkPackage",
    "CeeDossier",
    "CeeDossierEvidence",
    "WorkPackageSize",
    "CeeDossierStep",
    "CeeStatus",
    "MVAlertType",
    # V96: Payment Rules + Contract enums
    "PaymentRule",
    "PaymentRuleLevel",
    "ContractIndexation",
    "ContractStatus",
    "ReconciliationStatus",
    # V117: Anomaly-Action Link
    "AnomalyStatus",
    "DismissReason",
    "AnomalyActionLink",
    "AnomalyDismissal",
    # V97: Reconciliation Fix Log
    "ReconciliationFixLog",
    # V113: Energy Copilot
    "CopilotAction",
    "CopilotActionStatus",
    # V113: Action Templates
    "ActionTemplate",
    # V113: Onboarding Progress
    "OnboardingProgress",
    # Market Prices (Step 17)
    "MarketPrice",
    # Compliance Score History (Step 33)
    "ComplianceScoreHistory",
    # Action Plan Items (Workflow)
    "ActionPlanItem",
]
