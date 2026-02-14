"""
PROMEOS - Routes API Onboarding
POST /api/onboarding         - Creer organisation + entite + portefeuilles + sites
POST /api/onboarding/import-csv  - Import massif de sites via CSV
GET  /api/onboarding/status  - Etat de l'onboarding
"""
import io
import csv
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import Organisation, Portefeuille, Site, not_deleted
from services.onboarding_service import (
    create_organisation_full,
    create_site_from_data,
    provision_site,
)

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])


# ========================================
# Schemas
# ========================================

class OrgInput(BaseModel):
    nom: str
    siren: Optional[str] = None
    type_client: Optional[str] = "tertiaire"


class PortefeuilleInput(BaseModel):
    nom: str
    description: Optional[str] = None


class SiteInput(BaseModel):
    nom: str
    type: Optional[str] = None
    naf_code: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    surface_m2: Optional[float] = None


class OnboardingRequest(BaseModel):
    organisation: OrgInput
    portefeuilles: Optional[List[PortefeuilleInput]] = None
    sites: Optional[List[SiteInput]] = None


# ========================================
# Endpoints
# ========================================

@router.post("")
def create_onboarding(payload: OnboardingRequest, db: Session = Depends(get_db)):
    """
    Cree l'organisation complete en un seul appel.
    V1 mono-org: erreur 409 si une organisation existe deja.
    """
    # V1: mono-org
    existing = db.query(Organisation).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Organisation '{existing.nom}' existe deja. V1 mono-org: supprimez d'abord l'existante."
        )

    # Creer org + entite + portefeuilles
    portefeuilles_data = [p.model_dump() for p in (payload.portefeuilles or [])]
    result = create_organisation_full(
        db=db,
        org_nom=payload.organisation.nom,
        org_siren=payload.organisation.siren or "",
        org_type_client=payload.organisation.type_client or "tertiaire",
        portefeuilles_data=portefeuilles_data,
    )

    # Creer les sites s'ils sont fournis
    sites_created = []
    if payload.sites:
        default_pf_id = result["default_portefeuille_id"]
        for s_input in payload.sites:
            site = create_site_from_data(
                db=db,
                portefeuille_id=default_pf_id,
                nom=s_input.nom,
                type_site=s_input.type,
                naf_code=s_input.naf_code,
                adresse=s_input.adresse,
                code_postal=s_input.code_postal,
                ville=s_input.ville,
                surface_m2=s_input.surface_m2,
            )
            prov = provision_site(db, site)
            sites_created.append({
                "id": site.id,
                "nom": site.nom,
                "type": site.type.value,
                **prov,
            })

    db.commit()

    return {
        "status": "ok",
        "organisation_id": result["organisation_id"],
        "entite_juridique_id": result["entite_juridique_id"],
        "portefeuille_ids": result["portefeuille_ids"],
        "sites_created": len(sites_created),
        "sites": sites_created,
    }


@router.post("/import-csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Import massif de sites via CSV.
    Necessite une organisation existante (onboarding prealable).

    Format CSV attendu (separateur , ou ;):
    nom,adresse,code_postal,ville,surface_m2,type,naf_code
    """
    # Verifier qu'une org existe
    org = db.query(Organisation).first()
    if not org:
        raise HTTPException(
            status_code=400,
            detail="Aucune organisation. Creez d'abord une organisation via POST /api/onboarding."
        )

    # Trouver le premier portefeuille
    portefeuille = db.query(Portefeuille).first()
    if not portefeuille:
        raise HTTPException(status_code=400, detail="Aucun portefeuille existant.")

    # Lire le fichier
    content = await file.read()
    text = content.decode("utf-8-sig")  # utf-8-sig pour gerer le BOM Excel

    # Detecter le separateur
    first_line = text.split("\n")[0]
    delimiter = ";" if ";" in first_line else ","

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)

    imported = []
    errors = []

    for row_num, row in enumerate(reader, start=2):  # start=2 car ligne 1 = header
        try:
            nom = (row.get("nom") or "").strip()
            if not nom:
                errors.append({"row": row_num, "error": "Champ 'nom' manquant ou vide"})
                continue

            surface_raw = (row.get("surface_m2") or "").strip()
            surface = float(surface_raw) if surface_raw else None

            site = create_site_from_data(
                db=db,
                portefeuille_id=portefeuille.id,
                nom=nom,
                type_site=(row.get("type") or "").strip() or None,
                naf_code=(row.get("naf_code") or "").strip() or None,
                adresse=(row.get("adresse") or "").strip() or None,
                code_postal=(row.get("code_postal") or "").strip() or None,
                ville=(row.get("ville") or "").strip() or None,
                surface_m2=surface,
            )
            prov = provision_site(db, site)
            imported.append({
                "id": site.id,
                "nom": site.nom,
                "type": site.type.value,
                **prov,
            })

        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})

    db.commit()

    return {
        "status": "ok",
        "imported": len(imported),
        "errors": len(errors),
        "sites": imported,
        "error_details": errors,
    }


@router.get("/status")
def get_onboarding_status(db: Session = Depends(get_db)):
    """
    Retourne l'etat de l'onboarding:
    - has_organisation: bool
    - organisation_nom: str | null
    - total_sites: int
    - total_portefeuilles: int
    - onboarding_complete: bool (org existe ET >= 1 site)
    """
    org = db.query(Organisation).first()
    total_sites = not_deleted(db.query(Site), Site).count()
    total_portefeuilles = not_deleted(db.query(Portefeuille), Portefeuille).count()

    return {
        "has_organisation": org is not None,
        "organisation_nom": org.nom if org else None,
        "organisation_type": org.type_client if org else None,
        "total_sites": total_sites,
        "total_portefeuilles": total_portefeuilles,
        "onboarding_complete": org is not None and total_sites > 0,
    }
