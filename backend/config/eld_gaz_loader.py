"""
PROMEOS — ELD Gaz Loader (Sprint C-3 Phase 3.6)

Loader pour `eld_gaz_referentiel.yaml` — référentiel 21 ELD France
(GRDF national + 20 ELD locales).

Pattern reproduit identique à `regulatory_sources_loader.py` (Phase 3.2,
Step 18 tarif_loader) :
- `@lru_cache(maxsize=1)` sur `load_eld_gaz()` — 1 lecture YAML par process
- `reload_eld_gaz()` pour invalider le cache (tests, hot-patch)
- Helpers typés : `get_eld_by_code`, `is_grdf`, `is_eld_locale`,
  `list_eld_codes`

Usage cascade : `cascade_recompute_service._is_grd_eld_locale(grd_code)`
sur modification `DeliveryPoint.grd_code` → trigger Bill Intelligence
recheck (Phase 3.6 ce module + cascade).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml


_YAML_PATH = Path(__file__).resolve().parent / "eld_gaz_referentiel.yaml"


# ─── Loaders ─────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def load_eld_gaz() -> dict:
    """Charge le YAML une fois par process. Cache invalidable via reload_*.

    Raises:
        FileNotFoundError: si `eld_gaz_referentiel.yaml` introuvable.
        yaml.YAMLError: si YAML mal formé.
    """
    if not _YAML_PATH.exists():
        raise FileNotFoundError(f"eld_gaz_referentiel.yaml introuvable: {_YAML_PATH}")
    return yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))


def reload_eld_gaz() -> dict:
    """Pour tests / hot-patch : invalide le cache et recharge."""
    load_eld_gaz.cache_clear()
    return load_eld_gaz()


# ─── API publique ────────────────────────────────────────────────────────────


def get_eld_by_code(code: str) -> Optional[dict]:
    """Récupère une ELD par son code (ex: "GRDF", "REGAZ", "GREENALP").

    Returns:
        dict avec keys : code, label, type, perimetre, site_web,
        contact_consentement, notes. None si code inconnu.
    """
    if not code:
        return None
    data = load_eld_gaz()
    return data.get("eld", {}).get(code)


def list_eld_codes() -> list[str]:
    """Liste tous les codes ELD disponibles (utile diagnostic / tests)."""
    data = load_eld_gaz()
    return sorted(data.get("eld", {}).keys())


def is_grdf(code: str) -> bool:
    """True si le code = GRDF (GRD national).

    Helper : détermine si un site est sur le réseau national vs ELD locale.
    Impact : bascule tarif ATRD7 GRDF vs barème ELD spécifique.
    """
    return code == "GRDF"


def is_eld_locale(code: str) -> bool:
    """True si le code est une ELD locale (≠ GRDF national).

    Helper : ELD locale = barème tarifaire spécifique + consentement
    DataConnect/ADICT généralement absent (pas dans le périmètre GRDF API).
    """
    if not code:
        return False
    eld = get_eld_by_code(code)
    if eld is None:
        return False
    return eld.get("type") == "ELD_LOCALE"


def is_known_eld(code: str) -> bool:
    """True si le code est dans le référentiel (GRDF ou ELD locale).

    Helper : valide qu'un `DeliveryPoint.grd_code` est un opérateur connu.
    """
    return code is not None and code in load_eld_gaz().get("eld", {})


def get_eld_count_by_type() -> dict[str, int]:
    """Retourne le nombre d'ELD par type (diagnostic UI / tests)."""
    data = load_eld_gaz()
    counts: dict[str, int] = {}
    for eld in data.get("eld", {}).values():
        t = eld.get("type", "UNKNOWN")
        counts[t] = counts.get(t, 0) + 1
    return counts
