"""
PROMEOS Connectors - PVGIS (REAL - public API EU JRC)
Estimation de production photovoltaique.
"""

import urllib.request
import json
from datetime import datetime, timezone
from .base import Connector
from models import DataPoint, SourceType, Site


class PVGISConnector(Connector):
    name = "pvgis"
    description = "PVGIS - Estimation production PV (EU JRC public)"
    requires_auth = False
    env_vars = []

    def test_connection(self) -> dict:
        try:
            # Test API PVGIS avec coordonnees Paris
            url = "https://re.jrc.ec.europa.eu/api/seriescalc?lat=48.8566&lon=2.3522&peakpower=1&loss=14&outputformat=json"
            req = urllib.request.Request(url, headers={"User-Agent": "PROMEOS/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                if data.get("outputs"):
                    return {"status": "ok", "message": "API PVGIS accessible"}
                return {"status": "error", "message": "No data"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def sync(self, db, object_type: str, object_id: int, date_from=None, date_to=None):
        """
        Calcule l'estimation de production PV pour un site.
        Utilise lat/lon du site + roof_area_m2.
        """
        datapoints = []
        try:
            site = db.query(Site).filter(Site.id == object_id).first()
            if not site or not site.latitude or not site.longitude:
                return datapoints

            roof_area = site.roof_area_m2 or 100.0  # Default 100m2
            peak_power_kwp = roof_area * 0.15  # ~150 Wc/m2

            url = f"https://re.jrc.ec.europa.eu/api/seriescalc?lat={site.latitude}&lon={site.longitude}&peakpower={peak_power_kwp}&loss=14&outputformat=json"
            req = urllib.request.Request(url, headers={"User-Agent": "PROMEOS/1.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read())
                monthly = data.get("outputs", {}).get("monthly", {}).get("fixed", [])

                for month_data in monthly[:3]:  # First 3 months only for POC
                    month = month_data.get("month")
                    e_m = month_data.get("E_m")  # kWh/month

                    if month and e_m:
                        dp = DataPoint(
                            object_type=object_type,
                            object_id=object_id,
                            metric="pv_prod_estimate_kwh",
                            ts_start=datetime(2024, month, 1),
                            ts_end=datetime(2024, month, 28),
                            value=float(e_m),
                            unit="kWh/month",
                            source_type=SourceType.API,
                            source_name=self.name,
                            quality_score=0.8,
                            coverage_ratio=1.0,
                            retrieved_at=datetime.now(timezone.utc),
                            source_ref=url,
                        )
                        db.add(dp)
                        datapoints.append(dp)
            db.commit()
        except Exception as e:
            print(f"PVGIS sync error: {e}")
        return datapoints
