"""
PROMEOS Connectors - Base class ABC
"""
from abc import ABC, abstractmethod
from typing import List
from sqlalchemy.orm import Session


class Connector(ABC):
    """Interface de base pour tous les connecteurs."""

    name: str = "base_connector"
    description: str = "Base connector"
    requires_auth: bool = False
    env_vars: List[str] = []

    @abstractmethod
    def test_connection(self) -> dict:
        """
        Teste la connexion.
        Retourne: {"status": "ok"|"stub"|"error", "message": str}
        """
        pass

    @abstractmethod
    def sync(self, db: Session, object_type: str, object_id: int, date_from=None, date_to=None) -> List:
        """
        Synchronise les donnees et retourne une liste de DataPoints.
        """
        pass
