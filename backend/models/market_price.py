"""
PROMEOS — MarketPrice model (DEPRECATED)
Prix marché énergie (EPEX Spot, forwards, etc.)

⚠️ DEPRECATED: Ce modèle mappe vers la table legacy 'market_prices' (Step 17).
La source de vérité est désormais MktPrice (table 'mkt_prices') dans market_models.py.
Ne pas utiliser dans du nouveau code. Sera supprimé dans une future migration
après vérification que la table legacy peut être droppée.
"""

from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint

from .base import Base, TimestampMixin


class MarketPrice(Base, TimestampMixin):
    """Prix marché énergie (EPEX Spot FR, EEX CAL, etc.)"""

    __tablename__ = "market_prices"
    __table_args__ = (UniqueConstraint("market", "date", "energy_type", name="uq_market_date_energy"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    market = Column(String(50), nullable=False, index=True)  # "EPEX_SPOT_FR", "EEX_CAL"
    energy_type = Column(String(20), nullable=False, default="ELEC")  # ELEC, GAZ
    date = Column(Date, nullable=False, index=True)
    price_eur_mwh = Column(Float, nullable=False)  # Prix en EUR/MWh
    volume_mwh = Column(Float, nullable=True)  # Volume échangé (optionnel)
    source = Column(String(100), nullable=True)  # "Seed PROMEOS — basé sur tendances EPEX 2024-2025"

    def __repr__(self):
        return f"<MarketPrice(market={self.market}, date={self.date}, price={self.price_eur_mwh})>"
