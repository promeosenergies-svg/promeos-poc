"""Protocol EventDetector — contrat structurel pour détecteurs PROMEOS Sol.

Sprint 2 Vague C ét11bis (post-audit Architecture). PEP 544 Protocol :
duck-typing préservé, registry itérable, signature contractualisée.

Règles d'or détecteur (doctrine §10 + audit Architecture P0) :
1. **Pas de SQL métier inline** — un détecteur consomme un service métier
   existant (`losses_service`, `_load_org_context`, etc.) ; il ne ré-implémente
   pas la logique. Ex: `billing_anomaly_detector` consommera
   `losses_service.compute_billing_losses_summary` (pas de query directe sur
   `BillingInsight`).
2. **Org-scoping obligatoire** — `org_id` est paramètre obligatoire.
3. **Signature stable** — `detect(db, org_id) -> list[SolEventCard]`. Pas de
   `**kwargs`, pas de paramètres optionnels qui dérivent (period, force_refresh).
   Toute évolution doit passer par évolution du Protocol ici.
4. **Pureté lecture** — un détecteur ne mute jamais la DB. Lit + agrège + émet
   événements typés.

Tout détecteur doit être enregistré dans `DETECTORS` (`detectors/__init__.py`)
pour être pické par `event_service.compute_events`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session

from ..types import SolEventCard


@runtime_checkable
class EventDetector(Protocol):
    """Contrat structurel détecteur (PEP 544 + runtime_checkable).

    Module-level convention : chaque détecteur expose `detect(db, org_id)`
    fonction au top-level du module. `runtime_checkable` permet
    `isinstance(module, EventDetector)` côté tests pour vérifier la conformité.
    """

    def detect(self, db: Session, org_id: int) -> list[SolEventCard]:
        """Évalue l'état DB et émet 0..N événements typés doctrine §10.

        Parameters
        ----------
        db : Session
            Session SQLAlchemy active.
        org_id : int
            Scope multi-tenant (filtrage org obligatoire).

        Returns
        -------
        list[SolEventCard]
            Événements détectés. Liste vide si rien à signaler.
            Chaque event respecte le schéma doctrine §10 complet.
        """
        ...
