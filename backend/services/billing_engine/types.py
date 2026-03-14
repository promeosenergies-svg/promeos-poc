"""
PROMEOS Billing Engine — Types, enums, dataclasses.
Zero magic numbers. Every value is sourced or explicit.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional


# ─── Enums ────────────────────────────────────────────────────────────────────


class TariffSegment(str, enum.Enum):
    """Segment TURPE — déterminé par la puissance souscrite."""

    C5_BT = "C5_BT"  # ≤ 36 kVA
    C4_BT = "C4_BT"  # > 36 kVA, ≤ 250 kVA
    C3_HTA = "C3_HTA"  # > 250 kVA (hors scope V1)
    UNSUPPORTED = "UNSUPPORTED"


class TariffOption(str, enum.Enum):
    """Option tarifaire du point de livraison."""

    BASE = "BASE"  # C5 tarif de base (pas de plages)
    HP_HC = "HP_HC"  # C5 Heures Pleines / Heures Creuses
    CU = "CU"  # C4 Courte Utilisation
    MU = "MU"  # C4 Moyenne Utilisation
    LU = "LU"  # C4 Longue Utilisation
    UNSUPPORTED = "UNSUPPORTED"


class InvoiceType(str, enum.Enum):
    """Type de facture énergie."""

    NORMAL = "NORMAL"  # Facture de consommation standard
    ADVANCE = "ADVANCE"  # Acompte / mensualisation
    REGULARIZATION = "REGULARIZATION"  # Régularisation (estimé → réel)
    CREDIT_NOTE = "CREDIT_NOTE"  # Avoir


class ReconstitutionStatus(str, enum.Enum):
    """Statut de la reconstitution."""

    RECONSTITUTED = "RECONSTITUTED"  # Toutes composantes calculées
    PARTIAL = "PARTIAL"  # Composantes manquantes (données insuffisantes)
    READ_ONLY = "READ_ONLY"  # Affichage seul (gaz, acompte)
    UNSUPPORTED = "UNSUPPORTED"  # Segment non supporté (C3 HTA, etc.)


class PeriodCode(str, enum.Enum):
    """Code de période tarifaire."""

    BASE = "BASE"
    HP = "HP"
    HC = "HC"
    HPH = "HPH"  # Heures Pleines Hiver
    HCH = "HCH"  # Heures Creuses Hiver
    HPE = "HPE"  # Heures Pleines Été
    HCE = "HCE"  # Heures Creuses Été
    P = "P"  # Pointe (C3+ uniquement)


# ─── Dataclasses ──────────────────────────────────────────────────────────────


@dataclass
class RateSource:
    """Origine d'un taux utilisé dans le calcul."""

    code: str  # ex: TURPE_GESTION_C4_LU
    rate: float  # valeur utilisée
    unit: str  # EUR/kWh, EUR/kVA/an, EUR/an, PCT
    source: str  # ex: CRE délibération TURPE 7
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    fallback_used: bool = False


@dataclass
class ComponentResult:
    """Résultat d'une composante de facture."""

    code: str  # ex: turpe_gestion, supply_hpe, cta
    label: str  # ex: "Composante de gestion"
    amount_ht: float  # montant HT calculé
    tva_rate: float  # taux TVA applicable (0.20 ou 0.055)
    amount_tva: float  # montant TVA calculé
    amount_ttc: float  # HT + TVA

    # Traçabilité
    formula_used: str  # ex: "18.48 × (31/31) = 18.48"
    inputs_used: Dict[str, Any] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    rate_sources: List[RateSource] = field(default_factory=list)

    # Comparaison (optionnel, rempli par compare_to_supplier_invoice)
    supplier_amount_ht: Optional[float] = None
    gap_eur: Optional[float] = None
    gap_pct: Optional[float] = None
    gap_status: Optional[str] = None  # ok / warn / alert


@dataclass
class ReconstitutionResult:
    """Résultat complet d'une reconstitution de facture."""

    status: ReconstitutionStatus
    segment: TariffSegment
    tariff_option: TariffOption
    energy_type: str  # ELEC ou GAZ

    # Composantes
    components: List[ComponentResult] = field(default_factory=list)

    # Totaux
    total_ht: float = 0.0
    total_tva: float = 0.0
    total_ttc: float = 0.0
    total_tva_reduite: float = 0.0
    total_tva_normale: float = 0.0

    # Inputs
    kwh_total: float = 0.0
    kwh_by_period: Dict[str, float] = field(default_factory=dict)
    subscribed_power_kva: float = 0.0
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    prorata_days: int = 0
    prorata_factor: float = 0.0  # days / days_in_month (calendaire exact)

    # Méta
    missing_inputs: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    catalog_version: str = ""
    engine_version: str = "billing_engine_v2.0"


@dataclass
class AuditTrace:
    """Trace d'audit complète pour une reconstitution."""

    reconstitution: ReconstitutionResult
    rate_sources_used: List[RateSource] = field(default_factory=list)
    computation_steps: List[Dict[str, Any]] = field(default_factory=list)
    comparison: Optional[Dict[str, Any]] = None
