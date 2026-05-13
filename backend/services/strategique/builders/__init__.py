"""PROMEOS — Builders Synthèse Stratégique v1.0 (Phase 3.5 Vague C).

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md`.

Trois builders prioritaires (Phase 3.5) :
    RegulatoryDrivenBuilder    — mode HELIOS (DT/BACS APPLICABLE + drift)
    PerformanceDrivenBuilder   — mode MERIDIAN (default, intensité > médiane)
    DataInsufficientBuilder    — mode onboarding (maturité < 60 %)

Deux stubs (Phase 3.6) :
    ProcurementDrivenBuilder  — non implémenté → fallback PERFORMANCE
    OpportunityDrivenBuilder  — non implémenté → fallback PERFORMANCE

MODE_BUILDERS dispatcher consommé par routes/cockpit_strategique.py (Vague C.5).
"""

from services.strategique.builders.base import (
    DOCTRINE_VERSION_STRATEGIQUE,
    PERSONA_DG_COMEX,
    StrategicModeBuilder,
)
from services.strategique.builders.data_insufficient import DataInsufficientBuilder
from services.strategique.builders.performance import PerformanceDrivenBuilder
from services.strategique.builders.regulatory import RegulatoryDrivenBuilder
from services.strategique.builders.stubs import (
    OpportunityDrivenBuilder,
    ProcurementDrivenBuilder,
)
from services.strategique.mode_thresholds import StrategicMode


MODE_BUILDERS: dict[StrategicMode, StrategicModeBuilder] = {
    StrategicMode.REGULATORY_DRIVEN: RegulatoryDrivenBuilder(),
    StrategicMode.PERFORMANCE_DRIVEN: PerformanceDrivenBuilder(),
    StrategicMode.PROCUREMENT_DRIVEN: ProcurementDrivenBuilder(),
    StrategicMode.OPPORTUNITY_DRIVEN: OpportunityDrivenBuilder(),
    StrategicMode.DATA_INSUFFICIENT: DataInsufficientBuilder(),
}


IMPLEMENTED_MODES: frozenset[StrategicMode] = frozenset(
    {
        StrategicMode.REGULATORY_DRIVEN,
        StrategicMode.PERFORMANCE_DRIVEN,
        StrategicMode.DATA_INSUFFICIENT,
    }
)


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
