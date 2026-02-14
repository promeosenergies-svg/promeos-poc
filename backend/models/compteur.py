"""
PROMEOS - Modèle Compteur
Equipements de mesure énergétique (électricité, gaz, eau)
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin
from .enums import TypeCompteur, EnergyVector


class Compteur(Base, TimestampMixin, SoftDeleteMixin):
    """
    Compteur d'énergie (électricité, gaz, eau)
    Un site peut avoir plusieurs compteurs
    """
    __tablename__ = "compteurs"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)

    type = Column(Enum(TypeCompteur), nullable=False, comment="Type de compteur")
    numero_serie = Column(String(50), unique=True, index=True, comment="Numéro de série unique")
    puissance_souscrite_kw = Column(Float, comment="Puissance souscrite (kW) pour électricité")

    meter_id = Column(String(14), nullable=True, comment="Identifiant PRM/PDL/PCE (legacy, voir delivery_point)")
    energy_vector = Column(Enum(EnergyVector), nullable=True, comment="Vecteur energetique")
    actif = Column(Boolean, default=True, comment="Compteur actif ou non")

    # DeliveryPoint FK (nullable for backward compat during migration)
    delivery_point_id = Column(
        Integer, ForeignKey("delivery_points.id"), nullable=True, index=True,
        comment="Point de livraison associe (PRM/PCE)",
    )

    # Data lineage
    data_source = Column(String(20), nullable=True, comment="csv, manual, demo, api")
    data_source_ref = Column(String(200), nullable=True, comment="Batch ID or filename")

    # Relations
    site = relationship("Site", back_populates="compteurs")
    delivery_point = relationship("DeliveryPoint", back_populates="compteurs")
    consommations = relationship(
        "Consommation",
        back_populates="compteur",
        cascade="all, delete-orphan",
        lazy="dynamic"
    )

    @property
    def delivery_code(self):
        """Code PRM/PCE: prefer DeliveryPoint.code, fallback to legacy meter_id."""
        if self.delivery_point:
            return self.delivery_point.code
        return self.meter_id

    def __repr__(self):
        return f"<Compteur {self.id}: {self.type.value} - {self.numero_serie}>"
