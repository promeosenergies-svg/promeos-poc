"""
PROMEOS - Modèle Evidence (preuves de conformité)
"""

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from .enums import TypeEvidence, StatutEvidence


class Evidence(Base, TimestampMixin):
    """Preuve de conformité attachée à un site"""

    __tablename__ = "evidences"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    type = Column(Enum(TypeEvidence), nullable=False)
    statut = Column(Enum(StatutEvidence), nullable=False, default=StatutEvidence.EN_ATTENTE)
    note = Column(String, nullable=True)
    file_url = Column(String, nullable=True)

    # Relations
    site = relationship("Site", backref="evidences")
