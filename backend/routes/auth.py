"""
PROMEOS - Auth Routes
Sprint 11: IAM ULTIMATE
POST /api/auth/login, /refresh, /logout, /switch-org
GET  /api/auth/me
PUT  /api/auth/password
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserOrgRole, UserScope, AuditLog, Organisation, UserRole
from services.iam_service import (
    verify_password, create_access_token, decode_token,
    get_permissions_for_role, get_scoped_site_ids, hash_password,
    log_audit,
)
from middleware.auth import oauth2_scheme, get_current_user_role, require_permission, DEMO_MODE
from middleware.rate_limit import check_rate_limit

router = APIRouter(prefix="/api/auth", tags=["Auth"])


# ========================================
# Schemas
# ========================================

class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class SwitchOrgRequest(BaseModel):
    org_id: int


# ========================================
# Helpers
# ========================================

def _build_login_response(db: Session, user: User, uor: UserOrgRole) -> dict:
    """Build full login response with token, user info, permissions."""
    token = create_access_token(user.id, uor.org_id, uor.role.value)

    # All orgs for this user
    all_uors = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).all()
    orgs_list = []
    for u in all_uors:
        org = db.query(Organisation).filter(Organisation.id == u.org_id).first()
        if org:
            orgs_list.append({"id": org.id, "nom": org.nom, "role": u.role.value})

    # Scopes for current org
    scopes = db.query(UserScope).filter(UserScope.user_org_role_id == uor.id).all()
    scopes_list = [{"level": s.scope_level.value, "id": s.scope_id} for s in scopes]

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "nom": user.nom,
            "prenom": user.prenom,
        },
        "org": {"id": uor.org_id, "nom": next((o["nom"] for o in orgs_list if o["id"] == uor.org_id), "")},
        "role": uor.role.value,
        "orgs": orgs_list,
        "scopes": scopes_list,
        "permissions": get_permissions_for_role(uor.role),
    }


# ========================================
# Endpoints
# ========================================

@router.post("/login")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email + password → JWT."""
    check_rate_limit(request, key_prefix="login", max_requests=5, window_seconds=60)
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.actif:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")

    # Get first org role (default)
    uor = db.query(UserOrgRole).filter(UserOrgRole.user_id == user.id).first()
    if not uor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No org assigned")

    # Update last_login
    user.last_login = datetime.now(timezone.utc)
    log_audit(db, user.id, "login")
    db.commit()

    return _build_login_response(db, user, uor)


@router.post("/refresh")
def refresh_token(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Refresh JWT token."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub", 0))
    org_id = int(payload.get("org_id", 0))

    user = db.query(User).filter(User.id == user_id, User.actif == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id
    ).first()
    if not uor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No role for org")

    new_token = create_access_token(user.id, uor.org_id, uor.role.value)
    return {"access_token": new_token, "token_type": "bearer"}


@router.get("/me")
def get_me(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get current user profile + role + scopes + permissions."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub", 0))
    org_id = int(payload.get("org_id", 0))

    user = db.query(User).filter(User.id == user_id, User.actif == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id
    ).first()
    if not uor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No role for org")

    return _build_login_response(db, user, uor)


@router.post("/logout")
def logout(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Logout (client-side token removal). Server logs the event."""
    if token:
        try:
            payload = decode_token(token)
            user_id = int(payload.get("sub", 0))
            log_audit(db, user_id, "logout")
            db.commit()
        except Exception:
            db.rollback()
    return {"status": "ok"}


@router.put("/password")
def change_password(
    req: PasswordChange,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Change user password."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    if not verify_password(req.current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password incorrect")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")

    user.hashed_password = hash_password(req.new_password)
    log_audit(db, user.id, "password_change")
    db.commit()
    return {"status": "updated"}


@router.post("/switch-org")
def switch_org(
    req: SwitchOrgRequest,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Switch org context → new JWT."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.id == user_id, User.actif == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id, UserOrgRole.org_id == req.org_id
    ).first()
    if not uor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this org")

    log_audit(db, user.id, "switch_org", "organisation", str(req.org_id))
    db.commit()

    return _build_login_response(db, user, uor)


# ========================================
# Demo mode endpoints
# ========================================

class ImpersonateRequest(BaseModel):
    email: str


@router.post("/impersonate")
def impersonate(
    request: Request,
    req: ImpersonateRequest,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Impersonate another user (DEMO_MODE only or admin).
    Returns a new JWT as if logged in as that user.
    """
    check_rate_limit(request, key_prefix="impersonate", max_requests=10, window_seconds=60)
    if not DEMO_MODE:
        # Must be admin
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        try:
            payload = decode_token(token)
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        role_str = payload.get("role", "")
        if role_str not in ("dg_owner", "dsi_admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    target = db.query(User).filter(User.email == req.email, User.actif == True).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    uor = db.query(UserOrgRole).filter(UserOrgRole.user_id == target.id).first()
    if not uor:
        raise HTTPException(status_code=400, detail="User has no org role")

    # Log impersonation
    caller_id = None
    if token:
        try:
            p = decode_token(token)
            caller_id = int(p.get("sub", 0))
        except Exception:
            pass
    log_audit(db, caller_id, "impersonate", "user", str(target.id), {"target_email": req.email})
    db.commit()

    return _build_login_response(db, target, uor)


@router.post("/reset-demo")
def reset_demo(db: Session = Depends(get_db)):
    """Legacy compat — delegates to canonical /api/demo/reset-pack (soft + IAM)."""
    if not DEMO_MODE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Demo mode only")

    from services.demo_seed import SeedOrchestrator
    from routes.demo import _reset_iam_demo
    orch = SeedOrchestrator(db)
    result = orch.reset(mode="soft")
    _reset_iam_demo(db)
    return {"status": "reset", "message": "Demo data + IAM reseeded", **result}


# ========================================
# Audit log endpoints
# ========================================

@router.get("/audit")
def list_audit_logs(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    action: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    resource_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """List audit log entries (admin only). Filtrable by action, user_id, resource_type."""
    import json as json_mod
    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        q = q.filter(AuditLog.action == action)
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)

    total = q.count()
    entries = q.offset(offset).limit(limit).all()

    # Resolve user names for display
    user_cache = {}
    result = []
    for e in entries:
        if e.user_id and e.user_id not in user_cache:
            u = db.query(User).filter(User.id == e.user_id).first()
            user_cache[e.user_id] = f"{u.prenom} {u.nom}" if u else "?"

        result.append({
            "id": e.id,
            "user_id": e.user_id,
            "user_name": user_cache.get(e.user_id, "system"),
            "action": e.action,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "detail": json_mod.loads(e.detail_json) if e.detail_json else None,
            "ip_address": e.ip_address,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return {"total": total, "entries": result}
