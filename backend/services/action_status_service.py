"""
PROMEOS — Helper de clôture d'action unifié (Sprint CX 2.5 hardening, F1).

Centralise la logique "action passée à DONE" pour garantir que toute voie
qui ferme une action fire l'event CX_ACTION_FROM_INSIGHT (driver IAR + T2V).

Avant ce helper : seul routes/actions.py::patch_action logguait l'event.
Les auto-closures (CEE advance_step, action_hub sync, etc.) bypass-aient
le logger → KPIs IAR/T2V sous-comptés massivement.

RÈGLES :
- Ne commit PAS la transaction. Le caller doit commit/flush.
- log_cx_event (avec F2 hardening) utilise flush() interne → n'engage pas
  la transaction parente non plus.
- emit_event=False pour les seeds (demo_seed, scripts) qui ne doivent pas
  polluer les stats CX.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from middleware.cx_logger import log_cx_event
from models import ActionItem, ActionStatus


def mark_action_done(
    db: Session,
    action: ActionItem,
    user_id: Optional[int] = None,
    emit_event: bool = True,
    reason: Optional[str] = None,
) -> None:
    """
    Marque une action DONE + set closed_at (si None) + fire CX_ACTION_FROM_INSIGHT.

    Args:
        db: Session SQLAlchemy (le caller doit commit/flush après).
        action: L'ActionItem à clôturer.
        user_id: User qui déclenche la clôture (None pour auto-close backend).
        emit_event: False pour les seeds (pas de pollution stats CX).
        reason: Contexte optionnel pour le detail_json de l'event.
    """
    action.status = ActionStatus.DONE
    if action.closed_at is None:
        action.closed_at = datetime.now(timezone.utc)

    if emit_event and action.org_id is not None:
        log_cx_event(
            db,
            action.org_id,
            user_id,
            "CX_ACTION_FROM_INSIGHT",
            {
                "action_id": action.id,
                "source_type": action.source_type.value if action.source_type else None,
                "reason": reason or "mark_done",
            },
        )
