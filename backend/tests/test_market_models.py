"""Tests modeles Market Data -- schema, contraintes, enums."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from models.market_models import (
    MktPrice, RegulatedTariff, PriceSignal,
    MarketDataFetchLog, PriceDecomposition,
    MarketDataSource, MarketType, ProductType, PriceZone,
    TariffType, TariffComponent, SignalType, Resolution,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class TestMarketModelsSchema:
    """Verifie que les tables existent et ont les bonnes colonnes."""

    def test_mkt_prices_table_exists(self, db_session):
        inspector = inspect(db_session.bind)
        assert "mkt_prices" in inspector.get_table_names()

    def test_regulated_tariffs_table_exists(self, db_session):
        inspector = inspect(db_session.bind)
        assert "regulated_tariffs" in inspector.get_table_names()

    def test_price_signals_table_exists(self, db_session):
        inspector = inspect(db_session.bind)
        assert "price_signals" in inspector.get_table_names()

    def test_price_decompositions_table_exists(self, db_session):
        inspector = inspect(db_session.bind)
        assert "price_decompositions" in inspector.get_table_names()

    def test_fetch_logs_table_exists(self, db_session):
        inspector = inspect(db_session.bind)
        assert "market_data_fetch_logs" in inspector.get_table_names()


class TestMktPriceCRUD:
    """CRUD MktPrice."""

    def test_insert_spot_price(self, db_session):
        now = datetime.now(timezone.utc)
        price = MktPrice(
            source=MarketDataSource.ENTSOE,
            market_type=MarketType.SPOT_DAY_AHEAD,
            product_type=ProductType.HOURLY,
            zone=PriceZone.FR,
            delivery_start=now,
            delivery_end=now + timedelta(hours=1),
            price_eur_mwh=85.42,
            resolution=Resolution.PT60M,
        )
        db_session.add(price)
        db_session.commit()
        assert price.id is not None
        assert price.price_eur_mwh == 85.42

    def test_unique_constraint_prevents_duplicates(self, db_session):
        now = datetime.now(timezone.utc)
        kwargs = dict(
            source=MarketDataSource.ENTSOE,
            market_type=MarketType.SPOT_DAY_AHEAD,
            product_type=ProductType.HOURLY,
            zone=PriceZone.FR,
            delivery_start=now,
            delivery_end=now + timedelta(hours=1),
            price_eur_mwh=85.0,
            resolution=Resolution.PT60M,
        )
        db_session.add(MktPrice(**kwargs))
        db_session.commit()
        db_session.add(MktPrice(**kwargs))
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_negative_price_allowed(self, db_session):
        """Prix negatifs possibles (surplus EnR)."""
        now = datetime.now(timezone.utc)
        price = MktPrice(
            source=MarketDataSource.ENTSOE,
            market_type=MarketType.SPOT_DAY_AHEAD,
            product_type=ProductType.HOURLY,
            zone=PriceZone.FR,
            delivery_start=now,
            delivery_end=now + timedelta(hours=1),
            price_eur_mwh=-5.30,
            resolution=Resolution.PT60M,
        )
        db_session.add(price)
        db_session.commit()
        assert price.price_eur_mwh == -5.30


class TestRegulatedTariffCRUD:
    """CRUD RegulatedTariff."""

    def test_insert_cspe_2026(self, db_session):
        tariff = RegulatedTariff(
            tariff_type=TariffType.CSPE,
            component=TariffComponent.CSPE_C4,
            value=26.58,
            unit="EUR_MWH",
            valid_from=datetime(2026, 2, 1, tzinfo=timezone.utc),
            valid_to=None,  # En vigueur
            source_name="LOI_FINANCES_2026",
            source_reference="Art. 17 LF 2025 + arrete fev 2026",
            version="2026-02",
            applies_to_profile="C4",
            applies_to_power_range="36-250kVA",
        )
        db_session.add(tariff)
        db_session.commit()
        assert tariff.value == 26.58
        assert tariff.valid_to is None  # En vigueur

    def test_versioning_insert_only(self, db_session):
        """Verifier qu'on peut avoir plusieurs versions du meme tarif."""
        base = dict(
            tariff_type=TariffType.CSPE,
            component=TariffComponent.CSPE_C4,
            unit="EUR_MWH",
            source_name="LOI_FINANCES",
        )
        # Version 2025
        db_session.add(RegulatedTariff(
            **base, value=25.79, version="2025-08",
            valid_from=datetime(2025, 8, 1, tzinfo=timezone.utc),
            valid_to=datetime(2026, 1, 31, tzinfo=timezone.utc),
        ))
        # Version 2026
        db_session.add(RegulatedTariff(
            **base, value=26.58, version="2026-02",
            valid_from=datetime(2026, 2, 1, tzinfo=timezone.utc),
            valid_to=None,
        ))
        db_session.commit()
        from sqlalchemy import func
        count = db_session.query(func.count(RegulatedTariff.id)).filter(
            RegulatedTariff.component == TariffComponent.CSPE_C4
        ).scalar()
        assert count == 2


class TestEnumsCompleteness:
    """Verifie que les enums couvrent les cas 2026-2030."""

    def test_market_sources_cover_all_providers(self):
        names = [e.value for e in MarketDataSource]
        assert "ENTSOE" in names
        assert "RTE_WHOLESALE" in names
        assert "EEX" in names
        assert "MANUAL" in names
        assert "COMPUTED" in names

    def test_tariff_types_cover_post_arenh(self):
        names = [e.value for e in TariffType]
        assert "VNU" in names       # Post-ARENH 2026
        assert "TURPE" in names
        assert "CSPE" in names
        assert "CAPACITY" in names
        assert "CEE" in names

    def test_signal_types_cover_buying_scenarios(self):
        names = [e.value for e in SignalType]
        assert "BUYING_WINDOW" in names
        assert "VNU_ACTIVATION" in names
        assert "SPOT_NEGATIVE" in names

    def test_price_zones_cover_france_neighbors(self):
        names = [e.value for e in PriceZone]
        assert "FR" in names
        assert "DE_LU" in names
        assert "ES" in names
        assert "BE" in names
