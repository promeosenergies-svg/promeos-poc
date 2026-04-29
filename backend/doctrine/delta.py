"""PROMEOS — Helper doctrinal canonique : delta hebdomadaire push événementiel.

Phase 3.bis.b sprint refonte cockpit dual sol2 (29/04/2026). Hoist du helper
`_weekly_delta_struct` (créé Phase 3.3 dans `cockpit_facts_service.py`) vers
la couche doctrine — single SoT pour tout calcul delta hebdo Sol2.

Contrat canonique : doctrine §11.3 push événementiel hebdomadaire. Toute
métrique évoluant J vs J+1 dans la Vue Exécutive doit produire ce payload.

Ref :
- PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §4.B Phase 3.3
- Audit /simplify reuse fin Phase 3 (P1) — promotion canonique
"""

from __future__ import annotations

from typing import Literal, Optional, TypedDict, Union

# ── Direction canonique (Literal type pour validation statique) ─────────────
WeeklyDeltaDirection = Literal["up", "down", "stable", "unknown"]


class WeeklyDeltaPayload(TypedDict):
    """Structure canonique exposée par chaque métrique sous push hebdo.

    Champs :
        current : valeur actuelle (None si métrique non disponible)
        previous : valeur S-1 (None tant que historique non seedé)
        delta_absolute : différence absolue (current − previous), None si
                          previous est None
        delta_pct : ratio (current − previous) / previous, None si previous
                    null ou zero
        direction : "up" / "down" / "stable" / "unknown"
        unit : suffixe lisible affichage ("€", "MWh/an", "sites", "pts")
    """

    current: Optional[Union[int, float]]
    previous: Optional[Union[int, float]]
    delta_absolute: Optional[Union[int, float]]
    delta_pct: Optional[float]
    direction: WeeklyDeltaDirection
    unit: str


def weekly_delta_struct(
    current_value: Optional[Union[int, float]],
    previous_value: Optional[Union[int, float]] = None,
    *,
    unit: str = "",
) -> WeeklyDeltaPayload:
    """Construit le payload canonique d'un delta hebdomadaire push.

    Doctrine §11.3 (push événementiel) — structure exposée par chaque métrique
    sentinel de la Vue Exécutive (Exposition, Potentiel, Sites en dérive,
    Score conformité, etc.).

    Cas null-safe :
        - current_value None → tous champs None, direction='unknown'
        - previous_value None → current renseigné, deltas None,
          direction='unknown' (MVP avant seed historique)
        - previous_value 0 → delta_pct=None (division par zéro évitée)

    Args:
        current_value: valeur actuelle de la métrique
        previous_value: valeur S-1 (None tant que non disponible)
        unit: suffixe lisible affichage (ex: "k€", "MWh/an")

    Returns:
        WeeklyDeltaPayload TypedDict (6 champs canoniques garantis)
    """
    if current_value is None:
        return {
            "current": None,
            "previous": None,
            "delta_absolute": None,
            "delta_pct": None,
            "direction": "unknown",
            "unit": unit,
        }
    if previous_value is None:
        return {
            "current": current_value,
            "previous": None,
            "delta_absolute": None,
            "delta_pct": None,
            "direction": "unknown",
            "unit": unit,
        }
    delta_abs = current_value - previous_value
    delta_pct = (delta_abs / previous_value) if previous_value else None
    if delta_abs > 0:
        direction = "up"
    elif delta_abs < 0:
        direction = "down"
    else:
        direction = "stable"
    return {
        "current": current_value,
        "previous": previous_value,
        "delta_absolute": delta_abs,
        "delta_pct": round(delta_pct, 4) if delta_pct is not None else None,
        "direction": direction,
        "unit": unit,
    }


__all__ = [
    "WeeklyDeltaDirection",
    "WeeklyDeltaPayload",
    "weekly_delta_struct",
]
