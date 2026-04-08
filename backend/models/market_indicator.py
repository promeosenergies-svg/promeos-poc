"""
PROMEOS — MarketIndicator model
Indicateurs marché extraits des mensuels EuropEnergies.
Complète MktPrice avec des données agrégées mensuelles sourcées.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Index,
    UniqueConstraint,
)
from datetime import datetime, timezone

from models.base import Base, TimestampMixin


class MarketIndicator(TimestampMixin, Base):
    """Indicateurs marché extraits des mensuels (spot, forwards, gaz, pétrole, CO2)."""

    __tablename__ = "market_indicators"

    id = Column(Integer, primary_key=True)

    indicator_name = Column(String(100), nullable=False, index=True)
    period_label = Column(String(50), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=True)

    value_eur_mwh = Column(Float, nullable=True)
    value_low = Column(Float, nullable=True)
    value_high = Column(Float, nullable=True)
    value_close = Column(Float, nullable=True)
    variation_pct = Column(Float, nullable=True)
    unit = Column(String(20), nullable=False, default="EUR_MWH")

    # Provenance
    source_file = Column(String(200), nullable=False)
    source_issue = Column(String(50), nullable=True)
    extracted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("indicator_name", "period_label", "source_file", name="uq_indicator_period_source"),
        Index("ix_indicator_lookup", "indicator_name", "period_start"),
    )

    def __repr__(self):
        return f"<MarketIndicator({self.indicator_name}, {self.period_label}, {self.value_eur_mwh})>"
