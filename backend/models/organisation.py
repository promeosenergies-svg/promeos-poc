"""
PROMEOS - Modèle Organisation
Niveau groupe/client COMEX (ex: "Groupe Casino", "Ville de Lyon")
"""
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin


class Organisation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    type_client = Column(String, nullable=True)  # "retail", "tertiaire", "industrie"
    logo_url = Column(String, nullable=True)
    siren = Column(String(9), nullable=True, comment="Numero SIREN")
    actif = Column(Boolean, default=True)

    # Relations (1-to-many)
    entites_juridiques = relationship(
        "EntiteJuridique",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
