"""
PROMEOS - Routes API Cockpit & Portefeuilles
Endpoints pour le cockpit exécutif et la gestion des portefeuilles
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import (
    Organisation, Portefeuille, Site, Alerte,
    StatutConformite
)

router = APIRouter(prefix="/api", tags=["Cockpit"])


@router.get("/cockpit")
def get_cockpit(db: Session = Depends(get_db)):
    """
    GET /api/cockpit
    Statistiques globales pour le cockpit exécutif
    """
    # Organisation
    org = db.query(Organisation).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    # Stats sites
    total_sites = db.query(Site).count()
    sites_actifs = db.query(Site).filter(Site.actif == True).count()

    # Stats conformité
    sites_tertiaire_ko = db.query(Site).filter(
        Site.statut_decret_tertiaire == "non_conforme"
    ).count()

    sites_bacs_ko = db.query(Site).filter(
        Site.statut_bacs == "non_conforme"
    ).count()

    # Risque financier total
    risque_total = db.query(func.sum(Site.risque_financier_euro)).scalar() or 0

    # Avancement moyen décret tertiaire
    avg_avancement = db.query(func.avg(Site.avancement_decret_pct)).scalar() or 0

    # Alertes actives
    alertes_actives = db.query(Alerte).filter(Alerte.resolue == False).count()

    return {
        "organisation": {
            "nom": org.nom,
            "type_client": org.type_client
        },
        "stats": {
            "total_sites": total_sites,
            "sites_actifs": sites_actifs,
            "avancement_decret_pct": round(avg_avancement, 1),
            "risque_financier_euro": round(risque_total, 2),
            "sites_tertiaire_ko": sites_tertiaire_ko,
            "sites_bacs_ko": sites_bacs_ko,
            "alertes_actives": alertes_actives
        },
        "echeance_prochaine": "31 décembre 2026 (Décret Tertiaire 2030)"
    }


@router.get("/portefeuilles")
def get_portefeuilles(db: Session = Depends(get_db)):
    """
    GET /api/portefeuilles
    Liste des portefeuilles avec stats
    """
    portefeuilles = db.query(Portefeuille).all()

    result = []
    for p in portefeuilles:
        nb_sites = db.query(Site).filter(Site.portefeuille_id == p.id).count()

        result.append({
            "id": p.id,
            "nom": p.nom,
            "description": p.description,
            "nb_sites": nb_sites
        })

    return {
        "portefeuilles": result,
        "total": len(result)
    }
