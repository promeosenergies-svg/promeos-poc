"""
PROMEOS - IAM Service (Auth, JWT, Permissions, Scopes)
Sprint 11: IAM ULTIMATE
"""
import logging
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from models import (
    User, UserOrgRole, UserScope, AuditLog,
    Organisation, EntiteJuridique, Portefeuille, Site,
    UserRole, ScopeLevel,
)

_logger = logging.getLogger("promeos.iam")

# ========================================
# Config
# ========================================

JWT_SECRET = os.environ.get("PROMEOS_JWT_SECRET", "dev-secret-change-me-in-prod")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30

if JWT_SECRET == "dev-secret-change-me-in-prod":
    _logger.warning(
        "PROMEOS_JWT_SECRET is using the default dev value. "
        "Set PROMEOS_JWT_SECRET env var for production."
    )

# Sentinel for "all modules"
ALL = "__ALL__"

# ========================================
# Role → Permissions matrix
# ========================================

ROLE_PERMISSIONS = {
    UserRole.DG_OWNER: {
        "view": ALL, "edit": ALL, "admin": True,
        "export": True, "sync": True, "approve": True,
    },
    UserRole.DSI_ADMIN: {
        "view": ALL, "edit": ALL, "admin": True,
        "export": True, "sync": True, "approve": False,
    },
    UserRole.DAF: {
        "view": ["cockpit", "billing", "purchase", "actions", "reports"],
        "edit": ["billing", "purchase"],
        "export": True,
    },
    UserRole.ACHETEUR: {
        "view": ["purchase", "billing", "actions"],
        "edit": ["purchase"],
        "export": True,
    },
    UserRole.RESP_CONFORMITE: {
        "view": ["conformite", "actions", "reports"],
        "edit": ["conformite", "actions"],
        "export": True,
    },
    UserRole.ENERGY_MANAGER: {
        "view": ALL, "edit": ["consommations", "diagnostic", "actions", "monitoring"],
        "export": True, "sync": True,
    },
    UserRole.RESP_IMMOBILIER: {
        "view": ["patrimoine", "consommations", "actions"],
        "edit": ["patrimoine"],
        "export": True,
    },
    UserRole.RESP_SITE: {
        "view": ["patrimoine", "consommations", "conformite", "actions"],
        "edit": ["patrimoine"],
    },
    UserRole.PRESTATAIRE: {
        "view": ["patrimoine", "consommations", "monitoring"],
        "edit": [],
    },
    UserRole.AUDITEUR: {
        "view": ALL, "edit": [],
        "export": True,
    },
    UserRole.PMO_ACC: {
        "view": ALL, "edit": ["actions"],
        "export": True,
    },
}


# ========================================
# Password hashing
# ========================================

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ========================================
# JWT tokens
# ========================================

def create_access_token(user_id: int, org_id: int, role: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    payload = {
        "sub": str(user_id),
        "org_id": org_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode JWT. Raises JWTError if invalid/expired."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ========================================
# Permission checks
# ========================================

def check_permission(role: UserRole, action: str, module: Optional[str] = None) -> bool:
    """Check if role has permission for action on module."""
    perms = ROLE_PERMISSIONS.get(role, {})
    if action in ("admin", "export", "sync", "approve"):
        return perms.get(action, False) is True
    # view / edit
    allowed = perms.get(action, [])
    if allowed == ALL:
        return True
    if isinstance(allowed, list):
        if module is None:
            return len(allowed) > 0
        return module in allowed
    return False


def get_permissions_for_role(role: UserRole) -> dict:
    """Return serializable permissions dict for a role."""
    perms = ROLE_PERMISSIONS.get(role, {})
    result = {}
    for key in ("view", "edit"):
        val = perms.get(key, [])
        result[key] = "__all__" if val == ALL else (val if isinstance(val, list) else [])
    for key in ("admin", "export", "sync", "approve"):
        result[key] = perms.get(key, False) is True
    return result


# ========================================
# Scope resolution
# ========================================

def get_scoped_site_ids(db: Session, user_org_role: UserOrgRole) -> list[int]:
    """Resolve hierarchical scopes → list of accessible site IDs.
    Deny-by-default: no scopes → empty list.
    """
    scopes = db.query(UserScope).filter(
        UserScope.user_org_role_id == user_org_role.id
    ).all()

    if not scopes:
        return []

    now = datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None)
    site_ids = set()

    for scope in scopes:
        # Check expiration (handle both naive and aware datetimes from DB)
        if scope.expires_at and scope.expires_at < now_naive:
            continue

        if scope.scope_level == ScopeLevel.ORG:
            # All sites in the organisation
            ids = (
                db.query(Site.id)
                .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
                .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
                .filter(EntiteJuridique.organisation_id == scope.scope_id)
                .all()
            )
            site_ids.update(r[0] for r in ids)

        elif scope.scope_level == ScopeLevel.ENTITE:
            # All sites in the entite juridique
            ids = (
                db.query(Site.id)
                .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
                .filter(Portefeuille.entite_juridique_id == scope.scope_id)
                .all()
            )
            site_ids.update(r[0] for r in ids)

        elif scope.scope_level == ScopeLevel.SITE:
            site_ids.add(scope.scope_id)

    return list(site_ids)


# ========================================
# can() — full authorization check
# ========================================

def can(
    db: Session,
    user_id: int,
    permission: str,
    scope_type: Optional[str] = None,
    scope_id: Optional[int] = None,
    module: Optional[str] = None,
) -> dict:
    """Full authorization check with reason and matched assignments.

    Returns: {allowed: bool, reason: str, matched_assignments: [...]}
    Scope hierarchy: SITE→ENTITY→ORG, METER→SITE→ENTITY→ORG (deny-by-default).
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.actif:
        return {"allowed": False, "reason": "User inactive or not found", "matched_assignments": []}

    uors = db.query(UserOrgRole).filter(UserOrgRole.user_id == user_id).all()
    if not uors:
        return {"allowed": False, "reason": "No role assigned", "matched_assignments": []}

    now = datetime.now(timezone.utc)
    now_naive = now.replace(tzinfo=None)
    matched = []

    for uor in uors:
        # Check role permission
        if not check_permission(uor.role, permission, module):
            continue

        # If no scope_type required, role permission is enough
        if scope_type is None:
            matched.append({
                "org_id": uor.org_id,
                "role": uor.role.value,
                "scope": "role_level",
            })
            continue

        # Resolve scope: check if user has access to the requested scope
        scopes = db.query(UserScope).filter(
            UserScope.user_org_role_id == uor.id
        ).all()

        for scope in scopes:
            if scope.expires_at and scope.expires_at < now_naive:
                continue

            # Resolve the requested scope_type/scope_id against user's scopes
            has_access = False
            if scope.scope_level == ScopeLevel.ORG:
                # ORG scope covers everything in the org
                if scope_type == "org" and scope.scope_id == scope_id:
                    has_access = True
                elif scope_type == "entite":
                    ej = db.query(EntiteJuridique).filter(
                        EntiteJuridique.id == scope_id,
                        EntiteJuridique.organisation_id == scope.scope_id,
                    ).first()
                    has_access = ej is not None
                elif scope_type == "site":
                    site = (
                        db.query(Site)
                        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
                        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
                        .filter(Site.id == scope_id, EntiteJuridique.organisation_id == scope.scope_id)
                        .first()
                    )
                    has_access = site is not None
                elif scope_type == "meter":
                    from models import Compteur
                    meter = (
                        db.query(Compteur)
                        .join(Site, Compteur.site_id == Site.id)
                        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
                        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
                        .filter(Compteur.id == scope_id, EntiteJuridique.organisation_id == scope.scope_id)
                        .first()
                    )
                    has_access = meter is not None

            elif scope.scope_level == ScopeLevel.ENTITE:
                if scope_type == "entite" and scope.scope_id == scope_id:
                    has_access = True
                elif scope_type == "site":
                    site = (
                        db.query(Site)
                        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
                        .filter(Site.id == scope_id, Portefeuille.entite_juridique_id == scope.scope_id)
                        .first()
                    )
                    has_access = site is not None
                elif scope_type == "meter":
                    from models import Compteur
                    meter = (
                        db.query(Compteur)
                        .join(Site, Compteur.site_id == Site.id)
                        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
                        .filter(Compteur.id == scope_id, Portefeuille.entite_juridique_id == scope.scope_id)
                        .first()
                    )
                    has_access = meter is not None

            elif scope.scope_level == ScopeLevel.SITE:
                if scope_type == "site" and scope.scope_id == scope_id:
                    has_access = True
                elif scope_type == "meter":
                    from models import Compteur
                    meter = db.query(Compteur).filter(
                        Compteur.id == scope_id, Compteur.site_id == scope.scope_id
                    ).first()
                    has_access = meter is not None

            if has_access:
                matched.append({
                    "org_id": uor.org_id,
                    "role": uor.role.value,
                    "scope_level": scope.scope_level.value,
                    "scope_id": scope.scope_id,
                })

    if matched:
        return {"allowed": True, "reason": "Authorized", "matched_assignments": matched}
    return {"allowed": False, "reason": "Deny-by-default: no matching scope", "matched_assignments": []}


def get_accessible_entity_ids(db: Session, user_org_role: UserOrgRole) -> list[int]:
    """Resolve scopes → list of accessible EntiteJuridique IDs."""
    scopes = db.query(UserScope).filter(
        UserScope.user_org_role_id == user_org_role.id
    ).all()
    if not scopes:
        return []

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    entity_ids = set()

    for scope in scopes:
        if scope.expires_at and scope.expires_at < now:
            continue
        if scope.scope_level == ScopeLevel.ORG:
            ids = db.query(EntiteJuridique.id).filter(
                EntiteJuridique.organisation_id == scope.scope_id
            ).all()
            entity_ids.update(r[0] for r in ids)
        elif scope.scope_level == ScopeLevel.ENTITE:
            entity_ids.add(scope.scope_id)
        elif scope.scope_level == ScopeLevel.SITE:
            ej_id = (
                db.query(EntiteJuridique.id)
                .join(Portefeuille, EntiteJuridique.id == Portefeuille.entite_juridique_id)
                .join(Site, Portefeuille.id == Site.portefeuille_id)
                .filter(Site.id == scope.scope_id)
                .first()
            )
            if ej_id:
                entity_ids.add(ej_id[0])

    return list(entity_ids)


# ========================================
# User CRUD helpers
# ========================================

def create_user(db: Session, email: str, password: str, nom: str, prenom: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        nom=nom,
        prenom=prenom,
    )
    db.add(user)
    db.flush()
    return user


def assign_role(db: Session, user_id: int, org_id: int, role: UserRole) -> UserOrgRole:
    uor = UserOrgRole(user_id=user_id, org_id=org_id, role=role)
    db.add(uor)
    db.flush()
    return uor


def assign_scope(
    db: Session,
    user_org_role_id: int,
    scope_level: ScopeLevel,
    scope_id: int,
    expires_at: Optional[datetime] = None,
) -> UserScope:
    scope = UserScope(
        user_org_role_id=user_org_role_id,
        scope_level=scope_level,
        scope_id=scope_id,
        expires_at=expires_at,
    )
    db.add(scope)
    db.flush()
    return scope


def remove_role(db: Session, user_id: int, org_id: int) -> bool:
    """Remove user role from org. Returns False if last-owner protection triggered."""
    uor = db.query(UserOrgRole).filter(
        UserOrgRole.user_id == user_id,
        UserOrgRole.org_id == org_id,
    ).first()
    if not uor:
        return False

    # Last-owner protection
    if uor.role == UserRole.DG_OWNER:
        count = db.query(UserOrgRole).filter(
            UserOrgRole.org_id == org_id,
            UserOrgRole.role == UserRole.DG_OWNER,
        ).count()
        if count <= 1:
            return False  # Cannot remove last DG_OWNER

    db.delete(uor)
    db.flush()
    return True


def soft_delete_user(db: Session, user_id: int) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    user.actif = False
    db.flush()
    return True


def log_audit(
    db: Session,
    user_id: Optional[int],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
):
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_json=json.dumps(detail) if detail else None,
        ip_address=ip_address,
    )
    db.add(entry)
