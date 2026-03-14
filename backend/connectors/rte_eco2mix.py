"""
PROMEOS Connectors - RTE eCO2mix (REAL - public API)
Donnees du mix electrique francais (intensite CO2, prix).
"""

import urllib.request
import json
from datetime import datetime, timezone
from .base import Connector
from models import DataPoint, SourceType


class RTEEco2MixConnector(Connector):
    name = "rte_eco2mix"
    description = "RTE éCO₂mix — Mix électrique national (public)"
    requires_auth = False
    env_vars = []

    def test_connection(self) -> dict:
        try:
            # Test avec l'API publique RTE
            url = "https://odre.opendatasoft.com/api/records/1.0/search/?dataset=eco2mix-national-tr&rows=1"
            req = urllib.request.Request(url, headers={"User-Agent": "PROMEOS/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                if data.get("records"):
                    return {"status": "ok", "message": "API RTE accessible"}
                return {"status": "error", "message": "No data"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def sync(self, db, object_type: str, object_id: int, date_from=None, date_to=None):
        """
        Recupere les donnees nationales du mix electrique.
        Cree des DataPoints avec metric='grid_co2_intensity'.
        """
        datapoints = []
        try:
            url = "https://odre.opendatasoft.com/api/records/1.0/search/?dataset=eco2mix-national-tr&rows=10"
            req = urllib.request.Request(url, headers={"User-Agent": "PROMEOS/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                for record in data.get("records", [])[:5]:
                    fields = record.get("fields", {})
                    ts = fields.get("date_heure")
                    co2_rate = fields.get("taux_co2")

                    if ts and co2_rate:
                        dp = DataPoint(
                            object_type=object_type,
                            object_id=object_id,
                            metric="grid_co2_intensity",
                            ts_start=datetime.fromisoformat(ts.replace("Z", "")),
                            ts_end=datetime.fromisoformat(ts.replace("Z", "")),
                            value=float(co2_rate),
                            unit="gCO2/kWh",
                            source_type=SourceType.API,
                            source_name=self.name,
                            quality_score=1.0,
                            coverage_ratio=1.0,
                            retrieved_at=datetime.now(timezone.utc),
                            source_ref=url,
                        )
                        db.add(dp)
                        datapoints.append(dp)
            db.commit()
        except Exception as e:
            print(f"RTE sync error: {e}")
        return datapoints
