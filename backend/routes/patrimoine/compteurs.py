"""
PROMEOS - Patrimoine Compteur routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from models import (
    EntiteJuridique,
    Portefeuille,
    Site,
    not_deleted,
    Compteur,
    TypeCompteur,
)
from middleware.auth import get_optional_auth, AuthContext

from routes.patrimoine._helpers import (
    _get_org_id,
    _load_site_with_org_check,
    _load_compteur_with_org_check,
    _serialize_compteur,
    CompteurUpdateRequest,
    CompteurMoveRequest,
)

router = APIRouter(tags=["Patrimoine"])


# ========================================
# Compteur Operations (WORLD CLASS)
# ========================================


@router.get("/compteurs")
def list_compteurs(
    request: Request,
    site_id: Optional[int] = None,
    actif: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List compteurs with filters — scoped to org."""
    org_id = _get_org_id(request, auth, db)
    q = (
        db.query(Compteur)
        .join(Site, Compteur.site_id == Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, not_deleted(Compteur))
    )
    if site_id is not None:
        q = q.filter(Compteur.site_id == site_id)
    if actif is not None:
        q = q.filter(Compteur.actif == actif)
    total = q.count()
    compteurs = q.offset(skip).limit(limit).all()
    return {"total": total, "compteurs": [_serialize_compteur(c) for c in compteurs]}


@router.patch("/compteurs/{compteur_id}")
def update_compteur(
    compteur_id: int,
    request: Request,
    body: CompteurUpdateRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Update a compteur (partial update)."""
    org_id = _get_org_id(request, auth, db)
    c = _load_compteur_with_org_check(db, compteur_id, org_id)

    updated = []
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "type" and value is not None:
            try:
                value = TypeCompteur(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type invalide: {value}")
        setattr(c, field, value)
        updated.append(field)

    db.commit()

    # Auto-créer DeliveryPoint si meter_id modifié (#105)
    if "meter_id" in updated:
        from services.onboarding_service import ensure_delivery_points_for_site

        ensure_delivery_points_for_site(db, c.site_id)
        db.commit()

    return {"updated": updated, **_serialize_compteur(c)}


@router.post("/compteurs/{compteur_id}/move")
def move_compteur(
    compteur_id: int,
    request: Request,
    body: CompteurMoveRequest,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Move a compteur to another site."""
    org_id = _get_org_id(request, auth, db)
    c = _load_compteur_with_org_check(db, compteur_id, org_id)
    target = _load_site_with_org_check(db, body.target_site_id, org_id)

    old_site_id = c.site_id
    c.site_id = target.id
    db.commit()
    return {
        "detail": f"Compteur {compteur_id} deplace de site {old_site_id} vers {target.id}",
        **_serialize_compteur(c),
    }


@router.post("/compteurs/{compteur_id}/detach")
def detach_compteur(
    compteur_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Deactivate a compteur (soft detach)."""
    org_id = _get_org_id(request, auth, db)
    c = _load_compteur_with_org_check(db, compteur_id, org_id)
    c.soft_delete()
    db.commit()
    return {"detail": f"Compteur {compteur_id} desactive", **_serialize_compteur(c)}
