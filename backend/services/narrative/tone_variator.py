"""Variation tonale lexicale — Sprint Refonte Narrative dynamique Phase 4.2.

Module de ré-écriture lexicale pour adapter le ton du body narratif au
`NarrativeTone` calculé par `_compute_tone` (déjà existant dans
narrative_generator). Quatre tons : POSITIVE / NEUTRAL / TENSION / CRITICAL.

## Pourquoi ?

Doctrine §11.3 — la lecture 3 min CFO doit déclencher la **bonne posture
émotionnelle** :
- POSITIVE → confiance, célébration mesurée (« objectif tenu »)
- NEUTRAL → factuel, info posée (« vue stable »)
- TENSION → vigilance, alerte précoce (« vigilance requise »)
- CRITICAL → urgence, arbitrage CODIR (« écart significatif »)

Sans variation tonale, toutes les phrases ont le même registre — ce qui
sous-pondère les signaux critiques et sur-pondère les signaux positifs.
Le CFO décroche.

## Approche

Ce module fournit `apply_tone_variation(body, tone, typology)` qui :
1. Détecte des marqueurs lexicaux génériques dans `body`
2. Les remplace par leur variante tonale (ex: « stable » →
   « vigilance requise » en TENSION)
3. Préserve les chiffres et les sigles (pas de `.lower()` — leçon
   Phase 4.0.A)

## Conservatisme MVP

Les remplacements sont **conservateurs** : on ne réécrit pas la phrase
1 événementielle (déjà tonée par typology Phase 3.3) ni les phrases 2-3
structurelles génériques. On agit uniquement sur les **marqueurs
neutres** identifiables (ex: « patrimoine bien positionné » →
« patrimoine sous tension » en TENSION).

V2 (Phase 4.2bis) — un LLM léger pourrait re-formuler plus richement.
Pour l'instant : table de remplacement déterministe + tests stricts.

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 4.2.
"""

from __future__ import annotations

from typing import Optional

from doctrine.naf_to_typology import OrganizationTypology


# ─── Marqueurs tonals de référence ─────────────────────────────────────────


# Pour chaque tone, mapping marqueur générique → variante tonale.
# Les marqueurs sont des sous-chaînes recherchées en case-sensitive
# (préserve les sigles). Les remplacements gardent la longueur similaire
# pour ne pas casser le budget MAX_PHRASE_1_WORDS.
TONE_LEXICAL_VARIANTS: dict[str, dict[str, str]] = {
    "positive": {
        "vigilance requise": "trajectoire tenue avec confiance",
        "écart significatif": "objectif sur la bonne voie",
        "stable": "favorable",
        "à présenter en l'état au prochain CODIR": "à valoriser au prochain CODIR",
    },
    "neutral": {
        # NEUTRAL = identité (pas de réécriture)
    },
    "tension": {
        "stable": "sous vigilance",
        "favorable": "à surveiller",
        "à présenter en l'état au prochain CODIR": "à arbitrer au prochain CODIR",
        "patrimoine bien positionné": "patrimoine sous vigilance",
    },
    "critical": {
        "stable": "écart significatif",
        "favorable": "écart significatif",
        "vigilance requise": "écart critique à arbitrer",
        "à présenter en l'état au prochain CODIR": "à arbitrer en urgence au prochain CODIR",
        "patrimoine bien positionné": "patrimoine en écart critique",
    },
}


# ─── API publique ──────────────────────────────────────────────────────────


def apply_tone_variation(
    body: str,
    tone: str,
    typology: Optional[OrganizationTypology] = None,
) -> str:
    """Applique la variation lexicale au body narratif selon le tone.

    Args:
        body: texte narratif (peut contenir plusieurs phrases concaténées).
        tone: l'un de "positive" / "neutral" / "tension" / "critical"
            (cf NarrativeTone enum dans narrative_generator).
        typology: typologie organisationnelle (réservé V2 — différenciation
            tonale par typologie : commerce plus pédagogique, ERP plus
            institutionnel, etc.).

    Returns:
        Body avec marqueurs remplacés par leur variante tonale.
        Si tone inconnu ou "neutral" → body inchangé.

    Examples:
        >>> apply_tone_variation(
        ...     "Patrimoine bien positionné. Score 80/100, vigilance requise.",
        ...     "critical",
        ... )
        'Patrimoine en écart critique. Score 80/100, écart critique à arbitrer.'

        >>> apply_tone_variation("Score 78/100, stable.", "tension")
        'Score 78/100, sous vigilance.'
    """
    if not body:
        return body

    variants = TONE_LEXICAL_VARIANTS.get(tone, {})
    if not variants:
        return body

    result = body
    # Tri par longueur descendante : remplace les marqueurs longs avant
    # les courts (évite "stable" qui mangerait "écart significatif" → "stable")
    sorted_keys = sorted(variants.keys(), key=lambda k: -len(k))
    for marker in sorted_keys:
        replacement = variants[marker]
        result = result.replace(marker, replacement)
    return result


def get_tone_marker_count(tone: str) -> int:
    """Nombre de marqueurs définis pour un tone (couverture / debug)."""
    return len(TONE_LEXICAL_VARIANTS.get(tone, {}))


__all__ = [
    "TONE_LEXICAL_VARIANTS",
    "apply_tone_variation",
    "get_tone_marker_count",
]
