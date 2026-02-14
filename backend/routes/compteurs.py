"""
PROMEOS - Routes API pour les Compteurs
"""
import random
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Compteur, Site, TypeCompteur, EnergyVector, not_deleted
from routes.schemas import CompteurResponse
from typing import List, Optional

router = APIRouter(prefix="/api/compteurs", tags=["Compteurs"])


class CompteurCreateRequest(BaseModel):
    site_id: int
    type: str  # "electricite", "gaz", "eau"
    numero_serie: Optional[str] = None
    puissance_souscrite_kw: Optional[float] = None


@router.post("")
def create_compteur(req: CompteurCreateRequest, db: Session = Depends(get_db)):
    """Cree un compteur sur un site existant."""
    site = db.query(Site).filter(Site.id == req.site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouve")

    try:
        tc = TypeCompteur(req.type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Type invalide: {req.type}. Valeurs: electricite, gaz, eau")

    ev_map = {
        TypeCompteur.ELECTRICITE: EnergyVector.ELECTRICITY,
        TypeCompteur.GAZ: EnergyVector.GAS,
        TypeCompteur.EAU: EnergyVector.OTHER,
    }

    num_serie = req.numero_serie or f"CPT-{site.id}-{random.randint(1000, 9999)}"
    c = Compteur(
        site_id=site.id,
        type=tc,
        numero_serie=num_serie,
        puissance_souscrite_kw=req.puissance_souscrite_kw,
        meter_id=f"{random.randint(10000000000000, 99999999999999)}",
        energy_vector=ev_map.get(tc, EnergyVector.OTHER),
        actif=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return {
        "id": c.id,
        "site_id": c.site_id,
        "type": c.type.value,
        "numero_serie": c.numero_serie,
        "puissance_souscrite_kw": c.puissance_souscrite_kw,
    }

@router.get("", response_model=List[CompteurResponse])
def get_compteurs(
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    type: Optional[str] = Query(None, description="Filtrer par type (electricite, gaz, eau)"),
    db: Session = Depends(get_db)
):
    """
    Liste les compteurs avec filtres
    """
    query = not_deleted(db.query(Compteur), Compteur)

    if site_id:
        query = query.filter(Compteur.site_id == site_id)
    if type:
        query = query.filter(Compteur.type == type)

    compteurs = query.all()
    return compteurs

@router.get("/{compteur_id}", response_model=CompteurResponse)
def get_compteur(compteur_id: int, db: Session = Depends(get_db)):
    """
    Récupère un compteur spécifique
    """
    compteur = not_deleted(db.query(Compteur), Compteur).filter(Compteur.id == compteur_id).first()
    
    if not compteur:
        raise HTTPException(status_code=404, detail="Compteur non trouvé")
    
    return compteur
