"""Role enum — ADR-027 §3.1 + L7 §3.6.

4 valeurs cardinales pour `actor_role` (snapshot dans audit trail) +
`@org_scoped(allowed_roles=...)` décorateur Sprint M2-3.

Note `actor_type` BD utilise 2 valeurs strictes (`user`, `system`) — voir
ChkActorConsistency dans action_event_log.
"""

from enum import Enum


class Role(str, Enum):
    """4 rôles utilisateur PROMEOS V4."""

    ADMIN = "admin"  # Accès total + actions sensibles (kind_corrected, reopen, RGPD delete)
    USER = "user"  # Lecture + mutation items propres org
    VIEWER = "viewer"  # Lecture seule (analytics, dashboards)
    SYSTEM = "system"  # actor system uniquement (regulatory_applicability_service, etc.)

    @classmethod
    def values(cls) -> list[str]:
        return [r.value for r in cls]
