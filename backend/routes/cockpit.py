"""
PROMEOS - Routes API Cockpit & Portefeuilles
Endpoints pour le cockpit exécutif et la gestion des portefeuilles
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
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
from services.consumption_unified_service import get_portfolio_consumption, ConsumptionSource
from schemas.kpi_catalog import wrap_kpi_runtime

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
    sites_actifs = q_sites.count()  # not_deleted() déjà appliqué via _sites_for_org

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

    # A.1: Unified consumption for portfolio KPI
    from datetime import date, timedelta

    today = date.today()
    conso_start = today - timedelta(days=365)
    try:
        conso_portfolio = get_portfolio_consumption(db, effective_org_id, conso_start, today)
        conso_kwh = conso_portfolio["total_kwh"]
        conso_confidence = conso_portfolio["confidence"]
        conso_sites_with_data = conso_portfolio["sites_with_data"]
    except Exception:
        conso_kwh = 0
        conso_confidence = "none"
        conso_sites_with_data = 0

    # KPI runtime metadata for critical KPIs
    kpi_details = [
        wrap_kpi_runtime("compliance_score_composite", compliance_score_unified, perimeter="organisation"),
        wrap_kpi_runtime("risque_financier_euro", round(risque_total, 2), perimeter="organisation"),
        wrap_kpi_runtime("completeness_score", None, perimeter="organisation"),
    ]

    # Action center counts
    try:
        from services.action_center_service import get_action_center_issues

        action_issues = get_action_center_issues(db, effective_org_id)
        action_center_data = {
            "total_issues": action_issues["total"],
            "critical": action_issues["severities"].get("critical", 0),
            "high": action_issues["severities"].get("high", 0),
            "domains": action_issues["domains"],
        }
    except Exception:
        action_center_data = {"total_issues": 0, "critical": 0, "high": 0, "domains": {}}

    return JSONResponse(
        content={
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
                "conso_kwh_total": round(conso_kwh, 2),
                "conso_confidence": conso_confidence,
                "conso_sites_with_data": conso_sites_with_data,
            },
            "kpi_details": kpi_details,
            "action_center": action_center_data,
            "echeance_prochaine": "31 décembre 2026 (Décret Tertiaire 2030)",
        },
        headers={"Cache-Control": "public, max-age=30"},
    )


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


@router.get("/kpi-catalog")
def get_kpi_catalog():
    """GET /api/kpi-catalog — Catalogue machine-readable des KPIs canoniques PROMEOS."""
    from schemas.kpi_catalog import list_kpis, KPI_CATALOG

    return {"count": len(KPI_CATALOG), "kpis": list_kpis()}


@router.get("/cockpit/benchmark")
def get_benchmark(
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    [V110] Positionnement des sites par rapport aux benchmarks ADEME (kWh/m²/an).
    """
    from config.patrimoine_assumptions import BENCHMARK_ADEME_KWH_M2_AN
    from models import not_deleted

    org_id = int(request.headers.get("X-Org-Id", "0")) if request else 0
    sites = not_deleted(db.query(Site), Site).filter(Site.actif == True).all()

    results = []
    for site in sites:
        usage = str(site.type.value if hasattr(site.type, "value") else (site.type or "bureau")).lower()
        surface = site.surface_m2 or 0
        conso = getattr(site, "annual_kwh_total", None) or getattr(site, "conso_kwh_an", None) or 0

        ipe = round(conso / surface, 1) if surface > 0 else None
        bench = BENCHMARK_ADEME_KWH_M2_AN.get(usage, BENCHMARK_ADEME_KWH_M2_AN.get("bureau", {}))

        if ipe is not None and bench:
            if ipe <= bench.get("performant", 0):
                position = "performant"
            elif ipe <= bench.get("bon", 0):
                position = "bon"
            elif ipe <= bench.get("median", 0):
                position = "median"
            else:
                position = "au_dessus"
        else:
            position = None

        results.append(
            {
                "site_id": site.id,
                "site_nom": site.nom,
                "usage": usage,
                "surface_m2": surface,
                "conso_kwh_an": round(conso, 0),
                "ipe_kwh_m2_an": ipe,
                "benchmark": bench,
                "position": position,
            }
        )

    return {
        "sites": results,
        "source": "ADEME Observatoire DPE 2024",
        "unit": "kWh/m²/an",
    }


@router.get("/cockpit/co2")
def get_co2(
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    [V110] Empreinte CO₂ portfolio — facteurs ADEME Base Carbone 2024.
    """
    from services.co2_service import compute_portfolio_co2

    org_id = int(request.headers.get("X-Org-Id", "0")) if request else 0
    return compute_portfolio_co2(db, org_id)
