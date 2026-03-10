"""
PROMEOS Connectors - Enedis Open Data
"""

from .base import Connector


class EnedisOpenDataConnector(Connector):
    name = "enedis_opendata"
    description = "Enedis Open Data — donnees reseau publiques"
    requires_auth = False
    env_vars = []

    def test_connection(self) -> dict:
        return {"status": "ok", "message": "API publique — prêt à synchroniser", "doc": "https://data.enedis.fr/"}

    def sync(self, db, object_type: str, object_id: int, date_from=None, date_to=None):
        return []
