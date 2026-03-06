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
    Organisation,
    Portefeuille,
    EntiteJuridique,
    Site,
    Alerte,
    StatutConformite,
    not_deleted,
)
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id
from services.kpi_service import KpiService, KpiScope

router = APIRouter(prefix="/api", tags=["Cockpit"])


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
    # DEMO_MODE-aware scope resolution (auth > header > demo fallback > 401)
    effective_org_id = resolve_org_id(request, auth, db)
    org = db.query(Organisation).filter(Organisation.id == effective_org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    # Stats sites (exclude soft-deleted, scoped to org)
    q_sites = _sites_for_org(db, effective_org_id)
    total_sites = q_sites.count()
    sites_actifs = q_sites.filter(Site.actif == True).count()

    # Stats conformite (compare to enum, not string)
    sites_tertiaire_ko = (
        _sites_for_org(db, effective_org_id)
        .filter(
            Site.statut_decret_tertiaire.in_(
                [
                    StatutConformite.NON_CONFORME,
                    StatutConformite.A_RISQUE,
                ]
            )
        )
        .count()
    )

    sites_bacs_ko = (
        _sites_for_org(db, effective_org_id)
        .filter(
            Site.statut_bacs.in_(
                [
                    StatutConformite.NON_CONFORME,
                    StatutConformite.A_RISQUE,
                ]
            )
        )
        .count()
    )

    # Risque financier + avancement via KpiService (centralized)
    kpi = KpiService(db)
    _scope = KpiScope(org_id=effective_org_id)
    risque_total = kpi.get_financial_risk_eur(_scope).value
    avg_avancement = kpi.get_avancement_decret_pct(_scope).value

    # Score conformité unifié A.2
    compliance_kpi = kpi.get_compliance_score(_scope)
    compliance_score_unified = compliance_kpi.value
    compliance_confidence = compliance_kpi.confidence

    # Alertes actives — scoped to org's sites
    site_ids = [s.id for s in _sites_for_org(db, effective_org_id).with_entities(Site.id).all()]
    alertes_actives = (
        (db.query(Alerte).filter(Alerte.resolue == False, Alerte.site_id.in_(site_ids)).count()) if site_ids else 0
    )

    return {
        "organisation": {"nom": org.nom, "type_client": org.type_client},
        "stats": {
            "total_sites": total_sites,
            "sites_actifs": sites_actifs,
            "avancement_decret_pct": round(avg_avancement, 1),
            "risque_financier_euro": round(risque_total, 2),
            "sites_tertiaire_ko": sites_tertiaire_ko,
            "sites_bacs_ko": sites_bacs_ko,
            "alertes_actives": alertes_actives,
            "compliance_score": compliance_score_unified,
            "compliance_confidence": compliance_confidence,
        },
        "echeance_prochaine": "31 décembre 2026 (Décret Tertiaire 2030)",
    }


@router.get("/portefeuilles")
def get_portefeuilles(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/portefeuilles
    Liste des portefeuilles avec stats, scoped to org (DEMO_MODE-aware).
    """
    org_id = resolve_org_id(request, auth, db)

    q = (
        not_deleted(db.query(Portefeuille), Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
    )

    portefeuilles = q.all()

    # Single query for all site counts (fixes N+1)
    ptf_ids = [p.id for p in portefeuilles]
    count_rows = (
        (
            not_deleted(db.query(Site.portefeuille_id, func.count(Site.id)), Site)
            .filter(Site.portefeuille_id.in_(ptf_ids))
            .group_by(Site.portefeuille_id)
            .all()
        )
        if ptf_ids
        else []
    )
    count_map = {pid: cnt for pid, cnt in count_rows}

    result = []
    for p in portefeuilles:
        result.append({"id": p.id, "nom": p.nom, "description": p.description, "nb_sites": count_map.get(p.id, 0)})

    return {"portefeuilles": result, "total": len(result)}
