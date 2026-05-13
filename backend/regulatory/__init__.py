"""PROMEOS — `regulatory` package : moteur d'assujettissement réglementaire v1.0.

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` (Phase 3.5).

Ce package répond à la question cardinale "ce site/portefeuille est-il assujetti
à cette règle, et pourquoi ?" pour les 5 règles FR 2026 :
    DT     · Décret tertiaire 2019-771
    BACS   · Décret 2020-887 + 2025-1343
    APER   · Loi 2023-175 art. 40
    SMÉ    · Audit énergétique L233-1
    BEGES  · Bilan GES Grenelle 2 art. 75

Discipline d'import (cf. décision Phase 0 Q2) :
    from regulatory.applicability_service import compute_applicability
NE PAS confondre avec le legacy `services.compliance_readiness_service.compute_applicability`
(schéma dict[str, dict], conservé pour rétro-compat).
"""

from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from regulatory.reason_codes import REASON_CODES, is_valid_reason_code

__all__ = [
    "ApplicabilityStatus",
    "RuleApplicability",
    "RuleCode",
    "REASON_CODES",
    "is_valid_reason_code",
]
