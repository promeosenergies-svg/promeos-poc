"""
PROMEOS - Auth guards reutilisables (V119 J3).

Helpers de protection en ecriture sur les routes patrimoine + Sirene.
DEMO_MODE (auth=None) passe par defaut pour ne pas casser la demo.
"""

from typing import Optional

from fastapi import HTTPException

from middleware.auth import AuthContext

# Roles autorises a creer/modifier des entites patrimoine
WRITE_ROLES = frozenset(
    {
        "DG_OWNER",
        "DSI_ADMIN",
        "ENERGY_MANAGER",
        "RESP_CONFORMITE",
        "RESP_IMMOBILIER",
        "RESP_SITE",
        "DAF",
        "ACHETEUR",
        "PMO_ACC",
    }
)


def require_write_access(auth: Optional[AuthContext]) -> None:
    """Verifie que l'utilisateur peut creer/modifier des entites patrimoine.

    auth=None (DEMO_MODE) : accepte (compat existante).
    Roles operationnels : accepte.
    Lecture seule (VIEWER, AUDITEUR) ou role inconnu : 403 FORBIDDEN.
    """
    if auth is None:
        return
    role_value = auth.role.value if auth.role else None
    if role_value not in WRITE_ROLES:
        raise HTTPException(
            403,
            detail={
                "code": "FORBIDDEN_WRITE_PATRIMOINE",
                "message": "Acces en ecriture au patrimoine reserve aux roles operationnels",
                "hint": f"Votre role : {role_value or 'inconnu'} (lecture seule)",
            },
        )
