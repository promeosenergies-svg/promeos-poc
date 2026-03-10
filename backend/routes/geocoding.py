"""
PROMEOS — Géocodage Routes
POST /api/geocode/site/{id}    — géocoder un site
POST /api/geocode/org          — géocoder tous les sites d'une org
GET  /api/geocode/search       — recherche d'adresse (autocomplétion BAN)
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.geocoding_service import geocode_site, geocode_org_sites, geocode_address

router = APIRouter(prefix="/api/geocode", tags=["Geocoding"])


@router.post("/site/{site_id}")
def geocode_one_site(
    site_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Geocode a single site by ID."""
    result = geocode_site(db, site_id, force=force)
    db.commit()
    return result


@router.post("/org")
def geocode_org(
    request: Request,
    org_id: int = Query(None),
    force: bool = Query(False),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_optional_auth),
):
    """Geocode all sites for an org."""
    oid = resolve_org_id(request, auth, db, org_id_override=org_id)
    if not oid:
        return {"error": "org_id requis"}
    results = geocode_org_sites(db, oid, force=force)
    return {"status": "ok", "geocoded": len(results), "results": results}


@router.get("/search")
def search_address(
    q: str = Query(..., min_length=3),
):
    """Search BAN for address autocompletion."""
    result = geocode_address(q)
    return result
