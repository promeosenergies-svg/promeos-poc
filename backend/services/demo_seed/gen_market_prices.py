"""
PROMEOS — Demo Seed: Market Prices (EPEX Spot FR)
Generates 36 months of deterministic daily EPEX Spot FR prices.
Period: 2024-01-01 → 2026-12-31 (1096 days).

Includes forward curves (CAL, Q, M) for cockpit display.

Source de vérité : table mkt_prices (MktPrice) via market_models.py.
"""

import math
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models.market_models import (
    MktPrice,
    MarketDataSource,
    MarketType,
    ProductType,
    PriceZone,
    Resolution,
)


def _generate_prices(start_date: date, end_date: date) -> list[dict]:
    """Generate deterministic EPEX Spot FR daily prices."""
    prices = []
    base_2024 = 82.0  # EUR/MWh moyenne 2024 (post-crise, normalisation)
    base_2025 = 68.0  # EUR/MWh moyenne 2025 (tendance baissière)
    base_2026 = 62.0  # EUR/MWh moyenne 2026 (stabilisation)

    current = start_date
    day_index = 0
    while current <= end_date:
        year_base = base_2024 if current.year == 2024 else base_2025 if current.year == 2025 else base_2026

        # Saisonnalité (sinusoïde, pic en janvier, creux en juillet)
        day_of_year = current.timetuple().tm_yday
        seasonal = math.cos(2 * math.pi * (day_of_year - 15) / 365) * 0.18

        # Weekend discount (-5%)
        weekend = -0.05 if current.weekday() >= 5 else 0

        # Variabilité déterministe (pas de random)
        variation = math.sin(day_index * 0.73) * 0.08

        price = year_base * (1 + seasonal + weekend + variation)
        price = round(max(price, 15.0), 2)  # Floor à 15 EUR/MWh

        delivery_start = datetime(current.year, current.month, current.day, tzinfo=timezone.utc)
        delivery_end = delivery_start + timedelta(hours=24)

        prices.append(
            {
                "source": MarketDataSource.MANUAL,
                "market_type": MarketType.SPOT_DAY_AHEAD,
                "product_type": ProductType.BASELOAD,
                "zone": PriceZone.FR,
                "delivery_start": delivery_start,
                "delivery_end": delivery_end,
                "price_eur_mwh": price,
                "resolution": Resolution.P1D,
                "fetched_at": datetime.now(timezone.utc),
                "source_reference": "Seed PROMEOS — basé sur tendances EPEX 2024-2026",
            }
        )

        current += timedelta(days=1)
        day_index += 1

    return prices


def _generate_hourly_spot_last_90d(now_utc: datetime) -> list[dict]:
    """
    Genere 90 jours d'historique spot day-ahead horaire FR avec des prix
    negatifs plausibles sur la plage midi (10h-17h Europe/Paris) ~15% des jours
    ouvres -- reproduit le signal 2025 (513h prix negatifs observes par la CRE).

    Utilise par le Radar prix negatifs J+7 (heuristique 30% creneaux negatifs
    sur jours semblables). La courbe horaire est deterministe (pas de random).
    """
    rows: list[dict] = []
    # Plage solaire : surplus PV midi => pression baissiere forte.
    solar_noon_hours = {11, 12, 13, 14, 15}
    base_daily = 62.0  # moyenne 2026 EUR/MWh (aligne avec _generate_prices)

    for d in range(90, 0, -1):
        day = (now_utc - timedelta(days=d)).date()
        # Negatif midi ~3 jours/semaine : mer + jeu + ven. Ratio calibre pour
        # que le radar (seuil 30% creneaux negatifs sur jours semblables) declenche
        # sur ces 3 weekdays sans polluer lun/mar/samedi/dimanche.
        is_negative_day = day.weekday() in (2, 3, 4)

        for hour in range(24):
            # Profil diurne : pic 8h et 19h, creux nuit + midi.
            diurnal = math.cos(2 * math.pi * (hour - 8) / 24) * 0.15
            if hour in solar_noon_hours:
                diurnal -= 0.25  # creux PV
            price = base_daily * (1 + diurnal)

            if is_negative_day and hour in solar_noon_hours:
                # Force prix negatif sur 5 creneaux midi => 5/7 = 71% >> seuil 30%
                price = -5.0 - (hour - 11) * 1.2  # -5 a -9.8 EUR/MWh

            delivery_start = datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)
            rows.append(
                {
                    "source": MarketDataSource.MANUAL,
                    "market_type": MarketType.SPOT_DAY_AHEAD,
                    "product_type": ProductType.HOURLY,
                    "zone": PriceZone.FR,
                    "delivery_start": delivery_start,
                    "delivery_end": delivery_start + timedelta(hours=1),
                    "price_eur_mwh": round(price, 2),
                    "resolution": Resolution.PT60M,
                    "fetched_at": now_utc,
                    "source_reference": "Seed PROMEOS -- historique horaire 90j pour Radar prix negatifs",
                }
            )
    return rows


def _generate_forward_curves() -> list[dict]:
    """Generate forward curve records (CAL, Q, M) for cockpit display."""
    now = datetime.now(timezone.utc)
    curves = [
        # CAL 2026 — moyenne pondérée des Q2/Q3/Q4 2026 (Q1 déjà livré).
        # Requis par cost_simulator_2026 (filtre FORWARD_YEAR sur delivery_start).
        {
            "market_type": MarketType.FORWARD_YEAR,
            "delivery_start": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "delivery_end": datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            "price_eur_mwh": 62.0,
            "resolution": Resolution.P1Y,
        },
        # CAL 2027
        {
            "market_type": MarketType.FORWARD_YEAR,
            "delivery_start": datetime(2027, 1, 1, tzinfo=timezone.utc),
            "delivery_end": datetime(2027, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            "price_eur_mwh": 58.0,
            "resolution": Resolution.P1Y,
        },
        # Q2 2026
        {
            "market_type": MarketType.FORWARD_QUARTER,
            "delivery_start": datetime(2026, 4, 1, tzinfo=timezone.utc),
            "delivery_end": datetime(2026, 6, 30, 23, 59, 59, tzinfo=timezone.utc),
            "price_eur_mwh": 55.0,
            "resolution": Resolution.P3M,
        },
        # Q3 2026
        {
            "market_type": MarketType.FORWARD_QUARTER,
            "delivery_start": datetime(2026, 7, 1, tzinfo=timezone.utc),
            "delivery_end": datetime(2026, 9, 30, 23, 59, 59, tzinfo=timezone.utc),
            "price_eur_mwh": 48.0,
            "resolution": Resolution.P3M,
        },
        # Q4 2026
        {
            "market_type": MarketType.FORWARD_QUARTER,
            "delivery_start": datetime(2026, 10, 1, tzinfo=timezone.utc),
            "delivery_end": datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            "price_eur_mwh": 65.0,
            "resolution": Resolution.P3M,
        },
        # M04 2026
        {
            "market_type": MarketType.FORWARD_MONTH,
            "delivery_start": datetime(2026, 4, 1, tzinfo=timezone.utc),
            "delivery_end": datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc),
            "price_eur_mwh": 54.0,
            "resolution": Resolution.P1M,
        },
    ]
    common = {
        "source": MarketDataSource.MANUAL,
        "product_type": ProductType.BASELOAD,
        "zone": PriceZone.FR,
        "fetched_at": now,
        "source_reference": "Seed PROMEOS — forward curves estimées 2026-2027",
    }
    return [{**common, **c} for c in curves]


def generate_market_prices(db: Session) -> dict:
    """Seed EPEX Spot FR prices into mkt_prices. Idempotent via dedup check."""
    start = date(2024, 1, 1)
    end = date(2026, 12, 31)
    prices = _generate_prices(start, end)
    forwards = _generate_forward_curves()
    now_utc = datetime.now(timezone.utc)
    hourly_radar = _generate_hourly_spot_last_90d(now_utc)

    inserted = 0
    for p in prices + forwards + hourly_radar:
        existing = (
            db.query(MktPrice)
            .filter(
                MktPrice.source == p["source"],
                MktPrice.market_type == p["market_type"],
                MktPrice.product_type == p["product_type"],
                MktPrice.zone == p["zone"],
                MktPrice.delivery_start == p["delivery_start"],
                MktPrice.resolution == p["resolution"],
            )
            .first()
        )
        if not existing:
            db.add(MktPrice(**p))
            inserted += 1

    db.flush()
    total = len(prices) + len(forwards) + len(hourly_radar)
    return {"market_prices_total": total, "market_prices_inserted": inserted}
