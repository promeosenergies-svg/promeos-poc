"""M2-5.8.A / .bis — Connexion démo PROMEOS.

Débloque le P0-1 de l'audit M2-5 : sans session, `/action-center-v4` est
inaccessible (route derrière `RequireAuth`).

M2-5.8.A.bis (Option B) — le walkthrough navigateur a montré que `RequireAuth`
redirige vers `/login` avant que la page V4 ne se monte. Le demo-login est donc
surfacé sur `LoginPage` (point d'entrée auth canonique), pas en prompt inline.

Deux endpoints, accessibles UNIQUEMENT en DEMO_MODE :
- `GET  /api/auth/demo-login/available` — probe public, toujours 200, `{available}`.
- `POST /api/auth/demo-login` — connexion 1-clic comme Marie Dupont
  (energy_manager HELIOS). 404 en production (`PROMEOS_DEMO_MODE` off/absent).

Le POST renvoie **exactement** le schéma de `POST /api/auth/login` legacy
(Q3=A) : il réutilise `_build_login_response` — zéro divergence de format, la
session est strictement équivalente à une connexion email + mot de passe.

N'a PAS réutilisé `POST /api/auth/impersonate` : sémantique distincte
(impersonation admin ≠ connexion démo en 1 clic), et body requis (email).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import middleware.auth as auth_module
from database import get_db
from models.iam import User, UserOrgRole
from routes.auth import _build_login_response
from seeds.use_case_a_seed import HELIOS_DEMO_USER_EMAIL

router = APIRouter(prefix="/api/auth", tags=["Auth démo"])


@router.get("/demo-login/available")
def demo_login_available():
    """Probe public : indique si la connexion démo est disponible.

    Toujours **200** (jamais 404) — le frontend lit le flag `available` sans
    ambiguïté « endpoint absent vs mode désactivé ». Permet à `LoginPage`
    d'afficher ou non le bouton démo.
    """
    return {"available": auth_module.DEMO_MODE}


@router.post("/demo-login")
def demo_login(db: Session = Depends(get_db)):
    """Connexion démo HELIOS — disponible uniquement en DEMO_MODE.

    Body vide, idempotent. Renvoie le schéma `POST /api/auth/login` legacy
    (`access_token`, `token_type`, `user`, `org`, `role`, `orgs`, `scopes`,
    `permissions`) pour le compte démo Marie Dupont.

    Raises:
        HTTPException 404: si DEMO_MODE est inactif (endpoint masqué en prod).
        HTTPException 500: si le compte démo n'a pas été seedé.
    """
    # `DEMO_MODE` est figé à l'import dans `middleware.auth` ; lecture indirecte
    # via le module pour que le monkeypatch des tests soit effectif.
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

    # Format strictement aligné sur /api/auth/login (Q3=A) — session identique.
    return _build_login_response(db, user, uor)
