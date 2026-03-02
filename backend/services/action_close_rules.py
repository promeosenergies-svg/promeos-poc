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

def check_closable(action: ActionItem, closure_justification: str = None, evidence_count: int = 0) -> dict:
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
        # Generic evidence_required gate (non-OPERAT actions)
        if getattr(action, 'evidence_required', False):
            justification = closure_justification or action.closure_justification or ""
            has_justification = len(justification.strip()) >= 10
            if evidence_count == 0 and not has_justification:
                return {
                    "closable": False,
                    "code": "EVIDENCE_REQUIRED",
                    "reason": "Preuve requise pour clôturer cette action. Joignez une pièce ou fournissez une justification (≥ 10 caractères).",
                    "has_valid_proof": False,
                    "has_justification": False,
                }
            if evidence_count == 0 and has_justification and len(justification.strip()) < 10:
                return {
                    "closable": False,
                    "code": "JUSTIFICATION_TOO_SHORT",
                    "reason": "Justification trop courte (minimum 10 caractères).",
                    "has_valid_proof": False,
                    "has_justification": False,
                }
        return {
            "closable": True,
            "code": None,
            "reason": None,
            "has_valid_proof": evidence_count > 0,
            "has_justification": False,
        }

    # Already done
    if action.status and action.status.value in ("done", "false_positive"):
        return {
            "closable": True,
            "code": None,
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
    code = None
    if not closable:
        code = "EVIDENCE_REQUIRED"
        reason = (
            "Action OPERAT : preuve validée ou justification (≥ 10 caractères) "
            "requise pour clôturer."
        )

    return {
        "closable": closable,
        "code": code,
        "reason": reason,
        "has_valid_proof": has_valid_proof,
        "has_justification": has_justification,
    }
