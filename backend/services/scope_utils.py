"""
PROMEOS — Scope utilities : résolution canonique de l'org_id.

Priorité canonique PROMEOS (du plus au moins sûr) :
  1. auth.org_id  — JWT token (si authentifié)
  2. X-Org-Id     — header injecté par l'intercepteur frontend (setApiScope)
  3. None         — pas d'org résolu

Usage :
    from services.scope_utils import get_scope_org_id, resolve_org_id

    org_id = get_scope_org_id(request, auth)
    if org_id is None:
        from services.demo_state import DemoState
        org_id = DemoState.get_demo_org_id()
"""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional
from middleware.auth import AuthContext, DEMO_MODE


def get_scope_org_id(request: Request, auth: Optional[AuthContext]) -> Optional[int]:
    """
    Résout l'org_id de la requête avec la chaîne de priorité canonique.

    Args:
        request:  FastAPI Request (pour lire les headers)
        auth:     AuthContext injecté par get_optional_auth (None en mode démo)

    Returns:
        int org_id si résolu, None sinon.
    """
    # 1. JWT token (le plus sûr)
    if auth is not None:
        return auth.org_id

    # 2. X-Org-Id header (injecté par le scope interceptor frontend)
    raw = request.headers.get("X-Org-Id")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass

    return None


def get_scope_site_id(request: Request, auth: Optional[AuthContext]) -> Optional[int]:
    """
    Résout le site_id optionnel depuis X-Site-Id header.
    (auth.site_ids contient une liste — pas utilisé ici pour la sélection unique)

    Returns:
        int site_id si présent dans X-Site-Id, None sinon.
    """
    raw = request.headers.get("X-Site-Id")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def resolve_org_id(
    request: Request,
    auth: Optional[AuthContext],
    db: Session,
    *,
    org_id_override: Optional[int] = None,
) -> int:
    """
    Résout l'org_id avec la chaîne canonique, puis applique le guard DEMO_MODE.

    Priorité :
      1. auth.org_id   — JWT token
      2. org_id_override — explicit param (query param / request body)
      3. X-Org-Id header — frontend scope interceptor
      4. DEMO_MODE=true  → fallback DemoState puis première org active en DB.
      5. DEMO_MODE=false → 401 Unauthorized (pas de données sensibles sans auth).

    Raises:
        HTTPException 401 si non résolu et DEMO_MODE=false.
        HTTPException 403 si résolu mais org introuvable.
    """
    from models import Organisation

    org_id = get_scope_org_id(request, auth)
    if org_id is not None:
        return org_id

    if org_id_override is not None:
        return org_id_override

    # No org resolved — check DEMO_MODE
    if not DEMO_MODE:
        raise HTTPException(
            status_code=401,
            detail="Authentication required — org could not be resolved (DEMO_MODE is off)",
        )

    # DEMO_MODE=true: fallback chain
    from services.demo_state import DemoState
    demo_org_id = DemoState.get_demo_org_id()
    if demo_org_id:
        return demo_org_id

    org = db.query(Organisation).filter(Organisation.actif == True).first()
    if org:
        return org.id

    raise HTTPException(status_code=403, detail="Organisation non résolue")
