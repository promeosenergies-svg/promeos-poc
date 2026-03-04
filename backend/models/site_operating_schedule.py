"""
PROMEOS - Modele SiteOperatingSchedule
Horaires d'exploitation d'un site (pour detection hors_horaires).
"""

from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DateTime, Time
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class SiteOperatingSchedule(Base, TimestampMixin):
    """
    Horaires d'exploitation d'un site.
    Utilise par le detecteur hors_horaires pour definir
    les heures normales vs hors-horaires.
    """

    __tablename__ = "site_operating_schedules"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        unique=True,
        index=True,
        comment="Site concerne (1-to-1)",
    )
    timezone = Column(
        String(50),
        nullable=False,
        default="Europe/Paris",
        comment="Fuseau horaire IANA",
    )
    open_days = Column(
        String(20),
        nullable=False,
        default="0,1,2,3,4",
        comment="Jours ouverts (0=lundi, 6=dimanche), CSV",
    )
    open_time = Column(
        String(5),
        nullable=False,
        default="08:00",
        comment="Heure d'ouverture (HH:MM)",
    )
    close_time = Column(
        String(5),
        nullable=False,
        default="19:00",
        comment="Heure de fermeture (HH:MM)",
    )
    is_24_7 = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Site en fonctionnement 24/7",
    )
    exceptions_json = Column(
        Text,
        nullable=True,
        comment="Jours feries / exceptions (JSON array of YYYY-MM-DD)",
    )
    intervals_json = Column(
        Text,
        nullable=True,
        comment='Multi-interval schedule: {"0":[{"start":"08:00","end":"12:00"},...],...}',
    )

    # Relations
    site = relationship("Site", backref="operating_schedule", uselist=False)
