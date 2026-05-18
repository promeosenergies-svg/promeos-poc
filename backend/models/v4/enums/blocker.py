"""BlockerType enum — doctrine v0.3 §7.1 + ADR-025 §4.3 + L7 §3.9.

7 types de blockers actifs sur item (`action_blockers.blocker_type` CHECK).
Cohérent labels FR doctrine v0.3 §7.1.
"""

from enum import Enum


class BlockerType(str, Enum):
    """7 types de blockers V4."""

    WAITING_EVIDENCE = "waiting_evidence"
    WAITING_BUDGET = "waiting_budget"
    WAITING_THIRD_PARTY = "waiting_third_party"
    WAITING_DATA = "waiting_data"
    WAITING_SUPPLIER = "waiting_supplier"
    WAITING_MANAGER_VALIDATION = "waiting_manager_validation"
    WAITING_REGULATORY_CONFIRMATION = "waiting_regulatory_confirmation"

    @classmethod
    def values(cls) -> list[str]:
        return [b.value for b in cls]

    @classmethod
    def fr_label(cls, blocker: "BlockerType") -> str:
        """Mode standard FR (doctrine v0.3 §7.1)."""
        return {
            cls.WAITING_EVIDENCE: "Preuve attendue",
            cls.WAITING_BUDGET: "Budget attendu",
            cls.WAITING_THIRD_PARTY: "Tiers attendu",
            cls.WAITING_DATA: "Donnée attendue",
            cls.WAITING_SUPPLIER: "Fournisseur attendu",
            cls.WAITING_MANAGER_VALIDATION: "Validation manager attendue",
            cls.WAITING_REGULATORY_CONFIRMATION: "Confirmation réglementaire attendue",
        }[blocker]
