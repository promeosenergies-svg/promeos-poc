"""Narrative service — orchestrateur récit éditorial Sol §5.

ADR-001 grammaire Sol industrialisée : un seul endpoint par page Sol
qui retourne `Narrative` complet (kicker + titre + narrative 2-3l + 3 KPIs +
3 week-cards + provenance). Backend orchestre les services pillar existants.

ADR-003 chantier β multi-archetype : Sprint 3 introduira `archetype`
branching (5 archetypes seedés démo).

ADR-004 chantier δ transformation acronymes : Sprint 3 introduira lookup
glossaire pour titres/labels (DT → "trajectoire 2030 obligatoire", etc.).
"""

from .narrative_generator import (
    Narrative,
    NarrativeKpi,
    NarrativeWeekCard,
    generate_page_narrative,
)

__all__ = [
    "Narrative",
    "NarrativeKpi",
    "NarrativeWeekCard",
    "generate_page_narrative",
]
