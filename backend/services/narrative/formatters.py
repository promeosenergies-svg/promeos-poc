"""Formatters narrative — Sprint Refonte Narrative dynamique Phase 7 correctif D.

SoT canonique pour les helpers de formatage utilisés par les modules
narrative (sentence_composer, persona_context, narrative_generator).

## Pourquoi ce module ?

Audit final 2026-05-01 P1 : doublon `_format_eur_short` (persona_context) vs
`_fmt_eur_short` (narrative_generator) avec **conventions divergentes** :

| Helper | Séparateur décimal | Fallback None |
|---|---|---|
| `_format_eur_short` (persona_context) | virgule FR | `—` (tiret cadratin) |
| `_fmt_eur_short` (narrative_generator) | point anglo-saxon | `0 €` |

Risque : un même Narrative mêle les deux → CFO voit `12,7 k€` dans la
mention italique mais `12.7 k€` dans le KPI hero juste à côté. Incohérence
visuelle.

## Convention canonique (Phase 7)

- **Séparateur décimal** : virgule FR (`12,7 k€`)
- **Séparateur milliers** : espace insécable (`12 345 €`)
- **Fallback None** : `—` (tiret cadratin) — signal clair "donnée absente"
- **Zéro** : `0 €` (différencie de None — montant nul ≠ inconnu)

## Migration

- `persona_context._format_eur_short` → ré-export depuis ce module ✓ Phase 7
- `narrative_generator._fmt_eur_short` → migration progressive Phase 7.bis
  (callsites multiples dans week_cards/KPIs — risque régression cosmétique
  les nombreux tests). Coexistence acceptée short-term.

Ref : audit final 2026-05-01 P1.
"""

from __future__ import annotations

from typing import Optional


def format_eur_short(value: Optional[float]) -> str:
    """Formatage € court canonique FR (k€, M€).

    Convention :
    - virgule décimale FR (`12,7 k€`)
    - séparateur milliers espace (`1 234 567 €`)
    - fallback None → `—` (donnée absente)
    - zéro → `0 €` (montant nul ≠ inconnu)

    Examples:
        >>> format_eur_short(12700)
        '12,7 k€'
        >>> format_eur_short(1_500_000)
        '1,5 M€'
        >>> format_eur_short(450)
        '450 €'
        >>> format_eur_short(0)
        '0 €'
        >>> format_eur_short(None)
        '—'
    """
    if value is None:
        return "—"
    if value == 0:
        return "0 €"
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f} M€".replace(".", ",")
    if abs_value >= 1_000:
        return f"{value / 1_000:.1f} k€".replace(".", ",")
    return f"{round(value)} €"


def format_eur_thousand(value: float) -> str:
    """Formatage € avec séparateur milliers (sans abréviation k€/M€).

    Examples:
        >>> format_eur_thousand(1234)
        '1 234 €'
        >>> format_eur_thousand(1234567)
        '1 234 567 €'
    """
    rounded = round(value)
    formatted = f"{rounded:,}".replace(",", " ")
    return f"{formatted} €"


def format_pct_short(value: float) -> str:
    """Formatage % court avec signe explicite (plus / minus Unicode).

    Examples:
        >>> format_pct_short(14.3)
        '+14 %'
        >>> format_pct_short(-12.7)
        '−13 %'
        >>> format_pct_short(0)
        '0 %'
    """
    rounded = round(value)
    if rounded > 0:
        return f"+{rounded} %"
    if rounded < 0:
        return f"−{abs(rounded)} %"
    return "0 %"


__all__ = [
    "format_eur_short",
    "format_eur_thousand",
    "format_pct_short",
]
