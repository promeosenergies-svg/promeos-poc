"""Détecteurs d'événements PROMEOS Sol — chantier α (doctrine §10).

Chaque détecteur respecte le Protocol `EventDetector` (`_protocol.py`) :
fonction `detect(db, org_id) -> list[SolEventCard]` au top-level du module,
sans kwargs, sans logique SQL métier inline (consommer services existants).

Sprint 2 Vague C ét11 : compliance_deadline_detector seul (MVP α).
Sprint 2 Vague C ét11bis : Protocol formalisé + DETECTORS registry.
Sprint 2 Vague C ét12+ : billing_anomaly + consumption_drift + 6 autres.

Pour ajouter un détecteur :
1. Créer `detectors/<name>_detector.py` avec `def detect(db, org_id)`.
2. Importer + ajouter au `DETECTORS` registry ci-dessous.
3. Ajouter test conformité Protocol dans `test_event_bus.py`.
"""

from . import compliance_deadline_detector
from ._protocol import EventDetector

# Registry consommé par `event_service.compute_events`. Order ne porte pas
# de sémantique (le tri severity stable est appliqué après agrégation).
DETECTORS: list[EventDetector] = [
    compliance_deadline_detector,  # type: ignore[list-item]
]

__all__ = ["DETECTORS", "EventDetector"]
