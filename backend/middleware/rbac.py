"""M2-3.B — V4 RBAC wrapper aligned with V4 Role enum.

Provides `require_v4_role(*allowed_roles: Role)` factory that respects the
existing JWT auth flow but lets V4 routes choose their own role allowlist
without depending on the legacy `require_admin` (which enforces only `admin`).

Architecture decisions Sprint M2-3.B (validated by Amine) :

1. **Option B** : `_get_auth_payload` reuses the new `get_jwt_payload` JWT-only
   helper (decode + validate signature/expiry, no DB lookup, no role enforce).
   Granularité 401 vs DEMO_MODE preserved.

2. **Mapping centralisé** : `_LEGACY_TO_V4_ROLE` translates 11 PROMEOS legacy
   `UserRole` values (dg_owner, energy_manager, auditeur, ...) to 4 V4 `Role`
   values (admin/user/viewer/system). Maintained in 1 place — when the JWT
   issuer eventually emits Role.value natively (future sprint), the mapping
   collapses to identity (or this layer is removed in 1 line).

3. **Default least privilege** : unknown legacy role → `viewer` + warning log
   (révèle les rôles oubliés sans casser l'app).

Cohérent ADR-027 §4-6 (RBAC) + Q13-B inviolable (additif, ne touche pas
auth.py legacy except for ajout de `get_jwt_payload`).
"""

import logging
from collections.abc import Callable
from typing import Optional

from fastapi import Depends, HTTPException, status

from middleware.auth import get_jwt_payload
from models.v4.enums import Role

logger = logging.getLogger("promeos.security.rbac")


# ──────────────────────────────────────────────────────────────────────────
# Mapping legacy UserRole (11 valeurs PROMEOS métier) → V4 Role (4 valeurs)
# ──────────────────────────────────────────────────────────────────────────
# Source : backend/models/enums.py:446 UserRole(str, enum.Enum)
# Validation Amine 2026-05-15 (Sprint M2-3.B).
#
# Quand le JWT émettra Role.value natif (futur sprint), remplacer cette table
# par identity ou retirer cette couche entièrement.

_LEGACY_TO_V4_ROLE: dict[str, str] = {
    # admin : gouvernance plateforme
    "dg_owner": "admin",
    "dsi_admin": "admin",
    # user : lecture + écriture sur scope
    "daf": "user",
    "acheteur": "user",
    "resp_conformite": "user",
    "energy_manager": "user",
    "resp_immobilier": "user",
    "pmo_acc": "user",
    # viewer : lecture seule
    "resp_site": "viewer",  # discutable : pourrait passer "user" si écrit sur son site
    "prestataire": "viewer",
    "auditeur": "viewer",
}


def _translate_role(legacy_role: str) -> str:
    """Maps legacy UserRole values to V4 Role values.

    Defaults to 'viewer' (least privilege) for unknown roles + emits a WARNING
    log to révéler les rôles legacy non mappés (debug pilot + non-régression).

    Args:
        legacy_role: valeur string du claim 'role' du JWT (ex: 'dg_owner').

    Returns:
        V4 Role.value (admin/user/viewer/system) — toujours défini.
    """
    if legacy_role in _LEGACY_TO_V4_ROLE:
        return _LEGACY_TO_V4_ROLE[legacy_role]

    logger.warning(
        "rbac.unknown_legacy_role",
        extra={
            "legacy_role": legacy_role,
            "fallback_v4_role": "viewer",
            "hint": (
                "Add this legacy role to backend/middleware/rbac.py "
                "_LEGACY_TO_V4_ROLE table if it should map to a different V4 role."
            ),
        },
    )
    return "viewer"


def _get_auth_payload(
    payload: Optional[dict] = Depends(get_jwt_payload),
) -> Optional[dict]:
    """Adapter dependency : récupère le payload JWT-only et traduit le role legacy.

    - DEMO_MODE bypass : payload=None → retourne None (preserve existing demo UX).
    - Sinon : translate `payload['role']` legacy → V4 via `_translate_role`,
      réécrit le dict en place et retourne.

    Note : `get_jwt_payload` (au-dessus) handle déjà 401 (no-token hors DEMO,
    invalid token). Ici on traduit juste le role pour V4.
    """
    if payload is None:
        return None  # DEMO_MODE bypass

    legacy = payload.get("role", "")
    payload["role"] = _translate_role(legacy)
    return payload


# ──────────────────────────────────────────────────────────────────────────
# Public API : require_v4_role factory
# ──────────────────────────────────────────────────────────────────────────


def require_v4_role(*allowed_roles: Role) -> Callable:
    """FastAPI dependency factory : autorise la requête seulement si le JWT
    porte un rôle (après mapping V4) ∈ `allowed_roles`.

    Comportement :
    - Pas de JWT (hors DEMO_MODE)         → 401 (via get_jwt_payload)
    - DEMO_MODE bypass (payload=None)     → autorisé
    - JWT sans claim 'role'               → 403 (code=ROLE_MISSING)
    - Role mappé V4 ∉ allowed_roles       → 403 (code=ROLE_FORBIDDEN)
    - Role mappé V4 ∈ allowed_roles       → retourne payload dict

    Returns:
        dict | None : convention identique à `require_admin` (no AuthContext).

    Usage :
        @router.post("/sensitive")
        async def handler(
            _rbac=Depends(require_v4_role(Role.ADMIN, Role.USER)),
        ): ...

    Raises:
        ValueError : si `allowed_roles` est vide (boot-time, fail-fast).
    """
    if not allowed_roles:
        raise ValueError("require_v4_role requires at least one Role")

    allowed_values = {r.value if isinstance(r, Role) else r for r in allowed_roles}

    def _dependency(
        payload: Optional[dict] = Depends(_get_auth_payload),
    ) -> Optional[dict]:
        # DEMO_MODE bypass
        if payload is None:
            return None

        user_role = payload.get("role")
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ROLE_MISSING",
                    "message": "JWT does not carry a role claim",
                    "hint": "Re-issue the token via /api/auth/login",
                },
            )

        if user_role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ROLE_FORBIDDEN",
                    "message": f"Role '{user_role}' not allowed on this endpoint",
                    "hint": f"Allowed V4 roles: {sorted(allowed_values)}",
                    "current_role_v4": user_role,
                },
            )

        return payload

    return _dependency
