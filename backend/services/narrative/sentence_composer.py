"""Composition phrase 1 événementielle — Sprint Refonte Narrative dynamique Phase 3.3.

Compose la **phrase 1** du body narratif Sol2 en racontant le **trigger
primary** issu du `trigger_prioritizer` (Phase 3.2). Si pas de primary →
phrase de stabilité spécifique à la typologie.

## Doctrine §11.3 — body 3 phrases

| Phrase | Rôle | Source |
|---|---|---|
| 1 | Événementielle (le « il s'est passé X cette semaine ») | primary trigger |
| 2-3 | Structurelles (score / exposition / leviers) | builder existant |

Cette phase couvre uniquement la **phrase 1**. Les phrases 2-3 sont
inchangées dans `narrative_generator._build_cockpit_comex` — l'injection
d'une éventuelle phrase événementielle se fait en préfixe de `narrative`
(Phase 4 wiring final).

## Format par typologie (Phase 1.3 lexical_templates)

- **GRAND_GROUPE** : « X sites de votre patrimoine ont basculé en dérive… »
- **COMMERCE** : « Votre {activity} consomme X % de plus que les {activity}s
  similaires de votre région… » (registre comparatif pédagogique)
- **ERP** : « Votre établissement a basculé en dérive… »

## Stabilité (pas de primary)

Si silence narratif (aucun trigger), on retourne une phrase de **stabilité
typologique** plutôt qu'une chaîne vide — l'utilisateur a besoin d'un
ancrage éditorial même quand rien ne bouge.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.3.
"""

from __future__ import annotations

from typing import Callable, Optional

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import TriggerType
from services.event_bus.types import SolEventCard
from services.narrative.lexical_templates import get_activity_name
from services.narrative.trigger_prioritizer import TriggerPrioritization


# ─── Phrases de stabilité par typologie (fallback) ─────────────────────────


SENTENCE_STABLE_BY_TYPOLOGY: dict[OrganizationTypology, str] = {
    OrganizationTypology.GRAND_GROUPE: (
        "Votre patrimoine est stable cette semaine — aucun signal saillant à remonter au CODIR"
    ),
    OrganizationTypology.COMMERCE: (
        "Votre activité est stable cette semaine — pas de surcoût ni de variation à signaler"
    ),
    OrganizationTypology.ERP: (
        "Votre établissement est stable cette semaine — pas d'écart sur la trajectoire de service public"
    ),
    OrganizationTypology.UNKNOWN: ("Votre périmètre est stable cette semaine — aucun signal saillant à remonter"),
}


# ─── Composeurs spécialisés par trigger ────────────────────────────────────


def compose_dt_drift_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `DT_TRAJECTORY_DRIFT` (priorité 1).

    Adapte le sujet et le registre :
    - GRAND_GROUPE : « X sites de votre patrimoine ont basculé en dérive »
    - COMMERCE : comparatif benchmarks régionaux pour activité similaire
    - ERP : « Votre établissement a basculé en dérive »
    """
    sites_count = len(event.linked_assets.site_ids) or 1

    if typology == OrganizationTypology.GRAND_GROUPE:
        plural = "s" if sites_count > 1 else ""
        return (
            f"{sites_count} site{plural} de votre patrimoine "
            f"{'ont' if sites_count > 1 else 'a'} basculé en dérive de la trajectoire 2030 cette semaine"
        )

    if typology == OrganizationTypology.COMMERCE:
        # NAF embarqué : on tente de récupérer le code NAF du 1er site lié,
        # à défaut on tombe sur "magasin". Pour MVP, on n'a pas le NAF
        # directement dans SolEventCard — on utilise le fallback.
        activity = get_activity_name(None)  # MVP : "magasin" par défaut
        return f"Votre {activity} consomme plus que les {activity}s similaires de votre région cette semaine"

    if typology == OrganizationTypology.ERP:
        return "Votre établissement a basculé en dérive de la trajectoire 2030 cette semaine"

    # UNKNOWN fallback
    return "Votre périmètre s'éloigne de la trajectoire 2030 cette semaine"


def compose_major_anomaly_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `MAJOR_ANOMALY` (priorité 2 — billing_anomaly / action_overdue)."""
    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Anomalie majeure détectée sur votre patrimoine cette semaine : {event.title.lower()}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Anomalie détectée cette semaine : {event.title.lower()}"
    if typology == OrganizationTypology.ERP:
        return f"Anomalie majeure détectée sur votre établissement cette semaine : {event.title.lower()}"
    return f"Anomalie détectée cette semaine : {event.title.lower()}"


def compose_audit_deadline_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `AUDIT_DEADLINE_IMMINENT` (priorité 4)."""
    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Échéance réglementaire imminente sur votre patrimoine : {event.title.lower()}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Échéance imminente : {event.title.lower()}"
    if typology == OrganizationTypology.ERP:
        return f"Échéance réglementaire imminente sur votre établissement : {event.title.lower()}"
    return f"Échéance imminente : {event.title.lower()}"


def compose_purchase_window_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `PURCHASE_WINDOW_OPEN` (priorité 5)."""
    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Fenêtre achat ouverte sur votre patrimoine : {event.title.lower()}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Bonne fenêtre pour renégocier : {event.title.lower()}"
    if typology == OrganizationTypology.ERP:
        return f"Fenêtre achat ouverte sur votre établissement : {event.title.lower()}"
    return f"Fenêtre achat ouverte : {event.title.lower()}"


# ─── Dispatch trigger → composer ───────────────────────────────────────────


TRIGGER_TO_COMPOSER: dict[TriggerType, Callable[[SolEventCard, OrganizationTypology], str]] = {
    TriggerType.DT_TRAJECTORY_DRIFT: compose_dt_drift_sentence,
    TriggerType.MAJOR_ANOMALY: compose_major_anomaly_sentence,
    TriggerType.AUDIT_DEADLINE_IMMINENT: compose_audit_deadline_sentence,
    TriggerType.PURCHASE_WINDOW_OPEN: compose_purchase_window_sentence,
    # EXPOSURE_VARIATION et COMPLIANCE_THRESHOLD_CROSSED ne sont pas
    # event-driven (calculés via weekly_deltas / score) — pas de composer
    # déclenché ici. Phase 4 V2 ajoutera des composers calculatoires si
    # ces triggers deviennent primaires (peu probable en pratique vu
    # leur priorité 3/6 derrière les drivers event-driven).
}


# ─── API publique ──────────────────────────────────────────────────────────


def compose_sentence_1_eventful(
    prioritization: TriggerPrioritization,
    typology: OrganizationTypology,
) -> str:
    """Compose la phrase 1 événementielle du body narratif.

    Si `prioritization["primary"]` est `None` → phrase de stabilité
    typologique. Sinon dispatch vers le composer dédié au trigger.

    Args:
        prioritization: sortie de `prioritize_triggers` (Phase 3.2).
        typology: typologie organisationnelle (Phase 1.2).

    Returns:
        Phrase 1 prête à insérer en début de body. Pas de point final
        (le caller compose la ponctuation pour cohérence avec phrases 2-3).

    Examples:
        >>> # Silence → phrase stable
        >>> compose_sentence_1_eventful(
        ...     {"primary": None, "primary_event": None, ...},
        ...     OrganizationTypology.GRAND_GROUPE
        ... )
        'Votre patrimoine est stable cette semaine — aucun signal saillant à remonter au CODIR'

        >>> # DT drift → phrase patrimoine
        >>> # 'X sites de votre patrimoine ont basculé en dérive...'
    """
    primary = prioritization.get("primary")
    primary_event: Optional[SolEventCard] = prioritization.get("primary_event")

    if primary is None or primary_event is None:
        # Stabilité — fallback typologique safe
        return SENTENCE_STABLE_BY_TYPOLOGY.get(typology, SENTENCE_STABLE_BY_TYPOLOGY[OrganizationTypology.UNKNOWN])

    composer = TRIGGER_TO_COMPOSER.get(primary)
    if composer is None:
        # Trigger non event-driven (EXPOSURE_VARIATION / COMPLIANCE_THRESHOLD_CROSSED)
        # → fallback générique typologique
        return SENTENCE_STABLE_BY_TYPOLOGY.get(typology, SENTENCE_STABLE_BY_TYPOLOGY[OrganizationTypology.UNKNOWN])

    return composer(primary_event, typology)


__all__ = [
    "SENTENCE_STABLE_BY_TYPOLOGY",
    "TRIGGER_TO_COMPOSER",
    "compose_dt_drift_sentence",
    "compose_major_anomaly_sentence",
    "compose_audit_deadline_sentence",
    "compose_purchase_window_sentence",
    "compose_sentence_1_eventful",
]
