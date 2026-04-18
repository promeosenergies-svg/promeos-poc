"""
SolContext builder : construit SolContextData depuis une request FastAPI.

Org-scopé strict via `services.scope_utils.resolve_org_id` (DÉCISION P0-4 :
pattern body call, pas Depends). Utilisé par routes Sol Phase 4.

Lookup des 3 dernières actions Sol de l'org (mémoire courte agentique)
via `SolActionLog` avec filter_by(org_id) + order_by(created_at DESC) limit 3.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from models.sol import SolActionLog, SolOrgPolicy

from .schemas import AgenticMode, SolContextData
from .utils import generate_correlation_id, now_utc

if TYPE_CHECKING:
    from fastapi import Request
    from sqlalchemy.orm import Session


# ─────────────────────────────────────────────────────────────────────────────
# Org policy defaults
# ─────────────────────────────────────────────────────────────────────────────


# Si aucune SolOrgPolicy n'existe pour l'org, on applique ce profil
# "preview_only strict" — le plus conservateur : Sol propose et prévisualise,
# mais n'exécute jamais automatiquement.
_DEFAULT_ORG_POLICY: dict[str, Any] = {
    "agentic_mode": AgenticMode.PREVIEW_ONLY.value,
    "dry_run_until": None,
    "dual_validation_threshold": None,
    "confidence_threshold": 0.85,
    "grace_period_seconds": 900,
    "tone_preference": "vous",
}


def _load_or_default_policy(db: "Session", org_id: int) -> dict[str, Any]:
    """Lit SolOrgPolicy pour `org_id` ou retourne les defaults conservateurs."""
    policy: SolOrgPolicy | None = (
        db.query(SolOrgPolicy).filter(SolOrgPolicy.org_id == org_id).one_or_none()
    )
    if policy is None:
        return dict(_DEFAULT_ORG_POLICY)

    return {
        "agentic_mode": policy.agentic_mode,
        "dry_run_until": policy.dry_run_until.isoformat() if policy.dry_run_until else None,
        "dual_validation_threshold": (
            float(policy.dual_validation_threshold)
            if policy.dual_validation_threshold is not None
            else None
        ),
        "confidence_threshold": float(policy.confidence_threshold),
        "grace_period_seconds": policy.grace_period_seconds,
        "tone_preference": policy.tone_preference,
    }


def _load_last_3_actions(db: "Session", org_id: int) -> list[dict[str, Any]]:
    """
    Retourne les 3 dernières actions Sol pour l'org (mémoire courte agentique).

    Utilisé par le planner Phase 3 pour éviter les propositions en double
    et personnaliser le ton selon l'historique récent.
    """
    rows = (
        db.query(SolActionLog)
        .filter(SolActionLog.org_id == org_id)
        .order_by(SolActionLog.created_at.desc())
        .limit(3)
        .all()
    )
    return [
        {
            "correlation_id": r.correlation_id,
            "intent_kind": r.intent_kind,
            "action_phase": r.action_phase,
            "outcome_code": r.outcome_code,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Builder principal
# ─────────────────────────────────────────────────────────────────────────────


def build_sol_context(
    request: "Request",
    auth: Any,
    db: "Session",
    *,
    correlation_id: str | None = None,
    scope_site_id: int | None = None,
) -> SolContextData:
    """
    Construit un SolContextData complet depuis une request FastAPI.

    Args:
        request: Request FastAPI (pour resolve_org_id via scope headers).
        auth: AuthContext du get_optional_auth (peut être None en DEMO_MODE).
        db: SQLAlchemy Session.
        correlation_id: réutiliser un correlation_id existant (chain
            propose→preview→confirm→execute) ou laisser None pour en générer un.
        scope_site_id: restreindre au site courant si pertinent (optionnel).

    Returns:
        SolContextData org-scopé, prêt pour planner/validator.

    Raises:
        HTTPException 401 si org non résoluble (DEMO_MODE=false).
    """
    # Import lazy pour éviter cycle / charge startup
    from services.scope_utils import resolve_org_id

    org_id = resolve_org_id(request, auth, db)

    # user_id : depuis auth si présent, sinon depuis DemoState en DEMO_MODE
    user_id = _resolve_user_id(auth, db, org_id)

    return SolContextData(
        org_id=org_id,
        user_id=user_id,
        correlation_id=correlation_id or generate_correlation_id(),
        now=now_utc(),
        org_policy=_load_or_default_policy(db, org_id),
        scope_site_id=scope_site_id,
        last_3_actions=_load_last_3_actions(db, org_id),
    )


def _resolve_user_id(auth: Any, db: "Session", org_id: int) -> int:
    """
    Résout user_id depuis auth. En DEMO_MODE sans auth, fallback sur
    le premier user de l'organisation (seed demo) ou 0 (sentinel système).
    """
    # Cas 1 : auth résolu (JWT valide) → user_id disponible
    if auth is not None and getattr(auth, "user_id", None):
        return int(auth.user_id)

    # Cas 2 : DEMO_MODE — fallback sur premier user de l'org
    from models.iam import User, UserOrgRole

    first_user = (
        db.query(User)
        .join(UserOrgRole, UserOrgRole.user_id == User.id)
        .filter(UserOrgRole.org_id == org_id)
        .order_by(User.id)
        .first()
    )
    if first_user:
        return int(first_user.id)

    # Cas 3 : aucun user dans l'org (devrait pas arriver post-seed)
    # Retourne 0 comme sentinel "système" — SolActionLog.user_id FK users.id
    # validera côté DB (mais 0 peut ne pas exister → erreur explicite).
    return 0


__all__ = [
    "build_sol_context",
]
