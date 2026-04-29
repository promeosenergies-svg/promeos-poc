"""
PROMEOS - Routes API Cockpit & Portefeuilles
Endpoints pour le cockpit exécutif et la gestion des portefeuilles
"""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from database import get_db
from schemas.cockpit_schemas import (
    CockpitResponse,
    PortefeuillesResponse,
    KpiCatalogResponse,
    BenchmarkResponse,
    TrajectoryResponse,
    ConsoMonthResponse,
    Co2Response,
)
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
from middleware.cx_logger import log_cx_event
from services.scope_utils import resolve_org_id
from services.kpi_service import KpiService, KpiScope
from services.consumption_unified_service import get_portfolio_consumption, ConsumptionSource
from schemas.kpi_catalog import wrap_kpi_runtime
from config.default_prices import DEFAULT_PRICE_ELEC_EUR_KWH

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


def _statut_dt_value(site) -> str | None:
    """Extract Decret Tertiaire status string from Site model (handles enum or str).

    Returns the canonical lowercase value ("conforme"/"non_conforme"/"a_risque"/...)
    or None if the site has no status set.
    """
    raw = getattr(site, "statut_decret_tertiaire", None)
    if raw is None:
        return None
    return raw.value if hasattr(raw, "value") else str(raw)


def _count_dt_statuts(sites_objs) -> dict:
    """Count sites by Decret Tertiaire status in a single Python pass.

    Replaces N separate `_sites_for_org(...).filter(...).count()` SQL queries
    with one in-memory iteration over already-loaded site objects (perf F1+F3
    from /simplify audit).

    Returns dict: {conforme, non_conforme, a_risque, en_evaluation, total}.
    """
    counts = {"conforme": 0, "non_conforme": 0, "a_risque": 0, "en_evaluation": 0}
    for s in sites_objs:
        v = _statut_dt_value(s)
        if v in counts:
            counts[v] += 1
    counts["total"] = len(sites_objs)
    return counts


@router.get("/cockpit", responses={200: {"model": CockpitResponse}})
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

    log_cx_event(
        db,
        effective_org_id,
        auth.user.id if auth else None,
        "CX_DASHBOARD_OPENED",
        {"endpoint": "cockpit"},
    )

    # Stats sites (exclude soft-deleted, scoped to org)
    q_sites = _sites_for_org(db, effective_org_id)
    total_sites = q_sites.count()
    sites_actifs = total_sites  # not_deleted() déjà appliqué via _sites_for_org

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

    # Site IDs — single fetch, reused for RegAssessment, alertes, conso, billing
    sites_objs = _sites_for_org(db, effective_org_id).all()
    site_ids = [s.id for s in sites_objs]

    # RegAssessment — traçabilité source et computed_at (P0-1)
    _ra_computed_at = None
    _ra_sites_evaluated = 0
    if site_ids:
        ra_rows = (
            db.query(RegAssessment)
            .filter(
                RegAssessment.object_type == "site",
                RegAssessment.object_id.in_(site_ids),
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
        # Dominant source across portfolio sites
        from collections import Counter

        _src_counts = Counter(s["source_used"] for s in conso_portfolio.get("sites", []) if s.get("value_kwh", 0) > 0)
        _conso_dominant_source = _src_counts.most_common(1)[0][0] if _src_counts else "none"
    except Exception:
        conso_kwh = 0
        conso_confidence = "none"
        conso_sites_with_data = 0
        _conso_dominant_source = "none"

    # Declared consumption (patrimoine) for transparency
    _conso_declared_kwh = sum(s.annual_kwh_total or 0 for s in sites_objs)

    # Billing anomalies loss for risque_breakdown (P0-2: excl. resolved + false_positive)
    _billing_loss = 0.0
    try:
        from models import BillingInsight
        from models.enums import InsightStatus

        _billing_loss = (
            db.query(func.sum(BillingInsight.estimated_loss_eur))
            .filter(
                BillingInsight.site_id.in_(site_ids),
                BillingInsight.insight_status.notin_([InsightStatus.RESOLVED, InsightStatus.FALSE_POSITIVE]),
            )
            .scalar()
        ) or 0.0
    except Exception:
        _billing_loss = 0.0

    # Contract risk (P1-A2: renewal + price gap + volume penalties)
    _contract_risk = 0.0
    try:
        from services.contract_risk_service import compute_contract_risk_eur

        _contract_risk_data = compute_contract_risk_eur(db, site_ids)
        _contract_risk = _contract_risk_data["total_eur"]
    except Exception:
        _contract_risk = 0.0

    # D.3: Contrats expirant sous 90j + génération alertes automatiques
    _contrats_expirant_90j = 0
    try:
        from services.contract_expiration_alerts import generate_contract_expiration_alerts

        exp_result = generate_contract_expiration_alerts(db, site_ids, horizon_days=90)
        _contrats_expirant_90j = exp_result["contrats_expirant_90j"]
        db.commit()
    except Exception:
        _contrats_expirant_90j = 0

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
                    "billing_anomalies_eur": round(_billing_loss, 2),
                    "contract_risk_eur": round(_contract_risk, 2),
                    "total_eur": round(risque_total + _billing_loss + _contract_risk, 2),
                },
                "conso_kwh_total": round(conso_kwh, 2),
                "conso_declared_kwh": round(_conso_declared_kwh, 2),
                "conso_confidence": conso_confidence,
                "conso_sites_with_data": conso_sites_with_data,
                "conso_source": _conso_dominant_source,
                "contrats_expirant_90j": _contrats_expirant_90j,
            },
            "kpi_details": kpi_details,
            "action_center": action_center_data,
            "echeance_prochaine": "30 septembre 2026 (Déclaration OPERAT — consommations 2025)",
        },
        headers={"Cache-Control": "public, max-age=30"},
    )


@router.get("/portefeuilles", response_model=PortefeuillesResponse)
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


@router.get("/kpi-catalog", response_model=KpiCatalogResponse)
def get_kpi_catalog():
    """GET /api/kpi-catalog — Catalogue machine-readable des KPIs canoniques PROMEOS."""
    from schemas.kpi_catalog import list_kpis, KPI_CATALOG

    return {"count": len(KPI_CATALOG), "kpis": list_kpis()}


@router.get("/cockpit/benchmark", response_model=BenchmarkResponse)
def get_benchmark(
    db: Session = Depends(get_db),
    request: Request = None,
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    [V110] Positionnement des sites par rapport aux benchmarks ADEME (kWh/m²/an).
    """
    from config.patrimoine_assumptions import BENCHMARK_ADEME_KWH_M2_AN
    from models import not_deleted

    # I8 FIX: utiliser resolve_org_id (chaîne de fallback standard)
    org_id = resolve_org_id(request, auth, db)
    site_ids = [s.id for s in _sites_for_org(db, org_id).with_entities(Site.id).all()]
    sites = not_deleted(db.query(Site), Site).filter(Site.id.in_(site_ids), Site.actif == True).all()

    # Unified consumption for each site (single source of truth for IPE)
    from services.consumption_unified_service import get_consumption_summary

    today_bench = date.today()
    y_ago_bench = today_bench - timedelta(days=365)

    results = []
    for site in sites:
        usage = str(site.type.value if hasattr(site.type, "value") else (site.type or "bureau")).lower()
        surface = site.surface_m2 or 0

        # Consommation via unified service (metered > billed > estimated)
        try:
            conso_summary = get_consumption_summary(db, site.id, y_ago_bench, today_bench)
            conso = conso_summary.get("value_kwh", 0) or 0
        except Exception:
            conso = getattr(site, "annual_kwh_total", None) or 0

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


@router.get("/cockpit/trajectory", response_model=TrajectoryResponse)
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
        return {
            "error": "no_sites",
            "annees": [],
            "reel_mwh": [],
            "objectif_mwh": [],
            # Jalons officiels Decret n°2019-771 (pas de jalon 2026)
            "jalons": [
                {"annee": 2030, "reduction_pct": -40.0, "deadline": "2031-12-31", "is_official": True},
                {"annee": 2040, "reduction_pct": -50.0, "deadline": "2041-12-31", "is_official": True},
                {"annee": 2050, "reduction_pct": -60.0, "deadline": "2051-12-31", "is_official": True},
            ],
        }

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
            # Jalons officiels Decret n°2019-771 (pas de jalon 2026)
            "jalons": [
                {"annee": 2030, "reduction_pct": -40.0, "deadline": "2031-12-31", "is_official": True},
                {"annee": 2040, "reduction_pct": -50.0, "deadline": "2041-12-31", "is_official": True},
                {"annee": 2050, "reduction_pct": -60.0, "deadline": "2051-12-31", "is_official": True},
            ],
        }

    # 3. Année de référence = plus ancienne année avec target
    ref_year = min(targets_by_year.keys())
    ref_kwh = targets_by_year[ref_year]

    # 4. Consommations réelles annuelles depuis ConsumptionTarget.actual_kwh (rapide)
    #    Priorité aux targets yearly avec actual_kwh renseigné (seed + import)
    #    Fallback MeterReading si actual_kwh absent (lent sur SQLite)
    reel_by_year: dict[int, float] = {}

    # Source rapide : actual_kwh des targets yearly
    for t in yearly_targets:
        if t.actual_kwh and t.actual_kwh > 0:
            y = t.year
            reel_by_year[y] = reel_by_year.get(y, 0) + t.actual_kwh

    # Fallback : unified consumption service si aucun actual_kwh trouvé
    if not reel_by_year:
        from services.consumption_unified_service import get_consumption_summary as _get_conso

        for sid in site_ids:
            for yr in range(ref_year, date.today().year + 1):
                try:
                    s = _get_conso(db, sid, date(yr, 1, 1), date(yr, 12, 31))
                    v = s.get("value_kwh", 0) or 0
                    if v > 0:
                        reel_by_year[yr] = reel_by_year.get(yr, 0) + v
                except Exception:
                    pass

    # 5. Jalons réglementaires DT (décret n°2019-771 — Art. R131-39 CCH)
    # Source : legifrance.gouv.fr/jorf/id/JORFTEXT000038812251
    # NOTE : pas de jalon officiel en 2026 — le premier jalon est 2030
    DT_TARGETS = {2030: -0.40, 2040: -0.50, 2050: -0.60}

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

    current_year_val = datetime.now(tz=None).year
    current_month = datetime.now(tz=None).month
    for y in annees:
        reel = reel_by_year.get(y)
        # Exclure l'année en cours si données partielles (< 10 mois)
        if y == current_year_val and current_month < 10:
            reel_mwh.append(None)  # pas de point réel pour année partielle
        else:
            reel_mwh.append(round(reel / 1000, 1) if reel else None)
        obj_ratio = _interpolate_dt_target(y)
        objectif_mwh.append(round(ref_kwh * (1 + obj_ratio) / 1000, 1))

    # 7. Réduction cumulée actuelle
    # Utiliser la dernière année COMPLÈTE pour éviter de comparer 3 mois vs 12 mois
    current_year = datetime.now(tz=None).year
    last_full_year = current_year - 1
    best_reel = reel_by_year.get(last_full_year) or reel_by_year.get(current_year)
    reduction_pct = None
    reduction_year = None
    if best_reel and ref_kwh > 0:
        reduction_year = last_full_year if last_full_year in reel_by_year else current_year
        # Convention maquette : négatif = réduction (ex: -18% = 18% de réduction)
        reduction_pct = round((best_reel / ref_kwh - 1) * 100, 1)

    # Surface totale
    surface_total = (db.query(func.sum(Batiment.surface_m2)).filter(Batiment.site_id.in_(site_ids)).scalar()) or 0

    # 8. Projection trajectoire depuis actions planifiées (P1)
    from models.action_item import ActionItem

    _proj_actions = (
        db.query(ActionItem)
        .filter(ActionItem.site_id.in_(site_ids), ActionItem.status.in_(["open", "in_progress"]))
        .all()
    )
    _savings_kwh = (
        sum(a.estimated_gain_eur or 0 for a in _proj_actions) / DEFAULT_PRICE_ELEC_EUR_KWH if _proj_actions else 0
    )
    projection_mwh = []
    _cy = datetime.now(tz=None).year
    if _savings_kwh > 0:
        # Base de projection = dernière année COMPLÈTE (pas l'année en cours partielle)
        _lr = reel_by_year.get(_cy - 1)
        for y in annees:
            if y < _cy or _lr is None:
                projection_mwh.append(None)
            else:
                # Les savings s'appliquent UNE FOIS (réduction permanente), pas cumulativement
                projection_mwh.append(max(0, round((_lr - _savings_kwh) / 1000, 1)))

    return {
        "ref_year": ref_year,
        "ref_kwh": round(ref_kwh / 1000, 1),
        "reduction_pct_actuelle": reduction_pct,
        "reduction_year": reduction_year,
        "objectif_2030_pct": -40.0,  # premier jalon officiel DT (décret n°2019-771)
        "annees": annees,
        "reel_mwh": reel_mwh,
        "objectif_mwh": objectif_mwh,
        "projection_mwh": projection_mwh,
        "projection_savings_kwh_an": round(_savings_kwh) if _savings_kwh > 0 else 0,
        # Jalons officiels Decret n°2019-771, art. R131-39 CCH
        # Il n'existe PAS de jalon 2026 dans le texte reglementaire
        "jalons": [
            {"annee": 2030, "reduction_pct": -40.0, "deadline": "2031-12-31", "is_official": True},
            {"annee": 2040, "reduction_pct": -50.0, "deadline": "2041-12-31", "is_official": True},
            {"annee": 2050, "reduction_pct": -60.0, "deadline": "2051-12-31", "is_official": True},
        ],
        "source_reglementaire": "Décret n°2019-771, Art. R131-39 CCH",
        "surface_m2_total": round(surface_total, 1),
        "computed_at": datetime.now(tz=None).isoformat(),
    }


@router.get("/cockpit/conso-month", response_model=ConsoMonthResponse)
def get_cockpit_conso_month(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Consommation du mois courant — source ConsumptionTarget.actual_kwh."""
    from datetime import datetime as _dt
    from models.consumption_target import ConsumptionTarget

    effective_org_id = resolve_org_id(request, auth, db)
    site_ids = [s.id for s in _sites_for_org(db, effective_org_id).with_entities(Site.id).all()]
    today = _dt.now(tz=None)
    cm, cy = today.month, today.year

    monthly = (
        db.query(ConsumptionTarget)
        .filter(
            ConsumptionTarget.site_id.in_(site_ids),
            ConsumptionTarget.year == cy,
            ConsumptionTarget.month == cm,
            ConsumptionTarget.period.in_(["monthly", "month"]),
            ConsumptionTarget.energy_type == "electricity",
        )
        .all()
    )
    actual = sum(t.actual_kwh or 0 for t in monthly)
    target = sum(t.target_kwh or 0 for t in monthly)
    sites_data = sum(1 for t in monthly if t.actual_kwh)

    pm = cm - 1 if cm > 1 else 12
    py = cy if cm > 1 else cy - 1
    prev = (
        db.query(ConsumptionTarget)
        .filter(
            ConsumptionTarget.site_id.in_(site_ids),
            ConsumptionTarget.year == py,
            ConsumptionTarget.month == pm,
            ConsumptionTarget.period.in_(["monthly", "month"]),
            ConsumptionTarget.energy_type == "electricity",
        )
        .all()
    )
    prev_kwh = sum(t.actual_kwh or 0 for t in prev)
    delta = round((actual - prev_kwh) / prev_kwh * 100, 1) if prev_kwh > 0 and actual > 0 else None

    return {
        "year": cy,
        "month": cm,
        "actual_kwh": round(actual) if actual else None,
        "actual_mwh": round(actual / 1000, 1) if actual else None,
        "target_kwh": round(target) if target else None,
        "delta_vs_prev_month_pct": delta,
        "sites_with_data": sites_data,
        "total_sites": len(site_ids),
        "source": "ConsumptionTarget.actual_kwh",
    }


@router.get("/cockpit/co2", response_model=Co2Response)
def get_co2(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    [V110] Empreinte CO₂ portfolio — facteurs ADEME Base Carbone 2024.
    """
    from services.co2_service import compute_portfolio_co2

    effective_org_id = resolve_org_id(request, auth, db)
    return compute_portfolio_co2(db, effective_org_id)


# ── Endpoint #1 : GET /api/cockpit/_facts.scope ───────────────────────────


@router.get("/cockpit/_facts.scope")
def get_cockpit_facts_scope(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/_facts.scope
    Périmètre organisationnel du scope courant : org_id, org_name, site_count,
    portefeuille_count. Utilisé par le frontend pour afficher le scope actif.
    """
    org_id = resolve_org_id(request, auth, db)
    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation non trouvée")

    site_count = _sites_for_org(db, org_id).count()
    portefeuille_count = (
        not_deleted(db.query(Portefeuille), Portefeuille)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .count()
    )

    return {
        "org_id": org_id,
        "org_name": org.nom,
        "site_count": site_count,
        "portefeuille_count": portefeuille_count,
    }


# ── Endpoint #2 : GET /api/cockpit/_facts.alerts ─────────────────────────


@router.get("/cockpit/_facts.alerts")
def get_cockpit_facts_alerts(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/_facts.alerts
    Agrégation alertes + issues action center pour le scope courant.
    Retourne {count, top:[{id, title, priority, domain}]} (top 5 critiques).
    """
    org_id = resolve_org_id(request, auth, db)
    site_ids = [s.id for s in _sites_for_org(db, org_id).with_entities(Site.id).all()]

    # Alertes DB actives (Alerte model)
    alerte_rows = (
        db.query(Alerte).filter(Alerte.resolue == False, Alerte.site_id.in_(site_ids)).all() if site_ids else []
    )
    alert_count = len(alerte_rows)

    # Issues action center (cross-domain)
    top_items = []
    try:
        from services.action_center_service import get_action_center_issues

        issues_data = get_action_center_issues(db, org_id)
        for issue in issues_data.get("issues", [])[:5]:
            top_items.append(
                {
                    "id": issue.get("issue_id", ""),
                    "title": issue.get("title", issue.get("issue_label", "")),
                    "priority": issue.get("severity", "medium"),
                    "domain": issue.get("domain", ""),
                }
            )
        # Add alert count from action center total
        ac_total = issues_data.get("total", 0)
    except Exception:
        ac_total = 0

    return {
        "count": alert_count + ac_total,
        "alerte_db_count": alert_count,
        "action_center_count": ac_total,
        "top": top_items,
    }


# ── Endpoint #4 : GET /api/cockpit/cdc ───────────────────────────────────


@router.get("/cockpit/cdc")
def get_cockpit_cdc(
    request: Request,
    period: str = "j_minus_1",
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/cdc?period=j_minus_1
    Courbe de charge J-1 du compteur principal du scope.
    Délègue à cdc_service.query_cdc. Retourne hp_kwh[], hc_kwh[],
    puissance_souscrite_kva, puissance_max_kva.
    """
    from models.energy_models import Meter
    from services.ems.cdc_service import query_cdc

    org_id = resolve_org_id(request, auth, db)
    site_ids = [s.id for s in _sites_for_org(db, org_id).with_entities(Site.id).all()]

    if not site_ids:
        return {
            "period": period,
            "error": "no_sites",
            "hp_kwh": [],
            "hc_kwh": [],
            "puissance_souscrite_kva": None,
            "puissance_max_kva": None,
        }

    # Résolution J-1
    today = date.today()
    if period == "j_minus_1":
        target_date = today - timedelta(days=1)
    elif period == "j_minus_7":
        target_date = today - timedelta(days=7)
    else:
        target_date = today - timedelta(days=1)

    # Trouver le compteur principal du premier site avec un compteur
    meter = None
    for sid in site_ids:
        meter = db.query(Meter).filter(Meter.site_id == sid, Meter.is_active == True).first()
        if meter:
            break

    if not meter:
        return {
            "period": period,
            "error": "no_meter",
            "hp_kwh": [],
            "hc_kwh": [],
            "puissance_souscrite_kva": None,
            "puissance_max_kva": None,
        }

    cdc = query_cdc(db, meter.id, target_date, target_date)

    # Agréger les points par slot HP/HC
    hp_points = [p["kw"] for p in cdc.get("points", []) if p.get("slot") in ("HP", "HPH", "HPE", "Pointe")]
    hc_points = [p["kw"] for p in cdc.get("points", []) if p.get("slot") in ("HC", "HCH", "HCE", "Base")]
    all_kw = [p["kw"] for p in cdc.get("points", []) if p.get("kw") is not None]
    puissance_max = round(max(all_kw), 2) if all_kw else None

    # Puissance souscrite depuis ps_map (contrat)
    ps_map = cdc.get("ps", {})
    puissance_souscrite = None
    if ps_map:
        ps_vals = [v for v in ps_map.values() if v]
        puissance_souscrite = round(max(ps_vals), 2) if ps_vals else None

    return {
        "period": period,
        "date": target_date.isoformat(),
        "meter_id": meter.id,
        "hp_kwh": hp_points,
        "hc_kwh": hc_points,
        "puissance_souscrite_kva": puissance_souscrite,
        "puissance_max_kva": puissance_max,
        "point_count": len(cdc.get("points", [])),
    }


# ── Endpoint #5 : GET /api/cockpit/priorities ────────────────────────────


@router.get("/cockpit/priorities")
def get_cockpit_priorities(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/priorities
    Top-5 priorités cross-pillar pour le scope : alertes + actions overdue
    + risque financier. Retourne [{rank, title, urgency, domain, action_url}].
    """
    from datetime import datetime as _dt

    org_id = resolve_org_id(request, auth, db)
    site_ids = [s.id for s in _sites_for_org(db, org_id).with_entities(Site.id).all()]

    priorities = []

    # Source 1 : Issues action center critiques/high
    try:
        from services.action_center_service import get_action_center_issues

        issues_data = get_action_center_issues(db, org_id)
        for issue in issues_data.get("issues", []):
            sev = issue.get("severity", "medium")
            if sev in ("critical", "high"):
                priorities.append(
                    {
                        "title": issue.get("title", issue.get("issue_label", "")),
                        "urgency": sev,
                        "domain": issue.get("domain", ""),
                        "action_url": f"/anomalies?issue={issue.get('issue_id', '')}",
                        "_sort_key": 0 if sev == "critical" else 1,
                    }
                )
    except Exception:
        pass

    # Source 2 : Actions plan items overdue (status open/in_progress + due_date dépassée)
    try:
        from models.action_plan_item import ActionPlanItem

        now = _dt.utcnow()
        overdue = (
            (
                db.query(ActionPlanItem)
                .filter(
                    ActionPlanItem.site_id.in_(site_ids),
                    ActionPlanItem.status.in_(["open", "in_progress"]),
                    ActionPlanItem.due_date != None,  # noqa: E711
                    ActionPlanItem.due_date < now,
                )
                .order_by(ActionPlanItem.due_date.asc())
                .limit(5)
                .all()
            )
            if site_ids
            else []
        )

        for item in overdue:
            priorities.append(
                {
                    "title": item.issue_label,
                    "urgency": item.priority or "high",
                    "domain": item.domain,
                    "action_url": f"/action-center?action={item.id}",
                    "_sort_key": 0 if item.priority == "critical" else 1,
                }
            )
    except Exception:
        pass

    # Source 3 : Risque financier élevé (>5000 EUR)
    try:
        kpi = KpiService(db)
        _scope = KpiScope(org_id=org_id)
        risque = kpi.get_financial_risk_eur(_scope).value
        if risque > 5000:
            priorities.append(
                {
                    "title": f"Risque financier réglementaire : {round(risque):,} EUR",
                    "urgency": "high",
                    "domain": "compliance",
                    "action_url": "/cockpit",
                    "_sort_key": 1,
                }
            )
    except Exception:
        pass

    # Trier par urgency + dédupliquer + limiter top-5
    priorities.sort(key=lambda x: (x.pop("_sort_key", 1), x.get("title", "")))
    seen_titles = set()
    top5 = []
    for p in priorities:
        if p["title"] not in seen_titles:
            seen_titles.add(p["title"])
            top5.append({**p, "rank": len(top5) + 1})
        if len(top5) >= 5:
            break

    return {"priorities": top5, "total": len(top5)}


@router.get("/cockpit/levers")
def get_cockpit_levers(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/levers

    Phase 1.4.c — Moteur de leviers actionables (migration ex-`models/leverEngineModel.js`).

    Agrège les leviers conformité + facturation + optimisation + achat d'énergie
    à partir des données scope. Tri par impact_eur desc (null en dernier).

    Réponse :
        {
            "lever_result": LeverResult.to_dict()
        }
    """
    from services.lever_engine_service import compute_actionable_levers
    from models.enums import InsightStatus

    org_id = resolve_org_id(request, auth, db)
    sites_objs = _sites_for_org(db, org_id).all()
    site_ids = [s.id for s in sites_objs]
    total_sites = len(site_ids)

    # KPIs conformité — single fetch sites + Python count (perf F1+F3 /simplify audit)
    kpi = KpiService(db)
    _scope = KpiScope(org_id=org_id)
    risque_total = 0.0
    try:
        risque_total = kpi.get_financial_risk_eur(_scope).value or 0.0
    except Exception:
        risque_total = 0.0

    statut_counts = _count_dt_statuts(sites_objs)
    kpis_payload = {
        "total": total_sites,
        "nonConformes": statut_counts["non_conforme"],
        "aRisque": statut_counts["a_risque"],
        "risqueTotal": float(risque_total),
    }

    # Billing summary
    total_eur = 0.0
    total_loss_eur = 0.0
    invoices_with_anomalies = 0
    total_invoices = 0
    try:
        from models import EnergyInvoice, BillingInsight

        if site_ids:
            total_eur = (
                db.query(func.sum(EnergyInvoice.amount_eur)).filter(EnergyInvoice.site_id.in_(site_ids)).scalar()
            ) or 0.0
            total_invoices = db.query(EnergyInvoice).filter(EnergyInvoice.site_id.in_(site_ids)).count()
            total_loss_eur = (
                db.query(func.sum(BillingInsight.estimated_loss_eur))
                .filter(
                    BillingInsight.site_id.in_(site_ids),
                    BillingInsight.insight_status.notin_([InsightStatus.RESOLVED, InsightStatus.FALSE_POSITIVE]),
                )
                .scalar()
            ) or 0.0
            invoices_with_anomalies = (
                db.query(BillingInsight)
                .filter(
                    BillingInsight.site_id.in_(site_ids),
                    BillingInsight.insight_status.notin_([InsightStatus.RESOLVED, InsightStatus.FALSE_POSITIVE]),
                )
                .count()
            )
    except Exception:
        pass

    billing_payload = {
        "total_eur": float(total_eur),
        "total_loss_eur": float(total_loss_eur),
        "invoices_with_anomalies": invoices_with_anomalies,
        "total_invoices": total_invoices,
    }

    lever_result = compute_actionable_levers(
        kpis=kpis_payload,
        billing_summary=billing_payload,
    )

    return {"lever_result": lever_result.to_dict()}


@router.get("/cockpit/impact_decision")
def get_cockpit_impact_decision(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/impact_decision

    Phase 1.4.b — Endpoint Impact & Décision (migration ex-`models/impactDecisionModel.js`).

    Calcule les 3 KPIs Impact & Décision déterministes (risque conformité,
    surcoût facture, opportunité optimisation) + recommandation prioritaire
    rule-based à partir des données scope + billing.

    Réponse :
        {
            "impact": ImpactKpis (3 valeurs + 3 drapeaux available),
            "recommendation": Recommendation (key/titre/bullets/cta/cta_path)
        }
    """
    from services.impact_decision_service import compute_impact_kpis, compute_recommendation

    org_id = resolve_org_id(request, auth, db)
    sites_objs = _sites_for_org(db, org_id).all()
    site_ids = [s.id for s in sites_objs]
    total_sites = len(site_ids)

    # Risque financier conformité
    risque_total = 0.0
    try:
        kpi = KpiService(db)
        _scope = KpiScope(org_id=org_id)
        risque_total = kpi.get_financial_risk_eur(_scope).value or 0.0
    except Exception:
        risque_total = 0.0

    # Comptage statuts DT — single Python pass sur sites_objs déjà chargés
    statut_counts = _count_dt_statuts(sites_objs)
    non_conformes = statut_counts["non_conforme"]
    a_risque = statut_counts["a_risque"]

    # Billing summary — total facturé + total loss
    total_eur = 0.0
    total_loss_eur = 0.0
    total_invoices = 0
    try:
        from models import EnergyInvoice

        if site_ids:
            total_eur = (
                db.query(func.sum(EnergyInvoice.amount_eur)).filter(EnergyInvoice.site_id.in_(site_ids)).scalar()
            ) or 0.0
            total_invoices = db.query(EnergyInvoice).filter(EnergyInvoice.site_id.in_(site_ids)).count()
        from models import BillingInsight
        from models.enums import InsightStatus

        if site_ids:
            total_loss_eur = (
                db.query(func.sum(BillingInsight.estimated_loss_eur))
                .filter(
                    BillingInsight.site_id.in_(site_ids),
                    BillingInsight.insight_status.notin_([InsightStatus.RESOLVED, InsightStatus.FALSE_POSITIVE]),
                )
                .scalar()
            ) or 0.0
    except Exception:
        pass

    kpis_payload = {
        "risque_total_eur": float(risque_total),
        "total": total_sites,
        "non_conformes": non_conformes,
        "a_risque": a_risque,
    }
    billing_payload = {
        "total_eur": float(total_eur),
        "total_loss_eur": float(total_loss_eur),
        "total_invoices": total_invoices,
    }

    impact = compute_impact_kpis(kpis_payload, billing_payload)
    recommendation = compute_recommendation(impact, kpis_payload)

    return {
        "impact": impact.to_dict(),
        "recommendation": recommendation.to_dict(),
    }


@router.get("/cockpit/essentials")
def get_cockpit_essentials(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/essentials

    Phase 1.4.d — Dashboard Essentials (migration ex-`models/dashboardEssentials.js`).

    Agrège tous les modèles dashboard (watchlist, briefing, topSites, opportunities,
    todayActions, executiveSummary, executiveKpis, healthState) depuis les données
    scope. Source of Truth backend posée en 1.4.d — migration des 4 pages frontend
    (Cockpit, ConformitePage, CommandCenter, billingHealthModel) différée à Phase 1.4.d.bis.

    Réponse :
        DashboardEssentials.to_dict() — structure agrégée complète
    """
    from services.dashboard_essentials_service import build_dashboard_essentials

    org_id = resolve_org_id(request, auth, db)

    # Récupérer les sites du scope
    sites_objs = _sites_for_org(db, org_id).all()

    # KPIs conformité depuis KpiService (source canonique)
    kpi_svc = KpiService(db)
    _scope = KpiScope(org_id=org_id)

    compliance_score = None
    compliance_confidence = None
    try:
        compliance_kpi = kpi_svc.get_compliance_score(_scope)
        compliance_score = compliance_kpi.value
        compliance_confidence = compliance_kpi.confidence
    except Exception:
        pass

    # Alertes actives scoped
    site_ids = [s.id for s in sites_objs]
    alerts_count = (
        db.query(Alerte).filter(Alerte.resolue == False, Alerte.site_id.in_(site_ids)).count() if site_ids else 0
    )

    # Construire la liste de dicts sites (payload pour build_dashboard_essentials)
    sites_payload = []
    for s in sites_objs:
        statut = None
        if s.statut_decret_tertiaire is not None:
            raw = s.statut_decret_tertiaire
            statut = raw.value if hasattr(raw, "value") else str(raw)
        sites_payload.append(
            {
                "id": s.id,
                "nom": s.nom or "",
                "ville": getattr(s, "ville", None) or getattr(s, "city", None),
                "statut_conformite": statut,
                "risque_eur": float(getattr(s, "risque_eur", 0) or 0),
                "conso_kwh_an": float(s.annual_kwh_total or 0),
                "compliance_score": compliance_score,
                "compliance_confidence": compliance_confidence,
            }
        )

    # Injecter compliance_score dans le premier site ou via kpis patch
    # build_dashboard_essentials agrège les sites, mais compliance_score
    # est un KPI organisationnel → on le transmet via un site fictif «patch»
    # plutôt que de modifier la signature. Contournement propre : on enrichit
    # le kpis dict après construction.
    essentials = build_dashboard_essentials(
        sites=sites_payload,
        is_expert=False,
        alerts_count=alerts_count,
    )

    # Patch compliance_score dans les kpis retournés (SoT = KpiService)
    result_dict = essentials.to_dict()
    if compliance_score is not None:
        result_dict["kpis"]["compliance_score"] = compliance_score
        result_dict["kpis"]["compliance_confidence"] = compliance_confidence

    return result_dict


@router.get("/cockpit/essentials/health")
def get_cockpit_essentials_health(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/essentials/health

    Sous-endpoint HealthState uniquement — consommé par billingHealthModel.js
    et ConformitePage.jsx (Phase 1.4.d.bis migration différée).

    Retourne HealthState.to_dict()
    """
    from services.dashboard_essentials_service import (
        build_watchlist,
        check_consistency,
        compute_health_state,
    )

    org_id = resolve_org_id(request, auth, db)
    sites_objs = _sites_for_org(db, org_id).all()
    site_ids = [s.id for s in sites_objs]

    total = len(sites_objs)
    nc = sum(
        1
        for s in sites_objs
        if s.statut_decret_tertiaire is not None
        and (
            s.statut_decret_tertiaire.value
            if hasattr(s.statut_decret_tertiaire, "value")
            else str(s.statut_decret_tertiaire)
        )
        == "non_conforme"
    )
    ar = sum(
        1
        for s in sites_objs
        if s.statut_decret_tertiaire is not None
        and (
            s.statut_decret_tertiaire.value
            if hasattr(s.statut_decret_tertiaire, "value")
            else str(s.statut_decret_tertiaire)
        )
        == "a_risque"
    )
    conformes = sum(
        1
        for s in sites_objs
        if s.statut_decret_tertiaire is not None
        and (
            s.statut_decret_tertiaire.value
            if hasattr(s.statut_decret_tertiaire, "value")
            else str(s.statut_decret_tertiaire)
        )
        == "conforme"
    )
    couverture = round(sum(1 for s in sites_objs if (s.annual_kwh_total or 0) > 0) / total * 100) if total > 0 else 0

    kpis = {
        "total": total,
        "conformes": conformes,
        "nonConformes": nc,
        "aRisque": ar,
        "risqueTotal": 0.0,
        "couvertureDonnees": couverture,
    }

    alerts_count = (
        db.query(Alerte).filter(Alerte.resolue == False, Alerte.site_id.in_(site_ids)).count() if site_ids else 0
    )

    sites_payload = [{"conso_kwh_an": s.annual_kwh_total, "statut_conformite": _statut_dt_value(s)} for s in sites_objs]
    watchlist = build_watchlist(kpis, sites_payload)
    consistency = check_consistency(kpis)
    health = compute_health_state(
        kpis=kpis,
        watchlist=watchlist,
        consistency=consistency,
        alerts_count=alerts_count,
    )

    return health.to_dict()


@router.get("/cockpit/essentials/watchlist")
def get_cockpit_essentials_watchlist(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/essentials/watchlist

    Sous-endpoint Watchlist uniquement — consommé par ConformitePage.jsx
    (Phase 1.4.d.bis migration différée).

    Retourne { watchlist: WatchItem[] }
    """
    from services.dashboard_essentials_service import build_watchlist

    org_id = resolve_org_id(request, auth, db)
    sites_objs = _sites_for_org(db, org_id).all()

    total = len(sites_objs)
    nc = sum(
        1
        for s in sites_objs
        if s.statut_decret_tertiaire is not None
        and (
            s.statut_decret_tertiaire.value
            if hasattr(s.statut_decret_tertiaire, "value")
            else str(s.statut_decret_tertiaire)
        )
        == "non_conforme"
    )
    ar = sum(
        1
        for s in sites_objs
        if s.statut_decret_tertiaire is not None
        and (
            s.statut_decret_tertiaire.value
            if hasattr(s.statut_decret_tertiaire, "value")
            else str(s.statut_decret_tertiaire)
        )
        == "a_risque"
    )
    couverture = round(sum(1 for s in sites_objs if (s.annual_kwh_total or 0) > 0) / total * 100) if total > 0 else 0

    kpis = {
        "total": total,
        "nonConformes": nc,
        "aRisque": ar,
        "couvertureDonnees": couverture,
    }

    sites_payload = [{"conso_kwh_an": s.annual_kwh_total} for s in sites_objs]
    watchlist = build_watchlist(kpis, sites_payload)

    return {"watchlist": [w.to_dict() for w in watchlist]}


@router.get("/cockpit/data_activation")
def get_cockpit_data_activation(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/cockpit/data_activation

    Phase 1.4.e — Endpoint Data Activation (migration ex-`models/dataActivationModel.js`).

    Retourne la checklist d'activation des 5 dimensions canoniques
    (patrimoine, conformité, consommation, facturation, achat) +
    agrégats (activated_count, overall_coverage, next_action).

    Org-scoping via resolve_org_id (CLAUDE.md règle #2). Délègue à
    services/data_activation_service.build_activation_checklist().
    """
    from services.data_activation_service import build_activation_checklist

    org_id = resolve_org_id(request, auth, db)
    sites_objs = _sites_for_org(db, org_id).all()
    site_ids = [s.id for s in sites_objs]
    total_sites = len(site_ids)

    # Comptage statuts DT — single Python pass sur sites_objs déjà chargés
    statut_counts = _count_dt_statuts(sites_objs)
    conformes = statut_counts["conforme"]
    nc = statut_counts["non_conforme"]
    ar = statut_counts["a_risque"]

    sites_with_conso = sum(1 for s in sites_objs if (s.annual_kwh_total or 0) > 0)
    couverture = round((sites_with_conso / total_sites) * 100) if total_sites > 0 else 0

    total_eur = 0.0
    total_invoices = 0
    try:
        from models import EnergyInvoice

        if site_ids:
            total_eur = (
                db.query(func.sum(EnergyInvoice.amount_eur)).filter(EnergyInvoice.site_id.in_(site_ids)).scalar()
            ) or 0.0
            total_invoices = db.query(EnergyInvoice).filter(EnergyInvoice.site_id.in_(site_ids)).count()
    except Exception:
        pass

    total_contracts = 0
    try:
        from models.energy_contract import EnergyContract

        if site_ids:
            total_contracts = db.query(EnergyContract).filter(EnergyContract.site_id.in_(site_ids)).count()
    except Exception:
        pass

    coverage_contracts_pct = (
        round((total_contracts / total_sites) * 100) if total_sites > 0 and total_contracts > 0 else 0
    )

    kpis_payload = {
        "total": total_sites,
        "conformes": conformes,
        "non_conformes": nc,
        "a_risque": ar,
        "couverture_donnees": couverture,
    }
    billing_payload = {
        "total_invoices": total_invoices,
        "total_eur": float(total_eur),
    }
    purchase_payload = (
        {
            "totalContracts": total_contracts,
            "totalSites": total_sites,
            "coverageContractsPct": coverage_contracts_pct,
        }
        if total_contracts > 0
        else None
    )

    result = build_activation_checklist(kpis_payload, billing_payload, purchase_payload)
    return result.to_dict()
