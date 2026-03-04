"""
PROMEOS - Modele DataPoint
Donnee metrique avec lineage (source, qualite, couverture).
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from .base import Base, TimestampMixin
from .enums import SourceType


class DataPoint(Base, TimestampMixin):
    __tablename__ = "datapoints"

    id = Column(Integer, primary_key=True, index=True)
    object_type = Column(String(20), nullable=False, index=True)
    object_id = Column(Integer, nullable=False, index=True)
    metric = Column(String(50), nullable=False, index=True)
    ts_start = Column(DateTime, nullable=False)
    ts_end = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    source_name = Column(String(50), nullable=False)
    quality_score = Column(Float, default=1.0)
    coverage_ratio = Column(Float, default=1.0)
    retrieved_at = Column(DateTime, nullable=False)
    source_ref = Column(String(500), nullable=True)
