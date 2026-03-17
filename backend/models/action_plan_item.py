"""Persisted action plan items linked to ActionableIssues."""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.sql import func
from models.base import Base


class ActionPlanItem(Base):
    __tablename__ = "action_plan_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    issue_id = Column(String(200), nullable=False, index=True, comment="ActionableIssue.issue_id")
    domain = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    site_id = Column(Integer, nullable=False, index=True)
    issue_code = Column(String(100), nullable=False)
    issue_label = Column(String(500), nullable=False)
    reason_codes = Column(Text, nullable=True, comment="JSON array of reason codes")
    estimated_impact_eur = Column(Float, nullable=True)
    recommended_action = Column(String(1000), nullable=True)

    # Workflow
    status = Column(String(30), nullable=False, default="open", comment="open|in_progress|resolved|dismissed|reopened")
    owner = Column(String(255), nullable=True)
    due_date = Column(DateTime, nullable=True)
    evidence_required = Column(Boolean, default=False)
    evidence_received = Column(Boolean, default=False)
    evidence_note = Column(Text, nullable=True)
    resolution_note = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)
    reopened_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
