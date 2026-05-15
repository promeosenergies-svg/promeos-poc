"""RetentionCategory enum — ADR-029 §10.1 (IE3) + L7 §3.5.

3 catégories rétention RGPD CNIL conformes art. 5(1)(e) :
- compliance 5 ans (1825j) — preuves légales DT/BACS/APER + admin sensibles
- business 3 ans (1095j) — audit trail métier transitions
- system 1 an (365j) — events techniques bulk/export/recalcul

Mapping 16 event_types → catégorie : cf. ADR-029 §10.2 + EVENT_TYPE_CATEGORY ci-dessous.
"""

from enum import Enum

from backend.models.v4.enums.event_type import EventType


class RetentionCategory(str, Enum):
    """3 catégories rétention RGPD."""

    COMPLIANCE = "compliance"  # 5 ans (1825 jours) · CNIL art. 30 + 5(2)
    BUSINESS = "business"  # 3 ans (1095 jours) · CNIL art. 5(1)(e)
    SYSTEM = "system"  # 1 an  (365 jours)  · CNIL art. 5(1)(b) + 5(1)(e)

    @classmethod
    def values(cls) -> list[str]:
        return [c.value for c in cls]


CATEGORY_RETENTION_DAYS: dict[RetentionCategory, int] = {
    RetentionCategory.COMPLIANCE: 1825,
    RetentionCategory.BUSINESS: 1095,
    RetentionCategory.SYSTEM: 365,
}

# IE4 cardinal Amine : matrice rétention alignée doctrine v0.3
# `closed_via_merged_duplicate` (business 3y) ≠ `closed_via_resolved_via_recurrence` (compliance 5y)
EVENT_TYPE_CATEGORY: dict[EventType, RetentionCategory] = {
    # Business 3 ans (7 events)
    EventType.CREATED: RetentionCategory.BUSINESS,
    EventType.STATE_CHANGED: RetentionCategory.BUSINESS,
    EventType.OWNER_CHANGED: RetentionCategory.BUSINESS,
    EventType.PRIORITY_CHANGED: RetentionCategory.BUSINESS,
    EventType.BLOCKER_ADDED: RetentionCategory.BUSINESS,
    EventType.BLOCKER_REMOVED: RetentionCategory.BUSINESS,
    EventType.CLOSED_VIA_MERGED_DUPLICATE: RetentionCategory.BUSINESS,  # Q9-B doublon technique
    # Compliance 5 ans (6 events)
    EventType.EVIDENCE_ADDED: RetentionCategory.COMPLIANCE,
    EventType.EVIDENCE_VERIFIED: RetentionCategory.COMPLIANCE,
    EventType.CLOSED_WITH_EVIDENCE: RetentionCategory.COMPLIANCE,
    EventType.CLOSED_VIA_RESOLVED_VIA_RECURRENCE: RetentionCategory.COMPLIANCE,  # Q9-B preuve indirecte
    EventType.REOPENED: RetentionCategory.COMPLIANCE,  # IL3 admin sensible
    EventType.KIND_CORRECTED: RetentionCategory.COMPLIANCE,  # IS5 admin sensible
    # System 1 an (3 events)
    EventType.BULK_UPDATED: RetentionCategory.SYSTEM,
    EventType.EXPORTED: RetentionCategory.SYSTEM,
    EventType.PRIORITY_RECALCULATED: RetentionCategory.SYSTEM,
}
