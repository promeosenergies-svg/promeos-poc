"""
PROMEOS - Modèle Portefeuille
Regroupement décisionnel (ex: "Retail IDF", "Région Sud")
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin


class Portefeuille(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "portefeuilles"

    id = Column(Integer, primary_key=True, index=True)
    entite_juridique_id = Column(Integer, ForeignKey("entites_juridiques.id"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Relations
    entite_juridique = relationship("EntiteJuridique", back_populates="portefeuilles")
    sites = relationship("Site", back_populates="portefeuille", cascade="all, delete-orphan")
