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

import re
from typing import Literal, Optional, Union

from doctrine.naf_to_typology import OrganizationTypology

# Phase 4.bis3 — typage strict du tone (ValidationError si valeur inconnue).
# Aligné sur narrative_generator.NarrativeTone enum values.
ToneValue = Literal["positive", "neutral", "tension", "critical"]
VALID_TONES: frozenset = frozenset({"positive", "neutral", "tension", "critical"})


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


# ─── Garde-fou numérique Phase 4.bis3 (audit CX bug crédibilité) ───────────


# Score adjacent ≥ ce seuil → on n'applique pas la dégradation tonale
# CRITICAL/TENSION sur "stable"/"favorable" (sinon contradiction visible
# avec le chiffre cité juste à côté). Ex: "Score 80/100, stable" en CRITICAL
# devient "Score 80/100, écart significatif" — incohérent.
NUMERIC_GUARD_SCORE_THRESHOLD: int = 70

# Marqueurs où le garde-fou s'applique : ceux où l'effet tonal est de
# DÉGRADER une formulation neutre (incompatible avec un score positif).
_NUMERIC_GUARDED_MARKERS: frozenset = frozenset({"stable", "favorable"})

# Regex pour détecter "score X/100" avec X capturé.
_SCORE_RE = re.compile(r"score\s+(\d{1,3})\s*/\s*100", re.IGNORECASE)


def _has_high_score_nearby(body: str) -> bool:
    """Détecte un score X/100 ≥ NUMERIC_GUARD_SCORE_THRESHOLD dans le body.

    Phase 4.bis3 audit CX : si on a "score 80/100" et qu'on s'apprête à
    dégrader "stable" → "écart significatif" en CRITICAL, le résultat
    "score 80/100, écart significatif" est une contradiction visible
    qui décrédibilise la narrative. On skip dans ce cas.
    """
    for match in _SCORE_RE.finditer(body):
        try:
            score = int(match.group(1))
            if score >= NUMERIC_GUARD_SCORE_THRESHOLD:
                return True
        except ValueError:
            continue
    return False


def apply_tone_variation(
    body: str,
    tone: Union[ToneValue, str],
    typology: Optional[OrganizationTypology] = None,
) -> str:
    """Applique la variation lexicale au body narratif selon le tone.

    Args:
        body: texte narratif (peut contenir plusieurs phrases concaténées).
        tone: l'un de "positive" / "neutral" / "tension" / "critical"
            (cf NarrativeTone enum dans narrative_generator). Phase 4.bis3 :
            valeur inconnue → return body inchangé (fail-safe).
        typology: typologie organisationnelle (réservé V2 — différenciation
            tonale par typologie : commerce plus pédagogique, ERP plus
            institutionnel, etc.).

    Returns:
        Body avec marqueurs remplacés par leur variante tonale.
        - tone inconnu ou "neutral" → body inchangé
        - garde-fou numérique : si score ≥ 70 dans body, on ne dégrade pas
          "stable"/"favorable" en CRITICAL/TENSION (anti-contradiction).

    Examples:
        >>> apply_tone_variation(
        ...     "patrimoine bien positionné. vigilance requise.",
        ...     "critical",
        ... )
        'patrimoine en écart critique. écart critique à arbitrer.'

        >>> apply_tone_variation("Score 78/100, stable.", "tension")
        # Score 78 ≥ 70 → garde-fou numérique active, "stable" préservé
        'Score 78/100, stable.'

        >>> apply_tone_variation("Score 50/100, stable.", "tension")
        # Score 50 < 70 → tension applique
        'Score 50/100, sous vigilance.'
    """
    if not body:
        return body

    # Phase 4.bis3 — fail-safe sur tone inconnu (V1 acceptait str libre)
    if tone not in VALID_TONES:
        return body

    variants = TONE_LEXICAL_VARIANTS.get(tone, {})
    if not variants:
        return body

    # Phase 4.bis3 — garde-fou numérique : si score ≥ 70 dans body,
    # on skip les marqueurs "stable"/"favorable" pour TENSION/CRITICAL
    # (sinon contradiction "Score 80/100, écart significatif").
    skip_numeric_guarded = False
    if tone in ("tension", "critical") and _has_high_score_nearby(body):
        skip_numeric_guarded = True

    result = body
    # Tri par longueur descendante : remplace les marqueurs longs avant
    # les courts (évite "stable" qui mangerait "écart significatif" → "stable")
    sorted_keys = sorted(variants.keys(), key=lambda k: -len(k))
    for marker in sorted_keys:
        if skip_numeric_guarded and marker in _NUMERIC_GUARDED_MARKERS:
            continue
        replacement = variants[marker]
        result = result.replace(marker, replacement)
    return result


def get_tone_marker_count(tone: str) -> int:
    """Nombre de marqueurs définis pour un tone (couverture / debug)."""
    return len(TONE_LEXICAL_VARIANTS.get(tone, {}))


__all__ = [
    "TONE_LEXICAL_VARIANTS",
    "VALID_TONES",
    "ToneValue",
    "NUMERIC_GUARD_SCORE_THRESHOLD",
    "apply_tone_variation",
    "get_tone_marker_count",
]
