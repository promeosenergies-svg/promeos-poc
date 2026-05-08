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


class UsageFamily(str, enum.Enum):
    """Familles d'usages energetiques (niveau 1 de la taxonomie)."""

    THERMIQUE = "thermique"  # CVC chaud + froid + ventilation + ECS
    ECLAIRAGE = "eclairage"  # Eclairage interieur & exterieur
    ELECTRICITE_SPECIFIQUE = "elec_specifique"  # IT, bureautique, ascenseurs
    PROCESS = "process"  # Production, air comprime, process metier
    MOBILITE = "mobilite"  # IRVE, transport vertical
    AUXILIAIRES = "auxiliaires"  # Parties communes, pertes, divers


class TypeUsage(str, enum.Enum):
    """Types d'usage energetique — taxonomie alignee ADEME/OPERAT.

    12 usages structures en 6 familles (UsageFamily).
    Anciens codes preserves pour retrocompat (BUREAUX→AUTRES, CVC→CHAUFFAGE).
    """

    # Famille THERMIQUE
    CHAUFFAGE = "chauffage"
    CLIMATISATION = "climatisation"
    VENTILATION = "ventilation"
    ECS = "ecs"  # Eau chaude sanitaire

    # Famille ECLAIRAGE
    ECLAIRAGE = "eclairage"

    # Famille ELECTRICITE SPECIFIQUE
    IT = "it"
    BUREAUTIQUE = "bureautique"  # Postes de travail, impression
    TRANSPORT_VERTICAL = "transport_vertical"  # Ascenseurs, escaliers mecaniques

    # Famille PROCESS
    PROCESS = "process"
    PRODUCTION = "production"  # Lignes de fabrication, air comprime

    # Famille MOBILITE
    IRVE = "irve"  # Bornes de recharge vehicules electriques

    # Famille AUXILIAIRES / AUTRES
    PARTIES_COMMUNES = "parties_communes"
    AUTRES = "autres"

    # --- Legacy aliases (pour retrocompat seeds/imports existants) ---
    BUREAUX = "bureaux"  # Legacy: type batiment, pas un usage
    CVC = "cvc"  # Legacy: utiliser CHAUFFAGE/CLIM/VENTILATION
    FROID = "froid"  # Legacy: utiliser CLIMATISATION


# Mapping TypeUsage → UsageFamily pour regroupement UI
USAGE_FAMILY_MAP: dict[TypeUsage, UsageFamily] = {
    TypeUsage.CHAUFFAGE: UsageFamily.THERMIQUE,
    TypeUsage.CLIMATISATION: UsageFamily.THERMIQUE,
    TypeUsage.VENTILATION: UsageFamily.THERMIQUE,
    TypeUsage.ECS: UsageFamily.THERMIQUE,
    TypeUsage.ECLAIRAGE: UsageFamily.ECLAIRAGE,
    TypeUsage.IT: UsageFamily.ELECTRICITE_SPECIFIQUE,
    TypeUsage.BUREAUTIQUE: UsageFamily.ELECTRICITE_SPECIFIQUE,
    TypeUsage.TRANSPORT_VERTICAL: UsageFamily.ELECTRICITE_SPECIFIQUE,
    TypeUsage.PROCESS: UsageFamily.PROCESS,
    TypeUsage.PRODUCTION: UsageFamily.PROCESS,
    TypeUsage.IRVE: UsageFamily.MOBILITE,
    TypeUsage.PARTIES_COMMUNES: UsageFamily.AUXILIAIRES,
    TypeUsage.AUTRES: UsageFamily.AUXILIAIRES,
    # Legacy
    TypeUsage.BUREAUX: UsageFamily.AUXILIAIRES,
    TypeUsage.CVC: UsageFamily.THERMIQUE,
    TypeUsage.FROID: UsageFamily.THERMIQUE,
}


# Labels FR pour affichage UI
USAGE_LABELS_FR: dict[TypeUsage, str] = {
    TypeUsage.CHAUFFAGE: "Chauffage",
    TypeUsage.CLIMATISATION: "Climatisation",
    TypeUsage.VENTILATION: "Ventilation",
    TypeUsage.ECS: "Eau chaude sanitaire",
    TypeUsage.ECLAIRAGE: "Éclairage",
    TypeUsage.IT: "IT / Datacenter",
    TypeUsage.BUREAUTIQUE: "Bureautique",
    TypeUsage.TRANSPORT_VERTICAL: "Transport vertical",
    TypeUsage.PROCESS: "Process",
    TypeUsage.PRODUCTION: "Production",
    TypeUsage.IRVE: "IRVE",
    TypeUsage.PARTIES_COMMUNES: "Parties communes",
    TypeUsage.AUTRES: "Autres",
    TypeUsage.BUREAUX: "Bureaux (legacy)",
    TypeUsage.CVC: "CVC (legacy)",
    TypeUsage.FROID: "Froid (legacy)",
}


class DataSourceType(str, enum.Enum):
    """Source / methode d'obtention de la donnee usage."""

    MESURE_DIRECTE = "mesure_directe"  # Sous-compteur physique
    ESTIMATION_PRORATA = "estimation_prorata"  # Pro-rata surface ou archetype
    IMPORT_CSV = "import_csv"  # Import fichier
    GTB_API = "gtb_api"  # Donnee GTB/GTC via API
    FACTURATION = "facturation"  # Derive de la facture
    MANUEL = "manuel"  # Saisie manuelle


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
    DPE_TERTIAIRE = "dpe_tertiaire"  # Décret 2024-1040
    CSRD = "csrd"  # Directive 2022/2464


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
    ATTESTATION_OMBRIERE_PV = "attestation_ombriere_pv"
    ATTESTATION_TOITURE_PV = "attestation_toiture_pv"
    ATTESTATION_TOITURE_VEGETALISEE = "attestation_toiture_vegetalisee"
    ATTESTATION_DPE = "attestation_dpe"  # Décret 2024-1040 — DPE tertiaire


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
    DPE_TERTIAIRE = "dpe_tertiaire"  # Décret 2024-1040
    CSRD = "csrd"  # Directive 2022/2464
    CEE_P6 = "cee_p6"  # Financement (pas dans score A.2)


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
    PILOTAGE = "pilotage"  # V116: from Pilotage Radar/ROI CTAs (Baromètre Flex 2026)


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


class DpeClasseEnergie(str, enum.Enum):
    """Classe DPE tertiaire (décret 2024-1040, arrêté du 25/03/2024)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    VIERGE = "vierge"  # Pas de DPE réalisé


class DpeClasseGes(str, enum.Enum):
    """Classe GES du DPE tertiaire."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    VIERGE = "vierge"


class CsrdScope(str, enum.Enum):
    """Scope GHG pour reporting CSRD/taxonomie."""

    SCOPE_1 = "scope_1"  # Émissions directes
    SCOPE_2 = "scope_2"  # Électricité, chaleur, vapeur achetées
    SCOPE_3 = "scope_3"  # Chaîne de valeur amont/aval


class CsrdAssujettissement(str, enum.Enum):
    """Critère d'assujettissement CSRD (directive 2022/2464)."""

    GRANDE_ENTREPRISE = "grande_entreprise"  # 2 des 3 critères: >250 salariés, >50M€ CA, >25M€ bilan
    PME_COTEE = "pme_cotee"  # PME cotée (>2026)
    FILIALE_UE = "filiale_ue"  # Filiale d'un groupe UE assujetti
    NON_ASSUJETTI = "non_assujetti"


class BacsExemptionType(str, enum.Enum):
    """Type de dérogation BACS (art. R.175-6)."""

    TRI_NON_VIABLE = "tri_non_viable"  # TRI > 10 ans
    IMPOSSIBILITE_TECHNIQUE = "impossibilite_technique"  # Contrainte technique
    PATRIMOINE_HISTORIQUE = "patrimoine_historique"  # Monument historique
    MISE_EN_VENTE = "mise_en_vente"  # Bâtiment en vente/démolition prévue


class BacsExemptionStatus(str, enum.Enum):
    """Statut de la demande de dérogation BACS."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


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
    # V2 Cadre+Annexe — modeles prix etendus
    FIXE_HORS_ACHEMINEMENT = "fixe_hors_acheminement"
    INDEXE_TRVE = "indexe_trve"
    INDEXE_PEG = "indexe_peg"
    INDEXE_SPOT = "indexe_spot"
    # V2 Phase 1 — modeles cadre
    TUNNEL = "tunnel"  # Prix encadre plancher/plafond
    CLIC = "clic"  # Fixation progressive par clicks


class ContractStatus(str, enum.Enum):
    """Statut lifecycle d'un contrat energie."""

    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    # V2 Cadre+Annexe — statuts etendus
    DRAFT = "draft"
    TERMINATED = "terminated"


class ReconciliationStatus(str, enum.Enum):
    """Statut de reconciliation 3 voies."""

    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


class TariffOptionEnum(str, enum.Enum):
    """Option tarifaire d'un point de livraison / contrat."""

    BASE = "base"  # C5 BT <=36 kVA — tarif unique (pas de differentiation horaire)
    HP_HC = "hp_hc"  # C5 BT <=36 kVA — Heures Pleines / Heures Creuses
    CU4 = "cu4"  # C4 BT >36 kVA — Courte Utilisation 4 postes (HPH/HCH/HPB/HCB)
    MU4 = "mu4"  # C4 BT >36 kVA — Moyenne Utilisation 4 postes (HPH/HCH/HPB/HCB)
    CU = "cu"  # C3 HTA — Courte Utilisation 5 postes (+POINTE)
    MU = "mu"  # C4 legacy TURPE 6 (deprecated — utiliser MU4 pour TURPE 7)
    LU = "lu"  # C3/C4 — Longue Utilisation 5 postes (+POINTE)


class TariffSegmentEnum(str, enum.Enum):
    """Segment TURPE d'un point de livraison."""

    C5_BT = "c5_bt"  # BT ≤ 36 kVA
    C4_BT = "c4_bt"  # BT > 36 kVA ≤ 250 kVA
    C3_HTA = "c3_hta"  # HTA (C1-C4 dans la nomenclature Enedis)


class HcReprogPhase(str, enum.Enum):
    """Phase de reprogrammation HC Enedis (TURPE 7)."""

    PHASE_1 = "phase_1"  # Nov 2025 → Avr 2026, HC non saisonnalisées
    PHASE_2 = "phase_2"  # Nov 2026+, HC saisonnalisées (été/hiver)
    PHASE_3 = "phase_3"  # S2 2027 → Août 2028, C1-C4 (HTA/BT>36kVA)
    HORS_PERIMETRE = "hors_perimetre"  # Pas concerné


class HcReprogStatus(str, enum.Enum):
    """Statut de reprogrammation HC d'un PRM (fichiers Enedis M-6/M-2/CR-M)."""

    A_TRAITER = "a_traiter"  # Reprogrammation prévue
    EN_COURS = "en_cours"  # Téléopération concurrente, retry
    TRAITE = "traite"  # Reprogrammation réussie (ou MES)
    ABANDON = "abandon"  # Échec après 30 jours de tentatives


class InvoiceTypeEnum(str, enum.Enum):
    """Type de facture énergie."""

    NORMAL = "normal"  # Facture de consommation standard
    ADVANCE = "advance"  # Acompte / mensualisation
    REGULARIZATION = "regularization"  # Régularisation
    CREDIT_NOTE = "credit_note"  # Avoir


class ReconstitutionStatusEnum(str, enum.Enum):
    """Statut de la reconstitution moteur billing."""

    RECONSTITUTED = "reconstituted"
    PARTIAL = "partial"
    READ_ONLY = "read_only"
    UNSUPPORTED = "unsupported"


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


# ========================================
# Enums Market Intelligence
# ========================================


class ArticleCategory(str, enum.Enum):
    """Catégories d'articles EuropEnergies / veille marché."""

    FLASH = "flash"
    GROS_PLAN = "gros_plan"
    EDITORIAL = "editorial"
    MARKET_REVIEW = "market_review"
    GO_AUCTION = "go_auction"
    GEOPOLITICS = "geopolitics"
    REGULATORY = "regulatory"
    BUYER_PROFILE = "buyer_profile"
    SELLER_PROFILE = "seller_profile"
    EXPERT_OPINION = "expert_opinion"
    TECHNICAL = "technical"


class ArticleSource(str, enum.Enum):
    """Sources de veille marché."""

    EUROP_ENERGIES = "europ_energies"
    CRE = "cre"
    RTE = "rte"
    LEGIFRANCE = "legifrance"
    MANUAL = "manual"


# ============================================================
# Vague 1 data model — TaxProfile + pass-through policies
# ============================================================


class AcciseCategoryElec(str, enum.Enum):
    """Catégorie d'accise électricité par point de livraison (CIBS)."""

    HOUSEHOLD = "HOUSEHOLD"  # ménages & assimilés
    SME = "SME"  # PME / petites entreprises
    HIGH_POWER = "HIGH_POWER"  # sites à haute puissance
    REDUCED = "REDUCED"  # régime réduit (électro-intensif, double usage...)
    EXEMPT = "EXEMPT"  # exonération totale


class AcciseCategoryGaz(str, enum.Enum):
    """Catégorie d'accise gaz naturel par point de livraison (CIBS)."""

    NORMAL = "NORMAL"  # régime normal (tarif plein)
    REDUCED = "REDUCED"  # régime réduit
    EXEMPT = "EXEMPT"  # exonération (procédés industriels, double usage)


class NetworkCostModel(str, enum.Enum):
    """
    Politique de refacturation des coûts d'acheminement par le fournisseur.

    - INCLUDED : TURPE/ATRD inclus dans le prix de fourniture, non visible sur facture
    - FULL_PASS_THROUGH : TURPE/ATRD refacturé au réel, ligne séparée
    - FLAT_UNIT_COST : taux moyen €/MWh appliqué indépendamment de la grille réelle
    - MARGINATED : passthrough + marge fournisseur
    """

    INCLUDED = "INCLUDED"
    FULL_PASS_THROUGH = "FULL_PASS_THROUGH"
    FLAT_UNIT_COST = "FLAT_UNIT_COST"
    MARGINATED = "MARGINATED"


# ============================================================
# Vague 2 data model — ATRD options + profil gaz GRDF
# ============================================================


class AtrdOption(str, enum.Enum):
    """
    Option tarifaire ATRD7 GRDF (distribution gaz).

    Seuils CAR en kWh/an — la colonne `DeliveryPoint.car_kwh` et la fonction
    `derive_atrd_option_from_car(car_kwh)` travaillent en kWh :
    - T1 : 0 – 6 000 kWh/an           (petits consommateurs, cuisson)
    - T2 : 6 000 – 300 000 kWh/an     (résidentiel chauffage, petits pros)
    - T3 : 300 000 – 5 000 000 kWh/an (tertiaire, PME)
    - T4 : > 5 000 000 kWh/an         (gros industriels — abo + capacité journalière)
    - TP : tarif de proximité (industriels dédiés, non dérivable — négocié)
    """

    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    TP = "TP"


class GasProfileGrdf(str, enum.Enum):
    """Profil de consommation gaz GRDF (déterminé par usage + CAR)."""

    BASE = "BASE"  # profil plat (usage industriel régulier)
    B0 = "B0"  # cuisson uniquement (faible saisonnalité)
    B1 = "B1"  # chauffage individuel résidentiel
    B2I = "B2I"  # chauffage collectif ou tertiaire
    MODULANT = "MODULANT"  # gros site avec courbe de charge


# ========================================
# Enums OPERAT / APER (Sprint C-1 Phase 3 — matrice v1 §4.4.C/D)
# ========================================
#
# Convention SQLAlchemy : utiliser sa.Enum(<EnumClass>, native_enum=False) sur
# les colonnes Site → SQLite reçoit un CHECK constraint listant les valeurs,
# PostgreSQL (cible roadmap) recevra un type ENUM natif sans cassure.


class OperatZoneClimatiqueEnum(str, enum.Enum):
    """13 zones climatiques OPERAT (8 métropole + 5 DOM).

    Source primaire : Annexe III arrêté 10/04/2020 NOR LOGL2005904A,
    version consolidée 07/09/2025 (modifié par arrêté 01/08/2025
    NOR ATDL2430864A). Confidence 🟢 — recoupement direct PDF Légifrance v2.

    ⚠️ Réunion (pas "La Réunion") : la chaîne authentifiée Annexe III utilise
    "Réunion". Annexe I peut écrire "La Réunion" → normalisation requise dans
    OperatValeursAbsoluesService (Sprint C-1 Phase 4).
    """

    H1A = "H1a"
    H1B = "H1b"
    H1C = "H1c"
    H2A = "H2a"
    H2B = "H2b"
    H2C = "H2c"
    H2D = "H2d"
    H3 = "H3"
    GUADELOUPE = "Guadeloupe"
    MARTINIQUE = "Martinique"
    GUYANE = "Guyane"
    REUNION = "Réunion"
    MAYOTTE = "Mayotte"


class OperatPalierAltitudeEnum(str, enum.Enum):
    """5 paliers altitude OPERAT (palier strict, pas interpolation).

    Source primaire : Annexe I arrêté 01/08/2025 NOR ATDL2430864A.
    Le CVCi de chaque sous-catégorie est tabulé pour chacun de ces 5 paliers
    × 13 zones climatiques. Le palier est lu strictement, sans interpolation.
    """

    LT_400 = "alt_lt_400"
    BETW_400_800 = "alt_400_800"
    BETW_800_1200 = "alt_800_1200"
    BETW_1200_1600 = "alt_1200_1600"
    GTE_1600 = "alt_gte_1600"


class OperatUsagePrincipalEnum(str, enum.Enum):
    """Usage principal d'un site assujetti OPERAT (matrice v1 §4.4.C #32).

    Catégorie macro qui guide le choix du sous-catégorie (operat_sous_categorie_id).
    """

    BUREAUX = "BUREAUX"
    COMMERCES = "COMMERCES"
    ENSEIGNEMENT = "ENSEIGNEMENT"
    HOTELLERIE = "HOTELLERIE"
    RESTAURATION = "RESTAURATION"
    SANTE = "SANTE"
    SPORT_LOISIRS = "SPORT_LOISIRS"
    LOGISTIQUE = "LOGISTIQUE"
    MIXTE = "MIXTE"


class OperatModulationMotifEnum(str, enum.Enum):
    """4 motifs officiels de modulation DT.

    Source primaire : Arrêté 10/04/2020 art. 12 — dossier de modulation
    (dépôt avant 30/09/2026 selon échéance Décret Tertiaire).
    """

    COUT_DISPROPORTIONNE = "COUT_DISPROPORTIONNE"
    CONSEQUENCES_NEGATIVES = "CONSEQUENCES_NEGATIVES"
    PATRIMOINE_INCOMPATIBILITE = "PATRIMOINE_INCOMPATIBILITE"
    CHANGEMENT_ACTIVITE = "CHANGEMENT_ACTIVITE"


class AperCategorieTailleEnum(str, enum.Enum):
    """Catégories de taille parking pour APER.

    Source primaire : Loi 2023-175 art. 40 + Décret 2024-1023.
    - SMALL : 1 500 - 10 000 m² → deadline 01/07/2028
    - LARGE : > 10 000 m²       → deadline 01/07/2026
    """

    SMALL = "SMALL"
    LARGE = "LARGE"


class AperExemptionMotifEnum(str, enum.Enum):
    """4 motifs officiels d'exemption APER (matrice v1 §4.4.D #41)."""

    CONTRAINTES_TECHNIQUES = "CONTRAINTES_TECHNIQUES"
    CONTRAINTES_PATRIMONIALES = "CONTRAINTES_PATRIMONIALES"
    CONTRAINTES_ECONOMIQUES = "CONTRAINTES_ECONOMIQUES"
    CONTRAINTES_OPERATIONNELLES = "CONTRAINTES_OPERATIONNELLES"


# ============================================================
# Phase D-2.2 ajustée — Enum FtaCode CRE TURPE 7 canonique
# ============================================================
# Source : CRE délibération n°2025-78 du 13/03/2025 (TURPE 7 HTA-BT).
# Audit cardinal : docs/audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md.
# Pattern Pilier 9 ADR-016 : "Validator permissif transitoire (regex Phase D-1bis)
# → Enum strict canonique post-audit officiel" (cf. docs/adr/ADR-016-anti-patterns-piliers-7-8-9.md).
#
# La liste canonique reste sous medium-confidence (suffixes 4/5 postes à
# confirmer parsing PDF délibération 2025-78 Phase D-3). En attendant, l'Enum
# strict ci-dessous est le SoT exécutable (importé depuis doctrine/constants.py
# via CANONICAL_FTA_CODES_TURPE_7).


class FtaCode(str, enum.Enum):
    """Codes FTA canoniques CRE TURPE 7 (Formule Tarifaire d'Acheminement).

    Préfixe segment : BTINF (C5) / BTSUP (C4) / HTA (C3-C2) / HTB (C1).
    Suffixe durée : CU (courte) / MU (moyenne BT only) / LU (longue).
    Suffixe nb postes : 4 (BT) ou 5 (HTA + PTE).

    À élargir Phase D-3 post parsing PDF délibération 2025-78.
    """

    BTINFCU4 = "BTINFCU4"  # C5 BT≤36kVA — courte util. 4 postes (HPH/HCH/HPE/HCE)
    BTINFMU4 = "BTINFMU4"  # C5 BT≤36kVA — moyenne util. 4 postes
    BTSUPCU = "BTSUPCU"  # C4 BT>36kVA — courte util.
    BTSUPLU = "BTSUPLU"  # C4 BT>36kVA — longue util.
    HTACU5 = "HTACU5"  # C3/C2 HTA — courte util. 5 postes (PTE/HPH/HCH/HPE/HCE)
    HTALU5 = "HTALU5"  # C3/C2 HTA — longue util. 5 postes


# ============================================================
# Phase D-3 Tier 2 DOC-1 — 5 String→Enum Pilier 9 ADR-016 régularisation
# ============================================================
# Sources : audit Phase D commit 147d872b (P1-AUDIT-D-007 à -011).
# Pattern Pilier 9 ADR-016 (Phase D-1bis → Phase D-2.2 FtaCode) reproduit pour
# 5 nouveaux champs String hérités Phase D-0/D-1 où des Enum existaient ou
# devaient être créés.


class VersionTurpeEnum(str, enum.Enum):
    """Version TURPE active sur un point de livraison (CRE 2025-78 cardinal).

    Phase D-3 Tier 2 : Enum strict pour `DeliveryPoint.version_turpe` (était String(10)).
    """

    TURPE_6 = "TURPE_6"
    TURPE_7 = "TURPE_7"


class ModeTraitementEnum(str, enum.Enum):
    """Mode traitement compteur Enedis (matrice v1 §4.6).

    Phase D-3 Tier 2 : Enum strict pour `DeliveryPoint.mode_traitement` (était String(20)).
    """

    SMART = "smart"
    TRADITIONNEL = "traditionnel"
    TELERELEVE = "telereleve"
    MANUEL = "manuel"


class SubMeterUsageEnum(str, enum.Enum):
    """Usage sous-compteur D6 (différenciateur PROMEOS Mid-market premium).

    Phase D-3 Tier 2 : Enum strict pour `Compteur.sub_meter_usage` (était String(50)).
    Aligné UsageFamily (THERMIQUE/ELECTRICITE_SPECIFIQUE/ECLAIRAGE/PROCESS/AUXILIAIRES)
    en granularité usage atomique pour pilotage runtime CVC/IT/éclairage.
    """

    CVC = "CVC"  # Chauffage / Ventilation / Climatisation
    IT = "IT"  # Informatique / Datacenter
    ECLAIRAGE = "ECLAIRAGE"  # Éclairage interieur/exterieur
    PROCESS = "PROCESS"  # Production / process metier
    IRVE = "IRVE"  # Bornes de recharge VE
    AUTRES = "AUTRES"  # Auxiliaires / parties communes / divers


# ============================================================
# Phase D-4 Tier 1 — 6 Enums cardinaux matrice v1 §4.6 + ADR-D-02 + ADR-D-05
# ============================================================
# Sources :
#   - PCE format : CRE Délib. 2025-161 + smart.grtgaz.com (ADR-D-02 + Phase D-3 Tier 2)
#   - Accise CIBS : L.312-24 (gaz) + L.312-36/37 (élec) + arrêté 27/01/2026 (ADR-D-05)
#   - Mode releve : ATRD 7 GRDF référentiel (matrice v1 §4.6.C#8)


class PceFormatEnum(str, enum.Enum):
    """Format PCE/PRM gaz (matrice v1 §4.6.C#2 — ADR-D-02).

    Phase D-4 Tier 1 : matérialisation Enum pour audit traçabilité + perf query.
    Validator regex `code` Phase D-3 Tier 2 garantit la cohérence cross-FK.
    """

    DISTRIBUTION_14 = "DISTRIBUTION_14"  # 14 chiffres — Enedis PRM élec OU GRDF résidentiel/petit pro
    DISTRIBUTION_GI = "DISTRIBUTION_GI"  # GI + 6 chiffres — GRDF gros industriel distribution
    TRANSPORT_PIR = "TRANSPORT_PIR"  # IR + 4 chiffres — Point Interconnexion Réseau GRTgaz/NaTran/Teréga


class TypeReseauEnum(str, enum.Enum):
    """Type de réseau gaz (matrice v1 §4.6.C#3 — ADR-D-02).

    Détermine routage référentiel tarifaire (ATRD distribution / ATRT transport).
    """

    DISTRIBUTION = "DISTRIBUTION"  # GRDF + 21 ELD locales
    TRANSPORT = "TRANSPORT"  # GRTgaz + NaTran + Teréga


class ReferentielTarifaireEnum(str, enum.Enum):
    """Référentiel tarifaire gaz (matrice v1 §4.6.C#5 — ADR-D-02).

    Déductible de type_reseau mais matérialisé pour traçabilité audit + perf billing.
    """

    ATRD = "ATRD"  # Accès Tarifs Réseau Distribution (GRDF + ELD)
    ATRT = "ATRT"  # Accès Tarifs Réseau Transport (GRTgaz + NaTran + Teréga)


class ModeReleveGazEnum(str, enum.Enum):
    """Mode relevé compteur gaz (matrice v1 §4.6.C#8).

    Détermine granularité ingestion CDC + facturation.
    """

    MM = "MM"  # Mensuel Mensuel (relevé mensuel facturation mensuelle)
    MJ = "MJ"  # Mensuel Journalier (relevé mensuel CDC journalière)
    JJ = "JJ"  # Journalier Journalier (relevé + facturation quotidiens)
    MH = "MH"  # Mensuel Horaire (relevé mensuel CDC horaire)


class AcciseCategorieElec(str, enum.Enum):
    """Catégorie accise électricité CIBS (matrice v1 §4.6.B#16 — ADR-D-05).

    Source : CIBS L.312-36/37 + arrêté 27/01/2026 (JORFTEXT000053407616).
    Détermine taux d'accise applicable :
    - MENAGES_ASSIMILES : T1 = 30.85 EUR/MWh
    - PME : T2 = 26.58 EUR/MWh
    - HAUTE_PUISSANCE : HP = 5.71 EUR/MWh (>10 GWh/an industriel)
    """

    MENAGES_ASSIMILES = "MENAGES_ASSIMILES"
    PME = "PME"
    HAUTE_PUISSANCE = "HAUTE_PUISSANCE"


class AcciseCategorieGaz(str, enum.Enum):
    """Catégorie accise gaz CIBS (matrice v1 §4.6.C#18 — ADR-D-05).

    Source : CIBS L.312-24 + arrêté 27/01/2026 (JORFTEXT000053407616).
    Taux 2026 = 10.73 EUR/MWh pour gaz naturel — taux différenciés GPL/GNL.
    """

    NATUREL = "NATUREL"  # Gaz naturel (taux principal)
    GPL = "GPL"  # Gaz de Pétrole Liquéfié
    GNL = "GNL"  # Gaz Naturel Liquéfié


# ============================================================
# Phase D-4 Tier 2 — Enums P1 doctrine cardinaux matrice v1
# ============================================================


class UsageBatimentEnum(str, enum.Enum):
    """Usage principal bâtiment (matrice v1 §4.5#9).

    Différencié de Site.usage_principal pour cas multi-bâtiments multi-usages
    (ex. site mixte commerce+bureaux avec bâtiment principal commerce).
    """

    BUREAUX = "BUREAUX"
    COMMERCES = "COMMERCES"
    ENSEIGNEMENT = "ENSEIGNEMENT"
    HOTELLERIE = "HOTELLERIE"
    RESTAURATION = "RESTAURATION"
    SANTE = "SANTE"
    SPORT_LOISIRS = "SPORT_LOISIRS"
    LOGISTIQUE = "LOGISTIQUE"
    PARKING = "PARKING"  # Parking couvert/silo (différent surface tertiaire)
    TECHNIQUE = "TECHNIQUE"  # Local technique CVC/IT/transformateur
    MIXTE = "MIXTE"


class IndiceReferenceEnum(str, enum.Enum):
    """Indice de référence pour formule indexation contrat (matrice v1 §4.8.C#5).

    Source : indices marché énergie standards FR/UE.
    """

    EEX_BASE = "EEX_BASE"  # Indice EEX base (ruban élec)
    EEX_PEAK = "EEX_PEAK"  # Indice EEX peak (heures pleines)
    PEG = "PEG"  # Point d'Échange Gaz (FR)
    TTF = "TTF"  # Title Transfer Facility (NL — référence UE)
    SPOT_FR = "SPOT_FR"  # Spot day-ahead France
    FORWARD_CAL = "FORWARD_CAL"  # Forward calendrier annuel
    FORWARD_TRIM = "FORWARD_TRIM"  # Forward trimestriel
    FIXE = "FIXE"  # Prix fixe (pas d'indexation)
