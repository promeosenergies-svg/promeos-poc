"""
PROMEOS — CRUD Organisation / EntiteJuridique / Portefeuille / Site (Step 19)
Endpoints manuels pour ajouter/modifier/archiver des entités patrimoniales.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from models import (
    Organisation,
    EntiteJuridique,
    Portefeuille,
    Site,
    Batiment,
    TypeSite,
    not_deleted,
)
from schemas.patrimoine_crud import (
    OrganisationCreate,
    OrganisationUpdate,
    EntiteJuridiqueCreate,
    EntiteJuridiqueUpdate,
    PortefeuilleCreate,
    PortefeuilleUpdate,
    SiteCreate,
    SiteUpdate,
    BatimentCreate,
)

router = APIRouter(prefix="/api/patrimoine/crud", tags=["Patrimoine CRUD"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _org_to_dict(org: Organisation) -> dict:
    return {
        "id": org.id,
        "nom": org.nom,
        "type_client": org.type_client,
        "siren": org.siren,
        "actif": org.actif,
        "is_demo": org.is_demo,
    }


def _entite_to_dict(e: EntiteJuridique) -> dict:
    return {
        "id": e.id,
        "organisation_id": e.organisation_id,
        "nom": e.nom,
        "siren": e.siren,
        "siret": e.siret,
        "naf_code": e.naf_code,
        "region_code": e.region_code,
    }


def _pf_to_dict(pf: Portefeuille) -> dict:
    return {
        "id": pf.id,
        "entite_juridique_id": pf.entite_juridique_id,
        "nom": pf.nom,
        "description": pf.description,
    }


def _site_to_dict(s: Site) -> dict:
    return {
        "id": s.id,
        "portefeuille_id": s.portefeuille_id,
        "nom": s.nom,
        "type": s.type.value if s.type else None,
        "adresse": s.adresse,
        "code_postal": s.code_postal,
        "ville": s.ville,
        "region": s.region,
        "surface_m2": s.surface_m2,
        "tertiaire_area_m2": s.tertiaire_area_m2,
        "siret": s.siret,
        "naf_code": s.naf_code,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "actif": s.actif,
    }


# ══════════════════════════════════════════════════════════════════════════════
# ORGANISATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/organisations")
def list_organisations(
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste toutes les organisations actives."""
    orgs = db.query(Organisation).filter(not_deleted(Organisation)).all()
    return {"count": len(orgs), "organisations": [_org_to_dict(o) for o in orgs]}


@router.post("/organisations", status_code=201)
def create_organisation(
    body: OrganisationCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée une nouvelle organisation."""
    org = Organisation(
        nom=body.nom,
        type_client=body.type_client,
        siren=body.siren,
        actif=True,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return _org_to_dict(org)


@router.get("/organisations/{org_id}")
def get_organisation(
    org_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'une organisation."""
    org = db.query(Organisation).filter(Organisation.id == org_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(404, "Organisation introuvable")
    return _org_to_dict(org)


@router.patch("/organisations/{org_id}")
def update_organisation(
    org_id: int,
    body: OrganisationUpdate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour une organisation."""
    org = db.query(Organisation).filter(Organisation.id == org_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(404, "Organisation introuvable")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return _org_to_dict(org)


@router.delete("/organisations/{org_id}")
def archive_organisation(
    org_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) une organisation."""
    org = db.query(Organisation).filter(Organisation.id == org_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(404, "Organisation introuvable")
    org.actif = False
    db.commit()
    return {"status": "archived", "id": org_id}


# ══════════════════════════════════════════════════════════════════════════════
# ENTITES JURIDIQUES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/entites")
def list_entites(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les entités juridiques, optionnellement filtrées par organisation."""
    q = db.query(EntiteJuridique).filter(not_deleted(EntiteJuridique))
    if org_id:
        q = q.filter(EntiteJuridique.organisation_id == org_id)
    entites = q.all()
    return {"count": len(entites), "entites": [_entite_to_dict(e) for e in entites]}


@router.post("/entites", status_code=201)
def create_entite(
    body: EntiteJuridiqueCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée une entité juridique."""
    # Vérifier que l'organisation existe
    org = db.query(Organisation).filter(Organisation.id == body.organisation_id, not_deleted(Organisation)).first()
    if not org:
        raise HTTPException(404, "Organisation introuvable")
    # Vérifier unicité SIREN
    existing = db.query(EntiteJuridique).filter(
        EntiteJuridique.siren == body.siren,
        not_deleted(EntiteJuridique),
    ).first()
    if existing:
        raise HTTPException(409, f"SIREN {body.siren} déjà utilisé par l'entité #{existing.id}")
    entite = EntiteJuridique(
        organisation_id=body.organisation_id,
        nom=body.nom,
        siren=body.siren,
        siret=body.siret,
        naf_code=body.naf_code,
        region_code=body.region_code,
    )
    db.add(entite)
    db.commit()
    db.refresh(entite)
    return _entite_to_dict(entite)


@router.get("/entites/{entite_id}")
def get_entite(
    entite_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'une entité juridique."""
    e = db.query(EntiteJuridique).filter(EntiteJuridique.id == entite_id, not_deleted(EntiteJuridique)).first()
    if not e:
        raise HTTPException(404, "Entité juridique introuvable")
    return _entite_to_dict(e)


@router.patch("/entites/{entite_id}")
def update_entite(
    entite_id: int,
    body: EntiteJuridiqueUpdate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour une entité juridique."""
    e = db.query(EntiteJuridique).filter(EntiteJuridique.id == entite_id, not_deleted(EntiteJuridique)).first()
    if not e:
        raise HTTPException(404, "Entité juridique introuvable")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(e, field, value)
    db.commit()
    db.refresh(e)
    return _entite_to_dict(e)


@router.delete("/entites/{entite_id}")
def archive_entite(
    entite_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) une entité juridique."""
    e = db.query(EntiteJuridique).filter(EntiteJuridique.id == entite_id, not_deleted(EntiteJuridique)).first()
    if not e:
        raise HTTPException(404, "Entité juridique introuvable")
    # Soft delete via mixin if available, else set actif
    if hasattr(e, "deleted_at"):
        from datetime import datetime, timezone
        e.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "archived", "id": entite_id}


# ══════════════════════════════════════════════════════════════════════════════
# PORTEFEUILLES
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/portefeuilles")
def list_portefeuilles(
    entite_id: Optional[int] = Query(None),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les portefeuilles, optionnellement filtrés."""
    q = db.query(Portefeuille).filter(not_deleted(Portefeuille))
    if entite_id:
        q = q.filter(Portefeuille.entite_juridique_id == entite_id)
    if org_id:
        q = q.join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id).filter(
            EntiteJuridique.organisation_id == org_id
        )
    pfs = q.all()
    return {"count": len(pfs), "portefeuilles": [_pf_to_dict(pf) for pf in pfs]}


@router.post("/portefeuilles", status_code=201)
def create_portefeuille(
    body: PortefeuilleCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée un portefeuille."""
    entite = db.query(EntiteJuridique).filter(
        EntiteJuridique.id == body.entite_juridique_id,
        not_deleted(EntiteJuridique),
    ).first()
    if not entite:
        raise HTTPException(404, "Entité juridique introuvable")
    pf = Portefeuille(
        entite_juridique_id=body.entite_juridique_id,
        nom=body.nom,
        description=body.description,
    )
    db.add(pf)
    db.commit()
    db.refresh(pf)
    return _pf_to_dict(pf)


@router.get("/portefeuilles/{pf_id}")
def get_portefeuille(
    pf_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'un portefeuille."""
    pf = db.query(Portefeuille).filter(Portefeuille.id == pf_id, not_deleted(Portefeuille)).first()
    if not pf:
        raise HTTPException(404, "Portefeuille introuvable")
    return _pf_to_dict(pf)


@router.patch("/portefeuilles/{pf_id}")
def update_portefeuille(
    pf_id: int,
    body: PortefeuilleUpdate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour un portefeuille."""
    pf = db.query(Portefeuille).filter(Portefeuille.id == pf_id, not_deleted(Portefeuille)).first()
    if not pf:
        raise HTTPException(404, "Portefeuille introuvable")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pf, field, value)
    db.commit()
    db.refresh(pf)
    return _pf_to_dict(pf)


@router.delete("/portefeuilles/{pf_id}")
def archive_portefeuille(
    pf_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) un portefeuille."""
    pf = db.query(Portefeuille).filter(Portefeuille.id == pf_id, not_deleted(Portefeuille)).first()
    if not pf:
        raise HTTPException(404, "Portefeuille introuvable")
    if hasattr(pf, "deleted_at"):
        from datetime import datetime, timezone
        pf.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "archived", "id": pf_id}


# ══════════════════════════════════════════════════════════════════════════════
# SITES (CRUD complet via patrimoine_crud)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/sites")
def list_sites_crud(
    pf_id: Optional[int] = Query(None),
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Liste les sites, filtrables par portefeuille ou organisation."""
    q = db.query(Site).filter(not_deleted(Site), Site.actif == True)
    if pf_id:
        q = q.filter(Site.portefeuille_id == pf_id)
    if org_id:
        q = (
            q.join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == org_id)
        )
    sites = q.all()
    return {"count": len(sites), "sites": [_site_to_dict(s) for s in sites]}


@router.post("/sites", status_code=201)
def create_site_crud(
    body: SiteCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Crée un site dans un portefeuille."""
    pf = db.query(Portefeuille).filter(Portefeuille.id == body.portefeuille_id, not_deleted(Portefeuille)).first()
    if not pf:
        raise HTTPException(404, "Portefeuille introuvable")

    # Résoudre le TypeSite enum
    try:
        site_type = TypeSite(body.type)
    except ValueError:
        valid = [t.value for t in TypeSite]
        raise HTTPException(422, f"Type de site invalide : {body.type}. Valides : {valid}")

    site = Site(
        portefeuille_id=body.portefeuille_id,
        nom=body.nom,
        type=site_type,
        adresse=body.adresse,
        code_postal=body.code_postal,
        ville=body.ville,
        region=body.region,
        surface_m2=body.surface_m2,
        tertiaire_area_m2=body.tertiaire_area_m2,
        siret=body.siret,
        naf_code=body.naf_code,
        latitude=body.latitude,
        longitude=body.longitude,
        actif=True,
        data_source="manual",
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return _site_to_dict(site)


@router.get("/sites/{site_id}")
def get_site_crud(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Détail d'un site."""
    site = db.query(Site).filter(Site.id == site_id, not_deleted(Site)).first()
    if not site:
        raise HTTPException(404, "Site introuvable")
    return _site_to_dict(site)


@router.patch("/sites/{site_id}")
def update_site_crud(
    site_id: int,
    body: SiteUpdate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Met à jour un site."""
    site = db.query(Site).filter(Site.id == site_id, not_deleted(Site)).first()
    if not site:
        raise HTTPException(404, "Site introuvable")
    updates = body.model_dump(exclude_unset=True)
    if "type" in updates and updates["type"] is not None:
        try:
            updates["type"] = TypeSite(updates["type"])
        except ValueError:
            raise HTTPException(422, f"Type de site invalide : {updates['type']}")
    for field, value in updates.items():
        setattr(site, field, value)
    db.commit()
    db.refresh(site)
    return _site_to_dict(site)


@router.delete("/sites/{site_id}")
def archive_site_crud(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Archive (soft-delete) un site."""
    site = db.query(Site).filter(Site.id == site_id, not_deleted(Site)).first()
    if not site:
        raise HTTPException(404, "Site introuvable")
    site.actif = False
    db.commit()
    return {"status": "archived", "id": site_id}


# ══════════════════════════════════════════════════════════════════════════════
# BATIMENTS
# ══════════════════════════════════════════════════════════════════════════════

def _bat_to_dict(b: Batiment) -> dict:
    return {
        "id": b.id,
        "site_id": b.site_id,
        "nom": b.nom,
        "surface_m2": b.surface_m2,
        "annee_construction": b.annee_construction,
        "cvc_power_kw": b.cvc_power_kw,
    }


@router.post("/batiments", status_code=201)
def create_batiment(
    body: BatimentCreate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Cree un batiment rattache a un site."""
    site = db.query(Site).filter(Site.id == body.site_id, not_deleted(Site)).first()
    if not site:
        raise HTTPException(404, "Site introuvable")
    bat = Batiment(
        site_id=body.site_id,
        nom=body.nom,
        surface_m2=body.surface_m2,
        annee_construction=body.annee_construction,
        cvc_power_kw=body.cvc_power_kw,
    )
    db.add(bat)
    db.commit()
    db.refresh(bat)
    return _bat_to_dict(bat)
