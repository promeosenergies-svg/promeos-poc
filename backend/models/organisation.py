"""
PROMEOS - Modèle Organisation
Niveau groupe/client COMEX (ex: "Groupe Casino", "Ville de Lyon")
"""
from sqlalchemy import Column, Integer, String, Boolean
from .base import Base, TimestampMixin


class Organisation(Base, TimestampMixin):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    type_client = Column(String, nullable=True)  # "retail", "tertiaire", "industrie"
    logo_url = Column(String, nullable=True)
    actif = Column(Boolean, default=True)
