"""
PROMEOS — Action Template Model (Chantier 4)
Pre-built action templates (20 models) for quick action creation.
"""

from sqlalchemy import Column, Integer, String, Float, Text, Boolean

from .base import Base, TimestampMixin


class ActionTemplate(Base, TimestampMixin):
    """Bibliotheque d'actions types pre-remplies."""

    __tablename__ = "action_templates"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), nullable=False, unique=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False, index=True)
    priority = Column(Integer, nullable=False, default=3)
    estimated_gain_eur = Column(Float, nullable=True)
    estimated_gain_kwh = Column(Float, nullable=True)
    complexity = Column(String(20), nullable=True)  # simple, medium, complex
    typical_duration_days = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    tags = Column(String(500), nullable=True)  # comma-separated tags

    # V113 — Extra fields for demo-ready enrichment
    typical_gain_pct = Column(Float, nullable=True)  # Expected % energy gain
    typical_cost_range = Column(String(100), nullable=True)  # e.g. "500-2000 EUR"
    confidence_level = Column(String(20), nullable=True)  # high, medium, low
    regulatory_link = Column(String(500), nullable=True)  # URL to regulation
