"""
PROMEOS - Modèle Usage
Usage energetique d'un batiment / zone fonctionnelle.
Entite pivot reliant Compteur → Derive → Action → Conformite → Facture.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin
from .enums import TypeUsage, UsageFamily, DataSourceType, USAGE_FAMILY_MAP


class Usage(Base, TimestampMixin):
    """Usage energetique d'un batiment.

    Entite pivot V1.1 : lie un type d'usage a un batiment,
    avec surface, source de donnee, et score de readiness.
    Les Meter (sous-compteurs) referent cet usage via Meter.usage_id.
    """

    __tablename__ = "usages"

    id = Column(Integer, primary_key=True, index=True)
    batiment_id = Column(Integer, ForeignKey("batiments.id"), nullable=False, index=True)
    type = Column(Enum(TypeUsage), nullable=False)
    description = Column(String, nullable=True)

    # V1.1 — Enrichissement usage
    label = Column(String(200), nullable=True, comment="Label libre FR (ex: Chauffage RDC)")
    surface_m2 = Column(Float, nullable=True, comment="Surface couverte par cet usage (m2)")
    data_source = Column(
        Enum(DataSourceType), nullable=True, default=None, comment="Source principale des donnees pour cet usage"
    )
    is_significant = Column(
        Boolean, nullable=False, default=False, comment="Usage energetique significatif (UES) — critere ISO 50001"
    )
    pct_of_total = Column(Float, nullable=True, comment="Part estimee de la conso totale du site (0-100)")

    # Relations
    batiment = relationship("Batiment", backref="usages")
    meters = relationship("Meter", back_populates="usage", foreign_keys="Meter.usage_id")

    @property
    def family(self) -> UsageFamily | None:
        """Famille de rattachement (thermique, eclairage, etc.)."""
        return USAGE_FAMILY_MAP.get(self.type)

    def __repr__(self):
        return f"<Usage(id={self.id}, type='{self.type.value}', batiment_id={self.batiment_id})>"


class UsageBaseline(Base, TimestampMixin):
    """Baseline energetique d'un usage — reference pour avant/apres action.

    Permet de calculer l'IPE (kWh/m2/an) et de prouver les gains.
    """

    __tablename__ = "usage_baselines"

    id = Column(Integer, primary_key=True, index=True)
    usage_id = Column(Integer, ForeignKey("usages.id"), nullable=False, index=True)

    # Periode de reference
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Valeurs de reference
    kwh_total = Column(Float, nullable=False, comment="Consommation totale sur la periode (kWh)")
    kwh_m2_year = Column(Float, nullable=True, comment="IPE: kWh/m2/an normalise")
    peak_kw = Column(Float, nullable=True, comment="Puissance de pointe (kW)")

    # Metadonnees
    data_source = Column(Enum(DataSourceType), nullable=True, comment="Source des donnees baseline")
    confidence = Column(Float, nullable=True, comment="Score de confiance (0-1)")
    notes = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, comment="Baseline courante pour cet usage")

    # Relations
    usage = relationship("Usage", backref="baselines")

    def __repr__(self):
        return f"<UsageBaseline(usage_id={self.usage_id}, kwh={self.kwh_total}, period={self.period_start.date()})>"
