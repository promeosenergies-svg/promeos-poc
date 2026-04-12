"""
PROMEOS - UsageBreakdownSnapshot
Historise les decompositions CDC mensuelles par site.
Permet de suivre l'evolution de la repartition par usage dans le temps.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, Text, UniqueConstraint
from .base import Base, TimestampMixin


class UsageBreakdownSnapshot(Base, TimestampMixin):
    """Snapshot mensuel de la decomposition CDC par usage d'un site."""

    __tablename__ = "usage_breakdown_snapshot"
    __table_args__ = (UniqueConstraint("site_id", "month_key", name="uq_breakdown_site_month"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, nullable=False, index=True)
    month_key = Column(String(7), nullable=False)  # YYYY-MM
    archetype_code = Column(String(50), nullable=False)
    total_kwh = Column(Float, nullable=False)
    breakdown_json = Column(Text, nullable=False)  # JSON: [{code, label, kwh, pct, method, confidence}]
    confidence_global = Column(String(20), nullable=True)
    method = Column(String(50), nullable=True)
    n_readings = Column(Integer, nullable=True)
