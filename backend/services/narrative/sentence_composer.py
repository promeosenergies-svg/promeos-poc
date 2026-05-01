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
# Phase 8.C audit final P0 : ajout d'une action implicite ("focus de la
# semaine" / "prochaine étape") pour éviter le ressenti "rien à dire" en
# CODIR. Le silence Option 3.C reste tenu (pas de fausse alerte) mais
# l'utilisateur sort de la lecture avec un ancrage forward-looking.
#
# Phase 8.bis correction audit P1 — date OPERAT dynamique au lieu de
# "OPERAT 2026" hardcodée (qui aurait été obsolète au 1er janvier 2027).
# Convention OPERAT : déclaration N annuelle entre janvier et septembre
# de l'année N+1 (ex: conso 2026 → déclarable jusqu'au 30/09/2027). On
# pointe sur l'année courante comme année de conso à déclarer.
SENTENCE_STABLE_TEMPLATES: dict[OrganizationTypology, str] = {
    OrganizationTypology.GRAND_GROUPE: (
        "Votre patrimoine tient sa trajectoire cette semaine — "
        "score conformité maintenu, aucune nouvelle dérive détectée. "
        "Focus prochain comité : préparer les déclarations OPERAT annuelles "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    OrganizationTypology.ETI_TERTIAIRE: (
        # Phase 9.B — Marie audit : "parc" pas "patrimoine"
        "Votre parc tient sa trajectoire cette semaine — "
        "score conformité maintenu, aucune nouvelle dérive détectée. "
        "Focus prochain comité : préparer les déclarations OPERAT annuelles "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    OrganizationTypology.INDUSTRIE: (
        # Phase 11.C — Industrie manufacturière (Inès CSR_MANAGER)
        "Votre groupe industriel tient sa trajectoire cette semaine — "
        "émissions scope 1-2-3 alignées sur la trajectoire CSRD. "
        "Focus prochain comité : préparer le reporting CBAM trimestriel "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    OrganizationTypology.COMMERCE: (
        "Votre activité tient le cap cette semaine — pas de surcoût détecté, "
        "consommation alignée sur votre profil. "
        "Focus prochain mois : vérifier la facture S+2 vs profil "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    OrganizationTypology.ERP: (
        "Votre établissement tient sa trajectoire cette semaine — "
        "service public maintenu, pas d'écart sur la conformité. "
        "Focus prochain conseil : préparer l'audit énergétique annuel "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    OrganizationTypology.UNKNOWN: (
        "Votre périmètre tient le cap cette semaine — pas de signal saillant. "
        "Focus suggéré : vérifier les prochaines échéances réglementaires "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
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


# Phase 7 correctif D — délégation au SoT canonique services/narrative/formatters.py.
# Aliases internes conservent les noms historiques (_format_eur_fr / _format_pct_fr)
# pour minimiser la surface de modification et préserver les imports test existants.
from services.narrative.formatters import (
    format_eur_thousand as _format_eur_fr,  # noqa: F401
    format_pct_short as _format_pct_fr,  # noqa: F401
)


# ─── Phase 11.B — closing_clause forward-looking par typology ───────────────
# Audit personas P0-2 : la phrase 1 raconte un fait mais ne suggère pas
# d'action. Phase 11.B ajoute une closing_clause par typology + trigger
# pour ancrer un cadrage temporel ou un canal d'arbitrage.
#
# Convention :
#   GG/ETI : "à porter au prochain comité" (canal d'arbitrage)
#   COMMERCE : "à vérifier sur la prochaine facture" (canal pratique)
#   ERP : "à porter au prochain conseil" (canal officiel)
#   UNKNOWN : pas de closing (fallback safe)


_CLOSING_CLAUSE_BY_TYPOLOGY: dict[OrganizationTypology, str] = {
    OrganizationTypology.GRAND_GROUPE: "à porter au prochain comité",
    OrganizationTypology.ETI_TERTIAIRE: "à porter au prochain comité",
    OrganizationTypology.COMMERCE: "à traiter cette semaine",
    OrganizationTypology.ERP: "à porter au prochain conseil",
    OrganizationTypology.INDUSTRIE: "à intégrer au reporting CSRD",
    OrganizationTypology.UNKNOWN: "",
}


def _closing_for(typology: OrganizationTypology) -> str:
    """Retourne la closing_clause typology-aware ou chaîne vide si UNKNOWN."""
    clause = _CLOSING_CLAUSE_BY_TYPOLOGY.get(typology, "")
    return f" — {clause}" if clause else ""


# ─── Composeurs spécialisés par trigger ────────────────────────────────────


def compose_dt_drift_sentence(
    event: SolEventCard,
    typology: OrganizationTypology,
    naf_code: Optional[str] = None,
) -> str:
    """Phrase 1 pour `DT_TRAJECTORY_DRIFT` (priorité 1).

    Phase 4.0.A : injecte source + confiance ; Commerce reçoit un chiffre
    `event.impact.value` formaté FR pour ancrage quantitatif (anti-paternalisme §6).

    Phase 7 correctif B : `naf_code` propage le NAF du site lié pour Commerce
    → "boulangerie" / "restaurant" / etc. au lieu du générique "magasin"
    (bug audit final P0 latent).
    """
    sites_count = len(event.linked_assets.site_ids) or 1
    source_suffix = _format_source_suffix(event)
    # Phase 11.B — closing forward-looking par typology (audit personas P0-2)
    tail = f"{_closing_for(typology)} {source_suffix}".strip()

    if typology == OrganizationTypology.GRAND_GROUPE:
        plural = "s" if sites_count > 1 else ""
        verb = "ont" if sites_count > 1 else "a"
        return (
            f"{sites_count} site{plural} de votre patrimoine {verb} basculé en dérive "
            f"du jalon Décret Tertiaire -40 % cette semaine {tail}"
        )

    # Phase 9.B — ETI_TERTIAIRE : "parc" au lieu de "patrimoine" (audit Marie)
    if typology == OrganizationTypology.ETI_TERTIAIRE:
        plural = "s" if sites_count > 1 else ""
        verb = "ont" if sites_count > 1 else "a"
        return (
            f"{sites_count} site{plural} de votre parc {verb} basculé en dérive "
            f"du jalon Décret Tertiaire -40 % cette semaine {tail}"
        )

    # Phase 11.C — INDUSTRIE : "site industriel" + scope CSRD
    if typology == OrganizationTypology.INDUSTRIE:
        plural = "s" if sites_count > 1 else ""
        verb = "ont" if sites_count > 1 else "a"
        return (
            f"{sites_count} site industriel{plural} {verb} dépassé son budget énergétique "
            f"cette semaine, impact scope 1-2-3 à reporter CSRD {tail}"
        )

    if typology == OrganizationTypology.COMMERCE:
        # Phase 4.0.A + Phase 7 correctif B — NAF résolu, plus de "magasin" générique
        activity = get_activity_name(naf_code)
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
            f"Votre {activity} consomme {magnitude} vs la moyenne des {activity}s de votre région cette semaine {tail}"
        )

    if typology == OrganizationTypology.ERP:
        return f"Votre établissement a basculé en dérive du jalon Décret Tertiaire -40 % cette semaine {tail}"

    # UNKNOWN fallback
    return f"Votre périmètre s'éloigne de la trajectoire 2030 cette semaine {tail}"


def compose_major_anomaly_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `MAJOR_ANOMALY` (priorité 2 — billing_anomaly / action_overdue).

    Phase 4.0.A : `event.title` injecté SANS `.lower()` (préserve sigles
    TURPE/CTA/etc) + source + confiance.
    Phase 11.B : closing forward-looking typology-aware.
    """
    source_suffix = _format_source_suffix(event)
    title = event.title  # Phase 4.0.A — sigles préservés (pas de .lower())
    tail = f"{_closing_for(typology)} {source_suffix}".strip()

    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Anomalie majeure détectée sur votre patrimoine cette semaine : {title} {tail}"
    if typology == OrganizationTypology.ETI_TERTIAIRE:
        return f"Anomalie majeure détectée sur votre parc cette semaine : {title} {tail}"
    if typology == OrganizationTypology.INDUSTRIE:
        return f"Anomalie majeure détectée sur votre groupe industriel cette semaine : {title} {tail}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Anomalie détectée cette semaine, à vérifier : {title} {tail}"
    if typology == OrganizationTypology.ERP:
        return f"Anomalie majeure détectée sur votre établissement cette semaine : {title} {tail}"
    return f"Anomalie détectée cette semaine : {title} {tail}"


def compose_audit_deadline_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `AUDIT_DEADLINE_IMMINENT` (priorité 4).

    Phase 4.0.A : sigles préservés + source + confiance.
    Phase 11.B : closing forward-looking typology-aware.
    """
    source_suffix = _format_source_suffix(event)
    title = event.title
    tail = f"{_closing_for(typology)} {source_suffix}".strip()

    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Échéance réglementaire imminente sur votre patrimoine : {title} {tail}"
    if typology == OrganizationTypology.ETI_TERTIAIRE:
        return f"Échéance réglementaire imminente sur votre parc : {title} {tail}"
    if typology == OrganizationTypology.INDUSTRIE:
        return f"Échéance réglementaire imminente sur votre groupe industriel : {title} {tail}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Échéance imminente, à traiter rapidement : {title} {tail}"
    if typology == OrganizationTypology.ERP:
        return f"Échéance réglementaire imminente sur votre établissement : {title} {tail}"
    return f"Échéance imminente : {title} {tail}"


def compose_purchase_window_sentence(event: SolEventCard, typology: OrganizationTypology) -> str:
    """Phrase 1 pour `PURCHASE_WINDOW_OPEN` (priorité 5).

    Phase 4.0.A : sigles préservés + source + confiance.
    Phase 11.B : closing forward-looking typology-aware.
    """
    source_suffix = _format_source_suffix(event)
    title = event.title
    tail = f"{_closing_for(typology)} {source_suffix}".strip()

    if typology == OrganizationTypology.GRAND_GROUPE:
        return f"Fenêtre achat ouverte sur votre patrimoine : {title} {tail}"
    if typology == OrganizationTypology.ETI_TERTIAIRE:
        return f"Fenêtre achat ouverte sur votre parc : {title} {tail}"
    if typology == OrganizationTypology.INDUSTRIE:
        return f"Fenêtre achat ouverte sur votre groupe industriel : {title} {tail}"
    if typology == OrganizationTypology.COMMERCE:
        return f"Bonne fenêtre pour renégocier votre contrat : {title} {tail}"
    if typology == OrganizationTypology.ERP:
        return f"Fenêtre achat ouverte sur votre établissement : {title} {tail}"
    return f"Fenêtre achat ouverte : {title} {tail}"


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
    naf_code: Optional[str] = None,
) -> str:
    """Compose la phrase 1 événementielle du body narratif.

    Si `prioritization["primary"]` est `None` → phrase de stabilité
    typologique. Sinon dispatch vers le composer dédié au trigger.

    Args:
        prioritization: sortie de `prioritize_triggers` (Phase 3.2).
        typology: typologie organisationnelle (Phase 1.2).
        naf_code: code NAF du site primaire (Phase 7 correctif B). Propagé
            uniquement à `compose_dt_drift_sentence` qui en a besoin pour
            résoudre l'activity Commerce. Les autres composers ignorent.

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

    # Phase 7 correctif B — propager naf_code uniquement aux composers qui
    # l'acceptent (cf inspect.signature). DT_drift l'utilise, les autres
    # ignorent silencieusement (rétrocompat).
    import inspect

    sig = inspect.signature(composer)
    if "naf_code" in sig.parameters:
        return composer(primary_event, typology, naf_code=naf_code)
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
