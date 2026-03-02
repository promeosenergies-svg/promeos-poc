"""
PROMEOS — Achat Energie Endpoints V1.1
V1: Estimation, hypotheses, preferences, scenarios, recommandation.
V1.1: Portfolio roll-up, renewals, history, actions.
"""
import logging
import os
import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from middleware.auth import get_optional_auth, require_admin, AuthContext
from services.iam_scope import check_site_access

DEMO_SEED_ENABLED = os.environ.get("DEMO_SEED_ENABLED", "false").lower() == "true"


def _check_seed_enabled():
    """Guard: seed endpoints are only available when DEMO_SEED_ENABLED=true."""
    if not DEMO_SEED_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="Demo seed is disabled. Set DEMO_SEED_ENABLED=true to enable.",
        )


from models import (
    PurchaseAssumptionSet,
    PurchasePreference,
    PurchaseScenarioResult,
    PurchaseStrategy,
    PurchaseRecoStatus,
    BillingEnergyType,
    EnergyContract,
    Site,
)
from services.purchase_service import (
    estimate_consumption,
    compute_profile_factor,
    compute_scenarios,
    recommend_scenario,
    get_org_site_ids,
    compute_inputs_hash,
    aggregate_portfolio_results,
)
from services.purchase_actions_engine import compute_purchase_actions

router = APIRouter(prefix="/api/purchase", tags=["Achat Energie"])

# ── Energy Gate: ELEC-only (post-ARENH, Brique 3) ──
ALLOWED_ENERGY_TYPES = {"elec"}


def _resolve_org_id(db: Session, site: "Site") -> int | None:
    """Resolve org_id from Site → Portefeuille → EntiteJuridique → Organisation."""
    if not site or not site.portefeuille_id:
        return None
    from models import Portefeuille, EntiteJuridique
    pf = db.query(Portefeuille).filter(Portefeuille.id == site.portefeuille_id).first()
    if not pf:
        return None
    ej = db.query(EntiteJuridique).filter(EntiteJuridique.id == pf.entite_juridique_id).first()
    return ej.organisation_id if ej else None


def _get_latest_assumption(db: Session, site_id: int):
    """Get the most recent PurchaseAssumptionSet for a site."""
    return (
        db.query(PurchaseAssumptionSet)
        .filter(PurchaseAssumptionSet.site_id == site_id)
        .order_by(PurchaseAssumptionSet.created_at.desc())
        .first()
    )


# ── Pydantic schemas ──


class AssumptionSetIn(BaseModel):
    energy_type: str = "elec"
    volume_kwh_an: float = 0
    horizon_months: int = 24
    assumptions_json: Optional[str] = None


class PreferenceIn(BaseModel):
    risk_tolerance: str = "medium"
    budget_priority: float = 0.5
    green_preference: bool = False


# ══════════════════════════════════════
# V1 Endpoints (unchanged signatures)
# ══════════════════════════════════════

# ── 1. Estimation conso ──


@router.get("/estimate/{site_id}")
def get_estimate(site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)):
    """Estimate annual consumption for a site."""
    check_site_access(auth, site_id)
    result = estimate_consumption(db, site_id)
    profile = compute_profile_factor(db, site_id)
    result["profile_factor"] = profile
    return result


# ── 2-3. Assumptions CRUD ──


@router.get("/assumptions/{site_id}")
def get_assumptions(
    site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)
):
    """Get existing assumptions or defaults."""
    check_site_access(auth, site_id)
    assumption = _get_latest_assumption(db, site_id)
    if assumption:
        return {
            "id": assumption.id,
            "site_id": assumption.site_id,
            "energy_type": assumption.energy_type.value if assumption.energy_type else "elec",
            "volume_kwh_an": assumption.volume_kwh_an,
            "profile_factor": assumption.profile_factor,
            "horizon_months": assumption.horizon_months,
            "assumptions_json": assumption.assumptions_json,
        }
    # Defaults
    est = estimate_consumption(db, site_id)
    pf = compute_profile_factor(db, site_id)
    return {
        "id": None,
        "site_id": site_id,
        "energy_type": "elec",
        "volume_kwh_an": est["volume_kwh_an"],
        "profile_factor": pf,
        "horizon_months": 24,
        "assumptions_json": None,
    }


@router.put("/assumptions/{site_id}")
def put_assumptions(
    site_id: int,
    data: AssumptionSetIn,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create or update assumptions for a site."""
    check_site_access(auth, site_id)
    # Energy Gate: block non-ELEC energy types
    if data.energy_type not in ALLOWED_ENERGY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Energie '{data.energy_type}' non supportee. "
            f"Seule l'electricite (elec) est disponible dans cette version (post-ARENH).",
        )
    existing = _get_latest_assumption(db, site_id)
    profile = compute_profile_factor(db, site_id)

    if existing:
        existing.energy_type = BillingEnergyType(data.energy_type)
        existing.volume_kwh_an = data.volume_kwh_an
        existing.horizon_months = data.horizon_months
        existing.profile_factor = profile
        existing.assumptions_json = data.assumptions_json
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "status": "updated"}

    new_set = PurchaseAssumptionSet(
        site_id=site_id,
        energy_type=BillingEnergyType(data.energy_type),
        volume_kwh_an=data.volume_kwh_an,
        profile_factor=profile,
        horizon_months=data.horizon_months,
        assumptions_json=data.assumptions_json,
    )
    db.add(new_set)
    db.commit()
    db.refresh(new_set)
    return {"id": new_set.id, "status": "created"}


# ── 4-5. Preferences CRUD ──


@router.get("/preferences")
def get_preferences(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get purchase preferences."""
    if auth:
        org_id = auth.org_id
    elif not org_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    q = db.query(PurchasePreference)
    if org_id is not None:
        q = q.filter(PurchasePreference.org_id == org_id)
    pref = q.first()
    if pref:
        return {
            "id": pref.id,
            "org_id": pref.org_id,
            "risk_tolerance": pref.risk_tolerance,
            "budget_priority": pref.budget_priority,
            "green_preference": pref.green_preference,
        }
    return {
        "id": None,
        "org_id": org_id,
        "risk_tolerance": "medium",
        "budget_priority": 0.5,
        "green_preference": False,
    }


@router.put("/preferences")
def put_preferences(
    data: PreferenceIn,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Create or update purchase preferences."""
    if auth:
        org_id = auth.org_id
    elif not org_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    q = db.query(PurchasePreference)
    if org_id is not None:
        q = q.filter(PurchasePreference.org_id == org_id)
    existing = q.first()

    if existing:
        existing.risk_tolerance = data.risk_tolerance
        existing.budget_priority = data.budget_priority
        existing.green_preference = data.green_preference
        existing.updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"id": existing.id, "status": "updated"}

    new_pref = PurchasePreference(
        org_id=org_id,
        risk_tolerance=data.risk_tolerance,
        budget_priority=data.budget_priority,
        green_preference=data.green_preference,
    )
    db.add(new_pref)
    db.commit()
    db.refresh(new_pref)
    return {"id": new_pref.id, "status": "created"}


# ══════════════════════════════════════
# V1.1 Endpoints (new)
# CRITICAL: parameterless routes BEFORE
# path-param routes to avoid FastAPI collision
# ══════════════════════════════════════

# ── V1.1: Renewals ──


@router.get("/renewals")
def get_renewals(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """List contracts expiring within notice window (30/60/90 days)."""
    if auth:
        org_id = auth.org_id
    if not org_id:
        raise HTTPException(status_code=401, detail="Authentication required or org_id param needed")
    site_ids = get_org_site_ids(db, org_id)

    if not site_ids:
        return {"total": 0, "renewals": []}

    contracts = (
        db.query(EnergyContract)
        .filter(
            EnergyContract.site_id.in_(site_ids),
            EnergyContract.end_date.isnot(None),
        )
        .all()
    )

    today = date.today()
    renewals = []
    site_map = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()}

    for c in contracts:
        days_until_expiry = (c.end_date - today).days
        if days_until_expiry <= 0:
            continue

        notice_deadline = c.end_date - timedelta(days=c.notice_period_days or 90)
        days_until_notice = (notice_deadline - today).days

        # Only show contracts within actionable window
        if days_until_expiry > 365:
            continue

        if days_until_expiry <= 30:
            urgency = "red"
        elif days_until_expiry <= 60:
            urgency = "orange"
        elif days_until_expiry <= 90:
            urgency = "yellow"
        else:
            urgency = "gray"

        site = site_map.get(c.site_id)
        renewals.append(
            {
                "contract_id": c.id,
                "site_id": c.site_id,
                "site_nom": site.nom if site else None,
                "supplier_name": c.supplier_name,
                "energy_type": c.energy_type.value if c.energy_type else None,
                "end_date": c.end_date.isoformat(),
                "notice_period_days": c.notice_period_days,
                "notice_deadline": notice_deadline.isoformat(),
                "auto_renew": c.auto_renew,
                "days_until_expiry": days_until_expiry,
                "days_until_notice": days_until_notice,
                "urgency": urgency,
            }
        )

    renewals.sort(key=lambda r: r["days_until_expiry"])
    return {"total": len(renewals), "renewals": renewals}


# ── V1.1: Actions ──


@router.get("/actions")
def get_actions(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Get computed purchase actions (ephemeral, not persisted)."""
    if auth:
        org_id = auth.org_id
    if not org_id:
        raise HTTPException(status_code=401, detail="Authentication required or org_id param needed")
    return compute_purchase_actions(db, org_id=org_id)


# ── V1.1: Portfolio compute ──


@router.post("/compute")
def compute_portfolio(
    org_id: int = Query(...),
    scope: str = Query("org"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Compute scenarios for all sites in an org (scope=org)."""
    if auth:
        org_id = auth.org_id
    elif not org_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    if scope != "org":
        raise HTTPException(400, "Use POST /api/purchase/compute/{site_id} for single site")

    site_ids = get_org_site_ids(db, org_id)
    if not site_ids:
        raise HTTPException(404, "No active sites found for this org")

    logger.info("Portfolio compute: org_id=%s, %d sites", org_id, len(site_ids))
    batch_id = str(uuid.uuid4())
    results_by_site = []
    skipped_sites = []

    # Batch-fetch all Site objects to avoid N+1 queries in loop
    site_map = {s.id: s for s in db.query(Site).filter(Site.id.in_(site_ids)).all()}

    # Get org-level preferences
    pref = (
        db.query(PurchasePreference)
        .filter(
            PurchasePreference.org_id == org_id,
        )
        .first()
    )
    risk_tol = pref.risk_tolerance if pref else "medium"
    budget_pri = pref.budget_priority if pref else 0.5
    green_pref = pref.green_preference if pref else False

    try:
        for sid in site_ids:
            run_id = str(uuid.uuid4())

            # Get or create assumptions
            assumption = _get_latest_assumption(db, sid)
            if not assumption:
                est = estimate_consumption(db, sid)
                pf = compute_profile_factor(db, sid)
                assumption = PurchaseAssumptionSet(
                    site_id=sid,
                    energy_type=BillingEnergyType.ELEC,
                    volume_kwh_an=est["volume_kwh_an"],
                    profile_factor=pf,
                    horizon_months=24,
                )
                db.add(assumption)
                db.commit()
                db.refresh(assumption)

            energy_type_val = assumption.energy_type.value if assumption.energy_type else "elec"

            # Energy Gate: skip non-ELEC sites in portfolio
            if energy_type_val not in ALLOWED_ENERGY_TYPES:
                skipped_sites.append({"site_id": sid, "reason": f"energy_type '{energy_type_val}' not supported"})
                continue

            scenarios = compute_scenarios(
                db,
                sid,
                volume_kwh_an=assumption.volume_kwh_an,
                profile_factor=assumption.profile_factor,
                energy_type=energy_type_val,
            )
            scenarios = recommend_scenario(scenarios, risk_tol, budget_pri, green_pref)

            inputs_hash_val = compute_inputs_hash(
                assumption.volume_kwh_an,
                assumption.profile_factor,
                assumption.horizon_months,
                energy_type_val,
                risk_tol,
                budget_pri,
                green_pref,
            )

            # Persist (keep old results for history)
            result_ids = []
            for s in scenarios:
                result = PurchaseScenarioResult(
                    assumption_set_id=assumption.id,
                    run_id=run_id,
                    batch_id=batch_id,
                    inputs_hash=inputs_hash_val,
                    strategy=PurchaseStrategy(s["strategy"]),
                    price_eur_per_kwh=s["price_eur_per_kwh"],
                    total_annual_eur=s["total_annual_eur"],
                    risk_score=s["risk_score"],
                    savings_vs_current_pct=s.get("savings_vs_current_pct"),
                    p10_eur=s.get("p10_eur"),
                    p90_eur=s.get("p90_eur"),
                    is_recommended=s.get("is_recommended", False),
                    reco_status=PurchaseRecoStatus.DRAFT,
                )
                db.add(result)
                db.flush()
                result_ids.append(result.id)

            db.commit()

            for i, s in enumerate(scenarios):
                s["id"] = result_ids[i]

            site_obj = site_map.get(sid)
            results_by_site.append(
                {
                    "site_id": sid,
                    "site_nom": site_obj.nom if site_obj else f"Site {sid}",
                    "run_id": run_id,
                    "volume_kwh_an": assumption.volume_kwh_an,
                    "scenarios": scenarios,
                }
            )
    except Exception:
        db.rollback()
        logger.exception("Portfolio compute failed: org_id=%s, batch_id=%s", org_id, batch_id)
        raise

    portfolio = aggregate_portfolio_results(results_by_site)
    logger.info("Portfolio compute done: batch_id=%s, %d sites computed, %d skipped", batch_id, len(results_by_site), len(skipped_sites))

    return {
        "batch_id": batch_id,
        "org_id": org_id,
        "portfolio": portfolio,
        "sites": results_by_site,
        "skipped_sites": skipped_sites,
    }


# ── 6. Compute scenarios (per-site) — V1.1: +run_id +inputs_hash, preserve history ──


@router.post("/compute/{site_id}")
def compute(
    site_id: int,
    report_pct: float = Query(0.0, ge=0.0, le=1.0, description="Fraction of HP shifted to solaire (0.0–1.0)"),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Compute 4 scenarios + recommendation for a site."""
    check_site_access(auth, site_id)

    # Energy Gate: verify existing assumption is ELEC
    existing_check = _get_latest_assumption(db, site_id)
    if existing_check:
        et = existing_check.energy_type.value if existing_check.energy_type else "elec"
        if et not in ALLOWED_ENERGY_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Energie '{et}' non supportee. Modifiez les hypotheses vers 'elec' avant de calculer.",
            )

    logger.info("Single-site compute: site_id=%d, report_pct=%.2f", site_id, report_pct)
    try:
        # Get or create assumptions
        assumption = _get_latest_assumption(db, site_id)
        if not assumption:
            est = estimate_consumption(db, site_id)
            pf = compute_profile_factor(db, site_id)
            assumption = PurchaseAssumptionSet(
                site_id=site_id,
                energy_type=BillingEnergyType.ELEC,
                volume_kwh_an=est["volume_kwh_an"],
                profile_factor=pf,
                horizon_months=24,
            )
            db.add(assumption)
            db.commit()
            db.refresh(assumption)

        # Compute scenarios
        energy_type_val = assumption.energy_type.value if assumption.energy_type else "elec"
        scenarios = compute_scenarios(
            db,
            site_id,
            volume_kwh_an=assumption.volume_kwh_an,
            profile_factor=assumption.profile_factor,
            energy_type=energy_type_val,
            report_pct=report_pct,
        )

        # Get preferences for recommendation (scoped by org)
        site_obj = db.query(Site).filter(Site.id == site_id).first()
        org_id = _resolve_org_id(db, site_obj) if site_obj else None
        pref = (
            db.query(PurchasePreference)
            .filter(PurchasePreference.org_id == org_id)
            .first()
        ) if org_id else None
        risk_tol = pref.risk_tolerance if pref else "medium"
        budget_pri = pref.budget_priority if pref else 0.5
        green_pref = pref.green_preference if pref else False

        scenarios = recommend_scenario(scenarios, risk_tol, budget_pri, green_pref)

        # V1.1: Generate run_id and inputs_hash
        run_id = str(uuid.uuid4())
        inputs_hash_val = compute_inputs_hash(
            assumption.volume_kwh_an,
            assumption.profile_factor,
            assumption.horizon_months,
            energy_type_val,
            risk_tol,
            budget_pri,
            green_pref,
        )

        # V1.1: No longer delete old results — preserve for history

        # Persist results
        result_ids = []
        for s in scenarios:
            result = PurchaseScenarioResult(
                assumption_set_id=assumption.id,
                run_id=run_id,
                inputs_hash=inputs_hash_val,
                strategy=PurchaseStrategy(s["strategy"]),
                price_eur_per_kwh=s["price_eur_per_kwh"],
                total_annual_eur=s["total_annual_eur"],
                risk_score=s["risk_score"],
                savings_vs_current_pct=s.get("savings_vs_current_pct"),
                p10_eur=s.get("p10_eur"),
                p90_eur=s.get("p90_eur"),
                is_recommended=s.get("is_recommended", False),
                reco_status=PurchaseRecoStatus.DRAFT,
            )
            db.add(result)
            db.flush()
            result_ids.append(result.id)

        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Single-site compute failed: site_id=%d", site_id)
        raise

    logger.info("Single-site compute done: site_id=%d, run_id=%s, %d scenarios", site_id, run_id, len(scenarios))

    # Add result IDs to response
    for i, s in enumerate(scenarios):
        s["id"] = result_ids[i]

    return {
        "assumption_set_id": assumption.id,
        "site_id": site_id,
        "run_id": run_id,
        "scenarios": scenarios,
    }


# ── V1.1: Portfolio results ──


@router.get("/results")
def get_portfolio_results(
    org_id: int = Query(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Aggregated portfolio view: total cost, weighted risk, total savings."""
    if auth:
        org_id = auth.org_id
    elif not org_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    site_ids = get_org_site_ids(db, org_id)
    if not site_ids:
        return {"org_id": org_id, "portfolio": None, "sites": []}

    results_by_site = []
    for sid in site_ids:
        assumption = _get_latest_assumption(db, sid)
        if not assumption:
            continue

        # Get latest run results
        latest = (
            db.query(PurchaseScenarioResult)
            .filter(PurchaseScenarioResult.assumption_set_id == assumption.id)
            .order_by(PurchaseScenarioResult.computed_at.desc())
            .first()
        )
        if not latest:
            continue

        if latest.run_id:
            results = (
                db.query(PurchaseScenarioResult)
                .filter(
                    PurchaseScenarioResult.assumption_set_id == assumption.id,
                    PurchaseScenarioResult.run_id == latest.run_id,
                )
                .order_by(PurchaseScenarioResult.risk_score.asc())
                .all()
            )
        else:
            results = (
                db.query(PurchaseScenarioResult)
                .filter(PurchaseScenarioResult.assumption_set_id == assumption.id)
                .order_by(PurchaseScenarioResult.computed_at.desc())
                .limit(3)
                .all()
            )

        if not results:
            continue

        results_by_site.append(
            {
                "site_id": sid,
                "volume_kwh_an": assumption.volume_kwh_an,
                "scenarios": [
                    {
                        "strategy": r.strategy.value if r.strategy else None,
                        "total_annual_eur": r.total_annual_eur,
                        "risk_score": r.risk_score,
                        "savings_vs_current_pct": r.savings_vs_current_pct,
                        "is_recommended": r.is_recommended,
                    }
                    for r in results
                ],
            }
        )

    portfolio = aggregate_portfolio_results(results_by_site)

    return {
        "org_id": org_id,
        "portfolio": portfolio,
        "sites": results_by_site,
    }


# ── 7. Get results (per-site) — V1.1: filter by latest run_id ──


@router.get("/results/{site_id}")
def get_results(site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)):
    """Get latest scenario results for a site."""
    check_site_access(auth, site_id)
    assumption = _get_latest_assumption(db, site_id)
    if not assumption:
        return {"scenarios": [], "assumption_set_id": None}

    # V1.1: Find latest run, filter by run_id
    latest = (
        db.query(PurchaseScenarioResult)
        .filter(PurchaseScenarioResult.assumption_set_id == assumption.id)
        .order_by(PurchaseScenarioResult.computed_at.desc())
        .first()
    )
    if not latest:
        return {"scenarios": [], "assumption_set_id": assumption.id}

    if latest.run_id:
        results = (
            db.query(PurchaseScenarioResult)
            .filter(
                PurchaseScenarioResult.assumption_set_id == assumption.id,
                PurchaseScenarioResult.run_id == latest.run_id,
            )
            .order_by(PurchaseScenarioResult.risk_score.asc())
            .all()
        )
    else:
        # Legacy fallback: no run_id
        results = (
            db.query(PurchaseScenarioResult)
            .filter(PurchaseScenarioResult.assumption_set_id == assumption.id)
            .order_by(PurchaseScenarioResult.risk_score.asc())
            .all()
        )

    return {
        "assumption_set_id": assumption.id,
        "site_id": site_id,
        "run_id": latest.run_id,
        "scenarios": [
            {
                "id": r.id,
                "strategy": r.strategy.value if r.strategy else None,
                "price_eur_per_kwh": r.price_eur_per_kwh,
                "total_annual_eur": r.total_annual_eur,
                "risk_score": r.risk_score,
                "savings_vs_current_pct": r.savings_vs_current_pct,
                "p10_eur": r.p10_eur,
                "p90_eur": r.p90_eur,
                "is_recommended": r.is_recommended,
                "reco_status": r.reco_status.value if r.reco_status else None,
            }
            for r in results
        ],
    }


# ── V1.1: History ──


@router.get("/history/{site_id}")
def get_history(site_id: int, db: Session = Depends(get_db), auth: Optional[AuthContext] = Depends(get_optional_auth)):
    """List past computation runs for a site with timestamps and inputs_hash."""
    check_site_access(auth, site_id)
    assumptions = db.query(PurchaseAssumptionSet).filter(PurchaseAssumptionSet.site_id == site_id).all()
    assumption_ids = [a.id for a in assumptions]
    if not assumption_ids:
        return {"site_id": site_id, "total_runs": 0, "runs": []}

    results = (
        db.query(PurchaseScenarioResult)
        .filter(PurchaseScenarioResult.assumption_set_id.in_(assumption_ids))
        .order_by(PurchaseScenarioResult.computed_at.desc())
        .all()
    )

    # Group by run_id
    runs_map = {}
    for r in results:
        key = r.run_id or f"legacy_{r.computed_at.isoformat() if r.computed_at else r.id}"
        if key not in runs_map:
            runs_map[key] = {
                "run_id": r.run_id,
                "batch_id": r.batch_id,
                "inputs_hash": r.inputs_hash,
                "computed_at": r.computed_at.isoformat() if r.computed_at else None,
                "scenarios": [],
            }
        runs_map[key]["scenarios"].append(
            {
                "id": r.id,
                "strategy": r.strategy.value if r.strategy else None,
                "price_eur_per_kwh": r.price_eur_per_kwh,
                "total_annual_eur": r.total_annual_eur,
                "risk_score": r.risk_score,
                "savings_vs_current_pct": r.savings_vs_current_pct,
                "is_recommended": r.is_recommended,
                "reco_status": r.reco_status.value if r.reco_status else None,
            }
        )

    runs = list(runs_map.values())

    # Add summary to each run
    for run in runs:
        reco = next((s for s in run["scenarios"] if s.get("is_recommended")), None)
        run["summary"] = {
            "recommended_strategy": reco["strategy"] if reco else None,
            "recommended_total_eur": reco["total_annual_eur"] if reco else None,
            "recommended_savings_pct": reco["savings_vs_current_pct"] if reco else None,
        }

    return {
        "site_id": site_id,
        "total_runs": len(runs),
        "runs": runs,
    }


# ── 8. Accept result ──


@router.patch("/results/{result_id}/accept")
def accept_result(
    result_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Accept a recommended scenario."""
    result = db.query(PurchaseScenarioResult).filter(PurchaseScenarioResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    # IDOR guard: verify the result belongs to a site the user can access
    assumption = db.query(PurchaseAssumptionSet).filter(
        PurchaseAssumptionSet.id == result.assumption_set_id
    ).first()
    if assumption:
        check_site_access(auth, assumption.site_id)
    result.reco_status = PurchaseRecoStatus.ACCEPTED
    db.commit()
    return {"id": result.id, "reco_status": "accepted"}


# ── 9a. Assistant data ──


@router.get("/assistant")
def get_assistant_data(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Return portfolio summary data for the Purchase Assistant wizard.

    If real sites exist for the org, returns real data.
    Otherwise returns a minimal demo seed (flagged is_demo=true).
    """
    if auth:
        org_id = auth.org_id

    sites_out = []
    is_demo = False

    if org_id:
        site_ids = get_org_site_ids(db, org_id)
        if site_ids:
            sites_q = db.query(Site).filter(Site.id.in_(site_ids)).all()
            for s in sites_q:
                est = estimate_consumption(db, s.id)
                sites_out.append(
                    {
                        "id": s.id,
                        "name": s.nom,
                        "city": getattr(s, "ville", None),
                        "usage": s.type.value if s.type else None,
                        "surface_m2": s.surface_m2,
                        "energy_type": "elec",
                        "annual_kwh": est.get("volume_kwh_an", 0),
                        "source": est.get("source", "default"),
                    }
                )

    if not sites_out:
        is_demo = True
        sites_out = [
            {
                "id": 1,
                "name": "Usine Lyon",
                "city": "Lyon",
                "usage": "industriel",
                "surface_m2": 12000,
                "energy_type": "elec",
                "annual_kwh": 2400000,
                "source": "DEMO",
            },
            {
                "id": 2,
                "name": "Entrepot Grenoble",
                "city": "Grenoble",
                "usage": "logistique",
                "surface_m2": 5000,
                "energy_type": "elec",
                "annual_kwh": 800000,
                "source": "DEMO",
            },
            {
                "id": 3,
                "name": "Bureaux Paris 8e",
                "city": "Paris",
                "usage": "bureau",
                "surface_m2": 3000,
                "energy_type": "elec",
                "annual_kwh": 600000,
                "source": "DEMO",
            },
            {
                "id": 4,
                "name": "Agence Nantes",
                "city": "Nantes",
                "usage": "bureau",
                "surface_m2": 1500,
                "energy_type": "elec",
                "annual_kwh": 350000,
                "source": "DEMO",
            },
            {
                "id": 5,
                "name": "Atelier Toulouse",
                "city": "Toulouse",
                "usage": "industriel",
                "surface_m2": 8000,
                "energy_type": "elec",
                "annual_kwh": 1800000,
                "source": "DEMO",
            },
            {
                "id": 6,
                "name": "Datacenter Marseille",
                "city": "Marseille",
                "usage": "datacenter",
                "surface_m2": 2000,
                "energy_type": "elec",
                "annual_kwh": 5000000,
                "source": "DEMO",
            },
            {
                "id": 7,
                "name": "Depot Lille",
                "city": "Lille",
                "usage": "logistique",
                "surface_m2": 6000,
                "energy_type": "elec",
                "annual_kwh": 450000,
                "source": "DEMO",
            },
            {
                "id": 8,
                "name": "Siege Bordeaux",
                "city": "Bordeaux",
                "usage": "bureau",
                "surface_m2": 4000,
                "energy_type": "elec",
                "annual_kwh": 700000,
                "source": "DEMO",
            },
        ]

    return {
        "is_demo": is_demo,
        "org_id": org_id,
        "sites": sites_out,
        "total_sites": len(sites_out),
        "total_annual_kwh": sum(s["annual_kwh"] for s in sites_out),
    }


# ── 9. Seed demo ──


@router.post("/seed-demo")
def seed_demo(
    org_id: int = Query(1),
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin()),
):
    """Seed purchase demo data for 2 sites."""
    _check_seed_enabled()
    from services.purchase_seed import seed_purchase_demo

    return seed_purchase_demo(db, org_id=org_id)


# ── Brique 3: WOW multi-site datasets ──


@router.post("/seed-wow-happy")
def seed_wow_happy_endpoint(
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin()),
):
    """Seed 15-site portfolio with clean, realistic data (happy path demo)."""
    _check_seed_enabled()
    from services.purchase_seed_wow import seed_wow_happy

    return seed_wow_happy(db)


@router.post("/seed-wow-dirty")
def seed_wow_dirty_endpoint(
    db: Session = Depends(get_db),
    _admin: None = Depends(require_admin()),
):
    """Seed 15-site portfolio with degraded/edge-case data (dirty demo)."""
    _check_seed_enabled()
    from services.purchase_seed_wow import seed_wow_dirty

    return seed_wow_dirty(db)
