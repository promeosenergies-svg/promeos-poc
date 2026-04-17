"""
PROMEOS — CX Event Logger
Réutilise AuditLog model (V117) avec event_type préfixé CX_*
Fire-and-forget : les erreurs sont loggées mais ne bloquent pas la requête.
"""

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from models.iam import AuditLog

logger = logging.getLogger(__name__)

CX_EVENT_TYPES = frozenset(
    {
        "CX_INSIGHT_CONSULTED",
        "CX_MODULE_ACTIVATED",
        "CX_REPORT_EXPORTED",
        "CX_ONBOARDING_COMPLETED",
        "CX_ACTION_FROM_INSIGHT",
    }
)


def log_cx_event(
    db: Session,
    org_id: int,
    user_id: Optional[int],
    event_type: str,
    context: Optional[dict] = None,
) -> None:
    if event_type not in CX_EVENT_TYPES:
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
        db.commit()
    except Exception:
        db.rollback()
        logger.debug("CX event logging failed for %s", event_type, exc_info=True)
