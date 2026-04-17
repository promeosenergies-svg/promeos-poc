"""
PROMEOS — CX Event Logger
Réutilise AuditLog model (V117) avec event_type préfixé CX_*
Fire-and-forget : les erreurs sont loggées mais ne bloquent pas la requête.
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from models.iam import AuditLog, UserOrgRole

logger = logging.getLogger(__name__)

CX_EVENT_TYPES = frozenset(
    {
        "CX_INSIGHT_CONSULTED",
        "CX_MODULE_ACTIVATED",
        "CX_REPORT_EXPORTED",
        "CX_ONBOARDING_COMPLETED",
        "CX_ACTION_FROM_INSIGHT",
        "CX_DASHBOARD_OPENED",
    }
)


def log_cx_event(
    db: Session,
    org_id: int,
    user_id: Optional[int],
    event_type: str,
    context: Optional[dict] = None,
) -> None:
    """
    Fire-and-forget log d'un event CX_*.

    Sprint CX 2.5 hardening (F2) : utilise db.flush() au lieu de db.commit()
    pour ne pas engager la transaction parente du caller. Si le handler
    parent raise après cet appel, les modifs pending ne sont PAS persistées.
    Le commit/rollback final est la responsabilité du caller (route handler).

    Sprint CX 2.5 hardening (S1) : si user_id fourni, valide que l'utilisateur
    est bien membre de org_id via UserOrgRole avant de logger. Protège
    DEMO_MODE contre forge de X-Org-Id par un user authentifié.
    """
    if event_type not in CX_EVENT_TYPES:
        return

    # S1 hardening : validation membership user → org
    if user_id is not None and org_id is not None:
        is_member = (
            db.query(UserOrgRole.id).filter(UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id).first()
        )
        if not is_member:
            logger.warning(
                "CX event rejeté : user_id=%s pas membre de org_id=%s (event=%s)",
                user_id,
                org_id,
                event_type,
            )
            return

    try:
        entry = AuditLog(
            user_id=user_id,
            action=event_type,
            resource_type="cx_event",
            resource_id=str(org_id),
            detail_json=json.dumps({"org_id": org_id, **(context or {})}),
        )
        db.add(entry)
        db.flush()  # F2 : ne commit pas la transaction parente
    except Exception:
        # Pas de rollback : on ne casse pas la transaction du caller.
        logger.debug("CX event logging failed for %s", event_type, exc_info=True)
