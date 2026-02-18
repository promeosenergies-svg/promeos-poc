"""
PROMEOS - Routes API Cockpit & Portefeuilles
Endpoints pour le cockpit exécutif et la gestion des portefeuilles
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from database import get_db
from models import (
    Organisation, Portefeuille, EntiteJuridique, Site, Alerte,
    StatutConformite, not_deleted,
)
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import get_scope_org_id

router = APIRouter(prefix="/api", tags=["Cockpit"])


def _get_org_id(request: Request) -> int | None:
    """Extract X-Org-Id from request headers (injected by frontend scope interceptor)."""
    raw = request.headers.get("X-Org-Id")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return None


def _sites_for_org(db: Session, org_id: int | None):
    """Base query for non-deleted sites filtered by org_id via the join chain."""
    q = (
        not_deleted(db.query(Site), Site)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
    )
    if org_id is not None:
        q = q.filter(EntiteJuridique.organisation_id == org_id)
    return q


@router.get("/cockpit")
def get_cockpit(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit
    Statistiques globales pour le cockpit exécutif.
    Scope priority: auth.org_id > X-Org-Id header > DemoState > last org.
    """
    # V18-E: canonical scope resolution (auth > header > demo fallback)
    org_id = get_scope_org_id(request, auth)

    # Resolve organisation — canonical priority then demo fallback
    if org_id is not None:
        org = db.query(Organisation).filter(Organisation.id == org_id).first()
    else:
        from services.demo_state import DemoState
        demo_org_id = DemoState.get_demo_org_id()
        if demo_org_id:
            org = db.query(Organisation).filter(Organisation.id == demo_org_id).first()
        else:
            org = db.query(Organisation).order_by(Organisation.id.desc()).first()

    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    # Use resolved org_id for all site queries
    effective_org_id = org.id

    # Stats sites (exclude soft-deleted, scoped to org)
    q_sites = _sites_for_org(db, effective_org_id)
    total_sites = q_sites.count()
    sites_actifs = q_sites.filter(Site.actif == True).count()

    # Stats conformite
    sites_tertiaire_ko = _sites_for_org(db, effective_org_id).filter(
        Site.statut_decret_tertiaire == "non_conforme"
    ).count()

    sites_bacs_ko = _sites_for_org(db, effective_org_id).filter(
        Site.statut_bacs == "non_conforme"
    ).count()

    # Risque financier total
    risque_total = (
        _sites_for_org(db, effective_org_id)
        .with_entities(func.sum(Site.risque_financier_euro))
        .scalar() or 0
    )

    # Avancement moyen decret tertiaire
    avg_avancement = (
        _sites_for_org(db, effective_org_id)
        .with_entities(func.avg(Site.avancement_decret_pct))
        .scalar() or 0
    )

    # Alertes actives — scoped to org's sites
    site_ids = [s.id for s in _sites_for_org(db, effective_org_id).with_entities(Site.id).all()]
    alertes_actives = (
        db.query(Alerte)
        .filter(Alerte.resolue == False, Alerte.site_id.in_(site_ids))
        .count()
    ) if site_ids else 0

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
def get_portefeuilles(request: Request, db: Session = Depends(get_db)):
    """
    GET /api/portefeuilles
    Liste des portefeuilles avec stats, scoped to X-Org-Id.
    """
    org_id = _get_org_id(request)

    q = (
        not_deleted(db.query(Portefeuille), Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
    )
    if org_id is not None:
        q = q.filter(EntiteJuridique.organisation_id == org_id)

    portefeuilles = q.all()

    result = []
    for p in portefeuilles:
        nb_sites = not_deleted(db.query(Site), Site).filter(Site.portefeuille_id == p.id).count()

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
