"""
PROMEOS — Market Prices Route (Step 17)
GET /api/market/prices — prix marché EPEX Spot FR.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.market_price import MarketPrice

router = APIRouter(prefix="/api/market", tags=["Market Prices"])


@router.get("/prices")
def get_market_prices(
    market: str = Query("EPEX_SPOT_FR"),
    energy_type: str = Query("ELEC"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="YYYY-MM-DD"),
    granularity: str = Query("daily", description="daily|weekly|monthly"),
    db: Session = Depends(get_db),
):
    """Prix marché énergie (lecture seule, données publiques simulées)."""
    q = db.query(MarketPrice).filter(
        MarketPrice.market == market,
        MarketPrice.energy_type == energy_type,
    )

    # Date filters
    if date_from:
        try:
            q = q.filter(MarketPrice.date >= date.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.filter(MarketPrice.date <= date.fromisoformat(date_to))
        except ValueError:
            pass

    rows = q.order_by(MarketPrice.date.asc()).all()

    if granularity == "monthly":
        # Aggregate by month
        buckets = {}
        for r in rows:
            key = r.date.strftime("%Y-%m")
            if key not in buckets:
                buckets[key] = {"sum": 0.0, "count": 0}
            buckets[key]["sum"] += r.price_eur_mwh
            buckets[key]["count"] += 1
        prices = [
            {"date": k, "price_eur_mwh": round(v["sum"] / v["count"], 2)}
            for k, v in sorted(buckets.items())
        ]
    elif granularity == "weekly":
        buckets = {}
        for r in rows:
            # ISO week
            iso = r.date.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"
            if key not in buckets:
                buckets[key] = {"sum": 0.0, "count": 0}
            buckets[key]["sum"] += r.price_eur_mwh
            buckets[key]["count"] += 1
        prices = [
            {"date": k, "price_eur_mwh": round(v["sum"] / v["count"], 2)}
            for k, v in sorted(buckets.items())
        ]
    else:
        prices = [
            {"date": r.date.isoformat(), "price_eur_mwh": r.price_eur_mwh}
            for r in rows
        ]

    # Compute stats
    all_prices = [r.price_eur_mwh for r in rows]
    if all_prices:
        avg_val = round(sum(all_prices) / len(all_prices), 2)
        min_val = round(min(all_prices), 2)
        max_val = round(max(all_prices), 2)
        current_val = round(all_prices[-1], 2)

        # vs 12m avg
        twelve_months_ago = rows[-1].date - timedelta(days=365)
        older = [r.price_eur_mwh for r in rows if r.date <= twelve_months_ago]
        if older:
            avg_12m = sum(older) / len(older)
            vs_12m = round((current_val - avg_12m) / avg_12m * 100, 1) if avg_12m > 0 else None
        else:
            vs_12m = None

        stats = {
            "avg_eur_mwh": avg_val,
            "min_eur_mwh": min_val,
            "max_eur_mwh": max_val,
            "current_eur_mwh": current_val,
            "vs_12m_avg_pct": vs_12m,
        }
    else:
        stats = {
            "avg_eur_mwh": None,
            "min_eur_mwh": None,
            "max_eur_mwh": None,
            "current_eur_mwh": None,
            "vs_12m_avg_pct": None,
        }

    return {
        "market": market,
        "energy_type": energy_type,
        "granularity": granularity,
        "count": len(prices),
        "prices": prices,
        "stats": stats,
    }
