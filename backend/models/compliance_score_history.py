"""
PROMEOS — Step 33 : Historique mensuel du score conformite.
Snapshot idempotent par site + mois.
"""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, UniqueConstraint, JSON

from .base import Base, TimestampMixin


class ComplianceScoreHistory(Base, TimestampMixin):
    """Snapshot mensuel du score conformite par site."""

    __tablename__ = "compliance_score_history"
    __table_args__ = (
        UniqueConstraint("site_id", "month_key", name="uq_site_month_score"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    month_key = Column(String(7), nullable=False)  # "2025-03"
    score = Column(Float, nullable=False)  # 0-100
    grade = Column(String(1), nullable=True)  # A-F
    breakdown_json = Column(JSON, nullable=True)  # {dt, bacs, aper}
