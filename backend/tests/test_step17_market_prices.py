"""
Step 17 — M1 : Seed prix marché EPEX Spot FR 24 mois
Tests unitaires pour le modèle V2 (MktPrice), le seed, et get_reference_price.

NOTE: Le modèle legacy MarketPrice (table market_prices) est testé pour
rétrocompatibilité import uniquement. Tous les tests fonctionnels
utilisent MktPrice (table mkt_prices).
"""

import math
from datetime import date, timedelta

import pytest


# ============================================================
# Legacy model — rétrocompatibilité import uniquement
# ============================================================


class TestLegacyMarketPriceModel:
    """Vérifie que le modèle legacy reste importable (non cassé)."""

    def test_legacy_model_importable(self):
        from models.market_price import MarketPrice

        assert MarketPrice.__tablename__ == "market_prices"

    def test_legacy_model_registered_in_init(self):
        from models import MarketPrice

        assert MarketPrice.__tablename__ == "market_prices"


# ============================================================
# New model — MktPrice (source de vérité)
# ============================================================


class TestMktPriceModel:
    """Test that MktPrice model is importable and has expected fields."""

    def test_model_importable(self):
        from models.market_models import MktPrice

        assert MktPrice.__tablename__ == "mkt_prices"

    def test_model_has_price_field(self):
        from models.market_models import MktPrice

        assert hasattr(MktPrice, "price_eur_mwh")

    def test_model_has_zone_field(self):
        from models.market_models import MktPrice

        assert hasattr(MktPrice, "zone")

    def test_model_registered_in_init(self):
        from models import MktPrice

        assert MktPrice.__tablename__ == "mkt_prices"


# ============================================================
# Seed generation (pure function, no DB needed)
# ============================================================


class TestMarketPriceSeed:
    """Test gen_market_prices deterministic generation."""

    def test_generates_prices(self):
        from services.demo_seed.gen_market_prices import _generate_prices

        prices = _generate_prices(date(2024, 1, 1), date(2025, 12, 31))
        assert len(prices) >= 700  # ~730 days

    def test_seed_deterministic(self):
        from services.demo_seed.gen_market_prices import _generate_prices

        p1 = _generate_prices(date(2024, 1, 1), date(2025, 12, 31))
        p2 = _generate_prices(date(2024, 1, 1), date(2025, 12, 31))
        assert [p["price_eur_mwh"] for p in p1] == [p["price_eur_mwh"] for p in p2]

    def test_prices_realistic_range(self):
        from services.demo_seed.gen_market_prices import _generate_prices

        prices = _generate_prices(date(2024, 1, 1), date(2025, 12, 31))
        for p in prices:
            assert 15.0 <= p["price_eur_mwh"] <= 150.0, f"Price {p['price_eur_mwh']} out of range"

    def test_seasonality_winter_higher(self):
        from services.demo_seed.gen_market_prices import _generate_prices

        prices = _generate_prices(date(2024, 1, 1), date(2024, 12, 31))
        winter = [p["price_eur_mwh"] for p in prices if p["delivery_start"].month in (12, 1, 2)]
        summer = [p["price_eur_mwh"] for p in prices if p["delivery_start"].month in (6, 7, 8)]
        avg_winter = sum(winter) / len(winter)
        avg_summer = sum(summer) / len(summer)
        assert avg_winter > avg_summer, f"Winter {avg_winter:.1f} should be > summer {avg_summer:.1f}"

    def test_weekend_lower(self):
        from services.demo_seed.gen_market_prices import _generate_prices

        prices = _generate_prices(date(2024, 1, 1), date(2024, 12, 31))
        weekday = [p["price_eur_mwh"] for p in prices if p["delivery_start"].weekday() < 5]
        weekend = [p["price_eur_mwh"] for p in prices if p["delivery_start"].weekday() >= 5]
        avg_weekday = sum(weekday) / len(weekday)
        avg_weekend = sum(weekend) / len(weekend)
        assert avg_weekday > avg_weekend, f"Weekday {avg_weekday:.1f} should be > weekend {avg_weekend:.1f}"

    def test_2025_lower_than_2024(self):
        from services.demo_seed.gen_market_prices import _generate_prices

        prices = _generate_prices(date(2024, 1, 1), date(2025, 12, 31))
        avg_2024 = sum(p["price_eur_mwh"] for p in prices if p["delivery_start"].year == 2024) / sum(
            1 for p in prices if p["delivery_start"].year == 2024
        )
        avg_2025 = sum(p["price_eur_mwh"] for p in prices if p["delivery_start"].year == 2025) / sum(
            1 for p in prices if p["delivery_start"].year == 2025
        )
        assert avg_2025 < avg_2024, f"2025 avg {avg_2025:.1f} should be < 2024 avg {avg_2024:.1f}"

    def test_all_spot_fr(self):
        from services.demo_seed.gen_market_prices import _generate_prices
        from models.market_models import MarketType, PriceZone

        prices = _generate_prices(date(2024, 1, 1), date(2024, 1, 31))
        assert all(p["market_type"] == MarketType.SPOT_DAY_AHEAD for p in prices)
        assert all(p["zone"] == PriceZone.FR for p in prices)

    def test_seed_uses_mkt_price_schema(self):
        from services.demo_seed.gen_market_prices import _generate_prices
        from models.market_models import MarketDataSource, Resolution

        prices = _generate_prices(date(2024, 1, 1), date(2024, 1, 2))
        p = prices[0]
        assert "delivery_start" in p
        assert "delivery_end" in p
        assert p["source"] == MarketDataSource.MANUAL
        assert p["resolution"] == Resolution.P1D


# ============================================================
# get_reference_price fallback (no market data)
# ============================================================


class TestGetReferencePriceFallback:
    """Test updated fallback values."""

    def test_fallback_elec_uses_config(self):
        from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH

        assert DEFAULT_PRICE_ELEC_EUR_KWH == 0.068

    def test_fallback_gaz_uses_config(self):
        from config.default_prices import DEFAULT_PRICE_GAZ_EUR_KWH

        assert DEFAULT_PRICE_GAZ_EUR_KWH == 0.045


# ============================================================
# Route source guard
# ============================================================


class TestMarketRoute:
    """Test that market route file exists and has expected structure."""

    def test_route_file_importable(self):
        from routes.market import router

        assert router.prefix == "/api/market"

    def test_route_has_prices_endpoint(self):
        from routes.market import router

        paths = [r.path for r in router.routes]
        assert any("prices" in p for p in paths)
