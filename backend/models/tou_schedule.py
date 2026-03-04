"""
PROMEOS - TOU Schedule (Grille Tarifaire HP/HC)
Time-of-Use schedule with effective date versioning.
Supports HP/HC windows per day-type, with source tracking (manual, TURPE, Enedis).
"""

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin


class TOUSchedule(Base, TimestampMixin):
    """Versioned Time-of-Use tariff schedule for a meter or site."""

    __tablename__ = "tou_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Scope (meter-level or site-level)
    meter_id = Column(Integer, ForeignKey("meter.id"), nullable=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)

    # Identity
    name = Column(String(100), nullable=False, default="HC/HP Standard")

    # Versioning with effective dates
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)  # NULL = currently active
    is_active = Column(Boolean, nullable=False, default=True)

    # TOU windows (JSON array)
    # Format: [{"day_types": ["weekday"], "start": "06:00", "end": "22:00", "period": "HP", "price_eur_kwh": 0.18},
    #          {"day_types": ["weekday"], "start": "22:00", "end": "06:00", "period": "HC", "price_eur_kwh": 0.12},
    #          {"day_types": ["weekend", "holiday"], "start": "00:00", "end": "24:00", "period": "HC", "price_eur_kwh": 0.12}]
    windows_json = Column(Text, nullable=False)

    # Source tracking
    source = Column(String(50), nullable=True, default="manual")  # manual, turpe, enedis_sge, grdf
    source_ref = Column(String(200), nullable=True)  # reference doc/API

    # Pricing summary (denormalized for quick display)
    price_hp_eur_kwh = Column(Float, nullable=True)
    price_hc_eur_kwh = Column(Float, nullable=True)

    # Relationships
    meter = relationship("Meter")
    site = relationship("Site")

    def __repr__(self):
        return f"<TOUSchedule(id={self.id}, name='{self.name}', effective={self.effective_from})>"
