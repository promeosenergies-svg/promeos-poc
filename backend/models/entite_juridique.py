"""
PROMEOS - Modèle Entité Juridique
SIREN/SIRET - qui signe les contrats / qui paye
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin


class EntiteJuridique(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "entites_juridiques"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    siren = Column(String(9), unique=True, nullable=False)
    siret = Column(String(14), nullable=True)
    naf_code = Column(String(10), nullable=True, comment="Code NAF principal (ex: 47.11F)")
    region_code = Column(String(3), nullable=True, comment="Code region")
    insee_code = Column(String(5), nullable=True, comment="Code INSEE siege")

    # Relations
    organisation = relationship("Organisation", back_populates="entites_juridiques")
    portefeuilles = relationship(
        "Portefeuille",
        back_populates="entite_juridique",
        cascade="all, delete-orphan",
    )
