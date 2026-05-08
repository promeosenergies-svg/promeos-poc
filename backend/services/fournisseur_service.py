"""
PROMEOS — Phase F1.6 (ADR-F-01) : service Fournisseur cardinal.

Résolution UNION catalogue canonique (organisation_id=NULL) + fournisseurs privés
de l'organisation courante. Pattern hybride ADR-F-01 Option C.

Pattern Pilier 12 ADR-016 (org-scoping cardinal multi-tenant) + Phase E IDOR :
- get_fournisseurs_for_org : UNION canoniques + privés `org_id`
- get_fournisseur_by_id : check accès (canonique OU privé scope_org_id)
- create_fournisseur_for_org : validation parent org existante
- assert_can_mutate_fournisseur : refus mutation des canoniques par tenant
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from models import Organisation, not_deleted
from models.enums import TypeFournitureEnum
from models.fournisseur import Fournisseur


def canonical_or_scoped_filter(scope_org_id: int | None) -> ColumnElement:
    """Filtre SQL UNION canoniques (org_id NULL) + privés (org_id == scope).

    Phase F2 /simplify fix : dédoublonnage du pattern OR utilisé 4× dans
    les services Fournisseur. Si `scope_org_id is None`, retourne uniquement
    les canoniques.
    """
    if scope_org_id is None:
        return Fournisseur.organisation_id.is_(None)
    return or_(
        Fournisseur.organisation_id.is_(None),
        Fournisseur.organisation_id == scope_org_id,
    )


def get_fournisseurs_for_org(
    db: Session,
    org_id: int,
    *,
    type_fourniture: Optional[TypeFournitureEnum] = None,
    actif_only: bool = True,
) -> list[Fournisseur]:
    """Retourne UNION canoniques (org_id NULL) + privés (org_id == scope).

    Args:
        org_id: scope de l'organisation appelante (résolu via resolve_org_id).
        type_fourniture: filtre optionnel ELEC/GAZ/MULTI.
        actif_only: True (défaut) — exclut les fournisseurs désactivés.

    Returns:
        list[Fournisseur] triée par nom.
    """
    q = db.query(Fournisseur).filter(canonical_or_scoped_filter(org_id))
    if actif_only:
        q = q.filter(Fournisseur.actif.is_(True))
    if type_fourniture is not None:
        q = q.filter(Fournisseur.type_fourniture == type_fourniture)
    return q.order_by(Fournisseur.nom.asc()).all()


def get_fournisseur_by_id(
    db: Session,
    fournisseur_id: int,
    scope_org_id: int,
) -> Fournisseur:
    """Retourne un fournisseur par ID si accessible au scope.

    Accessible = canonique (organisation_id NULL) OU privé scope_org_id.
    404 anti-énumération si pas trouvé OU privé d'une autre org.
    """
    f = (
        db.query(Fournisseur)
        .filter(
            Fournisseur.id == fournisseur_id,
            canonical_or_scoped_filter(scope_org_id),
        )
        .first()
    )
    if not f:
        raise HTTPException(404, "Fournisseur introuvable")
    return f


def assert_can_mutate_fournisseur(
    fournisseur: Fournisseur,
    scope_org_id: int,
) -> None:
    """Garde mutation : seul le propriétaire d'un fournisseur privé peut le modifier.

    Les fournisseurs canoniques (organisation_id=NULL) sont LECTURE SEULE pour
    tous les tenants — seul un admin Promeos master peut les modifier (hors scope F1).

    Raises:
        HTTPException 403 : tentative mutation fournisseur canonique par tenant
        HTTPException 404 : tentative mutation fournisseur privé d'une autre org
    """
    if fournisseur.is_canonique():
        raise HTTPException(
            403,
            detail={
                "code": "FOURNISSEUR_CANONIQUE_READ_ONLY",
                "message": "Les fournisseurs canoniques sont en lecture seule pour les tenants",
                "hint": "Créer un fournisseur privé pour votre organisation à la place",
            },
        )
    if fournisseur.organisation_id != scope_org_id:
        raise HTTPException(404, "Fournisseur introuvable")


def create_fournisseur_for_org(
    db: Session,
    *,
    scope_org_id: int,
    nom: str,
    type_fourniture: TypeFournitureEnum,
    siren: Optional[str] = None,
    tva_intra: Optional[str] = None,
    naf_code: Optional[str] = None,
    contact_email: Optional[str] = None,
    contact_telephone: Optional[str] = None,
    site_web: Optional[str] = None,
    cgv_url: Optional[str] = None,
    signataire_nom: Optional[str] = None,
    signataire_email: Optional[str] = None,
) -> Fournisseur:
    """Crée un fournisseur privé pour l'organisation `scope_org_id`.

    Vérifie que l'organisation existe (pattern Phase E IDOR).
    Si SIREN matche un canonique existant : 409 + suggestion (anti-doublon métier).
    """
    # Vérification organisation existe (pattern Phase E)
    org = db.query(Organisation).filter(Organisation.id == scope_org_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(404, "Organisation introuvable")

    # Anti-doublon : SIREN match canonique existant ?
    if siren:
        canonique_match = (
            db.query(Fournisseur)
            .filter(
                Fournisseur.siren == siren,
                Fournisseur.organisation_id.is_(None),
            )
            .first()
        )
        if canonique_match:
            raise HTTPException(
                409,
                detail={
                    "code": "FOURNISSEUR_CANONIQUE_EXISTS",
                    "message": f"Un fournisseur canonique existe déjà avec SIREN={siren}",
                    "suggestion_id": canonique_match.id,
                    "suggestion_nom": canonique_match.nom,
                },
            )

    f = Fournisseur(
        organisation_id=scope_org_id,
        nom=nom,
        type_fourniture=type_fourniture,
        siren=siren,
        tva_intra=tva_intra,
        naf_code=naf_code,
        contact_email=contact_email,
        contact_telephone=contact_telephone,
        site_web=site_web,
        cgv_url=cgv_url,
        signataire_nom=signataire_nom,
        signataire_email=signataire_email,
        actif=True,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f
