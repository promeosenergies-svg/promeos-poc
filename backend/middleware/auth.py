"""
PROMEOS - Auth Middleware & Dependencies
Sprint 11: IAM ULTIMATE

Provides FastAPI dependencies for authentication:
- get_current_user: strict (raises 401)
- get_optional_auth: lenient (returns None in demo mode)
"""
import os
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserOrgRole, UserRole
from services.iam_service import decode_token, get_scoped_site_ids, check_permission

# auto_error=False → returns None instead of 401 when no token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

AUTH_ENABLED = os.environ.get("PROMEOS_AUTH_ENABLED", "false").lower() == "true"
DEMO_MODE = os.environ.get("PROMEOS_DEMO_MODE", "false").lower() == "true"


@dataclass
class AuthContext:
    """Injected into endpoints via Depends(get_optional_auth)."""
    user: User
    user_org_role: UserOrgRole
    org_id: int
    role: UserRole
    site_ids: list[int]


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Strict auth dependency — raises 401 if not authenticated."""
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.actif:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    return user


def get_current_user_role(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> tuple:
    """Returns (User, UserOrgRole) — strict."""
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub", 0))
    org_id = int(payload.get("org_id", 0))

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.actif:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or not found")

    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id,
        UserOrgRole.org_id == org_id,
    ).first()
    if not uor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No role for this org")

    return user, uor


def get_optional_auth(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[AuthContext]:
    """Lenient auth — returns None if no token (demo mode only).
    If DEMO_MODE=false and no token → 401.
    If token present, resolves full auth context with scoped site_ids.
    """
    if token is None:
        if DEMO_MODE:
            return None  # Demo mode: no filtering
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (DEMO_MODE is off)",
        )

    try:
        payload = decode_token(token)
    except Exception:
        if DEMO_MODE:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id = int(payload.get("sub", 0))
    org_id = int(payload.get("org_id", 0))

    user = db.query(User).filter(User.id == user_id, User.actif == True).first()
    if not user:
        return None

    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id,
        UserOrgRole.org_id == org_id,
    ).first()
    if not uor:
        return None

    site_ids = get_scoped_site_ids(db, uor)

    return AuthContext(
        user=user,
        user_org_role=uor,
        org_id=org_id,
        role=uor.role,
        site_ids=site_ids,
    )


def require_permission(action: str, module: Optional[str] = None):
    """Dependency factory: raise 403 if role lacks permission."""
    def _check(
        token: Optional[str] = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
    ):
        if token is None:
            if DEMO_MODE:
                return None  # Demo mode: lenient
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        try:
            payload = decode_token(token)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        role_str = payload.get("role", "")
        try:
            role = UserRole(role_str)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role")

        if not check_permission(role, action, module):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

        return payload

    return _check


def require_admin():
    """Dependency: require admin permission (DG_OWNER or DSI_ADMIN)."""
    return require_permission("admin")
