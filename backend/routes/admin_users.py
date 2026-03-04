"""
PROMEOS - Admin Users Routes
Sprint 11: IAM ULTIMATE
CRUD users, roles, scopes (admin only)
"""
import json
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    User, UserOrgRole, UserScope, Organisation,
    UserRole, ScopeLevel,
)
from services.iam_service import (
    create_user, assign_role, assign_scope, remove_role, soft_delete_user,
    hash_password, get_permissions_for_role, get_scoped_site_ids, log_audit, ROLE_PERMISSIONS,
)
from middleware.auth import require_permission, get_current_user_role
from models import Site, EntiteJuridique, Portefeuille


router = APIRouter(prefix="/api/admin", tags=["Admin Users"])


# ========================================
# Schemas
# ========================================

class CreateUserRequest(BaseModel):
    email: str
    password: str
    nom: str
    prenom: str
    role: str
    scopes: Optional[list] = None  # [{level, id, expires_at?}]


class PatchUserRequest(BaseModel):
    nom: Optional[str] = None
    prenom: Optional[str] = None
    email: Optional[str] = None
    actif: Optional[bool] = None


class ChangeRoleRequest(BaseModel):
    role: str


class SetScopesRequest(BaseModel):
    scopes: list  # [{level, id, expires_at?}]


# ========================================
# Helpers
# ========================================

def _serialize_user(db: Session, user: User, uor: Optional[UserOrgRole] = None) -> dict:
    result = {
        "id": user.id,
        "email": user.email,
        "nom": user.nom,
        "prenom": user.prenom,
        "actif": user.actif,
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
    if uor:
        scopes = db.query(UserScope).filter(UserScope.user_org_role_id == uor.id).all()
        result["role"] = uor.role.value
        result["scopes"] = [
            {
                "level": s.scope_level.value,
                "id": s.scope_id,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            }
            for s in scopes
        ]
    return result


# ========================================
# Endpoints
# ========================================

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """List all users for the current org."""
    # In demo mode (_admin is None), show all users
    if _admin is None:
        users = db.query(User).all()
        user_ids = [u.id for u in users]
        uors = db.query(UserOrgRole).filter(UserOrgRole.user_id.in_(user_ids)).all() if user_ids else []
        uor_map = {uor.user_id: uor for uor in uors}
        return [_serialize_user(db, u, uor_map.get(u.id)) for u in users]

    org_id = int(_admin.get("org_id", 0))
    uors = db.query(UserOrgRole).filter(UserOrgRole.org_id == org_id).all()
    user_ids = [uor.user_id for uor in uors]
    users = db.query(User).filter(User.id.in_(user_ids)).all() if user_ids else []
    user_map = {u.id: u for u in users}
    return [_serialize_user(db, user_map[uor.user_id], uor) for uor in uors if uor.user_id in user_map]


@router.post("/users")
def create_user_endpoint(
    req: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """Create a new user + role + scopes."""
    # Check email uniqueness
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    try:
        role = UserRole(req.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")

    # Determine org_id
    org_id = int(_admin.get("org_id", 0)) if _admin else 1

    user = create_user(db, req.email, req.password, req.nom, req.prenom)
    uor = assign_role(db, user.id, org_id, role)

    # Assign scopes
    if req.scopes:
        for s in req.scopes:
            try:
                level = ScopeLevel(s.get("level", "org"))
            except ValueError:
                continue
            expires = None
            if s.get("expires_at"):
                try:
                    expires = datetime.fromisoformat(s["expires_at"])
                except (ValueError, TypeError):
                    pass
            assign_scope(db, uor.id, level, s.get("id", org_id), expires)

    log_audit(db, None, "create_user", "user", str(user.id), {"email": req.email, "role": req.role})
    db.commit()

    return {"status": "created", "user_id": user.id}


@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """Get user detail."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    uor = None
    if _admin:
        org_id = int(_admin.get("org_id", 0))
        uor = db.query(UserOrgRole).filter(
            UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id
        ).first()
    else:
        uor = db.query(UserOrgRole).filter(UserOrgRole.user_id == user_id).first()

    return _serialize_user(db, user, uor)


@router.patch("/users/{user_id}")
def patch_user(
    user_id: int,
    req: PatchUserRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """Modify user fields."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.nom is not None:
        user.nom = req.nom
    if req.prenom is not None:
        user.prenom = req.prenom
    if req.email is not None:
        # Check uniqueness
        dup = db.query(User).filter(User.email == req.email, User.id != user_id).first()
        if dup:
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = req.email
    if req.actif is not None:
        user.actif = req.actif

    log_audit(db, None, "patch_user", "user", str(user_id))
    db.commit()
    return {"status": "updated"}


@router.put("/users/{user_id}/role")
def change_role(
    user_id: int,
    req: ChangeRoleRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """Change user role for current org."""
    try:
        new_role = UserRole(req.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {req.role}")

    org_id = int(_admin.get("org_id", 0)) if _admin else 1

    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id
    ).first()

    if not uor:
        # Create role
        uor = assign_role(db, user_id, org_id, new_role)
    else:
        # Last-owner protection
        if uor.role == UserRole.DG_OWNER and new_role != UserRole.DG_OWNER:
            count = db.query(UserOrgRole).filter(
                UserOrgRole.org_id == org_id,
                UserOrgRole.role == UserRole.DG_OWNER,
            ).count()
            if count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove last DG_OWNER")
        uor.role = new_role

    log_audit(db, None, "change_role", "user", str(user_id), {"new_role": req.role})
    db.commit()
    return {"status": "updated", "role": new_role.value}


@router.put("/users/{user_id}/scopes")
def set_scopes(
    user_id: int,
    req: SetScopesRequest,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """Set scopes for user in current org (replaces all existing)."""
    org_id = int(_admin.get("org_id", 0)) if _admin else 1

    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id
    ).first()
    if not uor:
        raise HTTPException(status_code=404, detail="User has no role in this org")

    # Delete existing scopes
    db.query(UserScope).filter(UserScope.user_org_role_id == uor.id).delete()

    # Create new scopes
    for s in req.scopes:
        try:
            level = ScopeLevel(s.get("level", "org"))
        except ValueError:
            continue
        expires = None
        if s.get("expires_at"):
            try:
                expires = datetime.fromisoformat(s["expires_at"])
            except (ValueError, TypeError):
                pass
        assign_scope(db, uor.id, level, s.get("id", org_id), expires)

    log_audit(db, None, "set_scopes", "user", str(user_id), {"scopes": req.scopes})
    db.commit()
    return {"status": "updated", "scopes_count": len(req.scopes)}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """Soft delete user (set actif=False). Last-owner protection."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if last DG_OWNER
    org_id = int(_admin.get("org_id", 0)) if _admin else None
    if org_id:
        uor = db.query(UserOrgRole).filter(
            UserOrgRole.user_id == user_id, UserOrgRole.org_id == org_id
        ).first()
        if uor and uor.role == UserRole.DG_OWNER:
            count = db.query(UserOrgRole).filter(
                UserOrgRole.org_id == org_id,
                UserOrgRole.role == UserRole.DG_OWNER,
            ).count()
            if count <= 1:
                raise HTTPException(status_code=400, detail="Cannot remove last DG_OWNER")

    soft_delete_user(db, user_id)
    log_audit(db, None, "soft_delete_user", "user", str(user_id))
    db.commit()
    return {"status": "deleted"}


@router.get("/roles")
def list_roles(
    _admin=Depends(require_permission("admin")),
):
    """List all roles with their permissions matrix."""
    result = []
    for role in UserRole:
        result.append({
            "role": role.value,
            "permissions": get_permissions_for_role(role),
        })
    return result


@router.get("/users/{user_id}/effective-access")
def get_effective_access(
    user_id: int,
    db: Session = Depends(get_db),
    _admin=Depends(require_permission("admin")),
):
    """Return the list of sites accessible by this user (resolved from scopes)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    org_id = int(_admin.get("org_id", 0)) if _admin else None
    uor = db.query(UserOrgRole).filter(UserOrgRole.user_id == user_id).first()
    if not uor:
        return {"user_id": user_id, "sites": [], "reason": "No role assigned"}

    site_ids = get_scoped_site_ids(db, uor)
    sites = db.query(Site).filter(Site.id.in_(site_ids)).all() if site_ids else []

    # Resolve scope reason
    scopes = db.query(UserScope).filter(UserScope.user_org_role_id == uor.id).all()
    scope_desc = []
    for s in scopes:
        label = s.scope_level.value.upper()
        if s.scope_level == ScopeLevel.ORG:
            org = db.query(Organisation).filter(Organisation.id == s.scope_id).first()
            label = f"ORG: {org.nom}" if org else f"ORG #{s.scope_id}"
        elif s.scope_level == ScopeLevel.ENTITE:
            ej = db.query(EntiteJuridique).filter(EntiteJuridique.id == s.scope_id).first()
            label = f"ENTITE: {ej.nom}" if ej else f"ENTITE #{s.scope_id}"
        elif s.scope_level == ScopeLevel.SITE:
            site = db.query(Site).filter(Site.id == s.scope_id).first()
            label = f"SITE: {site.nom}" if site else f"SITE #{s.scope_id}"
        scope_desc.append({
            "level": s.scope_level.value,
            "id": s.scope_id,
            "label": label,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        })

    return {
        "user_id": user_id,
        "role": uor.role.value,
        "permissions": get_permissions_for_role(uor.role),
        "scopes": scope_desc,
        "sites": [{"id": s.id, "nom": s.nom, "type": s.type.value if s.type else None} for s in sites],
        "total_sites": len(sites),
    }
