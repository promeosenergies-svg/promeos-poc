"""
PROMEOS - Demo Mode API Routes
POST /api/demo/enable, POST /api/demo/disable, GET /api/demo/status
POST /api/demo/seed - Peuple la DB avec un jeu de donnees demo
GET /api/demo/templates, GET /api/demo/templates/{template_id}
"""
import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation, EntiteJuridique, Portefeuille, Site, Compteur,
    TypeSite, TypeCompteur, EnergyVector,
)
from services.demo_state import DemoState
from services.onboarding_service import provision_site

router = APIRouter(prefix="/api/demo", tags=["Demo Mode"])


@router.post("/enable")
def enable_demo():
    DemoState.enable()
    return DemoState.status()


@router.post("/disable")
def disable_demo():
    DemoState.disable()
    return DemoState.status()


@router.get("/status")
def get_demo_status():
    return DemoState.status()


_DEMO_SITES = [
    {"nom": "Hypermarche Montreuil", "type": TypeSite.COMMERCE, "ville": "Montreuil", "cp": "93100", "surface": 4500},
    {"nom": "Bureau Haussmann", "type": TypeSite.BUREAU, "ville": "Paris", "cp": "75008", "surface": 1200},
    {"nom": "Entrepot Rungis", "type": TypeSite.ENTREPOT, "ville": "Rungis", "cp": "94150", "surface": 8000},
]


@router.post("/seed")
def seed_demo(db: Session = Depends(get_db)):
    """
    Peuple la DB avec un jeu de donnees demo:
    1 org + 2 entites juridiques + 1 portefeuille + 3 sites + compteurs + obligations.
    Erreur 409 si une organisation existe deja.
    """
    existing = db.query(Organisation).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Organisation '{existing.nom}' existe deja. Supprimez d'abord l'existante."
        )

    # Organisation
    org = Organisation(nom="Demo PROMEOS", type_client="tertiaire", actif=True, siren="999888777")
    db.add(org)
    db.flush()

    # 2 entites juridiques
    ej1 = EntiteJuridique(organisation_id=org.id, nom="Demo SAS", siren="999888777")
    ej2 = EntiteJuridique(organisation_id=org.id, nom="Demo Logistics SARL", siren="999888666")
    db.add_all([ej1, ej2])
    db.flush()

    # 1 portefeuille
    pf = Portefeuille(entite_juridique_id=ej1.id, nom="Portefeuille Demo", description="Sites de demonstration")
    db.add(pf)
    db.flush()

    sites_created = []
    for s_data in _DEMO_SITES:
        site = Site(
            portefeuille_id=pf.id,
            nom=s_data["nom"],
            type=s_data["type"],
            ville=s_data["ville"],
            code_postal=s_data["cp"],
            surface_m2=s_data["surface"],
            actif=True,
            tertiaire_area_m2=s_data["surface"],
        )
        db.add(site)
        db.flush()

        # 2 compteurs par site (elec + gaz)
        for i, (tc, ev) in enumerate([(TypeCompteur.ELECTRICITE, EnergyVector.ELECTRICITY), (TypeCompteur.GAZ, EnergyVector.GAS)]):
            c = Compteur(
                site_id=site.id,
                type=tc,
                numero_serie=f"DEMO-{site.id}-{i+1:02d}",
                puissance_souscrite_kw=random.randint(50, 300) if tc == TypeCompteur.ELECTRICITE else None,
                meter_id=f"{random.randint(10000000000000, 99999999999999)}",
                energy_vector=ev,
                actif=True,
            )
            db.add(c)

        prov = provision_site(db, site)
        sites_created.append({
            "id": site.id,
            "nom": site.nom,
            "type": site.type.value,
            **prov,
        })

    db.commit()

    DemoState.enable()

    return {
        "status": "ok",
        "organisation_id": org.id,
        "entites_juridiques": 2,
        "portefeuilles": 1,
        "sites_created": len(sites_created),
        "compteurs_created": len(sites_created) * 2,
        "sites": sites_created,
    }


@router.get("/templates")
def get_templates():
    """Liste des profils demo disponibles."""
    from services.demo_templates import get_all_templates
    return {"templates": get_all_templates()}


@router.get("/templates/{template_id}")
def get_template_detail(template_id: str):
    """Detail d'un profil demo."""
    from services.demo_templates import get_template
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template non trouve")
    return tpl
