"""
PROMEOS - Connecteur ENTSO-E Day-Ahead (helper lecture DB).

Lecture du dernier prix spot day-ahead zone FR depuis la table `mkt_prices`.
Fallback gracieux si aucune donnee n'est disponible.

Source : ENTSO-E Transparency Platform (zone 10YFR-RTE------C).
Remplissage DB : connectors/entsoe_connector.py + scheduler.

Usage:
    from services.pilotage.connectors.entsoe_day_ahead import get_latest_day_ahead_eur_mwh
    price = get_latest_day_ahead_eur_mwh(db)  # None si absent
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.market_models import (
    MktPrice,
    MarketType,
    PriceZone,
)


def get_latest_day_ahead_eur_mwh(
    db: Session,
    zone: PriceZone = PriceZone.FR,
    as_of: Optional[datetime] = None,
) -> Optional[float]:
    """
    Retourne le prix day-ahead le plus recent zone FR couvrant `as_of`
    (par defaut : now UTC). None si aucune donnee en DB.
    """
    now = as_of or datetime.now(timezone.utc)
    row = (
        db.query(MktPrice)
        .filter(
            MktPrice.zone == zone,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start <= now,
            MktPrice.delivery_end > now,
        )
        .order_by(MktPrice.delivery_start.desc())
        .first()
    )
    if row is None:
        # fallback : dernier point connu (meme si dans le passe)
        row = (
            db.query(MktPrice)
            .filter(
                MktPrice.zone == zone,
                MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            )
            .order_by(MktPrice.delivery_start.desc())
            .first()
        )
    return float(row.price_eur_mwh) if row else None


def get_latest_day_ahead_with_timestamp(
    db: Session,
    zone: PriceZone = PriceZone.FR,
    as_of: Optional[datetime] = None,
) -> Optional[tuple[float, datetime]]:
    """
    Retourne `(prix_eur_mwh, delivery_start_utc)` du dernier spot day-ahead
    couvrant `as_of`, pour permettre au caller de verifier la fraicheur.

    `delivery_start` renvoye est toujours un `datetime` timezone-aware en UTC.
    None si aucune donnee en DB.
    """
    now = as_of or datetime.now(timezone.utc)
    row = (
        db.query(MktPrice)
        .filter(
            MktPrice.zone == zone,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start <= now,
            MktPrice.delivery_end > now,
        )
        .order_by(MktPrice.delivery_start.desc())
        .first()
    )
    if row is None:
        row = (
            db.query(MktPrice)
            .filter(
                MktPrice.zone == zone,
                MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            )
            .order_by(MktPrice.delivery_start.desc())
            .first()
        )
    if row is None:
        return None
    delivery_start = row.delivery_start
    if delivery_start.tzinfo is None:
        # SQLite peut stocker naif : on assume UTC (convention PROMEOS)
        delivery_start = delivery_start.replace(tzinfo=timezone.utc)
    return (float(row.price_eur_mwh), delivery_start)
