"""
PROMEOS - Routes API pour les Consommations
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Consommation, Compteur
from routes.schemas import ConsommationResponse
from typing import List, Optional
from datetime import datetime
from middleware.auth import get_optional_auth, AuthContext

router = APIRouter(prefix="/api/consommations", tags=["Consommations"])


@router.get("", response_model=List[ConsommationResponse])
def get_consommations(
    compteur_id: Optional[int] = Query(None, description="Filtrer par compteur"),
    limit: int = Query(100, le=1000, description="Nombre max de résultats"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Liste les consommations
    """
    query = db.query(Consommation)

    if auth and auth.site_ids is not None:
        query = query.join(Compteur, Consommation.compteur_id == Compteur.id).filter(
            Compteur.site_id.in_(auth.site_ids)
        )
    if compteur_id:
        query = query.filter(Consommation.compteur_id == compteur_id)

    # Trier par date décroissante
    consommations = query.order_by(Consommation.timestamp.desc()).limit(limit).all()

    return consommations
