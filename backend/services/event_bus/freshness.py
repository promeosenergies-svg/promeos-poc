"""Helper TTL → freshness_status (doctrine §7.2 statuts data obligatoires).

Sprint 2 Vague C ét12d (audit Marie P0 #3 + EM P0-3) : avant ét12d les 3
détecteurs codaient `freshness_status="fresh"` en dur, sans regarder le
TTL réel des données source. Conséquence : badge §7.2 « Estimé / Stale /
Démo » jamais déclenché → faux sentiment de sécurité.

Ce helper unifie la logique de mapping `(source_system, last_updated)` →
`EventFreshnessStatus` selon les TTL canoniques par système :

  - Enedis        : 24 h (CDC J+1, contractuel SGE/DataConnect)
  - GRDF          : 48 h (relèves PCE J+2 typique)
  - invoice       : 31 j (cycle facturation mensuel)
  - GTB / IoT     : 1 h (temps réel attendu)
  - RegOps        : 7 j (OPERAT mis à jour annuellement, contrôles trim.)
  - EPEX          : 1 h (spot horaire)
  - benchmark     : 90 j (référentiel sectoriel mis à jour trimestriel)
  - manual        : pas de TTL (signal humain, toujours `fresh` côté usage)

DEMO_MODE override : si l'env `PROMEOS_DEMO_MODE=true`, retourne `"demo"`
quel que soit le calcul TTL — Marie doit voir le badge « Démo » dès qu'un
seed `helios` est actif (audit §7.2 P0).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Literal

# TTL canoniques (heures) par système source. Aligné avec
# `EventSourceSystem` Literal de `types.py` — toute évolution doit y être
# reportée et couverte par `test_event_bus_cross_stack_sync.py`.
_TTL_HOURS: dict[str, float] = {
    "Enedis": 24.0,
    "GRDF": 48.0,
    "invoice": 24.0 * 31,  # cycle mensuel
    "GTB": 1.0,
    "IoT": 1.0,
    "RegOps": 24.0 * 7,
    "EPEX": 1.0,
    "manual": float("inf"),  # signal humain : toujours frais
    "benchmark": 24.0 * 90,
}

# Multiplicateur du TTL au-delà duquel on bascule de `stale` à
# `incomplete` (donnée trop ancienne pour être actionnable).
_INCOMPLETE_FACTOR = 3.0

EventFreshnessStatusLit = Literal["fresh", "stale", "estimated", "incomplete", "demo"]


def _is_demo_mode() -> bool:
    """Lit `PROMEOS_DEMO_MODE` (cf middleware/auth.py SoT)."""
    return os.environ.get("PROMEOS_DEMO_MODE", "false").lower() == "true"


def compute_freshness(
    source_system: str,
    last_updated_at: datetime,
    *,
    now: datetime | None = None,
    is_estimated: bool = False,
) -> EventFreshnessStatusLit:
    """Mappe `(source, last_updated)` → `EventFreshnessStatus` doctrine §7.2.

    Args:
        source_system: nom du système source (cf `EventSourceSystem` Literal).
        last_updated_at: timestamp de dernière MAJ effective de la donnée.
        now: timestamp courant (injecté pour testabilité, défaut UTC now).
        is_estimated: True si la donnée est extrapolée (forward-looking
            ou lissage sur série incomplète) — court-circuite TTL pour
            renvoyer `"estimated"` (badge ambré §7.2).

    Returns:
        - `"demo"`     si `PROMEOS_DEMO_MODE=true`
        - `"estimated"` si `is_estimated=True`
        - `"fresh"`    si âge ≤ TTL système
        - `"stale"`    si TTL < âge ≤ 3×TTL
        - `"incomplete"` si âge > 3×TTL (donnée trop vieille pour décider)
    """
    if _is_demo_mode():
        return "demo"
    if is_estimated:
        return "estimated"

    if now is None:
        now = datetime.now(timezone.utc)

    # SQLAlchemy renvoie souvent un datetime naive (UTC implicite). On
    # normalise pour éviter `TypeError: can't subtract offset-naive`.
    if last_updated_at.tzinfo is None:
        last_updated_at = last_updated_at.replace(tzinfo=timezone.utc)

    ttl_hours = _TTL_HOURS.get(source_system, 24.0)  # défaut sain : 1 jour
    if ttl_hours == float("inf"):
        return "fresh"

    age = now - last_updated_at
    ttl = timedelta(hours=ttl_hours)
    if age <= ttl:
        return "fresh"
    if age <= ttl * _INCOMPLETE_FACTOR:
        return "stale"
    return "incomplete"


__all__ = ["compute_freshness", "EventFreshnessStatusLit"]
