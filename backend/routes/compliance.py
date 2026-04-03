"""
PROMEOS - Routes API Compliance Engine
Endpoint to trigger recomputation of site conformity snapshots.
+ Sprint 4: summary, sites findings, rules-based recompute.
+ Sprint 9: OPS workflow (findings PATCH, batches, findings list).
"""

import json
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation,
    ComplianceFinding,
    ComplianceRunBatch,
    InsightStatus,
    Site,
    Portefeuille,
    EntiteJuridique,
)
from services.compliance_coordinator import (
    recompute_site_full as recompute_site,
    recompute_portfolio,
    recompute_organisation,
)
from services.compliance_readiness_service import (
    compute_site_compliance_summary,
    compute_portfolio_compliance_summary,
)
from services.cee_service import (
    create_cee_dossier,
    advance_cee_step,
    compute_mv_summary,
    get_site_work_packages,
)
from models import WorkPackage
from models.enums import WorkPackageSize, CeeStatus
from services.compliance_rules import (
    evaluate_organisation,
    get_summary,
    get_sites_findings,
    get_compliance_bundle,
    load_all_packs,
)
from middleware.auth import get_optional_auth, AuthContext
from services.scope_utils import resolve_org_id

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


# ========================================
# Meta endpoint (configuration publique du scoring)
# ========================================


@router.get("/meta")
def get_compliance_meta():
    """GET /api/compliance/meta — Configuration publique du scoring conformité.

    Retourne les poids, seuils et frameworks depuis regs.yaml.
    Consommé par le frontend pour afficher les formules dans les modaux "Pourquoi ce chiffre?".
    """
    from services.compliance_score_service import (
        FRAMEWORK_WEIGHTS,
        MAX_CRITICAL_PENALTY,
        CRITICAL_PENALTY_PER_FINDING,
    )

    return {
        "framework_weights": FRAMEWORK_WEIGHTS,
        "frameworks_regulatory": list(FRAMEWORK_WEIGHTS.keys()),
        "thresholds": {
            "conforme": 70,
            "a_risque": 40,
            "non_conforme": 0,
        },
        "critical_penalty": {
            "max_pts": MAX_CRITICAL_PENALTY,
            "per_finding_pts": CRITICAL_PENALTY_PER_FINDING,
        },
        "scoring_version": "A.2",
        "source": "regs.yaml",
    }


# ========================================
# Schemas (Sprint 9)
# ========================================


class FindingPatch(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    notes: Optional[str] = None


# ========================================
# Existing endpoints
# ========================================


@router.post("/recompute")
def recompute_compliance(
    scope: str = Query(..., description="Scope: 'org', 'portfolio', or 'site'"),
    id: int = Query(..., description="ID of the org, portfolio, or site"),
    db: Session = Depends(get_db),
):
    """
    POST /api/compliance/recompute?scope=org|portfolio|site&id=<id>

    Recomputes compliance snapshots from obligations.
    """
    try:
        if scope == "site":
            snapshot = recompute_site(db, site_id=id)
            db.commit()
            return {"status": "ok", "scope": "site", "site_id": id, "snapshot": snapshot}
        elif scope == "portfolio":
            result = recompute_portfolio(db, portefeuille_id=id)
            return {"status": "ok", "scope": "portfolio", **result}
        elif scope == "org":
            result = recompute_organisation(db, organisation_id=id)
            return {"status": "ok", "scope": "org", **result}
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope '{scope}'. Must be 'org', 'portfolio', or 'site'.",
            )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========================================
# Sprint 4: Rules-based compliance
# ========================================


@router.get("/summary")
def compliance_summary(
    request: Request,
    org_id: Optional[int] = Query(None),
    entity_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/summary?org_id=&entity_id=&site_id=

    Aggregate compliance findings with scope filtering.
    Scope priority: site_id > entity_id > org_id.
    """
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    return get_summary(db, org_id, entity_id=entity_id, site_id=site_id)


@router.get("/sites")
def compliance_sites(
    request: Request,
    org_id: Optional[int] = Query(None),
    entity_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/sites?org_id=&entity_id=&site_id=&regulation=&status=&severity=

    Per-site findings list with scope filtering.
    """
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    return get_sites_findings(db, org_id, regulation, status, severity, entity_id=entity_id, site_id=site_id)


@router.get("/bundle")
def compliance_bundle(
    request: Request,
    org_id: Optional[int] = Query(None),
    entity_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    portefeuille_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/bundle?org_id=&entity_id=&site_id=&portefeuille_id=

    Single-request bundle: summary + sites + empty_reason.
    Scope priority: site_id > portefeuille_id > entity_id > org_id.
    """
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    return get_compliance_bundle(
        db,
        org_id,
        entity_id=entity_id,
        site_id=site_id,
        portefeuille_id=portefeuille_id,
        regulation=regulation,
        status=status,
        severity=severity,
    )


@router.post("/recompute-rules")
def recompute_rules(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    POST /api/compliance/recompute-rules?org_id=

    Evaluate all YAML rules for all sites of an organisation.
    Produces ComplianceFinding rows + ComplianceRunBatch (Sprint 9).
    """
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    result = evaluate_organisation(db, org_id)
    return {"status": "ok", **result}


@router.get("/rules")
def list_rules():
    """
    GET /api/compliance/rules

    List all loaded rule packs (for audit/transparency).
    """
    packs = load_all_packs()
    return [
        {
            "regulation": p["regulation"],
            "label": p["label"],
            "version": p["version"],
            "description": p["description"],
            "rules_count": len(p["rules"]),
            "rules": [{"id": r["id"], "label": r["label"], "severity": r.get("severity")} for r in p["rules"]],
        }
        for p in packs
    ]


# ========================================
# Sprint 9: OPS workflow
# ========================================


@router.get("/findings")
def list_findings(
    request: Request,
    org_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    insight_status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/findings

    List all findings with workflow fields. Supports filters.
    """
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)

    site_ids = [
        row[0]
        for row in db.query(Site.id)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    ]

    if not site_ids:
        return []

    q = db.query(ComplianceFinding).filter(ComplianceFinding.site_id.in_(site_ids))
    if regulation:
        q = q.filter(ComplianceFinding.regulation == regulation)
    if status:
        q = q.filter(ComplianceFinding.status == status)
    if severity:
        q = q.filter(ComplianceFinding.severity == severity)
    if insight_status:
        try:
            is_val = InsightStatus(insight_status)
            q = q.filter(ComplianceFinding.insight_status == is_val)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut workflow invalide: {insight_status}")
    if category == "obligation":
        q = q.filter(~ComplianceFinding.regulation.ilike("%cee%"))
    elif category == "incentive":
        q = q.filter(ComplianceFinding.regulation.ilike("%cee%"))

    findings = q.all()

    # Build response with site_nom
    site_names = {}
    result = []
    for f in findings:
        if f.site_id not in site_names:
            site = db.query(Site).filter(Site.id == f.site_id).first()
            site_names[f.site_id] = site.nom if site else "?"
        actions = json.loads(f.recommended_actions_json) if f.recommended_actions_json else []
        result.append(
            {
                "id": f.id,
                "site_id": f.site_id,
                "site_nom": site_names[f.site_id],
                "regulation": f.regulation,
                "rule_id": f.rule_id,
                "status": f.status,
                "severity": f.severity,
                "deadline": f.deadline.isoformat() if f.deadline else None,
                "evidence": f.evidence,
                "actions": actions,
                "insight_status": f.insight_status.value if f.insight_status else "open",
                "owner": f.owner,
                "notes": f.notes,
                "run_batch_id": f.run_batch_id,
                "category": "incentive" if "cee" in (f.regulation or "").lower() else "obligation",
                "estimated_penalty_eur": getattr(f, "estimated_penalty_eur", None),
                "penalty_source": getattr(f, "penalty_source", None),
                "penalty_basis": getattr(f, "penalty_basis", None),
                # A4 — audit trail fields (surfaced in expert mode)
                "inputs_json": json.loads(f.inputs_json) if f.inputs_json else None,
                "params_json": json.loads(f.params_json) if f.params_json else None,
                "engine_version": f.engine_version,
            }
        )

    return result


@router.patch("/findings/{finding_id}")
def patch_finding(
    finding_id: int,
    data: FindingPatch,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    PATCH /api/compliance/findings/{finding_id}

    Update finding workflow: status, owner, notes.
    """
    org_id = resolve_org_id(request, auth, db)
    finding = db.query(ComplianceFinding).filter(ComplianceFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding non trouve")
    # Verify finding belongs to user's org
    from services.scope_utils import resolve_org_id_from_site

    site = db.query(Site).filter(Site.id == finding.site_id).first()
    if site:
        finding_org_id = resolve_org_id_from_site(db, site.id)
        if not finding_org_id or finding_org_id != org_id:
            raise HTTPException(status_code=403, detail="Accès interdit à ce finding")

    if data.status is not None:
        try:
            finding.insight_status = InsightStatus(data.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut invalide: {data.status}")
    if data.owner is not None:
        finding.owner = data.owner
    if data.notes is not None:
        finding.notes = data.notes

    db.commit()
    db.refresh(finding)
    return {
        "status": "updated",
        "finding_id": finding.id,
        "insight_status": finding.insight_status.value if finding.insight_status else "open",
        "owner": finding.owner,
        "notes": finding.notes,
    }


@router.get("/batches")
def list_batches(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/batches

    List compliance run batches (evaluation history).
    """
    q = db.query(ComplianceRunBatch)
    if org_id is not None:
        q = q.filter(ComplianceRunBatch.org_id == org_id)
    batches = q.order_by(ComplianceRunBatch.started_at.desc()).all()

    return [
        {
            "id": b.id,
            "org_id": b.org_id,
            "triggered_by": b.triggered_by,
            "started_at": b.started_at.isoformat() if b.started_at else None,
            "completed_at": b.completed_at.isoformat() if b.completed_at else None,
            "sites_count": b.sites_count,
            "findings_count": b.findings_count,
            "nok_count": b.nok_count,
            "unknown_count": b.unknown_count,
        }
        for b in batches
    ]


@router.get("/findings/{finding_id}")
def get_finding_detail(
    finding_id: int,
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/findings/{finding_id}

    Detailed finding with audit fields (inputs, params, evidence, engine_version).
    """
    org_id = resolve_org_id(request, auth, db)
    f = db.query(ComplianceFinding).filter(ComplianceFinding.id == finding_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    # Verify finding belongs to user's org
    from services.scope_utils import resolve_org_id_from_site

    site = db.query(Site).filter(Site.id == f.site_id).first()
    if site:
        finding_org_id = resolve_org_id_from_site(db, site.id)
        if not finding_org_id or finding_org_id != org_id:
            raise HTTPException(status_code=403, detail="Accès interdit à ce finding")

    site = db.query(Site).filter(Site.id == f.site_id).first()
    actions = json.loads(f.recommended_actions_json) if f.recommended_actions_json else []

    return {
        "id": f.id,
        "site_id": f.site_id,
        "site_nom": site.nom if site else "?",
        "regulation": f.regulation,
        "rule_id": f.rule_id,
        "status": f.status,
        "severity": f.severity,
        "deadline": f.deadline.isoformat() if f.deadline else None,
        "evidence": f.evidence,
        "actions": actions,
        "insight_status": f.insight_status.value if f.insight_status else "open",
        "owner": f.owner,
        "notes": f.notes,
        "run_batch_id": f.run_batch_id,
        "inputs": json.loads(f.inputs_json) if f.inputs_json else {},
        "params": json.loads(f.params_json) if f.params_json else {},
        "evidence_refs": json.loads(f.evidence_json) if f.evidence_json else {},
        "engine_version": f.engine_version,
        "estimated_penalty_eur": getattr(f, "estimated_penalty_eur", None),
        "penalty_source": getattr(f, "penalty_source", None),
        "penalty_basis": getattr(f, "penalty_basis", None),
        "created_at": f.created_at.isoformat() if hasattr(f, "created_at") and f.created_at else None,
        "updated_at": f.updated_at.isoformat() if hasattr(f, "updated_at") and f.updated_at else None,
    }


# ========================================
# V68: Compliance Pipeline summaries
# ========================================


@router.get("/sites/{site_id}/summary")
def site_compliance_summary(
    site_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/sites/{site_id}/summary

    V68: Full compliance summary for one site — readiness gate,
    applicability, scores, deadlines, data trust.
    """
    try:
        return compute_site_compliance_summary(db, site_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/portfolio/summary")
def portfolio_compliance_summary(
    request: Request,
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/portfolio/summary?org_id=

    V68: Portfolio-level compliance summary — KPIs, top blockers,
    deadlines 30/90/180, untrusted sites, per-site gate status.
    """
    org_id = resolve_org_id(request, auth, db, org_id_override=org_id)
    return compute_portfolio_compliance_summary(db, org_id)


# ========================================
# V69: CEE Pipeline + M&V
# ========================================


class WorkPackageCreate(BaseModel):
    label: str
    size: str = "M"
    capex_eur: Optional[float] = None
    savings_eur_year: Optional[float] = None
    payback_years: Optional[float] = None
    complexity: Optional[str] = "medium"
    description: Optional[str] = None


@router.get("/sites/{site_id}/packages")
def list_work_packages(
    site_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/sites/{site_id}/packages

    V69: List all work packages (S/M/L) for a site with CEE dossier status.
    """
    return get_site_work_packages(db, site_id)


@router.post("/sites/{site_id}/packages")
def create_work_package(
    site_id: int,
    data: WorkPackageCreate,
    db: Session = Depends(get_db),
):
    """
    POST /api/compliance/sites/{site_id}/packages

    V69: Create a new work package for a site.
    """
    try:
        size = WorkPackageSize(data.size)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid size: {data.size}. Must be S, M, or L.")

    wp = WorkPackage(
        site_id=site_id,
        label=data.label,
        size=size,
        capex_eur=data.capex_eur,
        savings_eur_year=data.savings_eur_year,
        payback_years=data.payback_years,
        complexity=data.complexity,
        cee_status=CeeStatus.A_QUALIFIER,
        description=data.description,
    )
    db.add(wp)
    db.commit()
    db.refresh(wp)

    return {
        "id": wp.id,
        "site_id": wp.site_id,
        "label": wp.label,
        "size": wp.size.value,
        "cee_status": wp.cee_status.value,
    }


@router.post("/sites/{site_id}/cee/dossier")
def create_cee_dossier_endpoint(
    site_id: int,
    work_package_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """
    POST /api/compliance/sites/{site_id}/cee/dossier?work_package_id=

    V69: Create a CEE dossier from a work package.
    Auto-creates evidence items + Action Center items.
    """
    try:
        return create_cee_dossier(db, site_id, work_package_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class CeeStepAdvance(BaseModel):
    step: str


@router.patch("/cee/dossier/{dossier_id}/step")
def advance_cee_step_endpoint(
    dossier_id: int,
    data: CeeStepAdvance,
    db: Session = Depends(get_db),
):
    """
    PATCH /api/compliance/cee/dossier/{dossier_id}/step

    V69: Advance CEE dossier to next kanban step.
    Updates corresponding Action Center items.
    """
    try:
        return advance_cee_step(db, dossier_id, data.step)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sites/{site_id}/mv/summary")
def mv_summary_endpoint(
    site_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/sites/{site_id}/mv/summary

    V69: M&V summary — baseline, current, delta, alerts.
    """
    try:
        return compute_mv_summary(db, site_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========================================
# A.2 — Score conformité unifié
# ========================================


@router.get("/sites/{site_id}/score")
@router.get("/site/{site_id}/score")
def get_site_compliance_score(
    site_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/sites/{site_id}/score
    GET /api/compliance/site/{site_id}/score  (alias)

    Score conformité unifié 0-100 (A.2).
    Moyenne pondérée (Tertiaire 45% + BACS 30% + APER 25%)
    − pénalité findings critiques (max −20 pts).
    """
    from services.compliance_score_service import compute_site_compliance_score

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    result = compute_site_compliance_score(db, site_id)
    return result.to_dict()


@router.get("/portfolio/score")
def get_portfolio_compliance_score(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/portfolio/score

    Score conformité unifié du portefeuille (A.2).
    Moyenne pondérée par surface des scores sites.
    """
    from services.compliance_score_service import compute_portfolio_compliance

    org_id = resolve_org_id(request, auth, db)
    result = compute_portfolio_compliance(db, org_id)
    return JSONResponse(content=result, headers={"Cache-Control": "public, max-age=30"})


@router.get("/score-trend")
def get_compliance_score_trend(
    request: Request,
    months: int = 6,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """GET /api/compliance/score-trend — Trend mensuel du score conformite (sparkline)."""
    from services.compliance_score_trend import get_score_trend

    org_id = resolve_org_id(request, auth, db)
    trend = get_score_trend(db, org_id, months=months)
    return {"months": months, "trend": trend}


# ========================================
# Step 13 — Timeline reglementaire
# ========================================


def _build_timeline_events(db: Session, org_id: int, today: date) -> dict:
    """
    Construit la frise chronologique reglementaire a partir de regs.yaml
    et des sites de l'organisation.
    """
    import yaml
    import os

    # --- Load regs.yaml ---
    yaml_path = os.path.join(os.path.dirname(__file__), "..", "regops", "config", "regs.yaml")
    with open(yaml_path, "r", encoding="utf-8") as f:
        regs = yaml.safe_load(f)

    # --- Query org sites with relevant fields ---
    sites = (
        db.query(Site)
        .join(Portefeuille, Site.portefeuille_id == Portefeuille.id)
        .join(EntiteJuridique, Portefeuille.entite_juridique_id == EntiteJuridique.id)
        .filter(EntiteJuridique.organisation_id == org_id, Site.actif == True)
        .all()
    )

    # --- Query existing ComplianceFinding for NOK counts ---
    findings = (
        (db.query(ComplianceFinding).filter(ComplianceFinding.site_id.in_([s.id for s in sites])).all())
        if sites
        else []
    )

    nok_by_rule = {}
    for f in findings:
        if f.status in ("NOK", "non_conforme"):
            nok_by_rule.setdefault(f.rule_id or f.regulation, set()).add(f.site_id)

    # --- Build events from regs.yaml ---
    one_year = today + timedelta(days=365)
    events = []

    # Tertiaire
    dt_cfg = regs.get("tertiaire_operat", {})
    dt_deadlines = dt_cfg.get("deadlines", {})
    dt_penalties = dt_cfg.get("penalties", {})
    dt_threshold = dt_cfg.get("scope_threshold_m2", 1000)
    dt_sites = [s for s in sites if (s.tertiaire_area_m2 or 0) >= dt_threshold]

    if dt_deadlines.get("attestation_display"):
        dl = date.fromisoformat(dt_deadlines["attestation_display"])
        nok_count = len(nok_by_rule.get("OPERAT_NOT_STARTED", set()) | nok_by_rule.get("tertiaire_operat", set()))
        events.append(
            {
                "id": "tertiaire_affichage",
                "framework": "DECRET_TERTIAIRE",
                "label": "Attestation d'affichage énergétique",
                "deadline": dl.isoformat(),
                "status": _deadline_status(dl, today, one_year),
                "severity": "high",
                "sites_concerned": len(dt_sites),
                "sites_non_compliant": min(nok_count, len(dt_sites)),
                "description": "Tous les batiments tertiaires >= 1000 m\u00b2 doivent afficher leur performance energetique.",
                "penalty_eur": dt_penalties.get("non_affichage"),
            }
        )

    if dt_deadlines.get("declaration_2025"):
        dl = date.fromisoformat(dt_deadlines["declaration_2025"])
        nok_count = len(nok_by_rule.get("OPERAT_NOT_STARTED", set()) | nok_by_rule.get("tertiaire_operat", set()))
        events.append(
            {
                "id": "tertiaire_declaration",
                "framework": "DECRET_TERTIAIRE",
                "label": "Declaration OPERAT 2025",
                "deadline": dl.isoformat(),
                "status": _deadline_status(dl, today, one_year),
                "severity": "high",
                "sites_concerned": len(dt_sites),
                "sites_non_compliant": min(nok_count, len(dt_sites)),
                "description": "Declaration des consommations 2025 sur la plateforme OPERAT.",
                "penalty_eur": dt_penalties.get("non_declaration"),
            }
        )

    # BACS
    bacs_cfg = regs.get("bacs", {})
    bacs_deadlines = bacs_cfg.get("deadlines", {})
    bacs_penalties = bacs_cfg.get("penalties", {})
    bacs_thresholds = bacs_cfg.get("thresholds", {})

    # Count sites with BACS assets by CVC power (sum putile from systems)
    from models.bacs_models import BacsAsset, BacsCvcSystem
    from sqlalchemy import func as sa_func

    site_power = {}
    if sites:
        rows = (
            db.query(
                BacsAsset.site_id,
                sa_func.coalesce(sa_func.sum(BacsCvcSystem.putile_kw_computed), 0),
            )
            .outerjoin(BacsCvcSystem, BacsCvcSystem.asset_id == BacsAsset.id)
            .filter(BacsAsset.site_id.in_([s.id for s in sites]))
            .group_by(BacsAsset.site_id)
            .all()
        )
        site_power = {r[0]: r[1] for r in rows}

    sites_above_290 = {sid for sid, pw in site_power.items() if pw >= bacs_thresholds.get("high_kw", 290)}
    sites_70_to_290 = {
        sid
        for sid, pw in site_power.items()
        if bacs_thresholds.get("low_kw", 70) <= pw < bacs_thresholds.get("high_kw", 290)
    }

    if bacs_deadlines.get("above_290"):
        dl = date.fromisoformat(bacs_deadlines["above_290"])
        nok_count = len(nok_by_rule.get("BACS_290KW", set()) | nok_by_rule.get("bacs", set()))
        events.append(
            {
                "id": "bacs_290kw",
                "framework": "BACS",
                "label": "BACS > 290 kW — obligation GTB/GTC",
                "deadline": dl.isoformat(),
                "status": _deadline_status(dl, today, one_year),
                "severity": "critical",
                "sites_concerned": len(sites_above_290),
                "sites_non_compliant": min(nok_count, len(sites_above_290)),
                "description": "Les batiments avec une puissance CVC > 290 kW doivent etre equipes d'un systeme GTB/GTC.",
                "penalty_eur": bacs_penalties.get("non_compliance"),
            }
        )

    if bacs_deadlines.get("above_70"):
        dl = date.fromisoformat(bacs_deadlines["above_70"])
        events.append(
            {
                "id": "bacs_70kw",
                "framework": "BACS",
                "label": "BACS 70-290 kW — obligation GTB/GTC",
                "deadline": dl.isoformat(),
                "status": _deadline_status(dl, today, one_year),
                "severity": "medium",
                "sites_concerned": len(sites_70_to_290),
                "sites_non_compliant": 0,
                "description": "Extension de l'obligation GTB/GTC aux batiments avec puissance CVC 70-290 kW.",
                "penalty_eur": bacs_penalties.get("non_compliance"),
            }
        )

    # APER
    aper_cfg = regs.get("aper", {})
    aper_deadlines = aper_cfg.get("deadlines", {})
    aper_parking = aper_cfg.get("parking_thresholds", {})
    aper_roof = aper_cfg.get("roof_threshold_m2", 500)

    sites_parking_large = [s for s in sites if (s.parking_area_m2 or 0) >= aper_parking.get("large_m2", 10000)]
    sites_parking_medium = [
        s
        for s in sites
        if aper_parking.get("medium_m2", 1500) <= (s.parking_area_m2 or 0) < aper_parking.get("large_m2", 10000)
    ]
    sites_roof = [s for s in sites if (s.roof_area_m2 or 0) >= aper_roof]

    if aper_deadlines.get("parking_large"):
        dl = date.fromisoformat(aper_deadlines["parking_large"])
        events.append(
            {
                "id": "aper_parking_large",
                "framework": "APER",
                "label": "Solarisation parkings > 10 000 m\u00b2",
                "deadline": dl.isoformat(),
                "status": _deadline_status(dl, today, one_year),
                "severity": "medium",
                "sites_concerned": len(sites_parking_large),
                "sites_non_compliant": 0,
                "description": "Les parkings exterieurs > 10 000 m\u00b2 doivent etre equipes d'ombrieres photovoltaiques.",
                "penalty_eur": None,
            }
        )

    if aper_deadlines.get("parking_medium"):
        dl = date.fromisoformat(aper_deadlines["parking_medium"])
        events.append(
            {
                "id": "aper_parking_medium",
                "framework": "APER",
                "label": "Solarisation parkings 1 500-10 000 m\u00b2",
                "deadline": dl.isoformat(),
                "status": _deadline_status(dl, today, one_year),
                "severity": "medium",
                "sites_concerned": len(sites_parking_medium),
                "sites_non_compliant": 0,
                "description": "Les parkings exterieurs de 1 500 a 10 000 m\u00b2 doivent etre equipes d'ombrieres.",
                "penalty_eur": None,
            }
        )

    if aper_deadlines.get("roof"):
        dl = date.fromisoformat(aper_deadlines["roof"])
        events.append(
            {
                "id": "aper_roof",
                "framework": "APER",
                "label": "Solarisation toitures > 500 m\u00b2",
                "deadline": dl.isoformat(),
                "status": _deadline_status(dl, today, one_year),
                "severity": "medium",
                "sites_concerned": len(sites_roof),
                "sites_non_compliant": 0,
                "description": "Les toitures > 500 m\u00b2 des batiments neufs ou renoves doivent integrer du photovoltaique.",
                "penalty_eur": None,
            }
        )

    # Sort by deadline
    events.sort(key=lambda e: e["deadline"])

    # Next deadline (future only)
    next_dl = None
    for evt in events:
        dl = date.fromisoformat(evt["deadline"])
        if dl > today:
            days_remaining = (dl - today).days
            next_dl = {
                "id": evt["id"],
                "label": evt["label"],
                "deadline": evt["deadline"],
                "days_remaining": days_remaining,
            }
            break

    # Total penalty exposure
    total_penalty = sum(
        e.get("penalty_eur") or 0 for e in events if e["status"] != "passed" or e["sites_non_compliant"] > 0
    )

    return {
        "events": events,
        "today": today.isoformat(),
        "next_deadline": next_dl,
        "total_penalty_exposure_eur": total_penalty,
    }


def _deadline_status(deadline: date, today: date, one_year_out: date) -> str:
    """Determine event status based on deadline vs today."""
    if deadline < today:
        return "passed"
    elif deadline <= one_year_out:
        return "upcoming"
    else:
        return "future"


@router.get("/timeline")
def get_compliance_timeline(
    request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/timeline

    Frise chronologique reglementaire : evenements tries par date,
    statuts (passed/upcoming/future), sites concernes, penalites.
    """
    org_id = resolve_org_id(request, auth, db)
    today = date.today()
    result = _build_timeline_events(db, org_id, today)
    return JSONResponse(content=result, headers={"Cache-Control": "public, max-age=60"})
