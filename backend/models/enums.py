"""
PROMEOS - Tous les enums du domaine
Fichier unique pour eviter les imports circulaires.
"""
import enum


# ========================================
# Enums sites & assets
# ========================================

class TypeSite(str, enum.Enum):
    """Types de sites gérés par PROMEOS"""
    MAGASIN = "magasin"
    USINE = "usine"
    BUREAU = "bureau"
    ENTREPOT = "entrepot"


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
