"""PROMEOS — `services.strategique` package : dispatcher polymorphique
Synthèse Stratégique v1.0.

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md`.

Cinq modes cataloguées v1.0 :
    REGULATORY_DRIVEN   — trajectoire DT/BACS prime
    PERFORMANCE_DRIVEN  — intensité énergétique > benchmark NAF
    PROCUREMENT_DRIVEN  — fenêtre achat (échéance < 90 j ou spot > 40 %)
    OPPORTUNITY_DRIVEN  — APER applicable ou CEE non valorisés > 50 k€
    DATA_INSUFFICIENT   — maturité patrimoine < 60 % ou UNKNOWN ratio > 30 %

Phase 3.5 livre :
    - StrategicMode + ModeThresholds (B.1)
    - compute_strategic_mode (B.2)
    - StrategicModeBuilder + 3 builders prioritaires (C)

Phase 3.6 différée : 2 builders restants (PROCUREMENT, OPPORTUNITY) +
4 charts primitives (ForwardCurve, OpportunityMap, MaturityRadar, MissingFields).
"""

from services.strategique.mode_thresholds import (
    MODE_THRESHOLDS_V1,
    ModeThresholds,
    StrategicMode,
)

__all__ = ["StrategicMode", "ModeThresholds", "MODE_THRESHOLDS_V1"]
