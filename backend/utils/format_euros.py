"""M2-6.B.pdf — Format € français formel pour PDF COMEX.

Cohérent avec `frontend/src/utils/money.js::formatEuros(value, 'full')` :
même séparateur (NBSP), même règle « 0 = mesure valide » (≠ NULL), même tiret
cadratin U+2014 pour les manques.

Q23=A : format strict `'47 500 €'` (PAS le compact `'47,5 k€'` réservé UI).
Le PDF COMEX est un livrable signature — la précision pleine prime sur la
densité visuelle.

NBSP utilisé : U+00A0 (no-break space standard) — ReportLab et la plupart
des polices PDF le rendent correctement. Le FE utilise U+202F (narrow
NBSP) qui est plus typographique mais moins universel en PDF.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Union

# NBSP standard U+00A0 — compatible toutes polices PDF.
NBSP = " "
# Tiret cadratin U+2014 (cohérent FE money.js).
DASH = "—"


def format_euros_full(value: Optional[Union[float, Decimal, int, str]]) -> str:
    """Formate un montant en EUR au format FR formel.

    Args:
        value : montant à formater. `None`, `NaN`, valeurs non finies → `'—'`.

    Returns:
        `'47 500 €'` (NBSP entre milliers et entre montant/symbole),
        `'0 €'` pour zéro (valide ≠ NULL),
        `'—'` pour absence de mesure.

    Examples:
        >>> format_euros_full(47500)
        '47\\u00a0500\\u00a0€'
        >>> format_euros_full(3200.50)  # round half up → 3201
        '3\\u00a0201\\u00a0€'
        >>> format_euros_full(None)
        '—'
        >>> format_euros_full(0)
        '0\\u00a0€'
    """
    if value is None:
        return DASH

    try:
        decimal_value = Decimal(str(value))
    except (ValueError, ArithmeticError):
        return DASH

    if not decimal_value.is_finite():
        return DASH

    # Round half up — standard financier formel pour PDF signature.
    rounded = int(decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    abs_value = abs(rounded)
    sign = "-" if rounded < 0 else ""

    str_value = str(abs_value)
    if len(str_value) <= 3:
        formatted = str_value
    else:
        # Insère NBSP tous les 3 chars en partant de la droite.
        parts: list[str] = []
        remaining = str_value
        while len(remaining) > 3:
            parts.insert(0, remaining[-3:])
            remaining = remaining[:-3]
        parts.insert(0, remaining)
        formatted = NBSP.join(parts)

    return f"{sign}{formatted}{NBSP}€"
