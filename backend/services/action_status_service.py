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

from middleware.cx_logger import CX_ACTION_FROM_INSIGHT, log_cx_event
from models import ActionItem, ActionSourceType, ActionStatus

# Issue #225 IAR refinement (Option A whitelist source_type) :
# CX_ACTION_FROM_INSIGHT doit fire UNIQUEMENT pour les actions issues d'un
# insight/recommandation système PROMEOS, pas pour les actions manuelles
# créées par l'utilisateur (qui ne mesurent pas la capacité du système à
# convertir un insight en action).
#
# Exclus : MANUAL (l'user tape son propre titre, pas tracé côté CX_INSIGHT_CONSULTED)
# Inclus : tous les autres source_types qui correspondent à une détection
# ou une recommandation générée par le système.
INSIGHT_DRIVEN_SOURCE_TYPES: frozenset[ActionSourceType] = frozenset(
    {
        ActionSourceType.COMPLIANCE,
        ActionSourceType.CONSUMPTION,
        ActionSourceType.BILLING,
        ActionSourceType.PURCHASE,
        ActionSourceType.INSIGHT,
        ActionSourceType.SEGMENTATION,
        ActionSourceType.COPILOT,
        ActionSourceType.PILOTAGE,
    }
)


def mark_action_done(
    db: Session,
    action: ActionItem,
    user_id: Optional[int] = None,
    emit_event: bool = True,
    reason: Optional[str] = None,
) -> None:
    """
    Marque une action DONE + set closed_at (si None) + fire CX_ACTION_FROM_INSIGHT.

    Issue #225 (IAR refinement) : fire l'event UNIQUEMENT si le source_type
    appartient à INSIGHT_DRIVEN_SOURCE_TYPES (exclut MANUAL qui pollue IAR).

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

    if not emit_event or action.org_id is None:
        return

    # Issue #225 : filtre whitelist source_type pour sémantique IAR propre
    if action.source_type not in INSIGHT_DRIVEN_SOURCE_TYPES:
        return

    log_cx_event(
        db,
        action.org_id,
        user_id,
        CX_ACTION_FROM_INSIGHT,
        {
            "action_id": action.id,
            "source_type": action.source_type.value if action.source_type else None,
            "reason": reason or "mark_done",
        },
    )
