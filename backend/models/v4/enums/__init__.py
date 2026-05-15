"""9 enums Python V4 (cohérent L7 §3 + 5 décisions cardinales D1-D5).

Source consolidée :
- doctrine v0.3 §3 + §7.1 (Kind 7 valeurs · ClosureReason 6 révisés)
- ADR-025 §4.1 (chk_kind 7 valeurs · chk_lifecycle_state · chk_priority_bracket)
- ADR-027 §3.1 (Role)
- ADR-028 §6.1 (LifecycleState · ClosureReason)
- ADR-029 §6.1 + §10.1 (EventType 16 valeurs · RetentionCategory 3 valeurs)
- L7 §3 (consolidation 9 enums + BlockerType ajouté)

Décisions cardinales Phase 0 audit M2-2 :
- D1 : Kind 7 valeurs strictes (pas 3 — correction prompt M2-2)
- D5 : Domain VARCHAR(30) sans CHECK DB (extensible Mois 6+) — enum Python documente 7 canoniques
"""

from backend.models.v4.enums.blocker import BlockerType
from backend.models.v4.enums.closure import ClosureReason
from backend.models.v4.enums.domain import Domain
from backend.models.v4.enums.event_type import EventType
from backend.models.v4.enums.kind import Kind
from backend.models.v4.enums.lifecycle import LifecycleState
from backend.models.v4.enums.priority import PriorityBracket
from backend.models.v4.enums.retention import (
    CATEGORY_RETENTION_DAYS,
    EVENT_TYPE_CATEGORY,
    RetentionCategory,
)
from backend.models.v4.enums.role import Role

__all__ = [
    "CATEGORY_RETENTION_DAYS",
    "EVENT_TYPE_CATEGORY",
    "BlockerType",
    "ClosureReason",
    "Domain",
    "EventType",
    "Kind",
    "LifecycleState",
    "PriorityBracket",
    "RetentionCategory",
    "Role",
]
