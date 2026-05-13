"""PROMEOS — Builders Synthèse Stratégique v1.0 (Phase 3.5 Vague C + Phase 3.6 Vague BB).

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md`.

Cinq builders implémentés v1.0 :
    RegulatoryDrivenBuilder    — mode HELIOS (DT/BACS APPLICABLE + drift)
    PerformanceDrivenBuilder   — mode MERIDIAN (default, intensité > médiane)
    ProcurementDrivenBuilder   — Phase 3.6 (contrat échéance < 90j OU spot > 40%)
    OpportunityDrivenBuilder   — Phase 3.6 (APER applicable OU CEE > 50 k€)
    DataInsufficientBuilder    — mode onboarding (maturité < 60 %)

MODE_BUILDERS dispatcher consommé par routes/cockpit_strategique.py.
"""

from services.strategique.builders.base import (
    DOCTRINE_VERSION_STRATEGIQUE,
    PERSONA_DG_COMEX,
    StrategicModeBuilder,
)
from services.strategique.builders.data_insufficient import DataInsufficientBuilder
from services.strategique.builders.opportunity import OpportunityDrivenBuilder
from services.strategique.builders.performance import PerformanceDrivenBuilder
from services.strategique.builders.procurement import ProcurementDrivenBuilder
from services.strategique.builders.regulatory import RegulatoryDrivenBuilder
from services.strategique.mode_thresholds import StrategicMode


MODE_BUILDERS: dict[StrategicMode, StrategicModeBuilder] = {
    StrategicMode.REGULATORY_DRIVEN: RegulatoryDrivenBuilder(),
    StrategicMode.PERFORMANCE_DRIVEN: PerformanceDrivenBuilder(),
    StrategicMode.PROCUREMENT_DRIVEN: ProcurementDrivenBuilder(),
    StrategicMode.OPPORTUNITY_DRIVEN: OpportunityDrivenBuilder(),
    StrategicMode.DATA_INSUFFICIENT: DataInsufficientBuilder(),
}


# Phase 3.6 Vague BB : 5 modes désormais implémentés. La whitelist
# IMPLEMENTED_MODES couvre tout — plus de fallback runtime nécessaire.
IMPLEMENTED_MODES: frozenset[StrategicMode] = frozenset(StrategicMode)


__all__ = [
    "DOCTRINE_VERSION_STRATEGIQUE",
    "PERSONA_DG_COMEX",
    "StrategicModeBuilder",
    "RegulatoryDrivenBuilder",
    "PerformanceDrivenBuilder",
    "DataInsufficientBuilder",
    "ProcurementDrivenBuilder",
    "OpportunityDrivenBuilder",
    "MODE_BUILDERS",
    "IMPLEMENTED_MODES",
]
