"""
PROMEOS - Tous les enums du domaine
Fichier unique pour eviter les imports circulaires.
"""

import enum


# ========================================
# Enums sites & assets
# ========================================


class TypeSite(str, enum.Enum):
    """Types de sites gérés par PROMEOS — segments B2B France"""

    # Existants
    MAGASIN = "magasin"
    USINE = "usine"
    BUREAU = "bureau"
    ENTREPOT = "entrepot"
    # Nouveaux segments B2B
    COMMERCE = "commerce"
    COPROPRIETE = "copropriete"
    LOGEMENT_SOCIAL = "logement_social"
    COLLECTIVITE = "collectivite"
    HOTEL = "hotel"
    SANTE = "sante"
    ENSEIGNEMENT = "enseignement"


class TypeCompteur(str, enum.Enum):
    """Types de compteurs d'énergie"""

    ELECTRICITE = "electricite"
    GAZ = "gaz"
    EAU = "eau"


class SeveriteAlerte(str, enum.Enum):
    """Niveaux de sévérité des alertes énergétiques"""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class TypeUsage(str, enum.Enum):
    """Types d'usage énergétique"""

    BUREAUX = "bureaux"
    PROCESS = "process"
    FROID = "froid"
    CVC = "cvc"
    ECLAIRAGE = "eclairage"
    IT = "it"
    AUTRES = "autres"


# ========================================
# Enums conformité
# ========================================


class StatutConformite(str, enum.Enum):
    """Statut de conformité"""

    CONFORME = "conforme"
    DEROGATION = "derogation"
    A_RISQUE = "a_risque"
    NON_CONFORME = "non_conforme"


class TypeObligation(str, enum.Enum):
    """Types d'obligations réglementaires"""

    DECRET_TERTIAIRE = "decret_tertiaire"
    BACS = "bacs"
    APER = "aper"


class TypeEvidence(str, enum.Enum):
    """Types de preuves de conformité"""

    AUDIT = "audit"
    FACTURE = "facture"
    CERTIFICAT = "certificat"
    RAPPORT = "rapport"
    PHOTO = "photo"
    DECLARATION = "declaration"
    ATTESTATION_BACS = "attestation_bacs"
    DEROGATION_BACS = "derogation_bacs"


class StatutEvidence(str, enum.Enum):
    """Statut de la preuve"""

    VALIDE = "valide"
    EN_ATTENTE = "en_attente"
    MANQUANT = "manquant"
    EXPIRE = "expire"


# ========================================
# Enums RegOps / Lifecycle / Connectors
# ========================================


class ParkingType(str, enum.Enum):
    OUTDOOR = "outdoor"
    INDOOR = "indoor"
    UNDERGROUND = "underground"
    SILO = "silo"
    UNKNOWN = "unknown"


class OperatStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    UNKNOWN = "unknown"


class EnergyVector(str, enum.Enum):
    ELECTRICITY = "electricity"
    GAS = "gas"
    HEAT = "heat"
    WATER = "water"
    OTHER = "other"


class SourceType(str, enum.Enum):
    MANUAL = "manual"
    IMPORT = "import"
    API = "api"
    SCRAPE = "scrape"


class JobType(str, enum.Enum):
    RECOMPUTE_ASSESSMENT = "recompute_assessment"
    SYNC_CONNECTOR = "sync_connector"
    RUN_WATCHER = "run_watcher"
    RUN_AI_AGENT = "run_ai_agent"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class RegStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"
    OUT_OF_SCOPE = "out_of_scope"
    EXEMPTION_POSSIBLE = "exemption_possible"


class Severity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class InsightType(str, enum.Enum):
    EXPLAIN = "explain"
    SUGGEST = "suggest"
    CHANGE_IMPACT = "change_impact"
    EXEC_BRIEF = "exec_brief"
    DATA_QUALITY = "data_quality"


class RegulationType(str, enum.Enum):
    TERTIAIRE_OPERAT = "tertiaire_operat"
    BACS = "bacs"
    APER = "aper"
    CEE_P6 = "cee_p6"


class Typologie(str, enum.Enum):
    """Segment client detecte par la segmentation."""

    TERTIAIRE_PRIVE = "tertiaire_prive"
    TERTIAIRE_PUBLIC = "tertiaire_public"
    INDUSTRIE = "industrie"
    COMMERCE_RETAIL = "commerce_retail"
    COPROPRIETE_SYNDIC = "copropriete_syndic"
    BAILLEUR_SOCIAL = "bailleur_social"
    COLLECTIVITE = "collectivite"
    HOTELLERIE_RESTAURATION = "hotellerie_restauration"
    SANTE_MEDICO_SOCIAL = "sante_medico_social"
    ENSEIGNEMENT = "enseignement"
    MIXTE = "mixte"


# ========================================
# Enums Bill Intelligence
# ========================================


class BillingEnergyType(str, enum.Enum):
    """Type d'energie pour les contrats et factures."""

    ELEC = "elec"
    GAZ = "gaz"


class InvoiceLineType(str, enum.Enum):
    """Types de lignes d'une facture energie."""

    ENERGY = "energy"
    NETWORK = "network"
    TAX = "tax"
    OTHER = "other"


class BillingInvoiceStatus(str, enum.Enum):
    """Statut d'une facture energie persistee."""

    IMPORTED = "imported"
    VALIDATED = "validated"
    AUDITED = "audited"
    ANOMALY = "anomaly"
    ARCHIVED = "archived"


class InsightStatus(str, enum.Enum):
    """Statut workflow d'un insight de facturation (ops)."""

    OPEN = "open"
    ACK = "ack"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


# ========================================
# Enums Achat Energie
# ========================================


class PurchaseStrategy(str, enum.Enum):
    """Strategie d'achat energie."""

    FIXE = "fixe"
    INDEXE = "indexe"
    SPOT = "spot"
    REFLEX_SOLAR = "reflex_solar"


class PurchaseRecoStatus(str, enum.Enum):
    """Statut de la recommandation d'achat."""

    DRAFT = "draft"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


# ========================================
# Enums Action Hub (Sprint 10)
# ========================================


class ActionSourceType(str, enum.Enum):
    """Source brique generatrice de l'action."""

    COMPLIANCE = "compliance"
    CONSUMPTION = "consumption"
    BILLING = "billing"
    PURCHASE = "purchase"
    INSIGHT = "insight"  # from monitoring insight/alert
    MANUAL = "manual"  # manually created by user
    SEGMENTATION = "segmentation"  # V101: from segmentation recommendations
    COPILOT = "copilot"  # V113: from Energy Copilot rule engine


class ActionStatus(str, enum.Enum):
    """Statut workflow d'une action du hub."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"
    FALSE_POSITIVE = "false_positive"


# ========================================
# Enums Notifications (Sprint 10.2)
# ========================================


class NotificationSeverity(str, enum.Enum):
    """Severite d'un evenement notification."""

    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class NotificationStatus(str, enum.Enum):
    """Statut lifecycle d'une notification."""

    NEW = "new"
    READ = "read"
    DISMISSED = "dismissed"


class NotificationSourceType(str, enum.Enum):
    """Source brique generatrice de la notification."""

    COMPLIANCE = "compliance"
    BILLING = "billing"
    PURCHASE = "purchase"
    CONSUMPTION = "consumption"
    ACTION_HUB = "action_hub"


# ========================================
# Enums IAM (Users / Roles / Scopes)
# ========================================


class UserRole(str, enum.Enum):
    """11 roles metier PROMEOS."""

    DG_OWNER = "dg_owner"
    DSI_ADMIN = "dsi_admin"
    DAF = "daf"
    ACHETEUR = "acheteur"
    RESP_CONFORMITE = "resp_conformite"
    ENERGY_MANAGER = "energy_manager"
    RESP_IMMOBILIER = "resp_immobilier"
    RESP_SITE = "resp_site"
    PRESTATAIRE = "prestataire"
    AUDITEUR = "auditeur"
    PMO_ACC = "pmo_acc"


class ScopeLevel(str, enum.Enum):
    """Niveau de scope hierarchique."""

    ORG = "org"
    ENTITE = "entite"
    SITE = "site"


class PermissionAction(str, enum.Enum):
    """Actions granulaires."""

    VIEW = "view"
    EDIT = "edit"
    ADMIN = "admin"
    EXPORT = "export"
    SYNC = "sync"
    APPROVE = "approve"


# ========================================
# Enums Patrimoine / Staging (DIAMANT)
# ========================================


class StagingStatus(str, enum.Enum):
    """Statut d'un batch d'import staging."""

    DRAFT = "draft"
    VALIDATED = "validated"
    APPLIED = "applied"
    ABANDONED = "abandoned"


class ImportSourceType(str, enum.Enum):
    """Source d'un import patrimoine."""

    EXCEL = "excel"
    CSV = "csv"
    INVOICE = "invoice"
    MANUAL = "manual"
    DEMO = "demo"
    API = "api"


class QualityRuleSeverity(str, enum.Enum):
    """Severite d'un finding de qualite."""

    CRITICAL = "critical"
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class ActivationLogStatus(str, enum.Enum):
    """Statut d'une tentative d'activation batch."""

    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeliveryPointStatus(str, enum.Enum):
    """Statut d'un point de livraison (PRM/PCE)."""

    ACTIVE = "active"
    INACTIVE = "inactive"


class DeliveryPointEnergyType(str, enum.Enum):
    """Type d'energie du point de livraison."""

    ELEC = "elec"
    GAZ = "gaz"


# ========================================
# Enums Smart Intake (DIAMANT)
# ========================================


class IntakeSessionStatus(str, enum.Enum):
    """Statut lifecycle d'une session d'intake."""

    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class IntakeMode(str, enum.Enum):
    """Mode d'une session d'intake."""

    WIZARD = "wizard"
    CHAT = "chat"
    BULK = "bulk"
    DEMO = "demo"


class IntakeSource(str, enum.Enum):
    """Source d'une reponse intake."""

    USER = "user"
    IMPORT = "import"
    SYSTEM = "system"
    SYSTEM_DEMO = "system_demo"
    AI_PREFILL = "ai_prefill"


class WatcherEventStatus(str, enum.Enum):
    """Pipeline status for watcher events."""

    NEW = "new"
    REVIEWED = "reviewed"
    APPLIED = "applied"
    DISMISSED = "dismissed"


# ========================================
# Enums BACS Expert (Decret n°2020-887)
# ========================================


class CvcSystemType(str, enum.Enum):
    """Type de systeme CVC pour inventaire BACS."""

    HEATING = "heating"
    COOLING = "cooling"
    VENTILATION = "ventilation"


class CvcArchitecture(str, enum.Enum):
    """Architecture d'installation CVC (impacte le calcul Putile)."""

    CASCADE = "cascade"
    NETWORK = "network"
    INDEPENDENT = "independent"


class BacsTriggerReason(str, enum.Enum):
    """Raison declenchante de l'obligation BACS."""

    THRESHOLD_290 = "threshold_290"
    THRESHOLD_70 = "threshold_70"
    RENEWAL = "renewal"
    NEW_CONSTRUCTION = "new_construction"


class InspectionStatus(str, enum.Enum):
    """Statut d'une inspection quinquennale BACS."""

    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    OVERDUE = "overdue"


# ========================================
# Enums Tertiaire / OPERAT (V39)
# ========================================


class EfaStatut(str, enum.Enum):
    """Statut d'une EFA (Entite Fonctionnelle Assujettie)."""

    ACTIVE = "active"
    CLOSED = "closed"
    DRAFT = "draft"


class EfaRole(str, enum.Enum):
    """Role de l'assujetti dans l'EFA."""

    PROPRIETAIRE = "proprietaire"
    LOCATAIRE = "locataire"
    MANDATAIRE = "mandataire"


class DeclarationStatus(str, enum.Enum):
    """Statut d'une declaration annuelle OPERAT."""

    DRAFT = "draft"
    PRECHECKED = "prechecked"
    EXPORTED = "exported"
    SUBMITTED_SIMULATED = "submitted_simulated"


class PerimeterEventType(str, enum.Enum):
    """Type d'evenement de perimetre EFA."""

    CHANGEMENT_OCCUPANT = "changement_occupant"
    VACANCE = "vacance"
    RENOVATION_MAJEURE = "renovation_majeure"
    SCISSION = "scission"
    FUSION = "fusion"
    CHANGEMENT_USAGE = "changement_usage"
    AUTRE = "autre"


class DataQualityIssueSeverity(str, enum.Enum):
    """Severite d'une issue qualite tertiaire."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataQualityIssueStatus(str, enum.Enum):
    """Statut workflow d'une issue qualite tertiaire."""

    OPEN = "open"
    ACK = "ack"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


# ========================================
# Enums V69: CEE Pipeline + M&V
# ========================================


class WorkPackageSize(str, enum.Enum):
    """Taille du package de travaux."""

    S = "S"
    M = "M"
    L = "L"


class CeeDossierStep(str, enum.Enum):
    """Étapes kanban du dossier CEE."""

    DEVIS = "devis"
    ENGAGEMENT = "engagement"
    TRAVAUX = "travaux"
    PV_PHOTOS = "pv_photos"
    MV = "mv"
    VERSEMENT = "versement"


class CeeStatus(str, enum.Enum):
    """Statut CEE d'un work package."""

    A_QUALIFIER = "a_qualifier"
    OK = "ok"
    NON = "non"


class MVAlertType(str, enum.Enum):
    """Types d'alertes M&V."""

    BASELINE_DRIFT = "baseline_drift"
    DEADLINE_APPROACHING = "deadline_approaching"
    DATA_MISSING = "data_missing"


# ── V96: Patrimoine Unique Monde ──────────────────────────────────────────


class PaymentRuleLevel(str, enum.Enum):
    """Niveau d'application d'une regle de paiement."""

    PORTEFEUILLE = "portefeuille"
    SITE = "site"
    CONTRAT = "contrat"


class ContractIndexation(str, enum.Enum):
    """Type d'indexation d'un contrat energie."""

    FIXE = "fixe"
    INDEXE = "indexe"
    SPOT = "spot"
    HYBRIDE = "hybride"


class ContractStatus(str, enum.Enum):
    """Statut lifecycle d'un contrat energie."""

    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"


class ReconciliationStatus(str, enum.Enum):
    """Statut de reconciliation 3 voies."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


# ========================================
# Enums Anomaly-Action Link
# ========================================


class AnomalyStatus(str, enum.Enum):
    """Statut workflow d'une anomalie cross-domain."""

    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    LINKED = "linked"
    RESOLVED = "resolved"


class DismissReason(str, enum.Enum):
    """Motif d'ignorance d'une anomalie."""

    FALSE_POSITIVE = "false_positive"
    KNOWN_ISSUE = "known_issue"
    OUT_OF_SCOPE = "out_of_scope"
    DUPLICATE = "duplicate"
    OTHER = "other"
