"""
PROMEOS - Modèle Usage
Type d'usage d'un bâtiment (bureaux, process, froid, CVC, etc.)
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from .enums import TypeUsage


class Usage(Base, TimestampMixin):
    """Usage énergétique d'un bâtiment"""

    __tablename__ = "usages"

    id = Column(Integer, primary_key=True, index=True)
    batiment_id = Column(Integer, ForeignKey("batiments.id"), nullable=False)
    type = Column(Enum(TypeUsage), nullable=False)
    description = Column(String, nullable=True)

    # Relations
    batiment = relationship("Batiment", backref="usages")
