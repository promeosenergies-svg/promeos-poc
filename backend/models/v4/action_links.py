"""ActionLink — liens vers autres modules (ADR-025 §4.3).

Permet de relier un ActionCenterItem à des entités externes (factures, contrats,
sites, compteurs, certifications). Reverse lookup via target_module + target_id.

Invariants applicables :
- IS1 : organisation_id
- ON DELETE CASCADE : si l'item est supprimé, les liens disparaissent
"""

from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.models.base import Base


class ActionLink(Base):
    """Lien d'un ActionCenterItem vers une entité d'un autre module."""

    __tablename__ = "action_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    organisation_id = Column(UUID(as_uuid=True), nullable=False)  # IS1
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("action_center_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Type de lien (anomaly_caused_by_invoice, action_resolves_anomaly, ...)
    link_type = Column(String(40), nullable=False)
    target_module = Column(String(40), nullable=False)  # 'billing' | 'patrimoine' | 'conformity' | ...
    target_id = Column(UUID(as_uuid=True), nullable=False)
    relation = Column(String(40), nullable=False)  # 'caused_by' | 'resolves' | 'references' | ...

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        # ─── Indexes (cohérent ADR-025 §4.2 — 2 indexes pour cette table) ───
        Index("idx_links_item", "item_id"),
        Index("idx_links_target", "target_module", "target_id", "relation"),
    )
