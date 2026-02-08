"""
PROMEOS - Enums et modèles pour la conformité réglementaire
"""
import enum
from sqlalchemy import Column, Integer, String, Date, Boolean, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class StatutConformite(str, enum.Enum):
    """Statut de conformité"""
    CONFORME = "conforme"
    A_RISQUE = "a_risque"
    NON_CONFORME = "non_conforme"


class TypeObligation(str, enum.Enum):
    """Types d'obligations réglementaires"""
    DECRET_TERTIAIRE = "decret_tertiaire"
    BACS = "bacs"
    APER = "aper"


class Obligation(Base, TimestampMixin):
    """Obligation réglementaire attachée à un site"""
    __tablename__ = "obligations"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    type = Column(Enum(TypeObligation), nullable=False)
    description = Column(String, nullable=True)
    echeance = Column(Date, nullable=True)
    statut = Column(Enum(StatutConformite), default=StatutConformite.A_RISQUE)
    avancement_pct = Column(Float, default=0.0)  # 0-100

    # Relations
    site = relationship("Site", backref="obligations")
