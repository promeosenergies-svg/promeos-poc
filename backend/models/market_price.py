"""
PROMEOS — MarketPrice model (DEPRECATED — Step 17 legacy, conservation
data-only).

╔════════════════════════════════════════════════════════════════════╗
║ ⚠️  DEPRECATED — Sprint Énergie P2.3 (2026-05-30)                   ║
║                                                                    ║
║ Ce modèle SQLAlchemy mappe vers la table legacy `market_prices`    ║
║ (introduite Step 17). La SOURCE DE VÉRITÉ canonique pour les prix  ║
║ marché énergie est désormais `MktPrice` (table `mkt_prices`)       ║
║ exposé par `backend/models/market_models.py`.                      ║
║                                                                    ║
║ INTERDIT (vérifié par source-guard                                 ║
## `backend/tests/source_guards/test_market_price_canonical_source_guards.py`) :
║ - Tout import applicatif de `MarketPrice` dans                     ║
║   `backend/services/` (hors commentaires et warnings).             ║
║ - Tout import dans `backend/routes/`.                              ║
║ - Tout test métier NOUVEAU fondé sur `MarketPrice`.                ║
║                                                                    ║
║ AUTORISÉ (whitelist documentée) :                                  ║
║ - `backend/models/__init__.py` — export pour compat ORM (import    ║
║   nécessaire pour que SQLAlchemy reconnaisse la table existante).  ║
║ - `backend/tests/test_step17_market_prices.py` — tests legacy      ║
║   explicites du modèle Step 17 (préservation data).                ║
║ - Migrations Alembic — historique non modifiable.                  ║
║ - Source-guard lui-même qui interdit les imports.                  ║
║                                                                    ║
║ CIBLE DE SUPPRESSION (P2.x ultérieur) : table `market_prices`      ║
║ droppée après vérification :                                       ║
║   1. Aucune donnée orpheline qui n'est pas dans `mkt_prices`.      ║
║   2. Backup data triple-artefact (cf. ADR Cutover Mois 4).         ║
║   3. Source-guard 0 violation pendant 2 sprints consécutifs.       ║
║                                                                    ║
║ Migration de référence pour P2.3 → cible :                         ║
║ - Modèle canonique : `from models.market_models import MktPrice`   ║
║ - Champs canoniques : `market_type`, `zone`, `delivery_start`,     ║
║   `delivery_end`, `price_eur_mwh`, `quality_status`,               ║
║   `publication_datetime`.                                          ║
║ - Service abstraction : `backend/services/market_data_service.py`. ║
╚════════════════════════════════════════════════════════════════════╝
"""

from sqlalchemy import Column, Integer, String, Float, Date, UniqueConstraint

from .base import Base, TimestampMixin


class MarketPrice(Base, TimestampMixin):
    """Prix marché énergie LEGACY (EPEX Spot FR, EEX CAL, etc.).

    ⚠️ DEPRECATED — utiliser `MktPrice` depuis `models.market_models`
    pour tout nouveau code. Cf. doctrine in-file ci-dessus.
    """

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
