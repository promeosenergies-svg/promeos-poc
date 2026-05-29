"""
PROMEOS — Score utilities (clamp + bounds).

Helper canonique pour bornes des scores Monitoring / Usages / Diagnostic.
Sprint Énergie P0.S1a (2026-05-29, brief P0 #1 « 108/100 » visual credibility).

Doctrine :
- Tout score métier exposé au FE DOIT être borné [0, 100].
- Pas de fallback "0" silencieux : conserver None si valeur manquante.
- Tolérance aux entrées corrompues (str non-numérique, NaN) : retourne 0.

Avant ce module, deux duplications coexistaient :
- routes/monitoring.py:_clamp_monitoring_score
- services/electric_monitoring/monitoring_orchestrator.py:_persist_snapshot
  inner _clamp_score

Refactor : ces deux sites consomment désormais `clamp_score_0_100` ci-dessous.
"""

from __future__ import annotations

import math
from typing import Optional, Union

Numeric = Union[int, float, str, None]


def clamp_score_0_100(value: Numeric, *, preserve_none: bool = True) -> Optional[int]:
    """Borne un score sur [0, 100] et retourne un entier.

    Args:
        value: valeur brute (int / float / str castable / None).
        preserve_none: si True (défaut), `None` en entrée → `None` en sortie
            (utile pour différencier "pas de donnée" de "score nul").
            Si False, `None` → `0` (compat anciens appels orchestrator).

    Returns:
        Score entier dans [0, 100], ou None si preserve_none et value=None.

    Examples:
        >>> clamp_score_0_100(108)
        100
        >>> clamp_score_0_100(-5)
        0
        >>> clamp_score_0_100(72.4)
        72
        >>> clamp_score_0_100(None)
        >>> clamp_score_0_100(None, preserve_none=False)
        0
        >>> clamp_score_0_100("abc")
        0
        >>> clamp_score_0_100(float("nan"))
        0
    """
    if value is None:
        return None if preserve_none else 0
    try:
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return 0
        return max(0, min(100, round(v)))
    except (TypeError, ValueError):
        return 0
