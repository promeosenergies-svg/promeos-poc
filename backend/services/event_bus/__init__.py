"""Event bus PROMEOS Sol — chantier α moteur événements proactif (Vague C ét11).

Doctrine v1.1 §10 « Modèle d'événement énergétique » :
> Le produit vivant repose sur un moteur d'événements.

Doctrine v1.1 §6 Principes cardinaux :
- P6 « Le produit pousse, ne tire pas » — détecte/priorise/pousse les signaux
- P7 « Le patrimoine vit, le produit suit » — J ≠ J+1 si données changent

Doctrine v1.1 §14 Test 6 « J vs J+1 » : si un événement réel a changé, l'écran
le reflète. Test FAIL universel pré-α (4/4 pages auditées Vague B) → résolu
ici par l'orchestrateur `compute_events`.

API publique :
- `SolEventCard` : dataclass aligné §10 doctrine (mirror du type TypeScript)
- `compute_events(db, org_id) -> list[SolEventCard]` : orchestrateur multi-détecteurs
- `to_narrative_week_cards(events) -> list[NarrativeWeekCard]` : conversion
  rétro-compat pour SolWeekCards existant (transition douce Vague C ét11)

MVP α : 1 détecteur pilote `compliance_deadline_detector`. Vague C ét12+
ajoutera billing_anomaly / consumption_drift / contract_renewal /
market_window / data_quality_issue / flex_opportunity / asset_registry_issue
/ action_overdue (8 types restants doctrine §10).
"""

from .event_service import compute_events, to_narrative_week_cards
from .types import (
    EventAction,
    EventImpact,
    EventLinkedAssets,
    EventMitigation,
    EventSource,
    SolEventCard,
)

__all__ = [
    "SolEventCard",
    "EventImpact",
    "EventMitigation",
    "EventSource",
    "EventAction",
    "EventLinkedAssets",
    "compute_events",
    "to_narrative_week_cards",
]
