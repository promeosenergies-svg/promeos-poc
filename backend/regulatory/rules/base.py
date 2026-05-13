"""PROMEOS — Interface abstraite des évaluateurs d'assujettissement.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §3.

Chaque évaluateur respecte ce contrat :
    - `code`            — RuleCode évalué
    - `version`         — version normative datée (figée dans le code)
    - `scope`           — "site" | "organisation" | "portefeuille"
    - `evaluate(...)`   — retourne un RuleApplicability typé immuable

L'évaluateur ne touche jamais à la DB en écriture. Il lit Site/Bâtiment/
Organisation/RegAssessment/AuditSME et produit un verdict.

Discipline "from scratch" Phase 3.5 (décision user 2026-05-13) :
    - aucun import depuis backend/services/compliance_*
    - aucun import depuis backend/routes/cockpit_v2.py
    - lecture directe des modèles via Session
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Literal

from regulatory.applicability_types import DOCTRINE_VERSION, RuleApplicability, RuleCode


class RuleEvaluator(ABC):
    """Contrat de base d'un évaluateur d'assujettissement v1.0."""

    code: RuleCode
    version: str
    scope: Literal["site", "organisation", "portefeuille"]

    @abstractmethod
    def evaluate(self, *args: Any, **kwargs: Any) -> RuleApplicability:
        """Renvoie le verdict typé. Signature concrète définie par sous-classe."""

    def _build_audit(self, data_source: str) -> dict[str, Any]:
        """Construit le dict `_audit` avec les 5 clés requises."""
        return {
            "doctrine_version": DOCTRINE_VERSION,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "evaluator": self.__class__.__name__,
            "evaluator_version": self.version,
            "data_source": data_source,
        }
