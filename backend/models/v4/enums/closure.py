"""ClosureReason enum — doctrine v0.3 §7.1 (avenant Q37-A+) + ADR-028 §6.1 + ADR-029 §10.

Garde-fous cardinaux Amine :
- IL4 : `expired` interdit P0/P1 conformité/facturation (vérifié state machine, pas DB)
- IL5 : `merged_duplicate` interdit si recurrence_group_id sans duplicate_group_id (Q9-B)
"""

from enum import Enum


class ClosureReason(str, Enum):
    """6 closure_reasons révisés doctrine v0.3 (avenant L5 commit 466b64c3)."""

    RESOLVED = "resolved"  # Problème résolu + preuve vérifiée
    DISMISSED = "dismissed"  # Item écarté (faux positif, hors-scope)
    NOT_APPLICABLE = "not_applicable"  # Réglementation non-applicable (Q4-A)
    MERGED_DUPLICATE = "merged_duplicate"  # v0.3 unifié duplicate+merged (Q9-B doublon)
    RESOLVED_VIA_RECURRENCE = "resolved_via_recurrence"  # v0.3 ajouté Q37-A+ (Q9-B récurrence ≠ doublon)
    EXPIRED = "expired"  # SLA dépassé · IL4 interdit P0/P1 conformité/facturation

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]

    @classmethod
    def fr_label(cls, reason: "ClosureReason") -> str:
        """Mode standard FR (doctrine v0.3 §7.1)."""
        return {
            cls.RESOLVED: "Résolu",
            cls.DISMISSED: "Écarté",
            cls.NOT_APPLICABLE: "Non applicable",
            cls.MERGED_DUPLICATE: "Fusionné (doublon)",
            cls.RESOLVED_VIA_RECURRENCE: "Résolu via récurrence",
            cls.EXPIRED: "Expiré",
        }[reason]
