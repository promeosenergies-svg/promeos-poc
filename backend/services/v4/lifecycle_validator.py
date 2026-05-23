"""M2-4.4 — State machine lifecycle de l'ActionCenterItem.

Doctrine V4 : 5 états, 6 `ClosureReason` dont 3 user-facing (3 system-only
refusées en 422). Matrice câblée en dur — toute évolution = commit code + tests.

Conformité P0 2026-05-23 — ajout `validate_evidence_required_for_closure` :
un item de `kind=EVIDENCE_REQUEST` OU de `domain=CONFORMITE` ne peut pas être
clôturé en `RESOLVED` sans au moins une `Evidence` vérifiée (verified_at ≠ NULL).
Empêche le bypass "résolu avec preuve" sans aucune preuve réelle.
"""

from typing import Optional, Union

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.v4.enums import ClosureReason, Domain, Kind, LifecycleState

# (état_courant, état_cible) → closure_reason requise (toujours user-facing si True).
_ALLOWED_TRANSITIONS: dict[tuple[LifecycleState, LifecycleState], bool] = {
    (LifecycleState.NEW, LifecycleState.TRIAGED): False,
    (LifecycleState.NEW, LifecycleState.CLOSED): True,  # early dismissal
    (LifecycleState.TRIAGED, LifecycleState.PLANNED): False,
    (LifecycleState.TRIAGED, LifecycleState.CLOSED): True,
    (LifecycleState.PLANNED, LifecycleState.IN_PROGRESS): False,
    (LifecycleState.PLANNED, LifecycleState.CLOSED): True,
    (LifecycleState.IN_PROGRESS, LifecycleState.CLOSED): True,
}

# closure_reasons acceptées sur un PATCH /lifecycle user-driven.
_USER_FACING_CLOSURE_REASONS: frozenset[ClosureReason] = frozenset(
    {ClosureReason.RESOLVED, ClosureReason.DISMISSED, ClosureReason.NOT_APPLICABLE}
)
# closure_reasons posées UNIQUEMENT par les services système (Q9-B, SLA) — refusées API.
_SYSTEM_ONLY_CLOSURE_REASONS: frozenset[ClosureReason] = frozenset(
    {ClosureReason.MERGED_DUPLICATE, ClosureReason.RESOLVED_VIA_RECURRENCE, ClosureReason.EXPIRED}
)


def validate_lifecycle_transition(
    current_state: Union[LifecycleState, str],
    new_state: LifecycleState,
    closure_reason: Optional[ClosureReason],
) -> None:
    """Valide une transition de cycle de vie proposée.

    `current_state` peut être un str (valeur lue en DB) ou un `LifecycleState` —
    coercé en enum. Lève `HTTPException(422)` si :
    - la transition (courant → cible) n'est pas dans la matrice ;
    - `closure_reason` requise mais absente ;
    - `closure_reason` fournie alors que la cible n'est pas `closed` ;
    - `closure_reason` est une valeur system-only.
    """
    current = LifecycleState(current_state)
    key = (current, new_state)

    if key not in _ALLOWED_TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "LIFECYCLE_TRANSITION_FORBIDDEN",
                "message": f"Transition {current.value} → {new_state.value} not allowed",
                "hint": "Closed is terminal; no backward nor skip transitions",
            },
        )

    requires_reason = _ALLOWED_TRANSITIONS[key]

    if requires_reason and closure_reason is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CLOSURE_REASON_REQUIRED",
                "message": f"Transition to {new_state.value} requires a closure_reason",
                "hint": "Provide one of: resolved, dismissed, not_applicable",
            },
        )

    if not requires_reason and closure_reason is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CLOSURE_REASON_UNEXPECTED",
                "message": f"closure_reason must be null when transitioning to {new_state.value}",
                "hint": "closure_reason only applies to transitions into 'closed'",
            },
        )

    if closure_reason in _SYSTEM_ONLY_CLOSURE_REASONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CLOSURE_REASON_SYSTEM_ONLY",
                "message": f"closure_reason '{closure_reason.value}' is system-only",
                "hint": (
                    "User-facing values: resolved, dismissed, not_applicable. "
                    "System values are set automatically by background services."
                ),
            },
        )


# ─── Conformité P0 2026-05-23 — preuve requise pour clôture RESOLVED ────────


def _item_requires_evidence(item) -> bool:
    """Vrai si l'item exige une preuve vérifiée avant clôture RESOLVED.

    Doctrine : un item est "preuve-dépendant" si :
    - `kind == EVIDENCE_REQUEST` (par définition demande de preuve), OU
    - `domain == CONFORMITE` (DT/BACS/APER/SMÉ/BEGES — exige une preuve
      réglementaire opposable).

    Pour les autres combinaisons, la clôture RESOLVED reste possible sans
    preuve attachée (anomalie résolue par correction terrain, action
    purement opérationnelle, etc.).
    """
    kind = getattr(item, "kind", None)
    domain = getattr(item, "domain", None)
    return kind == Kind.EVIDENCE_REQUEST.value or domain == Domain.CONFORMITE.value


def validate_evidence_required_for_closure(
    db: Session,
    item,
    closure_reason: Optional[ClosureReason],
) -> None:
    """Refuse une clôture RESOLVED sans preuve vérifiée si l'item l'exige.

    Doctrine Conformité P0 2026-05-23 :
    - Clôture `DISMISSED` ou `NOT_APPLICABLE` → toujours autorisée (l'item
      n'est pas considéré comme "résolu avec preuve").
    - Clôture `RESOLVED` sur un item preuve-dépendant (cf.
      `_item_requires_evidence`) → exige au moins une `Evidence` avec
      `verified_at IS NOT NULL` rattachée.

    Lève `HTTPException(422)` avec code `CLOSURE_REQUIRES_EVIDENCE` + message
    FR canonique si la preuve manque. Sinon retourne `None` (no-op).

    Wiring : appelée par `routes/v4/action_center.py:transition_item_lifecycle`
    juste après `validate_lifecycle_transition`.
    """
    if closure_reason != ClosureReason.RESOLVED:
        return  # DISMISSED / NOT_APPLICABLE / autre = pas de check preuve

    if not _item_requires_evidence(item):
        return  # item non preuve-dépendant (ANOMALY hors conformite, etc.)

    # Import local pour éviter dépendance circulaire models/services
    from models.v4.evidences import Evidence

    verified_evidence_exists = (
        db.query(Evidence.id).filter(Evidence.action_item_id == item.id, Evidence.verified_at.isnot(None)).first()
        is not None
    )

    if not verified_evidence_exists:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "CLOSURE_REQUIRES_EVIDENCE",
                "message": (
                    "Impossible de clôturer cet item en « résolu » sans preuve vérifiée. "
                    "Cet item exige une preuve réglementaire opposable avant clôture."
                ),
                "hint": (
                    "Téléversez une preuve via POST /items/{item_id}/evidences puis "
                    "faites-la vérifier avant de retenter la clôture."
                ),
                "kind": getattr(item, "kind", None),
                "domain": getattr(item, "domain", None),
                "blocking": True,
            },
        )
