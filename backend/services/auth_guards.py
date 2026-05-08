"""
PROMEOS - Auth guards reutilisables (V119 J3).

Helpers de protection en ecriture sur les routes patrimoine + Sirene.
DEMO_MODE (auth=None) passe par defaut pour ne pas casser la demo.
"""

from typing import Optional

from fastapi import HTTPException

from middleware.auth import AuthContext

# Roles autorises a creer/modifier des entites patrimoine.
# Phase F audit dette : valeurs lowercase cohérentes avec UserRole enum
# (models/enums.py:436-446) — bug critique dormant : avant ce fix, le set
# uppercase ne matchait JAMAIS auth.role.value lowercase, ce qui aurait
# rejeté tout utilisateur authentifié non-DEMO_MODE. Tous les tests passaient
# car ils tournent en DEMO_MODE (auth=None court-circuite le check).
WRITE_ROLES = frozenset(
    {
        "dg_owner",
        "dsi_admin",
        "energy_manager",
        "resp_conformite",
        "resp_immobilier",
        "resp_site",
        "daf",
        "acheteur",
        "pmo_acc",
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


# Roles strictement admin pour provisioning (création Organisation, opérations sensibles)
# NB : valeurs lowercase cohérentes avec UserRole enum (models/enums.py:436-446)
ADMIN_ROLES = frozenset({"dg_owner", "dsi_admin"})


def require_admin_access(auth: Optional[AuthContext]) -> None:
    """Vérifie un rôle strictement admin (DG_OWNER / DSI_ADMIN).

    Phase F audit P0-3 fix code-reviewer : `create_organisation` est une
    opération de provisioning hors scope existant qui doit être réservée aux
    rôles admin pour éviter la création d'orgs orphelines par tout utilisateur
    authentifié en DEMO_MODE.

    auth=None (DEMO_MODE sans JWT) : accepte (compat démo).
    Sinon : DG_OWNER ou DSI_ADMIN exclusivement.
    """
    if auth is None:
        return
    role_value = auth.role.value if auth.role else None
    if role_value not in ADMIN_ROLES:
        raise HTTPException(
            403,
            detail={
                "code": "FORBIDDEN_ADMIN_PROVISIONING",
                "message": "Provisioning Organisation réservé aux rôles admin (DG_OWNER / DSI_ADMIN)",
                "hint": f"Votre rôle : {role_value or 'inconnu'}",
            },
        )
