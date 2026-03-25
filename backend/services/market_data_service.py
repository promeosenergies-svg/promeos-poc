"""
Service d'ingestion et de requete des donnees marche.
Orchestre les connecteurs -> DB, gere le dedup, le logging, et les requetes.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.market_models import (
    MktPrice, MarketDataSource, MarketType,
    ProductType, PriceZone, Resolution,
    MarketDataFetchLog
)

logger = logging.getLogger(__name__)


class MarketDataService:

    def __init__(self, db: Session):
        self.db = db

    # -- Ingestion ----------------------------------------------------------

    def ingest_prices(self, records: list[dict]) -> dict:
        """
        Insere des prix en bulk avec dedup (check existant -> skip).
        Retourne {"inserted": N, "skipped": N}
        """
        inserted = 0
        skipped = 0

        for record in records:
            existing = self.db.query(MktPrice).filter(
                MktPrice.source == record["source"],
                MktPrice.market_type == record["market_type"],
                MktPrice.product_type == record["product_type"],
                MktPrice.zone == record["zone"],
                MktPrice.delivery_start == record["delivery_start"],
                MktPrice.resolution == record["resolution"],
            ).first()

            if existing:
                skipped += 1
                continue

            self.db.add(MktPrice(**record))
            inserted += 1

        self.db.commit()
        logger.info(f"MarketDataService: ingested {inserted}, skipped {skipped}")
        return {"inserted": inserted, "skipped": skipped}

    def log_fetch(
        self, connector_name: str, fetch_type: str,
        zone: PriceZone, status: str,
        records_fetched: int = 0, records_inserted: int = 0,
        period_start: datetime = None, period_end: datetime = None,
        error_message: str = None,
    ) -> MarketDataFetchLog:
        """Enregistre un log de fetch."""
        log = MarketDataFetchLog(
            connector_name=connector_name,
            fetch_type=fetch_type,
            zone=zone,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            status=status,
            records_fetched=records_fetched,
            records_inserted=records_inserted,
            period_start=period_start,
            period_end=period_end,
            error_message=error_message,
        )
        self.db.add(log)
        self.db.commit()
        return log

    # -- Requetes -----------------------------------------------------------

    def get_spot_prices(
        self,
        zone: PriceZone = PriceZone.FR,
        start: datetime = None,
        end: datetime = None,
        limit: int = 168,  # 7 jours x 24h par defaut
    ) -> list[MktPrice]:
        """Retourne les prix spot day-ahead, tries par date."""
        q = self.db.query(MktPrice).filter(
            MktPrice.zone == zone,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
        )
        if start:
            q = q.filter(MktPrice.delivery_start >= start)
        if end:
            q = q.filter(MktPrice.delivery_start <= end)
        return q.order_by(MktPrice.delivery_start.desc()).limit(limit).all()

    def get_spot_average(
        self,
        zone: PriceZone = PriceZone.FR,
        days: int = 30,
    ) -> Optional[float]:
        """Moyenne spot sur N jours glissants."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = self.db.query(func.avg(MktPrice.price_eur_mwh)).filter(
            MktPrice.zone == zone,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start >= cutoff,
        ).scalar()
        return round(result, 2) if result else None

    def get_forward_curves(
        self,
        zone: PriceZone = PriceZone.FR,
        product: ProductType = ProductType.BASELOAD,
    ) -> list[MktPrice]:
        """Retourne les forward curves (CAL, Q, M)."""
        return self.db.query(MktPrice).filter(
            MktPrice.zone == zone,
            MktPrice.product_type == product,
            MktPrice.market_type.in_([
                MarketType.FORWARD_YEAR,
                MarketType.FORWARD_QUARTER,
                MarketType.FORWARD_MONTH,
            ]),
        ).order_by(MktPrice.delivery_start.asc()).all()

    def get_latest_price(
        self,
        zone: PriceZone = PriceZone.FR,
        market_type: MarketType = MarketType.SPOT_DAY_AHEAD,
    ) -> Optional[MktPrice]:
        """Retourne le dernier prix connu."""
        return self.db.query(MktPrice).filter(
            MktPrice.zone == zone,
            MktPrice.market_type == market_type,
        ).order_by(MktPrice.delivery_start.desc()).first()

    def get_price_stats(
        self,
        zone: PriceZone = PriceZone.FR,
        days: int = 30,
    ) -> dict:
        """Statistiques prix spot sur N jours."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        q = self.db.query(
            func.avg(MktPrice.price_eur_mwh).label("avg"),
            func.min(MktPrice.price_eur_mwh).label("min"),
            func.max(MktPrice.price_eur_mwh).label("max"),
            func.count(MktPrice.id).label("count"),
        ).filter(
            MktPrice.zone == zone,
            MktPrice.market_type == MarketType.SPOT_DAY_AHEAD,
            MktPrice.delivery_start >= cutoff,
        ).first()

        return {
            "zone": zone.value,
            "period_days": days,
            "avg_eur_mwh": round(q.avg, 2) if q.avg else None,
            "min_eur_mwh": round(q.min, 2) if q.min else None,
            "max_eur_mwh": round(q.max, 2) if q.max else None,
            "data_points": q.count or 0,
        }

    def get_data_freshness(self) -> dict:
        """Verifie la fraicheur des donnees par source."""
        sources = self.db.query(
            MktPrice.source,
            func.max(MktPrice.fetched_at).label("last_fetch"),
            func.count(MktPrice.id).label("total"),
        ).group_by(MktPrice.source).all()

        return {
            s.source.value: {
                "last_fetch": s.last_fetch.isoformat() if s.last_fetch else None,
                "total_records": s.total,
            }
            for s in sources
        }
