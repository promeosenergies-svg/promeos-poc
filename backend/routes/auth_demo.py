"""M2-5.8.A / .9.bis — Connexion démo PROMEOS.

Débloque le P0-1 de l'audit M2-5 : sans session, `/action-center-v4` est
inaccessible (route derrière `RequireAuth`).

M2-5.8.A.bis (Option B) — le demo-login est surfacé sur `LoginPage` (point
d'entrée auth canonique), pas en prompt inline.

Deux endpoints, accessibles UNIQUEMENT en DEMO_MODE :
- `GET  /api/auth/demo-login/available` — probe public, toujours 200. Renvoie
  `available: true` seulement si DEMO_MODE actif ET le compte démo est seedé
  (M2-5.9.bis : la probe garantit la jouabilité réelle, pas juste le flag).
- `POST /api/auth/demo-login` — connexion 1-clic comme Marie Dupont
  (energy_manager HELIOS). 404 en production. Rate-limité (M2-5.9.bis :
  même garde anti-bruteforce que `/api/auth/login`).

Le POST renvoie **exactement** le schéma de `POST /api/auth/login` legacy
(Q3=A) : il réutilise `_build_login_response` — session strictement
équivalente à une connexion email + mot de passe.

N'a PAS réutilisé `POST /api/auth/impersonate` : sémantique distincte
(impersonation admin ≠ connexion démo en 1 clic), et body requis (email).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

import middleware.auth as auth_module
from database import get_db
from middleware.rate_limit import check_rate_limit
from models.iam import User, UserOrgRole
from routes.auth import _build_login_response
from seeds.use_case_a_seed import HELIOS_DEMO_USER_EMAIL

router = APIRouter(prefix="/api/auth", tags=["Auth démo"])


def _demo_account(db: Session) -> tuple[User | None, UserOrgRole | None]:
    """Résout le compte démo + son rôle organisation. (None, None) si absent.

    Source unique de la résolution du compte — partagée par la probe
    `/available` et le POST `/demo-login` pour garantir leur cohérence.
    """
    user = db.query(User).filter(User.email == HELIOS_DEMO_USER_EMAIL).first()
    if user is None:
        return None, None
    uor = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).first()
    return user, uor


@router.get("/demo-login/available")
def demo_login_available(db: Session = Depends(get_db)):
    """Probe publique : la connexion démo est-elle réellement jouable ?

    Toujours **200** (jamais 404). `available` est vrai seulement si les trois
    conditions de jouabilité sont réunies : DEMO_MODE actif, compte démo seedé,
    et rôle organisation présent. M2-5.9.bis — la probe vérifie la jouabilité
    réelle (pas juste `DEMO_MODE`) : un `LoginPage` n'affiche le bouton démo
    que si un clic aboutira (sinon il masquait un futur 500). Ne révèle aucun
    détail sensible — un seul booléen.
    """
    user, uor = _demo_account(db)
    available = auth_module.DEMO_MODE and user is not None and uor is not None
    return {"available": available}


@router.post("/demo-login")
def demo_login(request: Request, db: Session = Depends(get_db)):
    """Connexion démo HELIOS — disponible uniquement en DEMO_MODE.

    Body vide, idempotent. Renvoie le schéma `POST /api/auth/login` legacy
    (`access_token`, `token_type`, `user`, `org`, `role`, `orgs`, `scopes`,
    `permissions`) pour le compte démo Marie Dupont.

    Rate-limité (M2-5.9.bis, CWE-307) : 5 requêtes / 60 s par IP — même garde
    que `/api/auth/login`, contre le token harvesting.

    Raises:
        HTTPException 404: si DEMO_MODE est inactif (endpoint masqué en prod).
        HTTPException 429: si le quota d'appels est dépassé.
        HTTPException 500: si le compte démo n'a pas été seedé.
    """
    # `DEMO_MODE` est figé à l'import dans `middleware.auth` ; lecture indirecte
    # via le module pour que le monkeypatch des tests soit effectif.
    if not auth_module.DEMO_MODE:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")

    check_rate_limit(request, key_prefix="demo-login", max_requests=5, window_seconds=60)

    user, uor = _demo_account(db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "DEMO_USER_NOT_SEEDED",
                "message": "Compte démo absent — exécuter le seed Use Case A.",
                "hint": "python -m seeds.use_case_a_seed",
            },
        )
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
