"""
PROMEOS Bill Intelligence — Domain Model
Modele canonique pour factures energie (elec + gaz).

Niveaux de shadow billing :
- L0 : Read & Explain (parsing + affichage structure)
- L1 : Partial Shadow (arithmetique + TVA + prorata + coherences)
- L2 : Component Shadow (composantes si doc+data)
- L3 : Full Shadow (recalcul complet, optionnel)

Chaque facture porte son niveau + "why_not_higher".
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any


# ========================================
# Enums
# ========================================

class EnergyType(str, Enum):
    ELEC = "elec"
    GAZ = "gaz"


class InvoiceStatus(str, Enum):
    IMPORTED = "imported"
    PARSED = "parsed"
    AUDITED = "audited"
    RECONCILED = "reconciled"
    ARCHIVED = "archived"


class ShadowLevel(str, Enum):
    L0_READ = "L0"
    L1_PARTIAL = "L1"
    L2_COMPONENT = "L2"
    L3_FULL = "L3"


class ComponentType(str, Enum):
    """Types de composantes d'une facture energie."""
    # Abonnement / fixe
    ABONNEMENT = "abonnement"
    # Consommation
    CONSO_HP = "conso_hp"
    CONSO_HC = "conso_hc"
    CONSO_BASE = "conso_base"
    CONSO_POINTE = "conso_pointe"
    CONSO_HPH = "conso_hph"
    CONSO_HCH = "conso_hch"
    CONSO_HPE = "conso_hpe"
    CONSO_HCE = "conso_hce"
    # Acheminement / reseau
    TURPE_FIXE = "turpe_fixe"
    TURPE_PUISSANCE = "turpe_puissance"
    TURPE_ENERGIE = "turpe_energie"
    # Capacite / depassement
    DEPASSEMENT_PUISSANCE = "depassement_puissance"
    REACTIVE = "reactive"
    # Taxes
    CTA = "cta"
    ACCISE = "accise"
    TVA_REDUITE = "tva_reduite"
    TVA_NORMALE = "tva_normale"
    # Gaz specifique
    TERME_FIXE = "terme_fixe"
    TERME_VARIABLE = "terme_variable"
    CEE = "cee"
    # Divers
    PRORATA = "prorata"
    REGULARISATION = "regularisation"
    PENALITE = "penalite"
    REMISE = "remise"
    AUTRE = "autre"


class AnomalyType(str, Enum):
    """Types d'anomalies detectees par l'audit."""
    ARITHMETIC_ERROR = "arithmetic_error"
    TVA_ERROR = "tva_error"
    PRORATA_ERROR = "prorata_error"
    MISSING_COMPONENT = "missing_component"
    DUPLICATE_CHARGE = "duplicate_charge"
    PERIOD_OVERLAP = "period_overlap"
    PERIOD_GAP = "period_gap"
    UNIT_PRICE_ANOMALY = "unit_price_anomaly"
    QUANTITY_ANOMALY = "quantity_anomaly"
    TAX_BASE_ERROR = "tax_base_error"
    TURPE_MISMATCH = "turpe_mismatch"
    SUBSCRIPTION_MISMATCH = "subscription_mismatch"
    INDEX_INCONSISTENCY = "index_inconsistency"
    ROUNDING_ERROR = "rounding_error"
    TOTAL_MISMATCH = "total_mismatch"
    OTHER = "other"


class AnomalySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ========================================
# Dataclasses
# ========================================

@dataclass
class InvoiceComponent:
    """Une ligne/composante d'une facture."""
    component_type: ComponentType
    label: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    amount_ht: Optional[float] = None
    amount_ttc: Optional[float] = None
    tva_rate: Optional[float] = None
    tva_amount: Optional[float] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    """Facture energie canonique."""
    invoice_id: str
    energy_type: EnergyType
    supplier: str
    contract_ref: Optional[str] = None
    pdl_pce: Optional[str] = None  # Point de Livraison / Point de Comptage
    site_id: Optional[int] = None

    # Dates
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None

    # Montants globaux
    total_ht: Optional[float] = None
    total_tva: Optional[float] = None
    total_ttc: Optional[float] = None

    # Composantes
    components: List[InvoiceComponent] = field(default_factory=list)

    # Consommation
    conso_kwh: Optional[float] = None
    puissance_souscrite_kva: Optional[float] = None

    # Metadata
    status: InvoiceStatus = InvoiceStatus.IMPORTED
    source_file: Optional[str] = None
    source_format: Optional[str] = None  # json, pdf, csv
    import_timestamp: Optional[str] = None
    parsing_confidence: Optional[float] = None

    # Shadow billing
    shadow_level: ShadowLevel = ShadowLevel.L0_READ
    why_not_higher: Optional[str] = None

    # Audit
    anomalies: List["InvoiceAnomaly"] = field(default_factory=list)
    audit_timestamp: Optional[str] = None
    engine_version: Optional[str] = None
    input_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise en dict pour JSON."""
        d = {
            "invoice_id": self.invoice_id,
            "energy_type": self.energy_type.value,
            "supplier": self.supplier,
            "contract_ref": self.contract_ref,
            "pdl_pce": self.pdl_pce,
            "site_id": self.site_id,
            "invoice_date": str(self.invoice_date) if self.invoice_date else None,
            "due_date": str(self.due_date) if self.due_date else None,
            "period_start": str(self.period_start) if self.period_start else None,
            "period_end": str(self.period_end) if self.period_end else None,
            "total_ht": self.total_ht,
            "total_tva": self.total_tva,
            "total_ttc": self.total_ttc,
            "conso_kwh": self.conso_kwh,
            "puissance_souscrite_kva": self.puissance_souscrite_kva,
            "status": self.status.value,
            "source_file": self.source_file,
            "source_format": self.source_format,
            "shadow_level": self.shadow_level.value,
            "why_not_higher": self.why_not_higher,
            "engine_version": self.engine_version,
            "input_hash": self.input_hash,
            "components": [
                {
                    "component_type": c.component_type.value,
                    "label": c.label,
                    "quantity": c.quantity,
                    "unit": c.unit,
                    "unit_price": c.unit_price,
                    "amount_ht": c.amount_ht,
                    "amount_ttc": c.amount_ttc,
                    "tva_rate": c.tva_rate,
                    "tva_amount": c.tva_amount,
                    "period_start": str(c.period_start) if c.period_start else None,
                    "period_end": str(c.period_end) if c.period_end else None,
                    "metadata": c.metadata,
                }
                for c in self.components
            ],
            "anomalies": [a.to_dict() for a in self.anomalies],
            "nb_components": len(self.components),
            "nb_anomalies": len(self.anomalies),
        }
        return d


@dataclass
class InvoiceAnomaly:
    """Anomalie detectee lors de l'audit d'une facture."""
    anomaly_id: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    message: str
    component_type: Optional[ComponentType] = None
    expected_value: Optional[float] = None
    actual_value: Optional[float] = None
    difference: Optional[float] = None
    rule_card_id: Optional[str] = None  # Lien vers RuleCard KB
    citations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "component_type": self.component_type.value if self.component_type else None,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "difference": self.difference,
            "rule_card_id": self.rule_card_id,
            "citations": self.citations,
            "confidence": self.confidence,
        }


@dataclass
class ShadowResult:
    """Resultat d'un shadow billing."""
    invoice_id: str
    shadow_level: ShadowLevel
    shadow_total_ht: Optional[float] = None
    shadow_total_ttc: Optional[float] = None
    shadow_components: List[Dict[str, Any]] = field(default_factory=list)
    delta_ht: Optional[float] = None
    delta_ttc: Optional[float] = None
    delta_percent: Optional[float] = None
    explain: List[str] = field(default_factory=list)
    why_not_higher: Optional[str] = None
    rule_cards_used: List[str] = field(default_factory=list)
    engine_version: Optional[str] = None
    computed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "shadow_level": self.shadow_level.value,
            "shadow_total_ht": self.shadow_total_ht,
            "shadow_total_ttc": self.shadow_total_ttc,
            "shadow_components": self.shadow_components,
            "delta_ht": self.delta_ht,
            "delta_ttc": self.delta_ttc,
            "delta_percent": self.delta_percent,
            "explain": self.explain,
            "why_not_higher": self.why_not_higher,
            "rule_cards_used": self.rule_cards_used,
            "engine_version": self.engine_version,
            "computed_at": self.computed_at,
        }


@dataclass
class AuditReport:
    """Rapport d'audit complet pour une facture."""
    invoice_id: str
    invoice: Dict[str, Any] = field(default_factory=dict)
    shadow: Optional[Dict[str, Any]] = None
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    coverage_level: str = "L0"
    total_anomalies: int = 0
    critical_anomalies: int = 0
    potential_savings_eur: Optional[float] = None
    explain_log: List[str] = field(default_factory=list)
    generated_at: Optional[str] = None
    engine_version: Optional[str] = None
