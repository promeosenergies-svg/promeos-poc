"""Tests service MarketData -- ingestion, dedup, requetes."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from models.base import Base
from services.market_data_service import MarketDataService
from models.market_models import MarketDataSource, MarketType, ProductType, PriceZone, Resolution


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


@pytest.fixture
def service(db_session):
    return MarketDataService(db_session)


@pytest.fixture
def sample_prices():
    """24h de prix spot factices."""
    base = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)
    prices = [75 + (h % 12) * 5 for h in range(24)]  # 75-130 EUR/MWh
    return [
        {
            "source": MarketDataSource.ENTSOE,
            "market_type": MarketType.SPOT_DAY_AHEAD,
            "product_type": ProductType.HOURLY,
            "zone": PriceZone.FR,
            "delivery_start": base + timedelta(hours=h),
            "delivery_end": base + timedelta(hours=h + 1),
            "price_eur_mwh": prices[h],
            "resolution": Resolution.PT60M,
            "fetched_at": datetime.now(timezone.utc),
        }
        for h in range(24)
    ]


class TestIngestion:
    def test_ingest_inserts_records(self, service, sample_prices):
        result = service.ingest_prices(sample_prices)
        assert result["inserted"] == 24
        assert result["skipped"] == 0

    def test_ingest_dedup(self, service, sample_prices):
        service.ingest_prices(sample_prices)
        result = service.ingest_prices(sample_prices)
        assert result["inserted"] == 0
        assert result["skipped"] == 24

    def test_ingest_partial_overlap(self, service, sample_prices):
        service.ingest_prices(sample_prices[:12])
        result = service.ingest_prices(sample_prices)
        assert result["inserted"] == 12
        assert result["skipped"] == 12


class TestQueries:
    def test_get_spot_prices(self, service, sample_prices):
        service.ingest_prices(sample_prices)
        prices = service.get_spot_prices(limit=10)
        assert len(prices) == 10
        # Tries desc
        assert prices[0].delivery_start > prices[1].delivery_start

    def test_get_spot_average(self, service, sample_prices):
        service.ingest_prices(sample_prices)
        avg = service.get_spot_average(days=30)
        assert avg is not None
        assert 70 < avg < 140

    def test_get_price_stats(self, service, sample_prices):
        service.ingest_prices(sample_prices)
        stats = service.get_price_stats(days=30)
        assert stats["zone"] == "FR"
        assert stats["data_points"] == 24
        assert stats["min_eur_mwh"] is not None
        assert stats["max_eur_mwh"] >= stats["min_eur_mwh"]

    def test_get_latest_price(self, service, sample_prices):
        service.ingest_prices(sample_prices)
        latest = service.get_latest_price()
        assert latest is not None
        assert latest.price_eur_mwh > 0

    def test_get_data_freshness_empty(self, service):
        freshness = service.get_data_freshness()
        assert isinstance(freshness, dict)

    def test_get_data_freshness_with_data(self, service, sample_prices):
        service.ingest_prices(sample_prices)
        freshness = service.get_data_freshness()
        assert "ENTSOE" in freshness
        assert freshness["ENTSOE"]["total_records"] == 24


class TestFetchLog:
    def test_log_fetch_success(self, service):
        log = service.log_fetch(
            connector_name="entsoe",
            fetch_type="day_ahead_prices",
            zone=PriceZone.FR,
            status="SUCCESS",
            records_fetched=24,
            records_inserted=24,
        )
        assert log.id is not None
        assert log.status == "SUCCESS"
        assert log.records_fetched == 24
