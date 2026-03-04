"""
PROMEOS — Energy Copilot Models (Chantier 3)
CopilotAction: auto-generated action proposal from rule engine.
"""

import enum

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class CopilotActionStatus(str, enum.Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    CONVERTED = "converted"  # converted to ActionItem


class CopilotAction(Base, TimestampMixin):
    """Auto-generated action proposal from the Energy Copilot rule engine."""

    __tablename__ = "copilot_actions"
    __table_args__ = (UniqueConstraint("site_id", "rule_code", "period_month", "period_year", name="uq_copilot_dedup"),)

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)

    # Rule that triggered this action
    rule_code = Column(String(100), nullable=False, index=True)
    rule_label = Column(String(300), nullable=False)

    # Action details
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, default="energie")
    priority = Column(Integer, nullable=False, default=3)

    # Impact estimation
    estimated_savings_kwh = Column(Float, nullable=True)
    estimated_savings_eur = Column(Float, nullable=True)

    # Evidence (JSON: metrics that triggered the rule)
    evidence_json = Column(Text, nullable=True)

    # Lifecycle
    status = Column(Enum(CopilotActionStatus), default=CopilotActionStatus.PROPOSED, nullable=False, index=True)
    validated_by = Column(String(200), nullable=True)
    validated_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Link to converted ActionItem (if validated)
    action_item_id = Column(Integer, ForeignKey("action_items.id"), nullable=True)

    # Period
    period_month = Column(Integer, nullable=True)  # 1-12
    period_year = Column(Integer, nullable=True)

    # Priority score for ranking (higher = more urgent)
    priority_score = Column(Float, nullable=True, default=0.0)

    # Relations
    site = relationship("Site")
