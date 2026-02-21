"""
PROMEOS V49 — Action Close Rules
Server-side enforcement for OPERAT action closure.

An OPERAT action cannot be closed (status → done) unless:
  1) At least one KB proof linked with status ∈ {validated, decisional}, OR
  2) A closure_justification of >= 10 chars is provided.

This module is the single source of truth for closability.
"""
from sqlalchemy.orm import Session

from models import ActionItem, ActionSourceType


# ── Detection ────────────────────────────────────────────────────────────────

def is_operat_action(action: ActionItem) -> bool:
    """True if the action originates from an OPERAT insight."""
    if not action:
        return False
    return (
        action.source_type == ActionSourceType.INSIGHT
        and (action.source_id or "").startswith("operat:")
    )


# ── Proof check ──────────────────────────────────────────────────────────────

def _count_valid_proofs(action_id: int) -> int:
    """Count KB docs linked to this action with status validated or decisional."""
    try:
        from app.kb.store import KBStore
        kb = KBStore()
        result = kb.list_action_proofs(action_id)
        summary = result.get("summary", {})
        return (summary.get("validated") or 0) + (summary.get("decisional") or 0)
    except Exception:
        return 0


# ── Closability check ────────────────────────────────────────────────────────

def check_closable(action: ActionItem, closure_justification: str = None) -> dict:
    """
    Evaluate whether an OPERAT action can be closed.

    Returns:
        {
            "closable": bool,
            "reason": str | None,       # FR message if not closable
            "has_valid_proof": bool,
            "has_justification": bool,
        }
    """
    if not is_operat_action(action):
        return {
            "closable": True,
            "reason": None,
            "has_valid_proof": False,
            "has_justification": False,
        }

    # Already done
    if action.status and action.status.value in ("done", "false_positive"):
        return {
            "closable": True,
            "reason": None,
            "has_valid_proof": True,
            "has_justification": bool(action.closure_justification),
        }

    valid_proofs = _count_valid_proofs(action.id)
    has_valid_proof = valid_proofs > 0

    # Check justification: either from the request or stored on the action
    justification = closure_justification or action.closure_justification or ""
    has_justification = len(justification.strip()) >= 10

    closable = has_valid_proof or has_justification

    reason = None
    if not closable:
        reason = (
            "Action OPERAT : preuve validée ou justification (≥ 10 caractères) "
            "requise pour clôturer."
        )

    return {
        "closable": closable,
        "reason": reason,
        "has_valid_proof": has_valid_proof,
        "has_justification": has_justification,
    }
