"""
PROMEOS - Modèle Bâtiment
Unité réglementaire (décret tertiaire, BACS)
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Batiment(Base, TimestampMixin):
    __tablename__ = "batiments"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    nom = Column(String, nullable=False)
    surface_m2 = Column(Float, nullable=False)
    annee_construction = Column(Integer, nullable=True)
    cvc_power_kw = Column(Float, nullable=True, comment="Puissance CVC nominale (kW)")

    # Relations
    site = relationship("Site", backref="batiments")
