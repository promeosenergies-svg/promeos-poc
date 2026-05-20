"""PriorityBracket enum — ADR-022 (priorité héritée) + doctrine v0.3 §2.2.

4 brackets persistés Q8-C pour tri SQL rapide via `idx_aci_org_priority`.
"""

from enum import Enum


class PriorityBracket(str, Enum):
    """4 brackets de priorité PROMEOS V4."""

    P0 = "P0"  # ≥ 80 — à traiter aujourd'hui
    P1 = "P1"  # 60-79 — à traiter cette semaine
    P2 = "P2"  # 40-59 — à traiter ce mois
    P3 = "P3"  # < 40  — backlog, surveillance

    @classmethod
    def values(cls) -> list[str]:
        return [b.value for b in cls]

    @classmethod
    def from_score(cls, score: float) -> "PriorityBracket":
        """Calcule le bracket depuis un score 0-100 (cf. doctrine v0.3 §2.2)."""
        if score >= 80:
            return cls.P0
        if score >= 60:
            return cls.P1
        if score >= 40:
            return cls.P2
        return cls.P3
