"""Trigger prioritizer — Sprint Refonte Narrative dynamique Phase 3.2.

Hiérarchise les `SolEventCard` détectés en **primary + secondary** selon
**Option 4.C** (max 2 triggers tissés en body narratif). Les autres
événements restent dans la pile `<SolEventStream>` pour drill-down — pas
dans le récit principal.

## Algorithme

1. **Mapper** chaque event vers son trigger cible via
   `EVENT_TYPE_TO_TRIGGER` (Phase 3.1). Filtrer les events dont le
   trigger est `None` (masqués globalement) ou dans
   `MASKED_TRIGGERS_BY_TYPOLOGY[typology]` (masqués pour cette typologie).
2. **Trier** par priorité ascendante (1 = plus urgent).
3. **Dédupliquer** par trigger (si plusieurs `consumption_drift` events,
   on ne garde que le plus saillant — l'event_bus a déjà trié par
   sévérité).
4. **Extraire** primary (rang 0) + secondary (rang 1).

## Pourquoi max 2 ?

Doctrine §11.3 « 1 phrase événementielle + 2 phrases structurelles » :
le body narratif a 3 phrases au total. La phrase 1 raconte le primary,
les phrases 2-3 portent le contexte structurel (score, exposition,
leviers) — pas une enfilade d'alertes qui dilue le signal.

Le secondary est exposé dans le retour pour usage futur (Phase 4 V2 où
il pourra être tissé en sous-clause "+ {secondary court}").

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.2 + Option 4.C.
"""

from __future__ import annotations

from typing import Optional, TypedDict

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import (
    EVENT_TYPE_TO_TRIGGER,
    MASKED_TRIGGERS_BY_TYPOLOGY,
    TRIGGER_PRIORITY,
    TriggerType,
)
from services.event_bus.types import SolEventCard


class TriggerPrioritization(TypedDict):
    """Résultat de la hiérarchisation primary + secondary."""

    primary: Optional[TriggerType]
    primary_event: Optional[SolEventCard]
    secondary: Optional[TriggerType]
    secondary_event: Optional[SolEventCard]
    all_active_triggers: list[TriggerType]


def prioritize_triggers(
    events: list[SolEventCard],
    typology: OrganizationTypology,
) -> TriggerPrioritization:
    """Hiérarchise les events détectés en primary + secondary (Option 4.C).

    Args:
        events: events produits par `services.event_bus.compute_events()`.
            Liste vide acceptée (silence narratif).
        typology: typologie organisationnelle (Phase 1.2). Filtre les
            triggers masqués pour cette typologie (cf
            `MASKED_TRIGGERS_BY_TYPOLOGY`).

    Returns:
        TriggerPrioritization avec primary/secondary (None si rien à dire),
        + liste exhaustive `all_active_triggers` pour télémétrie /
        export PDF complet.

    Examples:
        >>> # Pas d'events → silence
        >>> prioritize_triggers([], OrganizationTypology.GRAND_GROUPE)
        {'primary': None, 'primary_event': None, 'secondary': None, ...}

        >>> # Multiple events → primary = priorité la plus urgente
        >>> # (DT_TRAJECTORY_DRIFT prio 1 dominant sur PURCHASE_WINDOW prio 5)
    """
    masked = MASKED_TRIGGERS_BY_TYPOLOGY.get(typology, set())

    # 1. Mapper events → triggers (filtrer None + masqués)
    triggered: list[tuple[TriggerType, SolEventCard]] = []
    for event in events:
        trigger = EVENT_TYPE_TO_TRIGGER.get(event.event_type)
        if trigger is None or trigger in masked:
            continue
        triggered.append((trigger, event))

    # 2. Trier par priorité ascendante (1 = plus urgent)
    triggered.sort(key=lambda x: TRIGGER_PRIORITY[x[0]])

    # 3. Dédupliquer (même trigger = on garde le 1er = le plus prioritaire
    # selon ordre d'arrivée des events qui suit déjà la sévérité).
    seen: set[TriggerType] = set()
    unique: list[tuple[TriggerType, SolEventCard]] = []
    for trigger, event in triggered:
        if trigger in seen:
            continue
        seen.add(trigger)
        unique.append((trigger, event))

    # 4. Extraire primary + secondary
    primary_pair: tuple[Optional[TriggerType], Optional[SolEventCard]] = unique[0] if unique else (None, None)
    secondary_pair: tuple[Optional[TriggerType], Optional[SolEventCard]] = (
        unique[1] if len(unique) >= 2 else (None, None)
    )

    return {
        "primary": primary_pair[0],
        "primary_event": primary_pair[1],
        "secondary": secondary_pair[0],
        "secondary_event": secondary_pair[1],
        "all_active_triggers": [t for t, _ in unique],
    }


__all__ = [
    "TriggerPrioritization",
    "prioritize_triggers",
]
