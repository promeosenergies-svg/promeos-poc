"""
PROMEOS - Routes API pour les Consommations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Consommation
from routes.schemas import ConsommationResponse
from typing import List, Optional
from datetime import datetime

router = APIRouter(prefix="/api/consommations", tags=["Consommations"])

@router.get("", response_model=List[ConsommationResponse])
def get_consommations(
    compteur_id: Optional[int] = Query(None, description="Filtrer par compteur"),
    limit: int = Query(100, le=1000, description="Nombre max de résultats"),
    db: Session = Depends(get_db)
):
    """
    Liste les consommations
    """
    query = db.query(Consommation)
    
    if compteur_id:
        query = query.filter(Consommation.compteur_id == compteur_id)
    
    # Trier par date décroissante
    consommations = query.order_by(Consommation.timestamp.desc()).limit(limit).all()
    
    return consommations
