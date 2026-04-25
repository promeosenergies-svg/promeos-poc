"""
PROMEOS - IAM Models (Users / Roles / Scopes / Audit)
Sprint 11: IAM ULTIMATE
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, TimestampMixin
from .enums import UserRole, ScopeLevel


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    actif = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relations
    org_roles = relationship("UserOrgRole", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class UserOrgRole(TimestampMixin, Base):
    __tablename__ = "user_org_roles"
    __table_args__ = (UniqueConstraint("user_id", "org_id", name="uq_user_org"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)

    # Relations
    user = relationship("User", back_populates="org_roles")
    organisation = relationship("Organisation")
    scopes = relationship("UserScope", back_populates="user_org_role", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserOrgRole user={self.user_id} org={self.org_id} role={self.role}>"


class UserScope(Base):
    __tablename__ = "user_scopes"

    id = Column(Integer, primary_key=True, index=True)
    user_org_role_id = Column(Integer, ForeignKey("user_org_roles.id"), nullable=False)
    scope_level = Column(SAEnum(ScopeLevel), nullable=False)
    scope_id = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relations
    user_org_role = relationship("UserOrgRole", back_populates="scopes")

    def __repr__(self):
        return f"<UserScope {self.scope_level}={self.scope_id}>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    # Sprint CX 2.5 hardening (P1-perf) : indices composite + simples pour
    # optimiser les queries CX dashboard (T2V, IAR, WAU/MAU) qui filtrent sur
    # (action IN (...), resource_type='cx_event', created_at >= cutoff) +
    # group_by(resource_id, action) + distinct(user_id).
    __table_args__ = (
        Index(
            "ix_audit_cx_action_resource_created",
            "action",
            "resource_type",
            "created_at",
        ),
        Index("ix_audit_user_id", "user_id"),
        Index("ix_audit_resource_id", "resource_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    detail_json = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AuditLog {self.action} {self.resource_type}>"
