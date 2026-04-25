"""
PROMEOS — Base partagée entre les ParameterStore (billing) et parameters (pilotage).

Consolide ~100 LOC strictement identiques entre `services/billing_engine/
parameter_store.py` (V112) et `services/pilotage/parameters.py` (V115 Sprint 2) :

    - `ParameterResolution` : dataclass frozen `kw_only=True` avec trace d'audit
      (7 champs dont `unite` et `valid_to` tous deux `Optional`, extensibles
      sans breaking via default None).
    - `coerce_date(value)` : accepte str ISO / date / datetime / None.
    - `period_contains(at_date, valid_from, valid_to)` : test d'inclusion
      inclusive (valid_from ≤ at_date ≤ valid_to, bornes None = ouvertes).
    - `warn_unknown_once(seen_set, logger, code)` : anti-spam. Le set est
      passé en paramètre pour que billing et pilotage gardent leurs propres
      scopes isolés (évite pollution cross-module en tests parallèles).
    - `load_yaml_section(key)` : délégation `config.tarif_loader.load_tarifs()`
      (cache unique partagé, `reload_tarifs()` propagé).
    - `paris_today()` : date "aujourd'hui" forcée Europe/Paris (évite le
      bug latent UTC-vs-Paris sous Docker au tournant d'année).

Architecture : chaque ParameterStore applicatif (billing, pilotage) garde
sa propre logique de résolution (dispatch YAML par section vs liste plate +
scope scoring), son propre `KNOWN_CODES` frozenset, et sa propre façade
publique. Seul l'échafaudage commun vit ici.

Référence : review indépendant PR #231 Sprint 2 + audit pré-refactor Sprint 5b.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

_TZ_PARIS = ZoneInfo("Europe/Paris")


@dataclass(frozen=True, kw_only=True)
class ParameterResolution:
    """
    Résultat d'une résolution : valeur + trace d'audit réglementaire.

    Partagé entre billing et pilotage. `kw_only=True` + tous les champs
    extensibles `Optional = None` pour permettre l'ajout de champs futurs
    (ex. `confidence`) sans casser l'instanciation existante.

    Attributs
    ---------
    code        Code canonique du paramètre (ex. "TVA_RATE_TURPE", "CEE_BACS_EUR_M2")
    value       Valeur numérique résolue (int ou float)
    source      "db" | "yaml" | "fallback" | "missing" — origine machine-readable
    source_ref  Citation réglementaire (arrêté, CRE, Baromètre) — optionnelle
    valid_from  Date d'effet — ouverte (None) si applicable à toute l'histoire
    valid_to    Date de fin — ouverte (None) si paramètre encore en vigueur
    unite       Unité métier ("EUR/kWh", "h/an", etc.) — optionnelle pour billing
    scope       Dict scope effectivement résolu (ex. {"archetype": "BUREAU_STANDARD"})
    """

    code: str
    value: float
    source: str
    source_ref: Optional[str] = None
    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    unite: Optional[str] = None
    scope: dict[str, str] = field(default_factory=dict)

    def to_trace(self) -> dict[str, Any]:
        """Export dict pour injection dans payload hypotheses.parametres_sources."""
        return {
            "code": self.code,
            "value": self.value,
            "source": self.source,
            "source_ref": self.source_ref,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_to": self.valid_to.isoformat() if self.valid_to else None,
            "unite": self.unite,
            "scope": self.scope,
        }


def coerce_date(value: Any) -> Optional[date]:
    """
    Normalise en `date` depuis str ISO ("2026-01-01"), date, datetime, None.

    Retourne None si valeur vide ou non parseable (plutôt que raise —
    évite d'interrompre un batch de résolution sur une entrée YAML corrompue).
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def period_contains(
    at_date: date,
    valid_from: Optional[date],
    valid_to: Optional[date],
) -> bool:
    """
    True si `at_date ∈ [valid_from, valid_to]` (bornes inclusives).

    Bornes None = ouvertes (paramètre applicable à toute l'histoire côté
    début ou encore en vigueur côté fin). Utilisé par les 2 moteurs de
    résolution pour filtrer les candidats avant ranking.
    """
    if valid_from is not None and at_date < valid_from:
        return False
    if valid_to is not None and at_date > valid_to:
        return False
    return True


def warn_unknown_once(
    seen_set: set[str],
    logger: logging.Logger,
    code: str,
    module_tag: str = "parameter_store",
) -> None:
    """
    Log `warning` une seule fois par code inconnu (anti-spam).

    Le `seen_set` est passé en paramètre — billing et pilotage gardent
    chacun leur propre set module-level pour éviter qu'un test pilotage
    pollue silencieusement le cache billing (et inversement).

    Args
    ----
    seen_set   Set module-level du caller (append-only, thread-safe suffisant
               pour FastAPI sync)
    logger     Logger du caller (pour propagation du contexte "billing" ou
               "pilotage" dans les logs structurés)
    code       Code inconnu observé
    module_tag Label ajouté au message de log pour traçabilité
    """
    if code in seen_set:
        return
    seen_set.add(code)
    logger.warning("%s: code inconnu '%s'", module_tag, code)


def load_yaml_section(key: str) -> Any:
    """
    Charge une section du YAML `tarifs_reglementaires.yaml` via le loader
    unique `config.tarif_loader.load_tarifs` (cache `@lru_cache` partagé).

    Le test `reload_tarifs()` (côté billing) purge automatiquement les 2
    consommateurs (billing + pilotage). Retourne la valeur par défaut
    `None` si la section est absente — le caller décide du fallback.
    """
    from config.tarif_loader import load_tarifs

    return load_tarifs().get(key)


def paris_today() -> date:
    """
    Date "aujourd'hui" forcée Europe/Paris (pas UTC naïf).

    Fix le bug latent sous Docker UTC : à 01h Paris un 1er janvier,
    `date.today()` retourne J-1 UTC et rate un `valid_from: AAAA-01-01`.
    Doit être utilisé par tous les callers qui résolvent `at_date=None`.
    """
    return datetime.now(_TZ_PARIS).date()
