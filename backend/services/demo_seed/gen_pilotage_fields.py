"""
PROMEOS - Seed des champs Pilotage Flex Ready (R) sur les sites existants.

Populise `archetype_code` et `puissance_pilotable_kw` sur les sites du pack
demo courant. Priorite :
    1. Nom canonique connu (Carrefour Montreuil, Tour Haussmann, Entrepot Rungis)
    2. Fallback `TypeSite` -> archetype Barometre Flex 2026

Idempotent : n'ecrase pas les valeurs deja renseignees manuellement.

Source calibration : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
Les dicts canoniques et fallback vivent dans services/pilotage/constants.py
(co-localises avec ARCHETYPE_CALIBRATION_2024).
"""

from __future__ import annotations

import unicodedata
from typing import Optional

from sqlalchemy.orm import Session

from models import Site
from services.pilotage.constants import (
    CANONICAL_SITE_PILOTAGE,
    TYPESITE_ARCHETYPE_FALLBACK,
)


def _normalise_nom(nom: Optional[str]) -> str:
    """Normalise un nom de site pour matching canonique (casse + accents)."""
    if not nom:
        return ""
    # NFKD decompose les accents, puis on drop les marques non-ASCII.
    stripped = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode("ascii")
    return stripped.lower().strip()


def _resolve(site: Site) -> Optional[tuple[str, float]]:
    """Retourne (archetype_code, puissance_pilotable_kw) pour un site, ou None."""
    canonical = CANONICAL_SITE_PILOTAGE.get(_normalise_nom(site.nom))
    if canonical is not None:
        return canonical
    type_value = getattr(site.type, "value", None)
    if type_value:
        return TYPESITE_ARCHETYPE_FALLBACK.get(type_value)
    return None


def seed_pilotage_fields(db: Session, sites: list[Site]) -> dict:
    """
    Populise archetype_code + puissance_pilotable_kw sur une liste de sites.

    Idempotent : ne touche pas les sites ou les deux champs sont deja renseignes.
    Si un seul des deux champs est renseigne, on complete l'autre seulement.

    Returns:
        {"updated": N, "skipped_full": M, "unresolved": K}
    """
    stats = {"updated": 0, "skipped_full": 0, "unresolved": 0}

    for site in sites:
        has_arch = bool(site.archetype_code)
        has_kw = site.puissance_pilotable_kw is not None

        if has_arch and has_kw:
            stats["skipped_full"] += 1
            continue

        resolution = _resolve(site)
        if resolution is None:
            stats["unresolved"] += 1
            continue

        archetype, kw = resolution
        if not has_arch:
            site.archetype_code = archetype
        if not has_kw:
            site.puissance_pilotable_kw = kw
        stats["updated"] += 1

    if stats["updated"]:
        db.flush()
    return stats
