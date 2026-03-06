"""
PROMEOS - Routes API Compliance Engine
Endpoint to trigger recomputation of site conformity snapshots.
+ Sprint 4: summary, sites findings, rules-based recompute.
+ Sprint 9: OPS workflow (findings PATCH, batches, findings list).
"""

import json
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
from services.compliance_engine import (
    recompute_site,
    recompute_portfolio,
    recompute_organisation,
    compute_site_compliance_summary,
    compute_portfolio_compliance_summary,
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
    site = db.query(Site).filter(Site.id == finding.site_id).first()
    if site:
        org_match = (
            db.query(EntiteJuridique.organisation_id)
            .join(Portefeuille, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(Portefeuille.id == site.portefeuille_id)
            .first()
        )
        if not org_match or org_match[0] != org_id:
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
    site = db.query(Site).filter(Site.id == f.site_id).first()
    if site:
        org_match = (
            db.query(EntiteJuridique.organisation_id)
            .join(Portefeuille, Portefeuille.entite_juridique_id == EntiteJuridique.id)
            .filter(Portefeuille.id == site.portefeuille_id)
            .first()
        )
        if not org_match or org_match[0] != org_id:
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
def get_site_compliance_score(
    site_id: int,
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/sites/{site_id}/score

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
