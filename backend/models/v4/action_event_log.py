"""ActionEventLog — audit trail métier V4 (ADR-029 §6.1 + L7 §2.2).

Invariants applicables :
- IS1 : organisation_id
- IS9 : correlation_id obligatoire (propagation cross-actions)
- IL8 : toute transition lifecycle écrit ici (event_type=`state_changed`)
- IE7 : 16 event_types (chk_event_type) + schema_version Pydantic versionné
- IE8 : séparé strict de `security_audit_log` (90j Sprint M2-3)

Note d'extension event_types : 16 valeurs alignées doctrine v0.3 (extension
aval acceptée par convention vs ADR-025 §4.3 squelette préliminaire 15 valeurs).
"""

from uuid import uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from backend.models.base import Base


class ActionEventLog(Base):
    """Audit trail métier (rétention 1-5 ans selon catégorie IE3)."""

    __tablename__ = "action_event_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(UUID(as_uuid=True), nullable=False)  # IS1
    action_item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("action_center_items.id", ondelete="RESTRICT"),  # préserve audit trail
        nullable=False,
    )

    # Event metadata
    event_type = Column(String(60), nullable=False)  # 16 valeurs CHECK
    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Actor (snapshot pour audit trail historique stable)
    actor_type = Column(String(20), nullable=False)  # 'user' | 'system'
    actor_id = Column(UUID(as_uuid=True))  # NULL si system
    actor_name = Column(String(120))
    actor_role = Column(String(20))

    # IE7 : payload typé Pydantic versionné
    event_payload = Column(JSON, nullable=False)
    schema_version = Column(String(10), nullable=False, server_default="v1")

    # IS9 : traçabilité cross-actions
    correlation_id = Column(UUID(as_uuid=True), nullable=False)
    source_route = Column(String(120))

    __table_args__ = (
        # SG-6 cible : 16 event_types exhaustifs (extension ADR-025 §4.3 → ADR-029 §6.1)
        CheckConstraint(
            "event_type IN ("
            "'created', "
            "'state_changed', "
            "'owner_changed', "
            "'priority_changed', "
            "'blocker_added', "
            "'blocker_removed', "
            "'evidence_added', "
            "'evidence_verified', "
            "'closed_with_evidence', "
            "'closed_via_merged_duplicate', "
            "'closed_via_resolved_via_recurrence', "
            "'reopened', "
            "'bulk_updated', "
            "'exported', "
            "'kind_corrected', "
            "'priority_recalculated'"
            ")",
            name="chk_event_type",
        ),
        CheckConstraint(
            "(actor_type = 'system' AND actor_id IS NULL) OR (actor_type = 'user' AND actor_id IS NOT NULL)",
            name="chk_actor_consistency",
        ),
        # ─── Indexes (cohérent ADR-025 §4.2 — 4 indexes pour cette table) ───
        Index(
            "idx_event_log_org_item",
            "organisation_id",
            "action_item_id",
            "occurred_at",
        ),
        Index("idx_event_log_type", "event_type", "occurred_at"),
        Index("idx_event_log_correlation", "correlation_id"),
        Index(
            "idx_event_log_actor",
            "actor_id",
            "occurred_at",
            sqlite_where=text("actor_id IS NOT NULL"),
            postgresql_where=text("actor_id IS NOT NULL"),
        ),
    )
