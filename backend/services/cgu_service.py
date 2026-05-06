"""
PROMEOS — CGU service (Sprint C-8 Phase 8.1).

Source unique vérité versions CGU acceptables — fix dette
D-Sprint-C7-CGU-Referentiel-Central-001 P1 reportée Phase 7.7 → Sprint C-8.

Référentiel central : `backend/config/cgu_referentiel.yaml`.
Cohérent ADR-019 PATCH endpoints RGPD + CNIL article 7 (preuve d'origine forte).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

_CGU_YAML_PATH = Path(__file__).resolve().parent.parent / "config" / "cgu_referentiel.yaml"


@lru_cache(maxsize=1)
def _load_cgu_referentiel() -> dict:
    """Charge le référentiel CGU YAML (cache LRU pour performance)."""
    if not _CGU_YAML_PATH.exists():
        raise RuntimeError(f"CGU referentiel YAML introuvable : {_CGU_YAML_PATH}")
    with _CGU_YAML_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def reload_cgu_referentiel() -> dict:
    """Force le rechargement du référentiel (tests + admin runtime updates)."""
    _load_cgu_referentiel.cache_clear()
    return _load_cgu_referentiel()


def get_current_cgu_version() -> str:
    """Retourne la version CGU avec statut='actuel' (cardinal CNIL).

    Raises:
        RuntimeError si aucune version 'actuel' trouvée dans le référentiel.
    """
    config = _load_cgu_referentiel()
    for v in config.get("versions", []):
        if v.get("statut") == "actuel":
            return v["version"]
    raise RuntimeError("Aucune version CGU avec statut='actuel' trouvée dans cgu_referentiel.yaml")


def is_valid_cgu_version(version: Optional[str]) -> bool:
    """True si `version` correspond à une version connue (actuel ou archive).

    Cardinal validation Phase 7.3 PATCH endpoints RGPD : empêche stockage AuditLog
    avec version arbitraire (CNIL article 7 preuve d'origine forte = version vérifiable).

    None ou empty string → False (rejet — cgu_version doit être explicite).
    """
    if not version:
        return False
    config = _load_cgu_referentiel()
    return any(v.get("version") == version for v in config.get("versions", []))


def list_active_cgu_versions() -> list[dict]:
    """Liste toutes les versions CGU connues (actuel + archives) — pour endpoint admin."""
    config = _load_cgu_referentiel()
    return list(config.get("versions", []))
