"""
PROMEOS - Modèle Obligation (conformité réglementaire)
"""
from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
from .enums import StatutConformite, TypeObligation


class Obligation(Base, TimestampMixin):
    """Obligation réglementaire attachée à un site"""
    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    type = Column(Enum(TypeObligation), nullable=False)
    description = Column(String, nullable=True)
    echeance = Column(Date, nullable=True)
    statut = Column(Enum(StatutConformite), default=StatutConformite.A_RISQUE)
    avancement_pct = Column(Float, default=0.0)  # 0-100

    # Relations
    site = relationship("Site", back_populates="obligations")
