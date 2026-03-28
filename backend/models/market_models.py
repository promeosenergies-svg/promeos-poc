"""
Market Data Models -- Prix marche electricite France.
Architecture concue pour 2026-2030 : post-ARENH, VNU, nouveau mecanisme capacite.

COEXISTENCE TABLE LEGACY:
La table 'market_prices' (Step 17 legacy) existe encore en DB avec un schema simple.
La nouvelle table 'mkt_prices' (ce fichier) est la source de verite pour tous les
nouveaux developpements. La table legacy sera supprimee dans une future migration
apres verification que plus aucun code ne la reference.

Migration tracking:
- Commit fix/market-data-cleanup: consommateurs legacy migres vers mkt_prices
  (purchase_pricing.py, billing_service.py, routes/market.py, gen_market_prices.py)
- TODO: DROP TABLE market_prices quand seed_data.py ne la reference plus
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Enum as SAEnum,
    Boolean,
    Text,
    JSON,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum

from models.base import Base, TimestampMixin


# -- Enums ------------------------------------------------------------------


class MarketDataSource(str, enum.Enum):
    """Source de la donnee prix"""

    ENTSOE = "ENTSOE"  # ENTSO-E Transparency Platform (gratuit)
    RTE_WHOLESALE = "RTE_WHOLESALE"  # RTE data.rte-france.com (gratuit, OAuth2)
    EEX = "EEX"  # EEX Group DataSource (payant, sFTP/API)
    EPEX_SPOT = "EPEX_SPOT"  # EPEX SPOT direct (payant, licence)
    PILOTT = "PILOTT"  # Pilott/Sirenergies (freemium)
    MANUAL = "MANUAL"  # Saisie manuelle / import CSV
    COMPUTED = "COMPUTED"  # Calcule par PROMEOS (indices derives)


class MarketType(str, enum.Enum):
    """Type de marche"""

    SPOT_DAY_AHEAD = "SPOT_DAY_AHEAD"  # J-1, fixing 12h30-13h
    SPOT_INTRADAY = "SPOT_INTRADAY"  # Continu, jusqu'a 5min avant livraison
    FORWARD_MONTH = "FORWARD_MONTH"  # M+1, M+2, M+3...
    FORWARD_QUARTER = "FORWARD_QUARTER"  # Q+1, Q+2...
    FORWARD_YEAR = "FORWARD_YEAR"  # CAL+1, CAL+2, CAL+3...
    FORWARD_WEEK = "FORWARD_WEEK"  # W+1, W+2...
    CAPACITY = "CAPACITY"  # Mecanisme de capacite (encheres)
    BALANCING = "BALANCING"  # Prix d'ajustement RTE


class ProductType(str, enum.Enum):
    """Type de produit"""

    BASELOAD = "BASELOAD"  # 24h/24, 7j/7
    PEAKLOAD = "PEAKLOAD"  # Lun-Ven 8h-20h (France)
    OFFPEAK = "OFFPEAK"  # Heures creuses
    HOURLY = "HOURLY"  # Prix horaire (spot)


class PriceZone(str, enum.Enum):
    """Zone de prix (bidding zone ENTSO-E)"""

    FR = "FR"  # France -- 10YFR-RTE------C
    DE_LU = "DE_LU"  # Allemagne-Luxembourg
    BE = "BE"  # Belgique
    ES = "ES"  # Espagne
    IT_NORTH = "IT_NORTH"
    NL = "NL"  # Pays-Bas
    GB = "GB"  # Grande-Bretagne
    CH = "CH"  # Suisse


class TariffType(str, enum.Enum):
    """Type de tarif reglemente"""

    TURPE = "TURPE"  # Acheminement electricite
    CSPE = "CSPE"  # Accise sur l'electricite (ex-TICFE)
    CAPACITY = "CAPACITY"  # Mecanisme de capacite
    CEE = "CEE"  # Certificats Economies Energie
    CTA = "CTA"  # Contribution Tarifaire Acheminement
    TVA = "TVA"  # TVA (5.5% abo, 20% conso)
    VNU = "VNU"  # Versement Nucleaire Universel (post-ARENH)
    ATRD = "ATRD"  # Acheminement distribution gaz
    ATRT = "ATRT"  # Acheminement transport gaz
    TICGN = "TICGN"  # Accise gaz (ex-TICGN)


class TariffComponent(str, enum.Enum):
    """Composante de tarif (granularite fine)"""

    # TURPE
    TURPE_PART_FIXE = "TURPE_PART_FIXE"
    TURPE_SOUTIRAGE_HPH = "TURPE_SOUTIRAGE_HPH"
    TURPE_SOUTIRAGE_HCH = "TURPE_SOUTIRAGE_HCH"
    TURPE_SOUTIRAGE_HPB = "TURPE_SOUTIRAGE_HPB"
    TURPE_SOUTIRAGE_HCB = "TURPE_SOUTIRAGE_HCB"
    TURPE_SOUTIRAGE_POINTE = "TURPE_SOUTIRAGE_POINTE"
    TURPE_COMPTAGE = "TURPE_COMPTAGE"
    TURPE_DEPASSEMENT = "TURPE_DEPASSEMENT"
    # CSPE par profil
    CSPE_C5 = "CSPE_C5"  # <=36 kVA menages/assimiles
    CSPE_C4 = "CSPE_C4"  # >36 kVA PME
    CSPE_C2 = "CSPE_C2"  # >250 kVA
    CSPE_ELECTRO_INTENSIF = "CSPE_ELECTRO_INTENSIF"  # Taux reduit
    # Capacite
    CAPACITY_PRICE_MW = "CAPACITY_PRICE_MW"
    CAPACITY_COEFFICIENT = "CAPACITY_COEFFICIENT"
    # VNU
    VNU_SEUIL_BAS = "VNU_SEUIL_BAS"  # 78 EUR/MWh
    VNU_SEUIL_HAUT = "VNU_SEUIL_HAUT"  # 110 EUR/MWh
    VNU_TAUX_PRELEVEMENT = "VNU_TAUX_PRELEVEMENT"
    # CEE
    CEE_OBLIGATION = "CEE_OBLIGATION"
    # CTA
    CTA_TAUX = "CTA_TAUX"
    # TVA
    TVA_REDUIT = "TVA_REDUIT"
    TVA_NORMAL = "TVA_NORMAL"
    # Gaz — ATRD / ATRT / TICGN
    ATRD_VARIABLE_T2 = "ATRD_VARIABLE_T2"
    ATRT_VARIABLE = "ATRT_VARIABLE"
    TICGN_PRO = "TICGN_PRO"


class SignalType(str, enum.Enum):
    """Type de signal prix"""

    SPOT_ALERT_HIGH = "SPOT_ALERT_HIGH"  # Prix spot > seuil haut
    SPOT_ALERT_LOW = "SPOT_ALERT_LOW"  # Prix spot < seuil bas (fenetre achat)
    SPOT_NEGATIVE = "SPOT_NEGATIVE"  # Prix negatif (surplus EnR)
    FORWARD_TREND_UP = "FORWARD_TREND_UP"  # Tendance haussiere forwards
    FORWARD_TREND_DOWN = "FORWARD_TREND_DOWN"  # Tendance baissiere
    BUYING_WINDOW = "BUYING_WINDOW"  # Fenetre d'achat recommandee
    SPREAD_ALERT = "SPREAD_ALERT"  # Spread spot-forward anormal
    REGULATORY_CHANGE = "REGULATORY_CHANGE"  # Changement tarif reglemente
    VNU_ACTIVATION = "VNU_ACTIVATION"  # Seuil VNU atteint
    CAPACITY_AUCTION = "CAPACITY_AUCTION"  # Resultat enchere capacite


class SignalSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    OPPORTUNITY = "OPPORTUNITY"  # Signal positif (fenetre achat)


class Resolution(str, enum.Enum):
    """Resolution temporelle des donnees"""

    PT15M = "PT15M"  # 15 minutes (EPEX depuis oct 2025)
    PT30M = "PT30M"  # 30 minutes (Enedis C5)
    PT60M = "PT60M"  # 1 heure (standard day-ahead)
    P1D = "P1D"  # Journalier
    P1W = "P1W"  # Hebdomadaire
    P1M = "P1M"  # Mensuel
    P3M = "P3M"  # Trimestriel
    P1Y = "P1Y"  # Annuel


# -- Modeles ----------------------------------------------------------------


class MktPrice(TimestampMixin, Base):
    """
    Prix marche electricite -- table principale V2.
    Stocke spot, forwards, capacite, ajustement.
    Indexee pour des requetes rapides par zone+marche+date.

    NOTE: Table 'mkt_prices' (pas 'market_prices' qui est la table legacy Step 17).
    """

    __tablename__ = "mkt_prices"

    id = Column(Integer, primary_key=True)
    source = Column(SAEnum(MarketDataSource), nullable=False, index=True)
    market_type = Column(SAEnum(MarketType), nullable=False, index=True)
    product_type = Column(SAEnum(ProductType), nullable=False, index=True)
    zone = Column(SAEnum(PriceZone), nullable=False, default=PriceZone.FR, index=True)

    delivery_start = Column(DateTime(timezone=True), nullable=False, index=True)
    delivery_end = Column(DateTime(timezone=True), nullable=False)

    price_eur_mwh = Column(Float, nullable=False)
    volume_mwh = Column(Float, nullable=True)  # Volume echange (si dispo)

    resolution = Column(SAEnum(Resolution), nullable=False, default=Resolution.PT60M)
    fetched_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_provisional = Column(Boolean, default=False)  # Donnee provisoire vs definitive

    # Metadonnees source
    source_reference = Column(String(200), nullable=True)  # ID source externe
    quality_flag = Column(String(20), nullable=True)  # GOOD / ESTIMATED / MISSING

    __table_args__ = (
        UniqueConstraint(
            "source",
            "market_type",
            "product_type",
            "zone",
            "delivery_start",
            "resolution",
            name="uq_mkt_price_natural_key",
        ),
        Index("ix_mkt_price_lookup", "zone", "market_type", "delivery_start"),
        Index("ix_mkt_price_range", "zone", "market_type", "delivery_start", "delivery_end"),
    )


class RegulatedTariff(TimestampMixin, Base):
    """
    Tarifs reglementes versionnes -- TURPE, CSPE, Capacite, CEE, CTA, VNU.
    Chaque modification cree une nouvelle ligne avec valid_from/valid_to.
    Jamais de UPDATE -- insert-only pour tracabilite.
    """

    __tablename__ = "regulated_tariffs"

    id = Column(Integer, primary_key=True)
    tariff_type = Column(SAEnum(TariffType), nullable=False, index=True)
    component = Column(SAEnum(TariffComponent), nullable=False, index=True)

    value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # EUR_MWH, EUR_KW_AN, PCT, EUR_MW, etc.

    valid_from = Column(DateTime(timezone=True), nullable=False, index=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)  # NULL = en vigueur

    # Tracabilite
    source_name = Column(String(100), nullable=False)  # CRE, LOI_FINANCES, EPEX_SPOT
    source_reference = Column(String(500), nullable=True)  # URL deliberation, n. decret
    source_date = Column(DateTime(timezone=True), nullable=True)  # Date publication source
    version = Column(String(20), nullable=False)  # "TURPE7", "LF2025", "2026-Q1"
    notes = Column(Text, nullable=True)  # Commentaire libre (ex: "Bouclier tarifaire")

    # Contexte d'application
    applies_to_profile = Column(String(50), nullable=True)  # C5, C4, C2, HTA, HTB
    applies_to_voltage = Column(String(20), nullable=True)  # BT, HTA, HTB
    applies_to_power_range = Column(String(50), nullable=True)  # "<36kVA", "36-250kVA", ">250kVA"

    __table_args__ = (
        Index("ix_tariff_lookup", "tariff_type", "component", "valid_from"),
        Index("ix_tariff_current", "tariff_type", "component", "valid_to"),
    )


class PriceSignal(TimestampMixin, Base):
    """
    Signaux prix calcules pour les clients.
    Generes automatiquement par le signal_engine a partir des MktPrice + RegulatedTariff.
    Scopes par organisation.
    """

    __tablename__ = "price_signals"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=True, index=True)

    signal_type = Column(SAEnum(SignalType), nullable=False, index=True)
    severity = Column(SAEnum(SignalSeverity), nullable=False, index=True)

    title_fr = Column(String(200), nullable=False)
    message_fr = Column(Text, nullable=False)
    recommendation_fr = Column(Text, nullable=True)

    # Donnees structurees du signal
    data_json = Column(JSON, nullable=True)  # {price, threshold, trend, delta_pct, ...}

    # Lifecycle
    is_active = Column(Boolean, default=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(Integer, nullable=True)

    # Source du signal
    trigger_market_price_id = Column(Integer, ForeignKey("mkt_prices.id"), nullable=True)
    trigger_tariff_id = Column(Integer, ForeignKey("regulated_tariffs.id"), nullable=True)

    __table_args__ = (Index("ix_signal_active", "org_id", "is_active", "signal_type"),)


class MarketDataFetchLog(TimestampMixin, Base):
    """
    Log des fetches de donnees marche.
    Permet le monitoring, le retry, et l'audit de fraicheur.
    """

    __tablename__ = "market_data_fetch_logs"

    id = Column(Integer, primary_key=True)
    connector_name = Column(String(50), nullable=False, index=True)  # "entsoe", "rte_wholesale"
    fetch_type = Column(String(50), nullable=False)  # "day_ahead_prices", "forward_curves"
    zone = Column(SAEnum(PriceZone), nullable=False, default=PriceZone.FR)

    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    status = Column(String(20), nullable=False, default="RUNNING")  # RUNNING, SUCCESS, FAILED, PARTIAL
    records_fetched = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)

    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    # Periode couverte
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (Index("ix_fetch_log_recent", "connector_name", "started_at"),)


class PriceDecomposition(TimestampMixin, Base):
    """
    Decomposition du prix complet EUR/MWh pour un site/contrat.
    Calculee backend a partir de : MktPrice + RegulatedTariff + profil charge site.
    C'est la brique qui alimente le shadow pricing et la comparaison d'offres.
    """

    __tablename__ = "price_decompositions"

    id = Column(Integer, primary_key=True)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=True, index=True)

    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    profile = Column(String(20), nullable=False)  # C5, C4, C2, HTA

    # Decomposition en EUR/MWh
    energy_eur_mwh = Column(Float, nullable=False)  # Brique 1: commodity
    turpe_eur_mwh = Column(Float, nullable=False)  # Brique 2: acheminement
    cspe_eur_mwh = Column(Float, nullable=False)  # Brique 3: accise
    capacity_eur_mwh = Column(Float, nullable=False)  # Brique 4: capacite
    cee_eur_mwh = Column(Float, nullable=False)  # Brique 5: CEE
    cta_eur_mwh = Column(Float, nullable=False)  # Brique 6: CTA
    total_ht_eur_mwh = Column(Float, nullable=False)  # Total HT
    tva_eur_mwh = Column(Float, nullable=False)  # TVA
    total_ttc_eur_mwh = Column(Float, nullable=False)  # Total TTC

    # Contexte de calcul
    spot_avg_eur_mwh = Column(Float, nullable=True)  # Spot moyen periode
    forward_ref_eur_mwh = Column(Float, nullable=True)  # Forward de reference
    volume_mwh = Column(Float, nullable=True)  # Volume estime

    # Metadonnees
    calculation_method = Column(String(50), nullable=False)  # SPOT_BASED, FORWARD_BASED, CONTRACT
    calculated_at = Column(DateTime(timezone=True), nullable=False)
    tariff_version = Column(String(50), nullable=False)  # Ex: "TURPE7_CSPE_2026-02"

    __table_args__ = (Index("ix_decomp_lookup", "org_id", "site_id", "period_start"),)
