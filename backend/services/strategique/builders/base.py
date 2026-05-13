"""PROMEOS — Interface abstraite des builders Synthèse Stratégique v1.0.

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §2 + §3.

Chaque builder produit le payload complet de la page (schéma figé §3).
Le payload est consommé tel quel par le frontend ; aucun calcul métier ne
doit s'exécuter côté FE.

Discipline "from scratch" Phase 3.5 (clarif. user 2026-05-13) :
    - Aucun import depuis services/cockpit_*.py legacy
    - Aucun import depuis routes/cockpit_v2.py
    - Lecture directe via :
        * regulatory.applicability_service.compute_applicability
        * services.compliance_score_service (lecture seule)
        * services.consumption_unified_service (lecture seule)
        * services.scope_utils.sites_for_org_query
    - Aucun nom de site/portefeuille en dur dans un builder (AP-stratX7)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Any, Final

from sqlalchemy.orm import Session

from regulatory.applicability_service import (
    compute_applicability,
    compute_patrimoine_maturity,
)
from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.rules_catalog import RULES_VERSIONS

from services.strategique.mode_thresholds import StrategicMode


DOCTRINE_VERSION_STRATEGIQUE: Final[str] = "ADR-023-v1.0"
PERSONA_DG_COMEX: Final[str] = "dg_comex"


class StrategicModeBuilder(ABC):
    """Contrat de base d'un builder mode Synthèse Stratégique."""

    mode: StrategicMode

    @abstractmethod
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
        """Renvoie le payload complet de la page Synthèse Stratégique."""

    # ── Helpers communs (footer, audit, scope label) ──────────────────

    def _build_audit_section(self, org_id: int) -> dict[str, Any]:
        return {
            "doctrine_version": DOCTRINE_VERSION_STRATEGIQUE,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "builder": self.__class__.__name__,
            "mode": self.mode.value,
            "org_id": org_id,
        }

    def _build_footer(
        self,
        sources: list[str] | None = None,
        last_update: str | None = None,
    ) -> dict[str, Any]:
        return {
            "sources": sources or ["regulatory.applicability_service v1.0"],
            "version_tags": [
                "Assujettissement v1.0",
                "Doctrine priorisation v1.0",
                "Synthèse stratégique v1.0",
                "Sol v1.1",
            ]
            + [f"{rule.value} {ver}" for rule, ver in RULES_VERSIONS.items()],
            "last_update": last_update or datetime.now(timezone.utc).strftime("%d/%m %H:%M"),
            "methodology_link": "/methodologie",
        }

    def _serialize_applicability(
        self,
        applicability: dict[RuleCode, list[RuleApplicability]],
    ) -> dict[str, list[dict]]:
        return {rule.value: [entry.to_dict() for entry in entries] for rule, entries in applicability.items()}

    def _count_applicable_sites(
        self,
        applicability: dict[RuleCode, list[RuleApplicability]],
        rule: RuleCode,
    ) -> int:
        return sum(1 for entry in applicability.get(rule, []) if entry.status == ApplicabilityStatus.APPLICABLE)

    def _next_deadline_for_rule(
        self,
        applicability: dict[RuleCode, list[RuleApplicability]],
        rule: RuleCode,
    ) -> date | None:
        deadlines = [entry.deadline for entry in applicability.get(rule, []) if entry.deadline is not None]
        return min(deadlines) if deadlines else None
