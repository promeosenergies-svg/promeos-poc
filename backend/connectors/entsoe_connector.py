"""
Connecteur ENTSO-E Transparency Platform.
Source gratuite -- token API par email a transparency@entsoe.eu.
Zone France: 10YFR-RTE------C

pip install entsoe-py pandas
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd

from models.market_models import (
    MktPrice,
    MarketDataSource,
    MarketType,
    ProductType,
    PriceZone,
    Resolution,
    MarketDataFetchLog,
)

logger = logging.getLogger(__name__)

# Zone codes ENTSO-E
ZONE_CODES = {
    PriceZone.FR: "FR",
    PriceZone.DE_LU: "DE_LU",
    PriceZone.BE: "BE",
    PriceZone.ES: "ES",
    PriceZone.NL: "NL",
    PriceZone.GB: "GB",
}


class EntsoeConnector:
    """
    Connecteur ENTSO-E -- prix day-ahead France horaires.
    Usage:
        connector = EntsoeConnector(api_key="xxx")
        prices = connector.fetch_day_ahead_prices(start, end)
    """

    def __init__(self, api_key: str):
        from entsoe import EntsoePandasClient

        self.client = EntsoePandasClient(api_key=api_key)
        self.source = MarketDataSource.ENTSOE

    def fetch_day_ahead_prices(
        self,
        start: datetime,
        end: datetime,
        zone: PriceZone = PriceZone.FR,
    ) -> list[dict]:
        """
        Recupere les prix day-ahead horaires.
        Retourne une liste de dicts prets a inserer en DB.
        """
        country_code = ZONE_CODES.get(zone, "FR")
        start_ts = pd.Timestamp(start, tz="Europe/Paris")
        end_ts = pd.Timestamp(end, tz="Europe/Paris")

        try:
            series = self.client.query_day_ahead_prices(country_code, start=start_ts, end=end_ts)
        except Exception as e:
            logger.error(f"ENTSO-E fetch failed: {e}")
            raise

        records = []
        for ts, price in series.items():
            dt = ts.to_pydatetime()
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            records.append(
                {
                    "source": self.source,
                    "market_type": MarketType.SPOT_DAY_AHEAD,
                    "product_type": ProductType.HOURLY,
                    "zone": zone,
                    "delivery_start": dt,
                    "delivery_end": dt + timedelta(hours=1),
                    "price_eur_mwh": float(price),
                    "resolution": Resolution.PT60M,
                    "fetched_at": datetime.now(timezone.utc),
                    "quality_flag": "GOOD",
                }
            )

        logger.info(f"ENTSO-E: fetched {len(records)} prices for {zone.value} from {start.date()} to {end.date()}")
        return records

    def fetch_generation_by_type(
        self,
        start: datetime,
        end: datetime,
        zone: PriceZone = PriceZone.FR,
    ) -> pd.DataFrame:
        """Recupere la production par filiere (nucleaire, eolien, solaire, etc.)."""
        country_code = ZONE_CODES.get(zone, "FR")
        start_ts = pd.Timestamp(start, tz="Europe/Paris")
        end_ts = pd.Timestamp(end, tz="Europe/Paris")
        return self.client.query_generation(country_code, start=start_ts, end=end_ts)

    def fetch_load(
        self,
        start: datetime,
        end: datetime,
        zone: PriceZone = PriceZone.FR,
    ) -> pd.DataFrame:
        """Recupere la charge reelle."""
        country_code = ZONE_CODES.get(zone, "FR")
        start_ts = pd.Timestamp(start, tz="Europe/Paris")
        end_ts = pd.Timestamp(end, tz="Europe/Paris")
        return self.client.query_load(country_code, start=start_ts, end=end_ts)
