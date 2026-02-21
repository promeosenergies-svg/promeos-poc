"""
PROMEOS — TariffCalendar model (system-level reference tariff schedules)
Separate from TOUSchedule (user/site-level). Used for TURPE versioning & simulation.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from .base import Base, TimestampMixin


class TariffCalendar(Base, TimestampMixin):
    """Reference tariff calendar (TURPE, etc.) — system-level, not site-specific."""
    __tablename__ = "tariff_calendars"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="Ex: TURPE 6 HTA")
    version = Column(String(50), nullable=True, comment="Version tag")
    effective_from = Column(String(10), nullable=False, comment="ISO date YYYY-MM-DD")
    effective_to = Column(String(10), nullable=True, comment="ISO date YYYY-MM-DD or null")
    region = Column(String(100), nullable=True, comment="Region or 'national'")
    ruleset_json = Column(Text, nullable=False, comment="JSON array of windows")
    is_active = Column(Boolean, default=True)
    source = Column(String(100), nullable=True, comment="CRE, manual, etc.")
    notes = Column(Text, nullable=True)

    def __repr__(self):
        return f"<TariffCalendar {self.id}: {self.name} ({self.effective_from})>"
