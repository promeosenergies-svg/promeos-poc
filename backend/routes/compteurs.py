"""
PROMEOS - Routes API pour les Compteurs
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Compteur
from routes.schemas import CompteurResponse
from typing import List, Optional

router = APIRouter(prefix="/api/compteurs", tags=["Compteurs"])

@router.get("", response_model=List[CompteurResponse])
def get_compteurs(
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    type: Optional[str] = Query(None, description="Filtrer par type (electricite, gaz, eau)"),
    db: Session = Depends(get_db)
):
    """
    Liste les compteurs avec filtres
    """
    query = db.query(Compteur)
    
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
    compteur = db.query(Compteur).filter(Compteur.id == compteur_id).first()
    
    if not compteur:
        raise HTTPException(status_code=404, detail="Compteur non trouvé")
    
    return compteur
