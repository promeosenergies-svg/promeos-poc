"""RecurrenceGroup model — Q9-B groupes récurrence (ADR-025 §4.3).

Cardinal Q9-B : récurrence ≠ doublon. Auto-close cascade Q37-A+ (IL6) →
items rattachés ferment avec closure_reason=`resolved_via_recurrence`
(distinct de `merged_duplicate` Q9-B doublon strict).

Status `active/watching/closed` (cohérent ADR-025 §4.3 + L7 §2.5).
"""

from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from models.base import Base


class RecurrenceGroup(Base):
    """Groupe de récurrence (Q9-B)."""

    __tablename__ = "recurrence_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(  # IS1 · M2-4.1 Path B : Integer FK partagé legacy↔V4 (ADR-009 Option D)
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # Signature de récurrence
    domain = Column(String(20), nullable=False)
    source_signature = Column(Text, nullable=False)
    scope_signature = Column(Text, nullable=False)

    # Scope
    site_id = Column(UUID(as_uuid=True))
    building_id = Column(UUID(as_uuid=True))
    meter_id = Column(UUID(as_uuid=True))

    # Lifecycle récurrence
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    occurrence_count = Column(Integer, nullable=False, server_default="1")
    rolling_window_days = Column(Integer, nullable=False, server_default="90")
    representative_item_id = Column(UUID(as_uuid=True), nullable=False)

    # Status (cohérent ADR-025 §4.3)
    status = Column(String(20), nullable=False, server_default="active")
    resolved_at = Column(DateTime(timezone=True))
    resolution_justification = Column(Text)  # IL7 cardinal Amine (auto-close P0/P1 exige preuve OU justification)

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'watching', 'closed')",
            name="chk_recurrence_status",
        ),
        CheckConstraint("occurrence_count >= 1", name="chk_recurrence_occurrence_count"),
        Index(
            "idx_recurrence_groups_org_signature",
            "organisation_id",
            "source_signature",
            "scope_signature",
        ),
        Index(
            "idx_recurrence_groups_org_status",
            "organisation_id",
            "status",
            "last_seen_at",
        ),
    )
