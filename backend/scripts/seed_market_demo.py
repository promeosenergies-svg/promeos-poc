"""
Seed donnees marche demo -- 90 jours de prix spot France realistes.
+ Forward curves CAL27/28 + tarifs reglementaires.

Usage: python backend/scripts/seed_market_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import random
from datetime import datetime, timezone, timedelta
from database.connection import SessionLocal, engine
from models.base import Base
from models.market_models import (  # noqa: F401 — register models on Base
    MktPrice,
    RegulatedTariff,
    PriceSignal,
    MarketDataFetchLog,
    PriceDecomposition,
    MarketDataSource,
    MarketType,
    ProductType,
    PriceZone,
    Resolution,
)
from services.market_data_service import MarketDataService
from services.market_tariff_loader import load_tariffs_from_yaml


def generate_spot_prices(days: int = 90) -> list[dict]:
    """
    Genere des prix spot realistes.
    Pattern: base ~70 EUR/MWh, pointe matin/soir, bruit, saisonnalite.
    """
    records = []
    base_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)

    for day in range(days):
        date = base_date + timedelta(days=day)
        weekday = date.weekday()
        is_weekend = weekday >= 5

        # Saisonnalite: hiver = prix plus hauts
        month = date.month
        seasonal = 15 if month in (1, 2, 12) else 5 if month in (6, 7, 8) else 10

        for hour in range(24):
            # Profil journalier: pointe 8-12h et 18-20h
            if 8 <= hour <= 12:
                hourly_premium = 25
            elif 18 <= hour <= 20:
                hourly_premium = 30
            elif 0 <= hour <= 5:
                hourly_premium = -15
            else:
                hourly_premium = 5

            if is_weekend:
                hourly_premium *= 0.6

            base = 70 + seasonal + hourly_premium
            noise = random.gauss(0, 8)
            price = max(-10, round(base + noise, 2))

            # Quelques prix negatifs rares (surplus EnR dimanche midi)
            if is_weekend and 11 <= hour <= 14 and random.random() < 0.05:
                price = round(random.uniform(-20, -1), 2)

            records.append(
                {
                    "source": MarketDataSource.ENTSOE,
                    "market_type": MarketType.SPOT_DAY_AHEAD,
                    "product_type": ProductType.HOURLY,
                    "zone": PriceZone.FR,
                    "delivery_start": date + timedelta(hours=hour),
                    "delivery_end": date + timedelta(hours=hour + 1),
                    "price_eur_mwh": price,
                    "resolution": Resolution.PT60M,
                    "fetched_at": datetime.now(timezone.utc),
                    "quality_flag": "GOOD",
                }
            )

    return records


def generate_forward_curves() -> list[dict]:
    """Forward curves CAL27, CAL28, Q+1 a Q+4, M+1 a M+3."""
    records = []
    now = datetime.now(timezone.utc)

    forwards = [
        (MarketType.FORWARD_YEAR, "2027-01-01", "2027-12-31", 52.3, ProductType.BASELOAD),
        (MarketType.FORWARD_YEAR, "2027-01-01", "2027-12-31", 68.5, ProductType.PEAKLOAD),
        (MarketType.FORWARD_YEAR, "2028-01-01", "2028-12-31", 49.8, ProductType.BASELOAD),
        (MarketType.FORWARD_YEAR, "2028-01-01", "2028-12-31", 64.2, ProductType.PEAKLOAD),
        (MarketType.FORWARD_QUARTER, "2026-07-01", "2026-09-30", 58.1, ProductType.BASELOAD),
        (MarketType.FORWARD_QUARTER, "2026-10-01", "2026-12-31", 72.4, ProductType.BASELOAD),
        (MarketType.FORWARD_MONTH, "2026-04-01", "2026-04-30", 62.8, ProductType.BASELOAD),
        (MarketType.FORWARD_MONTH, "2026-05-01", "2026-05-31", 55.3, ProductType.BASELOAD),
        (MarketType.FORWARD_MONTH, "2026-06-01", "2026-06-30", 48.7, ProductType.BASELOAD),
    ]

    for mtype, start, end, price, product in forwards:
        records.append(
            {
                "source": MarketDataSource.MANUAL,
                "market_type": mtype,
                "product_type": product,
                "zone": PriceZone.FR,
                "delivery_start": datetime.fromisoformat(start).replace(tzinfo=timezone.utc),
                "delivery_end": datetime.fromisoformat(end).replace(tzinfo=timezone.utc),
                "price_eur_mwh": price,
                "resolution": Resolution.P1Y
                if mtype == MarketType.FORWARD_YEAR
                else Resolution.P3M
                if mtype == MarketType.FORWARD_QUARTER
                else Resolution.P1M,
                "fetched_at": now,
                "quality_flag": "GOOD",
                "source_reference": "Pilott/Sirenergies freemium -- mars 2026",
            }
        )

    return records


def main():
    # Ensure market data tables exist (idempotent — does not drop existing tables)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 1. Charger tarifs reglementaires
        print("Loading regulated tariffs...")
        tariff_result = load_tariffs_from_yaml(db)
        print(f"  Tariffs: {tariff_result}")

        # 2. Seed prix spot 90 jours
        print("Generating 90 days of spot prices...")
        spot = generate_spot_prices(90)
        svc = MarketDataService(db)
        spot_result = svc.ingest_prices(spot)
        print(f"  Spot: {spot_result}")

        # 3. Seed forward curves
        print("Generating forward curves...")
        forwards = generate_forward_curves()
        fwd_result = svc.ingest_prices(forwards)
        print(f"  Forwards: {fwd_result}")

        # 4. Log
        svc.log_fetch(
            connector_name="seed_demo",
            fetch_type="full_seed",
            zone=PriceZone.FR,
            status="SUCCESS",
            records_fetched=len(spot) + len(forwards),
            records_inserted=spot_result["inserted"] + fwd_result["inserted"],
        )

        print(f"\nDone! Total: {spot_result['inserted'] + fwd_result['inserted']} records inserted.")
        print(f"Freshness: {svc.get_data_freshness()}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
