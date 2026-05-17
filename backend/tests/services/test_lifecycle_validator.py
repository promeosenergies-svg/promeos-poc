"""M2-4.4 — Tests du lifecycle_validator (matrice de transitions doctrine V4).

Tests purs (pas de DB, pas d'app) : la fonction lève `HTTPException`.
"""

import pytest
from fastapi import HTTPException

from models.v4.enums import ClosureReason, LifecycleState
from services.v4.lifecycle_validator import validate_lifecycle_transition

LS = LifecycleState
CR = ClosureReason

# Transitions légales sans closure_reason.
_LEGAL_NO_REASON = [
    (LS.NEW, LS.TRIAGED),
    (LS.TRIAGED, LS.PLANNED),
    (LS.PLANNED, LS.IN_PROGRESS),
]
# États depuis lesquels closed est légal (avec closure_reason).
_LEGAL_CLOSE_FROM = [LS.NEW, LS.TRIAGED, LS.PLANNED, LS.IN_PROGRESS]
# Transitions interdites (saut, retour arrière, depuis terminal).
_ILLEGAL = [
    (LS.NEW, LS.PLANNED),
    (LS.NEW, LS.IN_PROGRESS),
    (LS.TRIAGED, LS.IN_PROGRESS),
    (LS.TRIAGED, LS.NEW),
    (LS.IN_PROGRESS, LS.TRIAGED),
    (LS.CLOSED, LS.NEW),
    (LS.CLOSED, LS.TRIAGED),
]


@pytest.mark.parametrize("current,target", _LEGAL_NO_REASON)
def test_legal_transition_no_reason_ok(current, target):
    validate_lifecycle_transition(current, target, None)  # ne lève pas


@pytest.mark.parametrize("current", _LEGAL_CLOSE_FROM)
def test_legal_close_with_user_reason_ok(current):
    validate_lifecycle_transition(current, LS.CLOSED, CR.RESOLVED)  # ne lève pas


@pytest.mark.parametrize("current,target", _ILLEGAL)
def test_illegal_transition_422(current, target):
    with pytest.raises(HTTPException) as exc:
        validate_lifecycle_transition(current, target, None)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "LIFECYCLE_TRANSITION_FORBIDDEN"


@pytest.mark.parametrize("current", _LEGAL_CLOSE_FROM)
def test_close_without_reason_422(current):
    with pytest.raises(HTTPException) as exc:
        validate_lifecycle_transition(current, LS.CLOSED, None)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "CLOSURE_REASON_REQUIRED"


def test_reason_on_non_close_422():
    with pytest.raises(HTTPException) as exc:
        validate_lifecycle_transition(LS.NEW, LS.TRIAGED, CR.RESOLVED)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "CLOSURE_REASON_UNEXPECTED"


@pytest.mark.parametrize("reason", [CR.MERGED_DUPLICATE, CR.RESOLVED_VIA_RECURRENCE, CR.EXPIRED])
def test_system_only_reason_refused_422(reason):
    """🛡️ Les 3 closure_reasons système sont refusées sur un PATCH /lifecycle."""
    with pytest.raises(HTTPException) as exc:
        validate_lifecycle_transition(LS.NEW, LS.CLOSED, reason)
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "CLOSURE_REASON_SYSTEM_ONLY"


def test_current_state_accepts_str():
    """current_state passé en str (valeur lue en DB) est coercé en enum."""
    validate_lifecycle_transition("new", LS.TRIAGED, None)  # ne lève pas
