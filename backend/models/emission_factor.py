"""
PROMEOS - Emission Factor Model (Sprint V9 Decarbonation)
Stores CO2e emission factors per energy type and region.
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime
from datetime import datetime

from .base import Base, TimestampMixin


class EmissionFactor(Base, TimestampMixin):
    """
    Facteur d'emission CO2e par type d'energie et region.
    Unite: kgCO2e/kWh
    """
    __tablename__ = "emission_factors"

    id = Column(Integer, primary_key=True, index=True)
    energy_type = Column(
        String(50), nullable=False, index=True,
        comment="Type d'energie: electricity, gas, heat, other",
    )
    region = Column(
        String(100), nullable=False, default="FR",
        comment="Region/pays (ex: FR, DE, EU-avg)",
    )
    valid_from = Column(Date, nullable=True, comment="Debut de validite")
    valid_to = Column(Date, nullable=True, comment="Fin de validite")
    kgco2e_per_kwh = Column(
        Float, nullable=False,
        comment="Facteur d'emission en kgCO2e/kWh",
    )
    source_label = Column(
        String(300), nullable=True,
        comment="Source du facteur (ex: ADEME Base Carbone 2024, Facteur demo POC)",
    )
    quality = Column(
        String(20), nullable=True, default="demo",
        comment="Qualite: official, estimated, demo",
    )

    def __repr__(self):
        return (
            f"<EmissionFactor(energy_type='{self.energy_type}', "
            f"region='{self.region}', kgCO2e={self.kgco2e_per_kwh})>"
        )
