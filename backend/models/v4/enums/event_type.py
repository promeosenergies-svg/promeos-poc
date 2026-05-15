"""EventType enum — ADR-029 §6.1 + L7 §3.4.

16 valeurs en 3 catégories rétention RGPD (IE3 + IE4) :
- Business 3 ans (7 events)
- Compliance 5 ans (6 events)
- System 1 an (3 events)

Note d'extension event_types (cf. ADR-029 §6.3 + L2 §15) : extension aval
acceptée par convention vs ADR-025 §4.3 (15 → 16 valeurs alignées doctrine v0.3).
"""

from enum import Enum


class EventType(str, Enum):
    """16 event_types V4 (ADR-029)."""

    # ─── Business 3 ans (7 events) ───
    CREATED = "created"
    STATE_CHANGED = "state_changed"
    OWNER_CHANGED = "owner_changed"  # renommé depuis 'assigned' (ADR-025 §4.3)
    PRIORITY_CHANGED = "priority_changed"
    BLOCKER_ADDED = "blocker_added"
    BLOCKER_REMOVED = "blocker_removed"
    CLOSED_VIA_MERGED_DUPLICATE = "closed_via_merged_duplicate"  # renommé depuis 'merged' Q9-B

    # ─── Compliance 5 ans (6 events) ───
    EVIDENCE_ADDED = "evidence_added"
    EVIDENCE_VERIFIED = "evidence_verified"
    CLOSED_WITH_EVIDENCE = "closed_with_evidence"  # split depuis 'closed' (ADR-029)
    CLOSED_VIA_RESOLVED_VIA_RECURRENCE = "closed_via_resolved_via_recurrence"  # split (Q9-B)
    REOPENED = "reopened"  # IL3 admin sensible
    KIND_CORRECTED = "kind_corrected"  # IS5 admin sensible

    # ─── System 1 an (3 events) ───
    BULK_UPDATED = "bulk_updated"
    EXPORTED = "exported"  # RGPD art. 15 (export user data)
    PRIORITY_RECALCULATED = "priority_recalculated"

    @classmethod
    def values(cls) -> list[str]:
        """Liste des 16 valeurs string (utile pour CHECK constraint + tests SG-6)."""
        return [e.value for e in cls]

    @classmethod
    def fr_label(cls, event: "EventType") -> str:
        """Mode standard FR (ADR-029 §10 + L7 §10.5)."""
        return {
            cls.CREATED: "Créé",
            cls.STATE_CHANGED: "État modifié",
            cls.OWNER_CHANGED: "Responsable modifié",
            cls.PRIORITY_CHANGED: "Priorité modifiée",
            cls.BLOCKER_ADDED: "Blocker ajouté",
            cls.BLOCKER_REMOVED: "Blocker levé",
            cls.EVIDENCE_ADDED: "Preuve ajoutée",
            cls.EVIDENCE_VERIFIED: "Preuve vérifiée",
            cls.CLOSED_WITH_EVIDENCE: "Clôturé avec preuve",
            cls.CLOSED_VIA_MERGED_DUPLICATE: "Fusionné (doublon)",
            cls.CLOSED_VIA_RESOLVED_VIA_RECURRENCE: "Résolu via récurrence",
            cls.REOPENED: "Rouvert",
            cls.BULK_UPDATED: "Modifié en lot",
            cls.EXPORTED: "Exporté",
            cls.KIND_CORRECTED: "Type corrigé (admin)",
            cls.PRIORITY_RECALCULATED: "Score recalculé",
        }[event]
