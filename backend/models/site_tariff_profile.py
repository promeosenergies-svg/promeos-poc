"""
PROMEOS - Modele SiteTariffProfile
Prix de reference kWh par site (pour estimation pertes EUR).
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH


class SiteTariffProfile(Base, TimestampMixin):
    """
    Profil tarifaire d'un site.
    Utilise pour convertir les pertes kWh en EUR.
    """

    __tablename__ = "site_tariff_profiles"

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=False,
        unique=True,
        index=True,
        comment="Site concerne (1-to-1)",
    )
    price_ref_eur_per_kwh = Column(
        Float,
        nullable=False,
        default=DEFAULT_PRICE_ELEC_EUR_KWH,
        comment="Prix de reference EUR HT par kWh",
    )
    currency = Column(
        String(3),
        nullable=False,
        default="EUR",
        comment="Devise (ISO 4217)",
    )

    # Relations
    site = relationship("Site", backref="tariff_profile", uselist=False)
