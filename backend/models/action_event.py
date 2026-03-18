"""Audit trail for action plan items (Sprint 13)."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from models.base import Base


class ActionPlanEvent(Base):
    __tablename__ = "action_plan_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("action_plan_items.id"), nullable=False, index=True)
    event_type = Column(
        String(50),
        nullable=False,
        comment="created|status_change|owner_change|priority_change|due_date_change|evidence_added|resolved|reopened|dismissed",
    )
    actor = Column(String(255), nullable=True, default="system")
    old_value = Column(String(500), nullable=True)
    new_value = Column(String(500), nullable=True)
    comment = Column(Text, nullable=True)
    occurred_at = Column(DateTime, server_default=func.now())


class ActionPlanEvidence(Base):
    __tablename__ = "action_plan_evidences"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("action_plan_items.id"), nullable=False, index=True)
    evidence_type = Column(String(50), nullable=False, comment="note|link|document|justification")
    label = Column(String(300), nullable=False)
    value = Column(Text, nullable=True, comment="URL, text content, or document reference")
    document_name = Column(String(300), nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    uploaded_by = Column(String(255), nullable=True, default="system")
