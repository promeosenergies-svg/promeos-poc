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

from . import (
    action_overdue_detector,
    asset_registry_issue_detector,
    billing_anomaly_detector,
    compliance_deadline_detector,
    consumption_drift_detector,
    contract_renewal_detector,
    data_quality_issue_detector,
    flex_opportunity_detector,
    market_window_detector,
)
from ._protocol import EventDetector

# Registry consommé par `event_service.compute_events`. Order ne porte pas
# de sémantique (le tri severity stable est appliqué après agrégation).
# Sprint 2 Vague C ét11→ét13f : 9/9 détecteurs doctrine §10 livrés.
DETECTORS: list[EventDetector] = [
    compliance_deadline_detector,  # type: ignore[list-item]
    billing_anomaly_detector,  # type: ignore[list-item]
    consumption_drift_detector,  # type: ignore[list-item]
    flex_opportunity_detector,  # type: ignore[list-item]
    market_window_detector,  # type: ignore[list-item]
    contract_renewal_detector,  # type: ignore[list-item]
    data_quality_issue_detector,  # type: ignore[list-item]
    asset_registry_issue_detector,  # type: ignore[list-item]
    action_overdue_detector,  # type: ignore[list-item]
]

__all__ = ["DETECTORS", "EventDetector"]
