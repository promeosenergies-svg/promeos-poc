"""
PROMEOS Connectors - Meteo-France (STUB - requires API key)
"""

import os
from .base import Connector


class MeteoFranceConnector(Connector):
    name = "meteofrance"
    description = "Meteo-France API — donnees meteorologiques historiques"
    requires_auth = True
    env_vars = ["METEOFRANCE_API_KEY"]

    def test_connection(self) -> dict:
        api_key = os.environ.get("METEOFRANCE_API_KEY")
        if not api_key:
            return {
                "status": "stub",
                "message": "Stub mode: definir METEOFRANCE_API_KEY pour activer",
                "doc": "https://portail-api.meteofrance.fr/",
            }
        return {"status": "ok", "message": "API key presente (non teste)"}

    def sync(self, db, object_type: str, object_id: int, date_from=None, date_to=None):
        return []  # Stub
