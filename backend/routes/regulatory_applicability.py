"""PROMEOS — Endpoint `/api/regulatory/applicability` (Vague A.6).

Référence : `docs/adr/ADR-024-moteur-assujettissement.md` §7.

Endpoint d'inspection du moteur d'assujettissement. Consommé par :
    - le drawer "Mon cadre applicable" (frontend `<CadreApplicable />` D.3)
    - les builders Synthèse Stratégique (Vague C, en interne)
    - les tests intégration (smoke vs HELIOS)

Org-scoping : obligatoire via `resolve_org_id` (P0 production).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from regulatory.applicability_service import (
    compute_applicability,
    compute_patrimoine_maturity,
)
from regulatory.applicability_types import RuleCode
from regulatory.rules_catalog import RULES_VERSIONS
from services.scope_utils import resolve_org_id


_logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/regulatory", tags=["Regulatory"])


@router.get("/applicability")
def get_applicability(
    request: Request,
    site_id: Optional[int] = None,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
) -> dict:
    """Renvoie l'état d'assujettissement v1.0 pour l'organisation courante.

    Args:
        request: requête FastAPI (utilisée pour scope cookie/header).
        site_id: filtre optionnel pour un site spécifique.
        db: session SQLAlchemy injectée.
        auth: contexte d'auth optionnel (mode démo léger).

    Returns:
        dict JSON-ready :
          {
            "applicability": {
              "DT":    [<RuleApplicability.to_dict>, ...],
              "BACS":  [...],
              ...
            },
            "maturity": 0.71,
            "rules_versions": { "DT": "DT-2019-771-...", ... },
            "computed_at": "2026-05-13T10:00:00+00:00",
            "org_id": 1
          }
    """
    org_id = resolve_org_id(request, auth, db)

    site_ids = [site_id] if site_id is not None else None
    applicability = compute_applicability(db, org_id, site_ids=site_ids)
    maturity = compute_patrimoine_maturity(db, org_id)

    payload_applicability = {
        rule.value: [entry.to_dict() for entry in entries] for rule, entries in applicability.items()
    }
    payload_versions = {rule.value: version for rule, version in RULES_VERSIONS.items()}

    return {
        "applicability": payload_applicability,
        "maturity": maturity,
        "rules_versions": payload_versions,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "org_id": org_id,
    }
