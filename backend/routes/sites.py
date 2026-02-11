"""
PROMEOS - Routes API pour les Sites
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Site, Compteur, Alerte, Consommation, Obligation, Evidence, Batiment, StatutConformite, StatutEvidence, TypeObligation
from routes.schemas import SiteResponse, SiteListResponse, SiteStats, SiteComplianceResponse, BatimentResponse
from services.compliance_engine import compute_action_recommandee, _ACTION_TEMPLATES
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/sites", tags=["Sites"])


class SiteCreateRequest(BaseModel):
    nom: str
    type: Optional[str] = None
    naf_code: Optional[str] = None
    adresse: Optional[str] = None
    code_postal: Optional[str] = None
    ville: Optional[str] = None
    surface_m2: Optional[float] = None


@router.post("")
def create_site(req: SiteCreateRequest, db: Session = Depends(get_db)):
    """
    Cree un site dans le premier portefeuille de l'organisation existante.
    Auto-provision: batiment + obligations + compliance recompute.
    """
    from models import Organisation, Portefeuille
    from services.onboarding_service import create_site_from_data, provision_site

    org = db.query(Organisation).first()
    if not org:
        raise HTTPException(status_code=400, detail="Aucune organisation. Creez-en une d'abord.")
    pf = db.query(Portefeuille).first()
    if not pf:
        raise HTTPException(status_code=400, detail="Aucun portefeuille.")

    site = create_site_from_data(
        db=db,
        portefeuille_id=pf.id,
        nom=req.nom,
        type_site=req.type,
        naf_code=req.naf_code,
        adresse=req.adresse,
        code_postal=req.code_postal,
        ville=req.ville,
        surface_m2=req.surface_m2,
    )
    prov = provision_site(db, site)

    # Auto-evaluate compliance rules
    from services.compliance_rules import evaluate_site as eval_rules
    findings = eval_rules(db, site.id)

    db.commit()
    return {
        "id": site.id,
        "nom": site.nom,
        "type": site.type.value,
        "findings_count": len(findings),
        **prov,
    }

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


@router.get("/{site_id}/compliance", response_model=SiteComplianceResponse)
def get_site_compliance(site_id: int, db: Session = Depends(get_db)):
    """
    Conformité détaillée d'un site : obligations, evidences, explications et actions.
    """
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    obligations = db.query(Obligation).filter(Obligation.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    batiments = db.query(Batiment).filter(Batiment.site_id == site_id).all()

    # Build explanations from obligations
    explanations = []
    for ob in obligations:
        if ob.type == TypeObligation.DECRET_TERTIAIRE:
            label = "Décret Tertiaire"
            if ob.statut == StatutConformite.CONFORME:
                why = f"Trajectoire 2030 respectée (avancement {ob.avancement_pct:.0f}%)"
            elif ob.statut == StatutConformite.A_RISQUE:
                why = f"Avancement insuffisant ({ob.avancement_pct:.0f}%) - trajectoire 2030 menacée"
            else:
                why = f"Avancement critique ({ob.avancement_pct:.0f}%) - objectif 2030 compromis"
        elif ob.type == TypeObligation.BACS:
            label = "BACS (GTB/GTC)"
            if ob.statut == StatutConformite.CONFORME:
                why = "Système GTB/GTC installé et conforme"
            elif ob.statut == StatutConformite.A_RISQUE:
                why = f"GTB/GTC partiellement conforme (avancement {ob.avancement_pct:.0f}%)"
            else:
                why = "Site >290 kW sans GTB/GTC conforme - pénalité applicable"
        else:
            label = ob.type.value.upper()
            why = ob.description or f"Statut: {ob.statut.value}"

        explanations.append({
            "label": label,
            "statut": ob.statut,
            "why": why,
        })

    # Add evidence gap explanation
    manquantes = [e for e in evidences if e.statut == StatutEvidence.MANQUANT]
    if manquantes:
        explanations.append({
            "label": "Preuves manquantes",
            "statut": StatutConformite.A_RISQUE,
            "why": f"{len(manquantes)} document(s) manquant(s) : {', '.join(e.note.split(' - ')[0] for e in manquantes)}",
        })

    # Build actions list from engine templates + evidence gaps
    actions = []
    for ob_type, ob_statut, action_text in _ACTION_TEMPLATES:
        if any(o.type == ob_type and o.statut == ob_statut for o in obligations):
            actions.append(action_text)
    if manquantes:
        actions.append(f"Fournir {len(manquantes)} preuve(s) manquante(s)")

    return {
        "site": site,
        "batiments": batiments,
        "obligations": obligations,
        "evidences": evidences,
        "explanations": explanations,
        "actions": actions,
    }


@router.get("/{site_id}/guardrails")
def get_site_guardrails(site_id: int, db: Session = Depends(get_db)):
    """
    Regles de validation (guardrails) pour un site.
    """
    from services.guardrails import validate_site
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    return validate_site(db, site_id)
