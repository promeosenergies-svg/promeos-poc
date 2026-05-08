"""
PROMEOS — Phase F1.10 (ADR-F-01) : endpoints REST Fournisseur cardinaux.

Pattern Phase E IDOR : tous les endpoints utilisent `resolve_org_id` + helpers
service `services/fournisseur_service.py` UNION canoniques + privés tenant.

Endpoints cardinaux :
- GET    /api/fournisseurs                     — liste UNION canoniques + privés scope
- GET    /api/fournisseurs/{fournisseur_id}    — détail (404 si pas accessible scope)
- POST   /api/fournisseurs                     — création fournisseur privé tenant
- PATCH  /api/fournisseurs/{fournisseur_id}    — modification (refus canoniques 403)
- DELETE /api/fournisseurs/{fournisseur_id}    — désactivation soft (refus canoniques 403)
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import AuthContext, get_optional_auth
from models.enums import TypeFournitureEnum
from models.fournisseur import Fournisseur
from services.auth_guards import require_write_access as _require_write_access
from services.fournisseur_service import (
    assert_can_mutate_fournisseur,
    create_fournisseur_for_org,
    get_fournisseur_by_id,
    get_fournisseurs_for_org,
)
from services.scope_utils import resolve_org_id


router = APIRouter(prefix="/api/fournisseurs", tags=["Fournisseurs"])


# ─── Schemas ──────────────────────────────────────────────────────────────────


_SIREN_REGEX = r"^\d{9}$"
_TVA_FR_REGEX = r"^FR\d{11}$"


class FournisseurCreate(BaseModel):
    nom: str = Field(..., min_length=1, max_length=200)
    type_fourniture: TypeFournitureEnum
    # Phase F1 P1 fix code-reviewer : validation Pydantic upstream avant ORM
    # → 422 propre au lieu de 500 sur ValueError validator ORM
    siren: Optional[str] = Field(None, max_length=9, pattern=_SIREN_REGEX)
    tva_intra: Optional[str] = Field(None, max_length=13, pattern=_TVA_FR_REGEX)
    naf_code: Optional[str] = Field(None, max_length=10)
    contact_email: Optional[str] = Field(None, max_length=320)
    contact_telephone: Optional[str] = Field(None, max_length=30)
    site_web: Optional[str] = Field(None, max_length=500)
    cgv_url: Optional[str] = Field(None, max_length=500)
    signataire_nom: Optional[str] = Field(None, max_length=200)
    signataire_email: Optional[str] = Field(None, max_length=320)


class FournisseurUpdate(BaseModel):
    nom: Optional[str] = Field(None, min_length=1, max_length=200)
    type_fourniture: Optional[TypeFournitureEnum] = None
    siren: Optional[str] = Field(None, max_length=9, pattern=_SIREN_REGEX)
    tva_intra: Optional[str] = Field(None, max_length=13, pattern=_TVA_FR_REGEX)
    naf_code: Optional[str] = Field(None, max_length=10)
    contact_email: Optional[str] = Field(None, max_length=320)
    contact_telephone: Optional[str] = Field(None, max_length=30)
    site_web: Optional[str] = Field(None, max_length=500)
    cgv_url: Optional[str] = Field(None, max_length=500)
    signataire_nom: Optional[str] = Field(None, max_length=200)
    signataire_email: Optional[str] = Field(None, max_length=320)
    actif: Optional[bool] = None


def _to_dict(f: Fournisseur, *, scope_org_id: Optional[int] = None) -> dict:
    """Sérialise un Fournisseur en dict.

    Phase F1 P1 fix code-reviewer (Pilier 13 ADR-016 PII SoT) : les emails
    contact_email + signataire_email + contact_telephone des fournisseurs
    canoniques (visibles à tous les tenants) ne doivent PAS être exposés en
    clair sans contrôle de rôle. Visibles uniquement sur fournisseurs privés
    appartenant au scope_org_id appelant.
    """
    is_owner = (not f.is_canonique()) and (f.organisation_id == scope_org_id)
    return {
        "id": f.id,
        "organisation_id": f.organisation_id,
        "is_canonique": f.is_canonique(),
        "nom": f.nom,
        "siren": f.siren,
        "tva_intra": f.tva_intra,
        "naf_code": f.naf_code,
        "type_fourniture": f.type_fourniture.value if f.type_fourniture else None,
        # PII : exposition uniquement au propriétaire (pattern Pilier 13 ADR-016)
        "contact_email": f.contact_email if is_owner else None,
        "contact_telephone": f.contact_telephone if is_owner else None,
        "site_web": f.site_web,
        "cgv_url": f.cgv_url,
        "actif": f.actif,
        "signataire_nom": f.signataire_nom if is_owner else None,
        "signataire_email": f.signataire_email if is_owner else None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.get("")
def list_fournisseurs(
    request: Request,
    type_fourniture: Optional[TypeFournitureEnum] = Query(None),
    actif_only: bool = Query(True),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste UNION canoniques + privés scope_org_id (Phase E IDOR cardinal)."""
    scope_org_id = resolve_org_id(request, auth, db)
    fs = get_fournisseurs_for_org(
        db,
        org_id=scope_org_id,
        type_fourniture=type_fourniture,
        actif_only=actif_only,
    )
    return {
        "count": len(fs),
        "fournisseurs": [_to_dict(f, scope_org_id=scope_org_id) for f in fs],
    }


@router.get("/{fournisseur_id}")
def get_fournisseur(
    fournisseur_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail fournisseur (404 anti-énumération si privé d'une autre org)."""
    scope_org_id = resolve_org_id(request, auth, db)
    f = get_fournisseur_by_id(db, fournisseur_id, scope_org_id)
    return _to_dict(f, scope_org_id=scope_org_id)


@router.post("", status_code=201)
def create_fournisseur(
    body: FournisseurCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Créer un fournisseur PRIVÉ pour l'organisation scope (Phase E IDOR)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    f = create_fournisseur_for_org(
        db,
        scope_org_id=scope_org_id,
        nom=body.nom,
        type_fourniture=body.type_fourniture,
        siren=body.siren,
        tva_intra=body.tva_intra,
        naf_code=body.naf_code,
        contact_email=body.contact_email,
        contact_telephone=body.contact_telephone,
        site_web=body.site_web,
        cgv_url=body.cgv_url,
        signataire_nom=body.signataire_nom,
        signataire_email=body.signataire_email,
    )
    return _to_dict(f, scope_org_id=scope_org_id)


@router.patch("/{fournisseur_id}")
def update_fournisseur(
    fournisseur_id: int,
    body: FournisseurUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Modifier un fournisseur PRIVÉ (refus canoniques 403, refus cross-tenant 404)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    f = get_fournisseur_by_id(db, fournisseur_id, scope_org_id)
    assert_can_mutate_fournisseur(f, scope_org_id)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(f, field, value)
    db.commit()
    db.refresh(f)
    return _to_dict(f, scope_org_id=scope_org_id)


@router.delete("/{fournisseur_id}")
def deactivate_fournisseur(
    fournisseur_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Désactivation soft d'un fournisseur PRIVÉ (refus canoniques 403)."""
    _require_write_access(auth)
    scope_org_id = resolve_org_id(request, auth, db)
    f = get_fournisseur_by_id(db, fournisseur_id, scope_org_id)
    assert_can_mutate_fournisseur(f, scope_org_id)
    f.actif = False
    db.commit()
    return {"status": "deactivated", "id": fournisseur_id}
