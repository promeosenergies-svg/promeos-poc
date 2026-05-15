"""ActionBlocker — blockers actifs sur ActionCenterItem (ADR-025 §4.3).

Blocker = motif qui empêche progression de l'item (ex: preuve attendue, budget,
validation manager). Levé → resolved_at + resolved_by remplis.

Invariants applicables :
- IS1 : organisation_id
- 7 blocker_type CHECK whitelist (cohérent BlockerType enum + doctrine v0.3 §7.1)
- ON DELETE CASCADE
- Index partiel sur blockers actifs (resolved_at IS NULL)
"""

from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from models.base import Base


class ActionBlocker(Base):
    """Blocker actif sur un ActionCenterItem (waiting_evidence, waiting_budget...)."""

    __tablename__ = "action_blockers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(UUID(as_uuid=True), nullable=False)  # IS1
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("action_center_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    blocker_type = Column(String(40), nullable=False)  # 7 valeurs CHECK
    added_by = Column(UUID(as_uuid=True))
    added_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    justification = Column(Text)
    expected_resolution_at = Column(DateTime(timezone=True))

    # Resolution
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True))

    __table_args__ = (
        CheckConstraint(
            "blocker_type IN ("
            "'waiting_evidence', "
            "'waiting_budget', "
            "'waiting_third_party', "
            "'waiting_data', "
            "'waiting_supplier', "
            "'waiting_manager_validation', "
            "'waiting_regulatory_confirmation'"
            ")",
            name="chk_blocker_type",
        ),
        # Index partiel sur blockers actifs (drawer M2 affichage temps réel)
        Index(
            "idx_blocker_item_active",
            "item_id",
            sqlite_where=text("resolved_at IS NULL"),
            postgresql_where=text("resolved_at IS NULL"),
        ),
    )
