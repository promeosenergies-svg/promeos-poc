"""
PROMEOS Connectors - Enedis Data Connect (STUB - requires OAuth)
"""

import os
from .base import Connector


class EnedisDataConnectConnector(Connector):
    name = "enedis_dataconnect"
    description = "Enedis Data Connect OAuth (stub - cles requises)"
    requires_auth = True
    env_vars = ["ENEDIS_CLIENT_ID", "ENEDIS_CLIENT_SECRET"]

    def test_connection(self) -> dict:
        client_id = os.environ.get("ENEDIS_CLIENT_ID")
        if not client_id:
            return {
                "status": "stub",
                "message": "Stub mode: definir ENEDIS_CLIENT_ID/SECRET pour activer",
                "doc": "https://data-connect.enedis.fr/",
            }
        return {"status": "ok", "message": "Client ID present (non teste)"}

    def sync(self, db, object_type: str, object_id: int, date_from=None, date_to=None):
        return []  # Stub
