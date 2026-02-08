"""
PROMEOS - Routes API pour les Sites
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Site, Compteur, Alerte, Consommation
from routes.schemas import SiteResponse, SiteListResponse, SiteStats
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/sites", tags=["Sites"])

@router.get("", response_model=SiteListResponse)
def get_sites(
    skip: int = 0,
    limit: int = 100,
    ville: Optional[str] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Liste tous les sites PROMEOS avec pagination et filtres
    """
    query = db.query(Site)
    
    # Filtres
    if ville:
        query = query.filter(Site.ville.ilike(f"%{ville}%"))
    if type:
        query = query.filter(Site.type == type)
    
    total = query.count()
    sites = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "sites": sites
    }

@router.get("/{site_id}", response_model=SiteResponse)
def get_site(site_id: int, db: Session = Depends(get_db)):
    """
    Récupère les détails d'un site spécifique
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    
    return site

@router.get("/{site_id}/stats", response_model=SiteStats)
def get_site_stats(site_id: int, db: Session = Depends(get_db)):
    """
    Statistiques d'un site
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    
    # Nombre de compteurs
    nb_compteurs = db.query(Compteur).filter(Compteur.site_id == site_id).count()
    
    # Nombre d'alertes actives
    nb_alertes_actives = db.query(Alerte).filter(
        Alerte.site_id == site_id,
        Alerte.resolue == False
    ).count()
    
    # Consommation du mois dernier
    date_debut = datetime.now() - timedelta(days=30)
    
    consommations = db.query(
        func.sum(Consommation.valeur).label('total_valeur'),
        func.sum(Consommation.cout_euro).label('total_cout')
    ).join(Compteur).filter(
        Compteur.site_id == site_id,
        Consommation.timestamp >= date_debut
    ).first()
    
    return {
        "nb_compteurs": nb_compteurs,
        "nb_alertes_actives": nb_alertes_actives,
        "consommation_totale_mois": consommations.total_valeur or 0,
        "cout_total_mois": consommations.total_cout or 0
    }
