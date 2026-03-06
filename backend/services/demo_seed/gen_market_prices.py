"""
PROMEOS — Demo Seed: Market Prices (EPEX Spot FR)
Generates 24 months of deterministic daily EPEX Spot FR prices.
Period: 2024-01-01 → 2025-12-31 (730 days).
"""

import math
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.market_price import MarketPrice


SOURCE = "Seed PROMEOS — basé sur tendances EPEX 2024-2025"


def _generate_prices(start_date: date, end_date: date) -> list[dict]:
    """Generate deterministic EPEX Spot FR daily prices."""
    prices = []
    base_2024 = 82.0  # EUR/MWh moyenne 2024 (post-crise, normalisation)
    base_2025 = 68.0  # EUR/MWh moyenne 2025 (tendance baissière)

    current = start_date
    day_index = 0
    while current <= end_date:
        year_base = base_2024 if current.year == 2024 else base_2025

        # Saisonnalité (sinusoïde, pic en janvier, creux en juillet)
        day_of_year = current.timetuple().tm_yday
        seasonal = math.cos(2 * math.pi * (day_of_year - 15) / 365) * 0.18

        # Weekend discount (-5%)
        weekend = -0.05 if current.weekday() >= 5 else 0

        # Variabilité déterministe (pas de random)
        variation = math.sin(day_index * 0.73) * 0.08

        price = year_base * (1 + seasonal + weekend + variation)
        price = round(max(price, 15.0), 2)  # Floor à 15 EUR/MWh

        prices.append({
            "market": "EPEX_SPOT_FR",
            "energy_type": "ELEC",
            "date": current,
            "price_eur_mwh": price,
            "source": SOURCE,
        })

        current += timedelta(days=1)
        day_index += 1

    return prices


def generate_market_prices(db: Session) -> dict:
    """Seed EPEX Spot FR prices. Idempotent via INSERT OR IGNORE."""
    start = date(2024, 1, 1)
    end = date(2025, 12, 31)
    prices = _generate_prices(start, end)

    inserted = 0
    for p in prices:
        existing = (
            db.query(MarketPrice)
            .filter(
                MarketPrice.market == p["market"],
                MarketPrice.date == p["date"],
                MarketPrice.energy_type == p["energy_type"],
            )
            .first()
        )
        if not existing:
            db.add(MarketPrice(**p))
            inserted += 1

    db.flush()
    return {"market_prices_total": len(prices), "market_prices_inserted": inserted}
