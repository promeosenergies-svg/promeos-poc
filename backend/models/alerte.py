"""
PROMEOS - Modèle Alerte
Notifications de dépassement ou anomalie énergétique
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from .enums import SeveriteAlerte


class Alerte(Base, TimestampMixin):
    """Alerte de dépassement ou anomalie énergétique"""
    __tablename__ = "alertes"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)

    severite = Column(Enum(SeveriteAlerte), nullable=False, index=True, comment="Niveau de gravité")
    titre = Column(String(200), nullable=False, comment="Titre de l'alerte")
    description = Column(Text, comment="Description détaillée")

    timestamp = Column(DateTime, nullable=False, index=True, comment="Date/heure de l'alerte")
    resolue = Column(Boolean, default=False, comment="Alerte résolue ou non")
    date_resolution = Column(DateTime, comment="Date de résolution")

    # Relations
    site = relationship("Site", back_populates="alertes")

    def __repr__(self):
        status = "OK" if self.resolue else "!!"
        return f"<Alerte {self.id}: {status} {self.titre} ({self.severite.value})>"
