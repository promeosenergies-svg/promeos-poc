"""DuplicateGroup model — Q9-B doublons stricts (ADR-025 §4.3).

🛡️ D4 VOCABULAIRE UX : status `suggested/merged/dismissed` (cohérent UX "Fusionner"
+ event_type `closed_via_merged_duplicate`).

Cardinal Q9-B : `duplicate_groups` ≠ `recurrence_groups` (tables séparées).
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, Index, String
from sqlalchemy import Text as SAText
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.models.base import Base


class DuplicateGroup(Base):
    """Groupe de doublons stricts (Q9-B)."""

    __tablename__ = "duplicate_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(UUID(as_uuid=True), nullable=False)  # IS1

    # Détection
    detection_method = Column(String(20), nullable=False)
    detection_signature = Column(SAText, nullable=False)
    representative_item_id = Column(UUID(as_uuid=True), nullable=False)  # FK virtual to action_center_items.id

    # Status (D4)
    status = Column(String(20), nullable=False, server_default="suggested")
    suggested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('suggested', 'merged', 'dismissed')",
            name="chk_duplicate_status",
        ),
        Index("idx_duplicate_groups_org_status", "organisation_id", "status"),
    )
