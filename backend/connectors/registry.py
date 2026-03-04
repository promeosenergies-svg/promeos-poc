"""
PROMEOS Connectors - Registry avec auto-discovery
"""

from typing import Dict, Optional
from .base import Connector
from . import rte_eco2mix, pvgis, meteofrance, enedis_opendata, enedis_dataconnect


_CONNECTORS: Dict[str, Connector] = {}


def _register_all():
    """Auto-discovery de tous les connecteurs."""
    if _CONNECTORS:
        return

    connectors = [
        rte_eco2mix.RTEEco2MixConnector(),
        pvgis.PVGISConnector(),
        meteofrance.MeteoFranceConnector(),
        enedis_opendata.EnedisOpenDataConnector(),
        enedis_dataconnect.EnedisDataConnectConnector(),
    ]

    for connector in connectors:
        _CONNECTORS[connector.name] = connector


def list_connectors() -> list[dict]:
    """Liste tous les connecteurs disponibles."""
    _register_all()
    return [
        {
            "name": c.name,
            "description": c.description,
            "requires_auth": c.requires_auth,
            "env_vars": c.env_vars,
        }
        for c in _CONNECTORS.values()
    ]


def get_connector(name: str) -> Optional[Connector]:
    """Recupere un connecteur par nom."""
    _register_all()
    return _CONNECTORS.get(name)


def run_sync(name: str, db, **kwargs):
    """Execute la synchro d'un connecteur."""
    connector = get_connector(name)
    if not connector:
        raise ValueError(f"Connector {name} not found")
    return connector.sync(db, **kwargs)
