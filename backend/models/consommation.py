"""
PROMEOS - Modèle Consommation
Relevés de consommation énergétique (horaires ou journaliers)
"""
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Consommation(Base, TimestampMixin):
    """
    Relevé de consommation énergétique
    Données horaires ou journalières
    """
    __tablename__ = "consommations"

    id = Column(Integer, primary_key=True, index=True)
    compteur_id = Column(Integer, ForeignKey("compteurs.id"), nullable=False, index=True)

    timestamp = Column(DateTime, nullable=False, index=True, comment="Date/heure du relevé")
    valeur = Column(Float, nullable=False, comment="Valeur consommée (kWh, m3, etc.)")
    cout_euro = Column(Float, comment="Coût en euros")

    # Relations
    compteur = relationship("Compteur", back_populates="consommations")

    def __repr__(self):
        return f"<Consommation {self.id}: {self.valeur} à {self.timestamp}>"
