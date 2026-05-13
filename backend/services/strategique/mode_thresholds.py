"""PROMEOS — StrategicMode enum + seuils versionnés v1.0.

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §9.

Politique de versioning :
    Toute modification des seuils passe par ADR (le mode dispatcher en
    dépend ; un changement non documenté fait dériver la narration produit).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final


class StrategicMode(StrEnum):
    """5 modes narratifs cataloguées v1.0 de la page Synthèse stratégique."""

    REGULATORY_DRIVEN = "regulatory_driven"
    PERFORMANCE_DRIVEN = "performance_driven"
    PROCUREMENT_DRIVEN = "procurement_driven"
    OPPORTUNITY_DRIVEN = "opportunity_driven"
    DATA_INSUFFICIENT = "data_insufficient"


@dataclass(frozen=True)
class ModeThresholds:
    """Seuils versionnés v1.0 — modifiables uniquement par ADR.

    Cf. ADR-023 §9 + ADR-024 (DT/BACS thresholds dans `regulatory.rules.*`).
    """

    # ── Gate 1 — DATA_INSUFFICIENT (priorité absolue) ──────────────────
    MIN_PATRIMOINE_MATURITY: float = 0.60
    MAX_UNKNOWN_RULES_RATIO: float = 0.30

    # ── Gate 2 — REGULATORY_DRIVEN ─────────────────────────────────────
    # Dérive trajectoire DT en % (ex. -32 % vs cible -40 % → drift = 8)
    MIN_TRAJECTORY_DRIFT_PCT: float = 5.0

    # ── Gate 3 — PROCUREMENT_DRIVEN ────────────────────────────────────
    MAX_CONTRACT_END_DAYS: int = 90
    MAX_SPOT_EXPOSURE_PCT: float = 40.0

    # ── Gate 4 — OPPORTUNITY_DRIVEN ────────────────────────────────────
    MIN_OPPORTUNITY_VALUE_K_EUR: float = 50.0

    # ── Default — PERFORMANCE_DRIVEN (fallback) ───────────────────────
    MIN_BENCH_DEVIATION_PCT: float = 10.0


# Instance figée v1.0 utilisée par le mode router (cf. B.2).
MODE_THRESHOLDS_V1: Final[ModeThresholds] = ModeThresholds()
