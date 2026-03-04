"""
PROMEOS Watchers - Base class ABC
"""

from abc import ABC, abstractmethod
from typing import List
from sqlalchemy.orm import Session
from models import RegSourceEvent


class Watcher(ABC):
    """Interface de base pour tous les watchers."""

    name: str = "base_watcher"
    description: str = "Base watcher"
    source_url: str = ""

    @abstractmethod
    def check(self, db: Session) -> List[RegSourceEvent]:
        """
        Verifie la source et retourne les nouveaux evenements.
        Gere automatiquement la deduplication par content_hash.
        """
        pass
