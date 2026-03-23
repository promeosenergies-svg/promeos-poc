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
from models.reg_assessment import RegAssessment
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

    # RegAssessment — traçabilité source et computed_at (P0-1)
    _ra_computed_at = None
    _ra_sites_evaluated = 0
    _site_ids_for_ra = [s.id for s in _sites_for_org(db, effective_org_id).with_entities(Site.id).all()]
    if _site_ids_for_ra:
        ra_rows = (
            db.query(RegAssessment)
            .filter(
                RegAssessment.object_type == "site",
                RegAssessment.object_id.in_(_site_ids_for_ra),
            )
            .order_by(RegAssessment.object_id, RegAssessment.computed_at.desc())
            .all()
        )
        _ra_latest = {}
        for ra in ra_rows:
            if ra.object_id not in _ra_latest:
                _ra_latest[ra.object_id] = ra
        _ra_sites_evaluated = len(_ra_latest)
        if _ra_latest:
            _ra_computed_at = max(ra.computed_at for ra in _ra_latest.values())

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
                "compliance_source": "RegAssessment",
                "compliance_computed_at": _ra_computed_at.isoformat() if _ra_computed_at else None,
                "sites_evaluated": _ra_sites_evaluated,
                "risque_breakdown": {
                    "reglementaire_eur": round(risque_total, 2),
                    "billing_anomalies_eur": 0,
                    "contract_risk_eur": 0,
                    "total_eur": round(risque_total, 2),
                },
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


@router.get("/cockpit/trajectory")
def get_cockpit_trajectory(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/trajectory
    Trajectoire DT portefeuille — série annuelle pré-calculée backend.
    Jamais calculée côté front (règle architecture P0-3).
    """
    from datetime import datetime
    from models.consumption_target import ConsumptionTarget
    from models.energy_models import Meter, MeterReading, FrequencyType
    from models.batiment import Batiment

    effective_org_id = resolve_org_id(request, auth, db)
    site_ids = [s.id for s in _sites_for_org(db, effective_org_id).with_entities(Site.id).all()]

    if not site_ids:
        return {"error": "no_sites", "annees": [], "reel_mwh": [], "objectif_mwh": []}

    # 1. Targets yearly (ConsumptionTarget, period='yearly')
    yearly_targets = (
        db.query(ConsumptionTarget)
        .filter(
            ConsumptionTarget.site_id.in_(site_ids),
            ConsumptionTarget.period == "yearly",
        )
        .order_by(ConsumptionTarget.year)
        .all()
    )

    # 2. Agréger targets par année (somme multi-sites)
    targets_by_year = {}
    for t in yearly_targets:
        targets_by_year[t.year] = targets_by_year.get(t.year, 0) + (t.target_kwh or 0)

    if not targets_by_year:
        return {
            "error": "no_targets",
            "annees": [],
            "reel_mwh": [],
            "objectif_mwh": [],
            "projection_mwh": [],
        }

    # 3. Année de référence = plus ancienne année avec target
    ref_year = min(targets_by_year.keys())
    ref_kwh = targets_by_year[ref_year]

    # 4. Consommations réelles annuelles depuis MeterReading
    #    Agréger par année civile, filtrer freq granulaires (éviter doublons)
    meter_ids = [m.id for m in db.query(Meter.id).filter(Meter.site_id.in_(site_ids)).all()]
    reel_by_year: dict[int, float] = {}
    if meter_ids:
        from sqlalchemy import extract

        rows = (
            db.query(
                extract("year", MeterReading.timestamp).label("yr"),
                func.sum(MeterReading.value_kwh),
            )
            .filter(
                MeterReading.meter_id.in_(meter_ids),
                MeterReading.frequency.in_(
                    [
                        FrequencyType.MIN_15,
                        FrequencyType.MIN_30,
                        FrequencyType.HOURLY,
                    ]
                ),
            )
            .group_by("yr")
            .all()
        )
        for yr, total in rows:
            reel_by_year[int(yr)] = total

    # 5. Jalons réglementaires DT (décret n°2019-771)
    DT_TARGETS = {2026: -0.25, 2030: -0.40, 2040: -0.50, 2050: -0.60}

    def _interpolate_dt_target(year: int) -> float:
        if year <= ref_year:
            return 0.0
        milestones = sorted(DT_TARGETS.items())
        for i, (my, mr) in enumerate(milestones):
            if year <= my:
                prev_y = ref_year if i == 0 else milestones[i - 1][0]
                prev_r = 0.0 if i == 0 else milestones[i - 1][1]
                if my == prev_y:
                    return mr
                return prev_r + (mr - prev_r) * (year - prev_y) / (my - prev_y)
        return milestones[-1][1]

    # 6. Construire série ref_year → 2030
    annees = list(range(ref_year, 2031))
    reel_mwh = []
    objectif_mwh = []

    for y in annees:
        reel = reel_by_year.get(y)
        reel_mwh.append(round(reel / 1000, 1) if reel else None)
        obj_ratio = _interpolate_dt_target(y)
        objectif_mwh.append(round(ref_kwh * (1 + obj_ratio) / 1000, 1))

    # 7. Réduction cumulée actuelle
    current_year = datetime.now(tz=None).year
    current_year_reel = reel_by_year.get(current_year)
    reduction_pct = None
    if current_year_reel and ref_kwh > 0:
        reduction_pct = round((1 - current_year_reel / ref_kwh) * 100, 1)

    # Surface totale
    surface_total = (db.query(func.sum(Batiment.surface_m2)).filter(Batiment.site_id.in_(site_ids)).scalar()) or 0

    return {
        "ref_year": ref_year,
        "ref_kwh": round(ref_kwh / 1000, 1),
        "reduction_pct_actuelle": reduction_pct,
        "objectif_2026_pct": -25.0,
        "annees": annees,
        "reel_mwh": reel_mwh,
        "objectif_mwh": objectif_mwh,
        "projection_mwh": [],
        "jalons": [
            {"annee": 2026, "reduction_pct": -25.0},
            {"annee": 2030, "reduction_pct": -40.0},
            {"annee": 2040, "reduction_pct": -50.0},
            {"annee": 2050, "reduction_pct": -60.0},
        ],
        "surface_m2_total": round(surface_total, 1),
        "computed_at": datetime.now(tz=None).isoformat(),
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
