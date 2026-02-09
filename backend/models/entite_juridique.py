"""
PROMEOS - Modèle Entité Juridique
SIREN/SIRET - qui signe les contrats / qui paye
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class EntiteJuridique(Base, TimestampMixin):
    __tablename__ = "entites_juridiques"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    nom = Column(String, nullable=False)
    siren = Column(String(9), unique=True, nullable=False)
    siret = Column(String(14), nullable=True)
    naf_code = Column(String(5), nullable=True, comment="Code NAF principal")
    region_code = Column(String(3), nullable=True, comment="Code region")
    insee_code = Column(String(5), nullable=True, comment="Code INSEE siege")

    # Relations
    organisation = relationship("Organisation", backref="entites_juridiques")
