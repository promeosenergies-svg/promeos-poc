"""M2-5.8.A — Endpoint de connexion démo PROMEOS.

Débloque le P0-1 de l'audit M2-5 : `/action-center-v4` renvoyait `401
NO_ORG_CONTEXT` en DEMO_MODE sans token, rendant le parcours pilote injouable.

ACCESSIBLE UNIQUEMENT EN DEMO_MODE. En production (`PROMEOS_DEMO_MODE` absent
ou `false`), l'endpoint répond **404** — invisible, pas 401/403.

Le JWT est produit par `create_access_token` legacy (`services/iam_service.py`):
claims `{sub, org_id, role, exp, iat}` — exactement ceux que `populate_org_context`
(lit `org_id`) et `require_v4_role` (lit `role`) consomment. Aucun claim custom,
aucun bricolage : un token demo-login est strictement équivalent à un token
`/api/auth/login`.

N'a PAS réutilisé `POST /api/auth/impersonate` (qui existe déjà) : sémantique
distincte (impersonation admin ≠ connexion démo en 1 clic), et body requis
(email) là où demo-login a un body vide et est idempotent.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import middleware.auth as auth_module
from database import get_db
from models.iam import User, UserOrgRole
from seeds.use_case_a_seed import HELIOS_DEMO_USER_EMAIL
from services.iam_service import create_access_token

router = APIRouter(prefix="/api/auth", tags=["Auth démo"])

# TTL volontairement long (8 h) : une session de démo pilote tient une journée
# sans réauthentification. `create_access_token` accepte un `expires_delta`
# explicite (défaut legacy = 30 min, trop court ici).
_TOKEN_TTL = timedelta(hours=8)


@router.post("/demo-login")
def demo_login(db: Session = Depends(get_db)):
    """Connexion démo HELIOS — disponible uniquement en DEMO_MODE.

    Body vide, idempotent : chaque appel renvoie un JWT frais pour le compte
    démo Marie Dupont (energy_manager HELIOS, org id=1).

    Returns:
        access_token: JWT signé (claims sub/org_id/role — équivalent /login).
        user_email: email du compte démo.
        organisation_id: id HELIOS.
        expires_in: durée de validité du token, en secondes.

    Raises:
        HTTPException 404: si DEMO_MODE est inactif (endpoint masqué en prod).
        HTTPException 500: si le compte démo n'a pas été seedé.
    """
    # `DEMO_MODE` est une constante figée à l'import dans `middleware.auth`.
    # On la lit via le module (`auth_module.DEMO_MODE`) et non par
    # `from ... import DEMO_MODE` : l'accès indirect rend le monkeypatch des
    # tests effectif (`setattr("middleware.auth.DEMO_MODE", ...)`).
    if not auth_module.DEMO_MODE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    user = db.query(User).filter(User.email == HELIOS_DEMO_USER_EMAIL).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DEMO_USER_NOT_SEEDED",
                "message": "Compte démo absent — exécuter le seed Use Case A.",
                "hint": "python -m seeds.use_case_a_seed",
            },
        )

    uor = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).first()
    if uor is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DEMO_USER_NO_ORG_ROLE",
                "message": "Compte démo sans rôle organisation.",
                "hint": "python -m seeds.use_case_a_seed",
            },
        )

    token = create_access_token(user.id, uor.org_id, uor.role.value, expires_delta=_TOKEN_TTL)
    return {
        "access_token": token,
        "user_email": user.email,
        "organisation_id": uor.org_id,
        "expires_in": int(_TOKEN_TTL.total_seconds()),
    }
