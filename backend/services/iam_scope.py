"""
PROMEOS - Centralized Scope Filtering Helper
Sprint 12: IAM POLISH

Provides reusable scope-enforcement for all routers:
- check_site_access(auth, site_id) → 403 if denied
- apply_scope_filter(query, auth, model, site_col) → scoped query
- get_accessible_site_ids(auth) → list[int]
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Query

from middleware.auth import AuthContext


def get_accessible_site_ids(auth: Optional[AuthContext]) -> Optional[list[int]]:
    """Return list of accessible site IDs, or None if no auth (demo mode)."""
    if auth is None:
        return None  # demo: no filtering
    return auth.site_ids


def check_site_access(auth: Optional[AuthContext], site_id: int) -> None:
    """Raise 403 if authenticated user cannot access this site.
    No-op if auth is None (demo mode).
    """
    if auth is None:
        return
    if auth.site_ids is not None and site_id not in auth.site_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Site not in your scope",
        )


def apply_scope_filter(query, auth: Optional[AuthContext], site_id_col):
    """Apply site-scope filter to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        auth: AuthContext or None (demo mode → no filter)
        site_id_col: SQLAlchemy column for site_id (e.g. Site.id, Action.site_id)

    Returns:
        Filtered query
    """
    if auth is None:
        return query
    if auth.site_ids is not None:
        query = query.filter(site_id_col.in_(auth.site_ids))
    return query


def apply_org_filter(query, auth: Optional[AuthContext], org_id_col):
    """Apply org-scope filter to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        auth: AuthContext or None
        org_id_col: SQLAlchemy column for org_id

    Returns:
        Filtered query
    """
    if auth is None:
        return query
    query = query.filter(org_id_col == auth.org_id)
    return query


def get_effective_org_id(auth: Optional[AuthContext], org_id_param: Optional[int]) -> Optional[int]:
    """Return the effective org_id: auth-enforced if authenticated, param otherwise."""
    if auth is not None:
        return auth.org_id
    return org_id_param
