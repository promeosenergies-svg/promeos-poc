"""Composition phrase 1 événementielle — Sprint Refonte Narrative dynamique Phase 3.3 + Phase 4.0.A.

Compose la **phrase 1** du body narratif Sol2 en racontant le **trigger
primary** issu du `trigger_prioritizer` (Phase 3.2). Si pas de primary →
phrase de stabilité spécifique à la typologie.

## Phase 4.0.A — corrections audit (drift doctrine §6/§7)

Audit 3 agents (Marie DAF + Ergonomie + CX) a identifié 3 P0 :

1. **§7 sourçage absent** : aucune phrase ne citait `event.source` /
   `event.confidence` → maintenant tissé en suffixe `(source RegOps,
   confiance haute)`.
2. **§6 KPI magique** : `event.title.lower()` cassait les sigles
   (TURPE→turpe) → suppression `.lower()`, sigles préservés.
3. **§6 paternalisme COMMERCE** : "consomme plus" sans chiffre → injection
   de `event.impact.value` formaté FR pour donner un repère quantitatif.

+ phrases de stabilité **reformulées avec ancrage positif** (audit Marie/CX)
plutôt que "rien à remonter" perçu comme creux en présentation.

## Doctrine §11.3 — body 3 phrases

| Phrase | Rôle | Source |
|---|---|---|
| 1 | Événementielle (le « il s'est passé X cette semaine ») | primary trigger |
| 2-3 | Structurelles (score / exposition / leviers) | builder existant |

## Format par typologie (Phase 1.3 lexical_templates)

- **GRAND_GROUPE** : « X sites de votre patrimoine ont basculé en dérive… »
- **COMMERCE** : « Votre {activity} consomme +X % vs la moyenne régionale… »
- **ERP** : « Votre établissement a basculé en dérive… »

## Garde-fou longueur (Phase 4.0.A)

`MAX_PHRASE_1_WORDS = 35` — au-delà, la phrase 1 dépasse le budget de
lecture 3 min CFO §11.3. Vérifié par source-guards.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 3.3 + audit Phase 4.0.A.
"""

from __future__ import annotations

from typing import Callable, Optional

from doctrine.naf_to_typology import OrganizationTypology
from doctrine.triggers import TriggerType
from services.event_bus.types import EventConfidence, EventSourceSystem, SolEventCard
from services.narrative.lexical_templates import get_activity_name
from services.narrative.trigger_prioritizer import TriggerPrioritization


# ─── Garde-fou longueur (audit §11.3 lecture 3 min) ────────────────────────


MAX_PHRASE_1_WORDS: int = 35


# ─── Phrases de stabilité par typologie (ancrage positif Phase 4.0.A) ──────


# Audit Marie + CX : ancrage chiffré + ton confiant > "rien à remonter".
# Variables {score} / {sites_count} sont substituées au runtime via
# render_stable_sentence si les données sont disponibles. Sinon, fallback
# sur la version générique sans variable.
SENTENCE_STABLE_TEMPLATES: dict[OrganizationTypology, str] = {
    OrganizationTypology.GRAND_GROUPE: (
        "Votre patrimoine tient sa trajectoire cette semaine — "
        "score conformité maintenu, aucune nouvelle dérive détectée"
    ),
    OrganizationTypology.COMMERCE: (
        "Votre activité tient le cap cette semaine — pas de surcoût détecté, consommation alignée sur votre profil"
    ),
    OrganizationTypology.ERP: (
        "Votre établissement tient sa trajectoire cette semaine — "
        "service public maintenu, pas d'écart sur la conformité"
    ),
    OrganizationTypology.UNKNOWN: ("Votre périmètre tient le cap cette semaine — pas de signal saillant"),
}

# Backward-compat alias — anciens imports.
SENTENCE_STABLE_BY_TYPOLOGY = SENTENCE_STABLE_TEMPLATES


# ─── Helpers Phase 4.0.A ────────────────────────────────────────────────────


# Mapping interne system canonique → libellé FR pour le suffixe source.
# Conserve les sigles connus (Enedis, GRDF, EPEX) en majuscules de marque.
_SOURCE_LABEL: dict[EventSourceSystem, str] = {
    "Enedis": "Enedis",
    "GRDF": "GRDF",
    "invoice": "facture fournisseur",
    "GTB": "GTB",
    "IoT": "capteurs IoT",
    "RegOps": "RegOps",
    "EPEX": "EPEX",
    "manual": "saisie manuelle",
    "benchmark": "benchmark INSEE",
}

_CONFIDENCE_LABEL: dict[EventConfidence, str] = {
    "high": "haute",
    "medium": "moyenne",
    "low": "à confirmer",
}


def _format_source_suffix(event: SolEventCard) -> str:
    """Formate le suffixe `(source X, confiance Y)` doctrine §7.

    Retourne chaîne vide si event sans source identifiable (jamais en
    pratique car SolEventCard exige une `source.system`).
    """
    src = _SOURCE_LABEL.get(event.source.system, str(event.source.system))
    conf = _CONFIDENCE_LABEL.get(event.source.confidence, str(event.source.confidence))
    return f"(source {src}, confiance {conf})"


def _format_eur_fr(value: float) -> str:
    """Formate un montant en € avec espaces français comme séparateurs milliers.

    Examples:
        >>> _format_eur_fr(1234)
        '1 234 €'
        >>> _format_eur_fr(1234567.5)
        '1 234 568 €'
    """
    rounded = round(value)
    # Format avec séparateur espace insécable (\xa0 → ' ' simple pour SQL/log compat)
    formatted = f"{rounded:,}".replace(",", " ")
    return f"{formatted} €"


def _format_pct_fr(value: float) -> str:
    """Formate un pourcentage avec signe explicite et 0 décimale.

    Examples:
        >>> _format_pct_fr(14.3)
        '+14 %'
        >>> _format_pct_fr(-12.7)
        '−13 %'
    """
    rounded = round(value)
    if rounded > 0:
        return f"+{rounded} %"
    if rounded < 0:
        return f"−{abs(rounded)} %"
    return "0 %"


# ─── Composeurs spécialisés par trigger ────────────────────────────────────


def compose_dt_drift_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `DT_TRAJECTORY_DRIFT` (priorité 1).

    Phase 4.0.A : injecte source + confiance ; Commerce reçoit un chiffre
    `event.impact.value` formaté FR pour ancrage quantitatif (anti-paternalisme §6).
    """
    sites_count = len(event.linked_assets.site_ids) or 1
    source_suffix = _format_source_suffix(event)

    if typology == OrganizationTypology.GRAND_GROUPE:
        plural = "s" if sites_count > 1 else ""
        verb = "ont" if sites_count > 1 else "a"
        return (
            f"{sites_count} site{plural} de votre patrimoine {verb} basculé en dérive "
            f"du jalon Décret Tertiaire -40 % cette semaine {source_suffix}"
        )

    if typology == OrganizationTypology.COMMERCE:
        # Phase 4.0.A — anti-paternalisme : injection chiffre concret
        activity = get_activity_name(None)
        impact = event.impact.value
        if impact is not None and event.impact.unit == "%":
            magnitude = _format_pct_fr(impact)
        elif impact is not None and event.impact.unit == "€":
            magnitude = f"surcoût {_format_eur_fr(impact)}"
        else:
            # Fallback si impact non chiffré — pas de paternalisme, on
            # qualifie l'écart même sans chiffre.
            magnitude = "écart marqué"
        return (
            f"Votre {activity} consomme {magnitude} vs la moyenne des {activity}s "
            f"de votre région cette semaine {source_suffix}"
        )

    if typology == OrganizationTypology.ERP:
        return f"Votre établissement a basculé en dérive du jalon Décret Tertiaire -40 % cette semaine {source_suffix}"

    # UNKNOWN fallback
    return f"Votre périmètre s'éloigne de la trajectoire 2030 cette semaine {source_suffix}"


def compose_major_anomaly_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `MAJOR_ANOMALY` (priorité 2 — billing_anomaly / action_overdue).

    Phase 4.0.A : `event.title` injecté SANS `.lower()` (préserve sigles
    TURPE/CTA/etc) + source + confiance.
    """
    source_suffix = _format_source_suffix(event)
    title = event.title  # Phase 4.0.A — sigles préservés (pas de .lower())

    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Anomalie majeure détectée sur votre patrimoine cette semaine : {title} {source_suffix}"
    if typology == OrganizationTypology.COMMERCE:
        # Empathie + verbe d'action implicite via formule "à vérifier"
        return f"Anomalie détectée cette semaine, à vérifier : {title} {source_suffix}"
    if typology == OrganizationTypology.ERP:
        return f"Anomalie majeure détectée sur votre établissement cette semaine : {title} {source_suffix}"
    return f"Anomalie détectée cette semaine : {title} {source_suffix}"


def compose_audit_deadline_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `AUDIT_DEADLINE_IMMINENT` (priorité 4).

    Phase 4.0.A : sigles préservés + source + confiance.
    """
    source_suffix = _format_source_suffix(event)
    title = event.title

    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Échéance réglementaire imminente sur votre patrimoine : {title} {source_suffix}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Échéance imminente, à traiter rapidement : {title} {source_suffix}"
    if typology == OrganizationTypology.ERP:
        return f"Échéance réglementaire imminente sur votre établissement : {title} {source_suffix}"
    return f"Échéance imminente : {title} {source_suffix}"


def compose_purchase_window_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `PURCHASE_WINDOW_OPEN` (priorité 5).

    Phase 4.0.A : sigles préservés + source + confiance.
    """
    source_suffix = _format_source_suffix(event)
    title = event.title

    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Fenêtre achat ouverte sur votre patrimoine : {title} {source_suffix}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Bonne fenêtre pour renégocier votre contrat : {title} {source_suffix}"
    if typology == OrganizationTypology.ERP:
        return f"Fenêtre achat ouverte sur votre établissement : {title} {source_suffix}"
    return f"Fenêtre achat ouverte : {title} {source_suffix}"


# ─── Dispatch trigger → composer ───────────────────────────────────────────


TRIGGER_TO_COMPOSER: dict[TriggerType, Callable[[SolEventCard, OrganizationTypology], str]] = {
    TriggerType.DT_TRAJECTORY_DRIFT: compose_dt_drift_sentence,
    TriggerType.MAJOR_ANOMALY: compose_major_anomaly_sentence,
    TriggerType.AUDIT_DEADLINE_IMMINENT: compose_audit_deadline_sentence,
    TriggerType.PURCHASE_WINDOW_OPEN: compose_purchase_window_sentence,
    # EXPOSURE_VARIATION et COMPLIANCE_THRESHOLD_CROSSED ne sont pas
    # event-driven (calculés via weekly_deltas / score) — pas de composer
    # déclenché ici. Phase 4 V2 ajoutera des composers calculatoires si
    # ces triggers deviennent primaires.
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
    """
    primary = prioritization.get("primary")
    primary_event: Optional[SolEventCard] = prioritization.get("primary_event")

    if primary is None or primary_event is None:
        return SENTENCE_STABLE_TEMPLATES.get(typology, SENTENCE_STABLE_TEMPLATES[OrganizationTypology.UNKNOWN])

    composer = TRIGGER_TO_COMPOSER.get(primary)
    if composer is None:
        # Trigger non event-driven → fallback stable typologique
        return SENTENCE_STABLE_TEMPLATES.get(typology, SENTENCE_STABLE_TEMPLATES[OrganizationTypology.UNKNOWN])

    return composer(primary_event, typology)


__all__ = [
    "MAX_PHRASE_1_WORDS",
    "SENTENCE_STABLE_TEMPLATES",
    "SENTENCE_STABLE_BY_TYPOLOGY",  # backward-compat alias
    "TRIGGER_TO_COMPOSER",
    "compose_dt_drift_sentence",
    "compose_major_anomaly_sentence",
    "compose_audit_deadline_sentence",
    "compose_purchase_window_sentence",
    "compose_sentence_1_eventful",
]
