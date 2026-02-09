"""
PROMEOS - Modele RegAssessment
Cache persistant des evaluations reglementaires RegOps.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, Text, Enum
from .base import Base
from .enums import RegStatus
from datetime import datetime


class RegAssessment(Base):
    __tablename__ = "reg_assessments"

    id = Column(Integer, primary_key=True, index=True)
    object_type = Column(String(20), nullable=False, index=True)
    object_id = Column(Integer, nullable=False, index=True)
    computed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    global_status = Column(Enum(RegStatus), nullable=False)
    compliance_score = Column(Float, default=0.0)
    next_deadline = Column(Date, nullable=True)
    findings_json = Column(Text, nullable=True)
    top_actions_json = Column(Text, nullable=True)
    missing_data_json = Column(Text, nullable=True)
    deterministic_version = Column(String(64), nullable=False)
    ai_version = Column(String(64), nullable=True)
    data_version = Column(String(64), nullable=False)
    is_stale = Column(Boolean, default=False)
    stale_reason = Column(String(200), nullable=True)
