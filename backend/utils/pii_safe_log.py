"""
PROMEOS — Helper PII-safe logging (Phase L34.5 audit fix Medium SECURITY).

PROMEOS-SEC-2026-018 : auparavant les PRM Enedis (14 chiffres) et autres
identifiants client (PCE GRDF, SIREN/SIRET, emails) étaient logués en clair
dans data_staging/engine.py:110, connectors/enedis_dataconnect.py:269 et
ailleurs. RGPD HELIOS § 5 (minimisation) impose la pseudonymisation.

Usage canonical :
    from utils.pii_safe_log import hash_prm
    logger.info("Token refreshed pour PRM %s", hash_prm(prm))
    # → "Token refreshed pour PRM prm:a1b2c3d4"

Le hash sha256 tronqué (8 hex chars) est :
- non-réversible (pas de PRM clair en logs)
- déterministe (un PRM = même hash) → grep cross-logs reste possible pour
  debugging par opérateur autorisé qui dispose du PRM
- non identifiant (8 hex = 32 bits collisions à 65k PRMs, mais l'opérateur
  qui dispose du PRM peut le confirmer via DB)

Ne sert PAS à anonymiser durablement (CNIL : pseudonymisation stricte
réversible si le hash + PRM sont conservés ensemble). Sert uniquement à
éviter les fuites accidentelles dans logs de prod / agrégation Datadog /
exports SIEM.
"""

from __future__ import annotations

import hashlib
from typing import Optional


def hash_prm(prm: Optional[str]) -> str:
    """Hash un PRM Enedis / PCE GRDF / identifiant client pour log PII-safe.

    Args:
        prm: PRM 14 chiffres (ou PCE 14 chiffres GRDF) ou identifiant similaire.

    Returns:
        "prm:<8 hex chars>" si prm renseigné, "prm:none" sinon.
        Le préfixe "prm:" rend le hash searchable et explicite dans les logs.
    """
    if not prm:
        return "prm:none"
    digest = hashlib.sha256(str(prm).encode("utf-8")).hexdigest()[:8]
    return f"prm:{digest}"


def hash_pii(value: Optional[str], prefix: str = "pii") -> str:
    """Hash générique PII (email, SIREN, etc.) pour log.

    Args:
        value: valeur PII à hasher.
        prefix: préfixe taggué dans le log (ex. "siren", "email").

    Returns:
        "<prefix>:<8 hex chars>" si value renseigné, "<prefix>:none" sinon.
    """
    if not value:
        return f"{prefix}:none"
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:8]
    return f"{prefix}:{digest}"
