"""
PROMEOS - Pilotage ParameterStore léger (V120+ Sprint 2 Item 6).

Expose `get_pilotage_param(code, at_date=None, archetype=None)` pour les
constantes MVP du module Pilotage (ROI Flex Ready® + scoring portefeuille).

Pattern : inspiré du `ParameterStore` billing V112 (résolution YAML versionnée
par `valid_from` + scope), mais scopé sur les paramètres pilotage uniquement.
Les paramètres pilotage vivent dans la section `pilotage_flex_ready:` du YAML
`tarifs_reglementaires`.

Depuis Sprint 5b, la dataclass `ParameterResolution` + helpers (`coerce_date`,
`warn_unknown_once`, `paris_today`, `load_yaml_section`) sont partagés avec
billing via `utils.parameter_store_base`. La logique de résolution (scope
scoring archetype, liste plate YAML) reste spécifique pilotage.

Principes :
- Une seule source de vérité : `config/tarifs_reglementaires.yaml`
- Versioning par `valid_from` (sélection la plus récente ≤ at_date)
- Résolution de scope : scope exact (archetype=X) prioritaire sur wildcard "*"
- Fallback défensif : si YAML indisponible/corrompu, utiliser `default` fourni
  par l'appelant + logger.warning (pas de crash prod)
- Traçabilité : chaque résolution porte `source`, `valid_from`, `unite`
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional, Union

from utils.parameter_store_base import (
    ParameterResolution,
    coerce_date,
    load_yaml_section,
    paris_today,
    warn_unknown_once,
)

logger = logging.getLogger(__name__)

# Codes connus du référentiel pilotage — documentés pour éviter fautes de frappe.
KNOWN_PILOTAGE_CODES = frozenset(
    {
        # ROI Flex Ready® (roi_flex_ready.py)
        "HEURES_FENETRES_FAVORABLES_AN",
        "SPREAD_MOYEN_EUR_MWH",
        "SPREAD_POINTE_EUR_MWH",
        "JOURS_EFFACEMENT_PAR_AN",
        "CEE_BACS_EUR_M2",
        # Scoring portefeuille (portefeuille_scoring.py)
        "HEURES_FAVORABLES_AN",  # scope par archetype
        "SPREAD_EUR_PAR_KWH",
    }
)

# Cache des codes inconnus déjà loggés (module-level, isolé de billing) — évite spam.
_unknown_codes_seen: set[str] = set()

# Alias rétrocompat : code externe peut avoir importé `PilotageParameterResolution`.
# La dataclass est maintenant `ParameterResolution` dans `utils.parameter_store_base`.
PilotageParameterResolution = ParameterResolution


def _load_pilotage_entries() -> list[dict]:
    """Charge la section `pilotage_flex_ready:` du YAML. [] si indisponible."""
    entries = load_yaml_section("pilotage_flex_ready") or []
    if not isinstance(entries, list):
        logger.warning("pilotage.parameters: section 'pilotage_flex_ready' malformée")
        return []
    return entries


def _match_scope(entry_scope: dict, archetype: Optional[str]) -> Optional[int]:
    """
    Retourne un score de match (plus élevé = plus précis) ou None si incompat.

    - scope exact archetype=X et archetype=X → score 2 (priorité)
    - scope wildcard archetype="*" (peu importe archetype appelé) → score 1
    - incompatible → None
    """
    entry_archetype = entry_scope.get("archetype") if entry_scope else None
    if entry_archetype is None or entry_archetype == "*":
        return 1
    if archetype is not None and entry_archetype == archetype:
        return 2
    return None


def _resolve(
    code: str,
    at_date: date,
    archetype: Optional[str],
) -> Optional[ParameterResolution]:
    """Parcourt les entrées YAML et sélectionne la plus précise/récente."""
    entries = _load_pilotage_entries()
    if not entries:
        return None

    # Candidats : mêmes code, scope compatible, valid_from ≤ at_date
    scored: list[tuple[int, date, dict]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("code") != code:
            continue
        scope_dict = entry.get("scope") or {}
        scope_score = _match_scope(scope_dict, archetype)
        if scope_score is None:
            continue
        vfrom = coerce_date(entry.get("valid_from"))
        if vfrom and vfrom > at_date:
            continue
        # Date default : "2000-01-01" si absente (applicable tout le temps)
        effective_vfrom = vfrom or date(2000, 1, 1)
        scored.append((scope_score, effective_vfrom, entry))

    if not scored:
        return None

    # Tri : scope_score DESC (précis avant wildcard) puis valid_from DESC
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    best_score, best_vfrom, best_entry = scored[0]

    valeur = best_entry.get("valeur")
    if valeur is None:
        return None

    return ParameterResolution(
        code=code,
        value=valeur,
        source="yaml",
        source_ref=best_entry.get("source"),
        valid_from=coerce_date(best_entry.get("valid_from")),
        unite=best_entry.get("unite"),
        scope=dict(best_entry.get("scope") or {}),
    )


def get_pilotage_param(
    code: str,
    at_date: Optional[date] = None,
    archetype: Optional[str] = None,
    default: Optional[Union[float, int]] = None,
) -> ParameterResolution:
    """
    Résout un paramètre pilotage (YAML → fallback → missing).

    Parameters
    ----------
    code : str
        Code canonique (ex. "HEURES_FENETRES_FAVORABLES_AN").
    at_date : date | None
        Date d'effet à considérer. Default = aujourd'hui Europe/Paris.
    archetype : str | None
        Archetype canonique (ex. "COMMERCE_ALIMENTAIRE"). Si None, seul le
        scope wildcard "*" est considéré.
    default : float | int | None
        Valeur de repli si YAML indispo ET code inconnu. Pour fallback
        défensif en prod : si fourni, retourne ce default avec source="fallback".

    Returns
    -------
    ParameterResolution (jamais None) : value + trace.
    Si code inconnu et pas de default → value=0, source="missing" (+ warning).
    """
    if code not in KNOWN_PILOTAGE_CODES:
        warn_unknown_once(_unknown_codes_seen, logger, code, module_tag="pilotage.parameters")

    if at_date is None:
        at_date = paris_today()
    if isinstance(at_date, datetime):
        at_date = at_date.date()

    resolved = _resolve(code, at_date, archetype)
    if resolved is not None:
        logger.debug(
            "pilotage_param %s = %s from %s (scope=%s)",
            code,
            resolved.value,
            resolved.source_ref,
            resolved.scope,
        )
        return resolved

    # Fallback défensif si default fourni (évite crash prod si YAML corrompu)
    if default is not None:
        logger.warning(
            "pilotage.parameters: %s introuvable au YAML, fallback default=%s",
            code,
            default,
        )
        return ParameterResolution(
            code=code,
            value=default,
            source="fallback",
            source_ref="hardcoded fallback (YAML indisponible ou code absent)",
            scope={"archetype": archetype or "*"},
        )

    logger.warning(
        "pilotage.parameters: aucune valeur pour code=%s archetype=%s at=%s",
        code,
        archetype,
        at_date,
    )
    return ParameterResolution(
        code=code,
        value=0,
        source="missing",
        scope={"archetype": archetype or "*"},
    )


def get_pilotage_value(
    code: str,
    at_date: Optional[date] = None,
    archetype: Optional[str] = None,
    default: Optional[Union[float, int]] = None,
) -> Union[float, int]:
    """Raccourci : retourne uniquement la valeur (ou default si missing)."""
    res = get_pilotage_param(code, at_date=at_date, archetype=archetype, default=default)
    if res.source == "missing" and default is not None:
        return default
    return res.value
