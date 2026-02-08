"""
PROMEOS - Routes API pour les Alertes
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Alerte
from routes.schemas import AlerteResponse, AlerteListResponse
from typing import Optional

router = APIRouter(prefix="/api/alertes", tags=["Alertes"])

@router.get("", response_model=AlerteListResponse)
def get_alertes(
    site_id: Optional[int] = Query(None, description="Filtrer par site"),
    severite: Optional[str] = Query(None, description="Filtrer par sévérité"),
    resolue: Optional[bool] = Query(None, description="Filtrer par statut résolution"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    """
    Liste les alertes avec filtres
    """
    query = db.query(Alerte)
    
    if site_id:
        query = query.filter(Alerte.site_id == site_id)
    if severite:
        query = query.filter(Alerte.severite == severite)
    if resolue is not None:
        query = query.filter(Alerte.resolue == resolue)
    
    total = query.count()
    alertes = query.order_by(Alerte.timestamp.desc()).limit(limit).all()
    
    return {
        "total": total,
        "alertes": alertes
    }

@router.get("/{alerte_id}", response_model=AlerteResponse)
def get_alerte(alerte_id: int, db: Session = Depends(get_db)):
    """
    Récupère une alerte spécifique
    """
    alerte = db.query(Alerte).filter(Alerte.id == alerte_id).first()
    
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    return alerte

@router.patch("/{alerte_id}/resolve")
def resolve_alerte(alerte_id: int, db: Session = Depends(get_db)):
    """
    Marque une alerte comme résolue
    """
    alerte = db.query(Alerte).filter(Alerte.id == alerte_id).first()
    
    if not alerte:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    
    alerte.resolue = True
    alerte.date_resolution = datetime.now()
    db.commit()
    
    return {"message": "Alerte résolue avec succès"}
