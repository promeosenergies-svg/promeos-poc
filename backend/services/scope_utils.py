"""
PROMEOS — Scope utilities : résolution canonique de l'org_id.

Priorité canonique PROMEOS (du plus au moins sûr) :
  1. auth.org_id  — JWT token (si authentifié)
  2. X-Org-Id     — header injecté par l'intercepteur frontend (setApiScope)
  3. None         — pas d'org résolu

Usage :
    from services.scope_utils import get_scope_org_id

    org_id = get_scope_org_id(request, auth)
    if org_id is None:
        from services.demo_state import DemoState
        org_id = DemoState.get_demo_org_id()
"""
from fastapi import Request
from typing import Optional
from middleware.auth import AuthContext


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
