"""
PROMEOS — Bill Intelligence priority score helper (Phase L22.1).

Helper SoT cardinal pour mapping severity → priority_score UI flat.

Phase L22.1 audit fix P1 (audit Phase L22 reviewer #2 + reviewer #1 finding 2 +
reconciliation reviewer #1 finding 3) :

Avant L22.1 :
- `_PRIORITY_SCORE_MAP` (90/70/50/30) HARDCODED dans `routes/billing.py:1548`
  → violation doctrine "no fake code" Phase L8.1
- `_severity_to_priority_score` helper de calcul dans `routes/`
  → violation règle d'or "zero business logic in routes/"

Après L22.1 :
- 4 clés YAML SoT `BILL_PRIORITY_SCORE_{CRITICAL,HIGH,MEDIUM,LOW}` lazy-load
- Module `services/bill_intelligence/priority.py` cardinal cross-callsites
- `routes/billing.py` import depuis services (zero business logic)

Indépendance déclarée vs `patrimoine_impact._SEV_BASE` :
- `_PRIORITY_SCORE_MAP` (billing) : score UI flat lookup direct (30-90)
- `_SEV_BASE` (patrimoine) : composante d'un score composite multi-facteurs
  (severity + framework_weight + eur_bucket → 0-100)
Les deux échelles sont DIFFÉRENTES BY DESIGN. Tri cross-source dans
AnomaliesPage frontend = P1 architectural différé Phase L23 (decision
architect-helios requise pour échelle commune).
"""

from __future__ import annotations

from typing import Optional

from config.regulatory_sources_loader import get_term_value


_PRIORITY_SCORE_MAP_CACHE: Optional[dict[str, int]] = None


def _load_priority_score_map() -> dict[str, int]:
    """Lazy-load YAML SoT 4 clés BILL_PRIORITY_SCORE_*.

    Returns:
        dict {"CRITICAL": 90, "HIGH": 70, "MEDIUM": 50, "LOW": 30}
    """
    return {
        "CRITICAL": int(get_term_value("BILL_PRIORITY_SCORE_CRITICAL")),
        "HIGH": int(get_term_value("BILL_PRIORITY_SCORE_HIGH")),
        "MEDIUM": int(get_term_value("BILL_PRIORITY_SCORE_MEDIUM")),
        "LOW": int(get_term_value("BILL_PRIORITY_SCORE_LOW")),
    }


def severity_to_priority_score(severity: Optional[str]) -> int:
    """Phase L22.1 — Helper SoT priority_score depuis severity.

    Phase L21.1 cumul : normalise UPPERCASE en interne (avant : silencieux
    fallback LOW si lowercase passé) → robuste cross-callsite.

    Args:
        severity: severity string (case-insensitive, None toléré)

    Returns:
        int score UI 30-90. Default LOW (30) si severity inconnue/None.
    """
    global _PRIORITY_SCORE_MAP_CACHE
    if _PRIORITY_SCORE_MAP_CACHE is None:
        _PRIORITY_SCORE_MAP_CACHE = _load_priority_score_map()
    return _PRIORITY_SCORE_MAP_CACHE.get((severity or "").upper(), 30)
