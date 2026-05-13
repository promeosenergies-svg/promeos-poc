"""PROMEOS — Stubs typés ProcurementDrivenBuilder + OpportunityDrivenBuilder.

Décision Phase 0 Q3 (Amine 2026-05-13) :
  Ces deux builders sont stubs Phase 3.5 et seront livrés Phase 3.6.
  Si le dispatcher mode_router renvoie PROCUREMENT/OPPORTUNITY mais que
  le builder correspondant n'est pas encore implémenté, le caller doit
  basculer automatiquement sur PERFORMANCE_DRIVEN avec
  `_fallback_reason="mode_not_implemented_v1.0"` dans l'audit trail.

Les classes lèvent NotImplementedError pour rendre la dette explicite
au runtime + log structuré pour traçabilité Phase 3.6.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from regulatory.applicability_types import RuleApplicability, RuleCode
from services.strategique.builders.base import (
    PERSONA_DG_COMEX,
    StrategicModeBuilder,
)
from services.strategique.mode_thresholds import StrategicMode


_logger = logging.getLogger(__name__)


class _UnimplementedBuilder(StrategicModeBuilder):
    """Stub interne — sous-classes spécifient `mode`."""

    def build(
        self,
        db: Session,
        org_id: int,
        applicability: dict[RuleCode, list[RuleApplicability]],
        patrimoine_maturity: float,
        persona: str = PERSONA_DG_COMEX,
        period_type: str = "month",
        horizon_year: int = 2030,
    ) -> dict:
        _logger.warning(
            "[strategique-stub] mode=%s builder non implémenté (Phase 3.6) — "
            "caller doit basculer sur PERFORMANCE_DRIVEN. org_id=%s",
            self.mode.value,
            org_id,
        )
        raise NotImplementedError(
            f"{self.__class__.__name__} non implémenté Phase 3.5 — différé Phase 3.6 "
            f"(décision Phase 0 Q3). Caller doit basculer sur PerformanceDrivenBuilder."
        )


class ProcurementDrivenBuilder(_UnimplementedBuilder):
    mode = StrategicMode.PROCUREMENT_DRIVEN


class OpportunityDrivenBuilder(_UnimplementedBuilder):
    mode = StrategicMode.OPPORTUNITY_DRIVEN
