"""Event service — orchestrateur multi-détecteurs (doctrine v1.1 §10 + chantier α).

Pattern :
1. Chaque détecteur (`detectors/*.py`) implémente `detect(db, org_id) -> list[SolEventCard]`.
2. `compute_events` agrège tous les détecteurs et retourne la liste consolidée
   triée par severity (critical → warning → watch → info).
3. `to_narrative_week_cards` convertit en `NarrativeWeekCard` pour SolWeekCards
   existant (transition douce — Vague C ét12+ migrera vers `<SolEventCard>` natif).

MVP α (ét11) : 1 seul détecteur `compliance_deadline_detector`. Vague C ét12+
ajoutera 8 détecteurs supplémentaires (cf doctrine §10 9 event_types).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .detectors import compliance_deadline_detector
from .types import SEVERITY_TO_CARD_TYPE, EventSeverity, SolEventCard

# Ordre de tri severity (le plus urgent d'abord).
_SEVERITY_ORDER: dict[EventSeverity, int] = {
    "critical": 0,
    "warning": 1,
    "watch": 2,
    "info": 3,
}


def compute_events(db: Session, org_id: int) -> list[SolEventCard]:
    """Orchestrateur : appelle tous les détecteurs et trie par severity.

    Doctrine §6 P6 « Le produit pousse, ne tire pas » : chaque appel
    réévalue tous les détecteurs depuis l'état courant DB → garantit
    P7 « Le patrimoine vit, le produit suit » (J ≠ J+1 si données changent).

    Parameters
    ----------
    db : Session
        Session SQLAlchemy active.
    org_id : int
        Scope multi-tenant — chaque détecteur applique le filtrage org.

    Returns
    -------
    list[SolEventCard]
        Événements triés (critical d'abord), MVP α uniquement issus de
        `compliance_deadline_detector`. Liste vide si rien à signaler.
    """
    events: list[SolEventCard] = []
    events.extend(compliance_deadline_detector.detect(db, org_id))

    # Tri stable par severity ascendant (critical=0 d'abord).
    events.sort(key=lambda e: _SEVERITY_ORDER.get(e.severity, 99))
    return events


def to_narrative_week_cards(events: list[SolEventCard]) -> list:
    """Convertit `SolEventCard` → `NarrativeWeekCard` pour SolWeekCards
    existant (transition Vague C ét11).

    Mapping :
    - severity → type (critical/warning → todo, watch → watch, info → good_news)
    - title → title (déjà narrative §5)
    - narrative → body
    - action.route → cta_path, action.label → cta_label
    - impact.value (si unit=€) → impact_eur
    - impact.period=deadline + impact.value → urgency_days (approximation MVP)
    """
    # Import local pour éviter cycle (narrative_generator dépend de event_service)
    from services.narrative.narrative_generator import NarrativeWeekCard

    cards = []
    for event in events:
        impact_eur = event.impact.value if event.impact.value is not None and event.impact.unit == "€" else None
        urgency_days = (
            int(event.impact.value)
            if event.impact.value is not None and event.impact.unit == "days" and event.impact.period == "deadline"
            else None
        )
        cards.append(
            NarrativeWeekCard(
                type=SEVERITY_TO_CARD_TYPE.get(event.severity, "watch"),
                title=event.title,
                body=event.narrative,
                cta_path=event.action.route,
                cta_label=event.action.label,
                impact_eur=impact_eur,
                urgency_days=urgency_days,
            )
        )
    return cards
