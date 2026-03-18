"""Persisted decisions on recommendations."""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float
from sqlalchemy.sql import func
from models.base import Base


class RecommendationDecision(Base):
    __tablename__ = "recommendation_decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String(100), nullable=False, index=True, comment="rec_{action_id}")
    action_id = Column(Integer, nullable=True, comment="Source action_plan_item.id")
    decision = Column(String(30), nullable=False, comment="accepted|dismissed|deferred|converted_to_action")
    reason = Column(Text, nullable=True)
    created_action_id = Column(Integer, nullable=True, comment="New action created from conversion")
    decision_score_at_time = Column(Float, nullable=True)
    actor = Column(String(255), default="system")
    decided_at = Column(DateTime, server_default=func.now())
