"""Observed outcomes of recommendations for quality measurement."""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.sql import func
from .base import Base


class RecommendationOutcome(Base):
    __tablename__ = "recommendation_outcomes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String(100), nullable=False, index=True)
    action_id = Column(Integer, nullable=True)
    calibration_version = Column(String(20), nullable=True)
    domain = Column(String(50), nullable=True)
    decision = Column(String(30), nullable=True)
    outcome_status = Column(String(30), nullable=False, default="pending", comment="pending|positive|neutral|negative")
    outcome_reason = Column(Text, nullable=True)
    backlog_delta = Column(Integer, nullable=True)
    overdue_delta = Column(Integer, nullable=True)
    impact_delta_eur = Column(Float, nullable=True)
    measured_at = Column(DateTime, server_default=func.now())


class CalibrationVersion(Base):
    __tablename__ = "calibration_versions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default="draft", comment="draft|active|archived|rolled_back")
    weights_json = Column(Text, nullable=False, comment="JSON: {urgency, risk, ease, confidence}")
    domain_adjustments_json = Column(Text, nullable=True)
    comment = Column(Text, nullable=True)
    created_by = Column(String(255), default="system")
    effective_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    activated_at = Column(DateTime, nullable=True)
    rolled_back_at = Column(DateTime, nullable=True)
