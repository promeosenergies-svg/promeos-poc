"""Push événementiel "+X vs S-1" — Sprint Refonte Narrative dynamique Phase 2.1.

Helper doctrinal pour décider quels deltas hebdomadaires (`weekly_deltas`
exposés par `cockpit_facts_service`) méritent un push narratif, selon
l'**Option 3.C** (silence éditorial strict) :

> Si la variation est dans le bruit statistique (< 5 % en relatif ET sous
> seuil absolu métier), on n'écrit RIEN. Mieux vaut un silence qu'une
> phrase qui dit "stable" — la stabilité se déduit de l'absence de push.

## Doctrine §11.3 — push événementiel

| Métrique | Seuil relatif | Seuil absolu | Silence si … |
|---|---|---|---|
| `exposure_eur` | 5 % | 1 k€ | rel < 5 % ET abs < 1 000 € |
| `potential_mwh_year` | 5 % | 5 MWh/an | rel < 5 % ET abs < 5 MWh/an |
| `compliance_score` | 3 % | — | rel < 3 % |
| `sites_in_drift` | — | 1 site | abs < 1 site |
| (autre métrique) | 5 % (default) | — | rel < 5 % |

Logique : silence si **tous** les seuils définis sont franchis vers le bas.
Push si au moins un seuil défini est dépassé.

## Format par typologie (Phase 1.3 lexical_templates)

- Grand groupe : "+ 18 % vs semaine précédente" (registre expert/CFO)
- Commerce : "+ 14 % vs la semaine dernière" (registre pédagogique)
- ERP : "+ 14 % vs semaine dernière" (registre pédagogique-pro)
- UNKNOWN : hérite Grand groupe (registre expert par défaut)

Ref : `docs/maquettes/narrative-sol2/PROMPT_REFONTE_NARRATIVE_DYNAMIQUE_EXECUTION.md`
Phase 2.1 + Option 3.C.
"""

from __future__ import annotations

from typing import Optional

from doctrine.naf_to_typology import OrganizationTypology

# ─── Seuils silence éditorial Option 3.C ───────────────────────────────────


# Format : (rel_threshold_pct, abs_threshold). None = pas de seuil défini.
# Silence si TOUS les seuils définis sont franchis vers le bas.
PUSH_THRESHOLDS: dict[str, tuple[Optional[float], Optional[float]]] = {
    "exposure_eur": (5.0, 1000.0),  # 5 % OR 1 k€
    "potential_mwh_year": (5.0, 5.0),  # 5 % OR 5 MWh/an
    "compliance_score": (3.0, None),  # 3 points (relatif uniquement)
    "sites_in_drift": (None, 1.0),  # 1 site (absolu uniquement)
}

# Seuil par défaut pour métrique non listée.
DEFAULT_REL_THRESHOLD_PCT: float = 5.0


def should_push_metric(
    metric_name: str,
    current: Optional[float],
    previous: Optional[float],
) -> bool:
    """Décide si on push un signal selon Option 3.C (silence éditorial strict).

    Règles silence (Option 3.C) :
    - `previous = None` ou `previous = 0` → silence (pas de baseline)
    - `current = None` → silence (métrique indisponible)
    - Variation < seuil relatif ET < seuil absolu → silence
    - Au moins un seuil défini dépassé → push

    Args:
        metric_name: nom canonique de la métrique
            (`exposure_eur` / `potential_mwh_year` / `compliance_score` /
            `sites_in_drift` / autre).
        current: valeur actuelle.
        previous: valeur S-1 (None tant que historique non seedé MVP).

    Returns:
        True si push à émettre, False si silence.

    Examples:
        >>> should_push_metric("exposure_eur", 105_000, 100_000)
        True  # +5 % et +5 k€ → significatif
        >>> should_push_metric("exposure_eur", 100_800, 100_000)
        False  # +0,8 % et +800 € → bruit
        >>> should_push_metric("compliance_score", 72, 70)
        False  # +2,9 % < 3 % → silence
        >>> should_push_metric("sites_in_drift", 4, 3)
        True  # +1 site → significatif
    """
    if previous is None or previous == 0:
        return False
    if current is None:
        return False

    delta_abs = abs(current - previous)
    rel_pct = (delta_abs / abs(previous)) * 100

    rel_threshold, abs_threshold = PUSH_THRESHOLDS.get(metric_name, (DEFAULT_REL_THRESHOLD_PCT, None))

    rel_below = rel_threshold is None or rel_pct < rel_threshold
    abs_below = abs_threshold is None or delta_abs < abs_threshold

    # Silence si tous les seuils définis sont franchis vers le bas.
    # Push si au moins un seuil défini est dépassé.
    return not (rel_below and abs_below)


def format_push_clause(
    metric_name: str,
    current: float,
    previous: float,
    typology: OrganizationTypology,
) -> str:
    """Formate la clause "+X % vs S-1" dans le ton typologique.

    Doctrine §11.3 — adapter le registre lexical au persona cible :
    - Grand groupe → "vs semaine précédente" (registre CFO expert)
    - Commerce → "vs la semaine dernière" (registre commerçant pédagogique)
    - ERP → "vs semaine dernière" (registre directeur pédagogique-pro)

    Args:
        metric_name: nom métrique (réservé pour évolutions futures —
            ex: ajouter unité dans la clause).
        current: valeur actuelle.
        previous: valeur S-1 (doit être ≠ 0 — caller doit pré-filtrer
            via `should_push_metric`).
        typology: typologie organisationnelle (Phase 1.1).

    Returns:
        Clause prête à insérer en body, ex: "+ 18 % vs semaine précédente".

    Examples:
        >>> format_push_clause("exposure_eur", 118_000, 100_000, OrganizationTypology.GRAND_GROUPE)
        '+ 18 % vs semaine précédente'
        >>> format_push_clause("potential_mwh_year", 114, 100, OrganizationTypology.COMMERCE)
        '+ 14 % vs la semaine dernière'
        >>> format_push_clause("exposure_eur", 90_000, 100_000, OrganizationTypology.ERP)
        '− 10 % vs semaine dernière'
    """
    delta = current - previous
    relative_pct = (delta / previous) * 100 if previous else 0
    direction = "+ " if delta > 0 else "− "

    if typology == OrganizationTypology.COMMERCE:
        suffix = "vs la semaine dernière"
    elif typology == OrganizationTypology.ERP:
        suffix = "vs semaine dernière"
    else:
        # GRAND_GROUPE + UNKNOWN (fallback expert)
        suffix = "vs semaine précédente"

    return f"{direction}{abs(relative_pct):.0f} % {suffix}"


__all__ = [
    "PUSH_THRESHOLDS",
    "DEFAULT_REL_THRESHOLD_PCT",
    "should_push_metric",
    "format_push_clause",
]
