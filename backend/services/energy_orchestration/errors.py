"""
PROMEOS — Erreurs standardisées /api/energy/* (Sprint P1.S2b).

Centralise les codes d'erreur stables et la génération de correlation_id
pour les endpoints d'orchestration énergie.

Doctrine :
- code : identifiant stable consommable par FE pour i18n / branchements.
- message : phrase lisible côté API doc.
- hint : action recommandée pour résoudre (FE ou opérateur).
- correlation_id : UUID pour cross-référence logs / support.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, Request

from schemas.energy_orchestration import EnergyErrorPayload


# Codes erreur stables (préfixe ENERGY_*).
CODE_GRANULARITY_TOO_FINE = "ENERGY_GRANULARITY_TOO_FINE"
CODE_GRANULARITY_UNKNOWN = "ENERGY_GRANULARITY_UNKNOWN"
CODE_PERIOD_INVALID = "ENERGY_PERIOD_INVALID"
CODE_SCOPE_INVALID = "ENERGY_SCOPE_INVALID"
CODE_SCOPE_ID_REQUIRED = "ENERGY_SCOPE_ID_REQUIRED"
CODE_RANGE_INVALID = "ENERGY_RANGE_INVALID"
CODE_COMPARE_INVALID = "ENERGY_COMPARE_INVALID"
CODE_DAYS_INSUFFICIENT = "ENERGY_DAYS_INSUFFICIENT"


def get_correlation_id(request: Optional[Request] = None) -> str:
    """Retourne le correlation_id depuis le header X-Correlation-Id si présent,
    sinon génère un UUID v4."""
    if request is not None:
        header_id = request.headers.get("X-Correlation-Id")
        if header_id:
            return header_id
        # Compat avec d'autres conventions courantes.
        for alt in ("X-Request-Id", "X-Trace-Id"):
            v = request.headers.get(alt)
            if v:
                return v
    return str(uuid.uuid4())


def energy_error(
    *,
    code: str,
    message: str,
    hint: Optional[str] = None,
    request: Optional[Request] = None,
    status_code: int = 400,
) -> HTTPException:
    """Construit une HTTPException avec payload standardisé EnergyErrorPayload.

    Le `detail` est un dict (compatible FastAPI) qui matche le schéma
    `EnergyErrorPayload`. Le `correlation_id` est extrait des headers si
    présents, sinon généré.
    """
    payload = EnergyErrorPayload(
        code=code,
        message=message,
        hint=hint,
        correlation_id=get_correlation_id(request),
    )
    return HTTPException(status_code=status_code, detail=payload.model_dump())
