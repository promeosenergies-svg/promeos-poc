"""
PROMEOS - EMS Consumption Explorer Models
Weather cache and saved view presets.
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin


class EmsWeatherCache(Base, TimestampMixin):
    """Cached daily weather data per site for energy signature analysis."""

    __tablename__ = "ems_weather_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    temp_avg_c = Column(Float, nullable=False)
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    source = Column(String(50), nullable=False, default="demo")

    site = relationship("Site")

    __table_args__ = (Index("ix_ems_weather_site_date", "site_id", "date", unique=True),)

    def __repr__(self):
        return f"<EmsWeatherCache(site_id={self.site_id}, date={self.date}, avg={self.temp_avg_c})>"


class EmsSavedView(Base, TimestampMixin):
    """Saved view preset for the Consumption Explorer."""

    __tablename__ = "ems_saved_view"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    name = Column(String(200), nullable=False)
    config_json = Column(Text, nullable=False)

    def __repr__(self):
        return f"<EmsSavedView(id={self.id}, name='{self.name}')>"


class EmsCollection(Base, TimestampMixin):
    """Saved site selection ('panier') for the Consumption Explorer."""

    __tablename__ = "ems_collection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    scope_type = Column(String(50), nullable=False, default="custom")  # portfolio/org/custom
    site_ids_json = Column(Text, nullable=False, default="[]")
    is_favorite = Column(Integer, nullable=False, default=0)  # SQLite boolean

    def __repr__(self):
        return f"<EmsCollection(id={self.id}, name='{self.name}')>"
