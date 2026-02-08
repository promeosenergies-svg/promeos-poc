"""
PROMEOS - Modèle Portefeuille
Regroupement décisionnel (ex: "Retail IDF", "Région Sud")
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Portefeuille(Base, TimestampMixin):
    __tablename__ = "portefeuilles"

    id = Column(Integer, primary_key=True, index=True)
    entite_juridique_id = Column(Integer, ForeignKey("entites_juridiques.id"), nullable=False)
    nom = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Relations
    entite_juridique = relationship("EntiteJuridique", backref="portefeuilles")
