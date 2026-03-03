"""
PROMEOS — V97 Reconciliation Fix Log (audit trail)
Tracks every 1-click fix applied to a reconciliation check.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum as SAEnum
from datetime import datetime

from .base import Base, TimestampMixin
from .enums import ReconciliationStatus


class ReconciliationFixLog(Base, TimestampMixin):
    __tablename__ = "reconciliation_fix_logs"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    check_id = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    status_before = Column(SAEnum(ReconciliationStatus), nullable=False)
    status_after = Column(SAEnum(ReconciliationStatus), nullable=False)
    detail_json = Column(Text, nullable=True)
    applied_by = Column(String(200), nullable=True)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)
