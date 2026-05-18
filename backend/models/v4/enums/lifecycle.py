"""LifecycleState enum — ADR-028 §6.1 + doctrine v0.3 §7.1.

Invariant IL2 : `chk_lifecycle_state` CHECK constraint DB whitelist 5 valeurs strictes.
Invariants IL1-IL11 : transitions strictes via `VALID_TRANSITIONS` dict (Sprint M2-5).
"""

from enum import Enum


class LifecycleState(str, Enum):
    """5 lifecycle states figés doctrine v0.3."""

    NEW = "new"
    TRIAGED = "triaged"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

    @classmethod
    def values(cls) -> list[str]:
        """Liste des valeurs string (utile pour CHECK constraint + tests)."""
        return [s.value for s in cls]

    @classmethod
    def fr_label(cls, state: "LifecycleState") -> str:
        """Mode standard FR (cf. ADR-028 §10 + L7 §10.1)."""
        return {
            cls.NEW: "Nouveau",
            cls.TRIAGED: "Qualifié",
            cls.PLANNED: "Planifié",
            cls.IN_PROGRESS: "En cours",
            cls.CLOSED: "Clôturé",
        }[state]
