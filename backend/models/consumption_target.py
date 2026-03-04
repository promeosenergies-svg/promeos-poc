"""
PROMEOS - Consumption Target (Objectifs & Budgets)
Monthly/yearly energy targets per site with kWh, EUR, and CO2e tracking.
"""

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin


class ConsumptionTarget(Base, TimestampMixin):
    """Energy consumption target for a site and period."""

    __tablename__ = "consumption_targets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Scope
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    energy_type = Column(String(20), nullable=False, default="electricity")  # electricity, gas

    # Period
    period = Column(String(10), nullable=False)  # "monthly" or "yearly"
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=True)  # 1-12 for monthly, NULL for yearly

    # Targets
    target_kwh = Column(Float, nullable=True)
    target_eur = Column(Float, nullable=True)
    target_co2e_kg = Column(Float, nullable=True)

    # Actual (filled by measurement)
    actual_kwh = Column(Float, nullable=True)
    actual_eur = Column(Float, nullable=True)
    actual_co2e_kg = Column(Float, nullable=True)

    # Metadata
    source = Column(String(50), nullable=True, default="manual")  # manual, import, forecast
    notes = Column(Text, nullable=True)

    # Relationships
    site = relationship("Site")

    def __repr__(self):
        return f"<ConsumptionTarget(site_id={self.site_id}, {self.energy_type}, {self.year}-{self.month or 'Y'})>"
