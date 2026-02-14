"""
PROMEOS - Routes API Compliance Engine
Endpoint to trigger recomputation of site conformity snapshots.
+ Sprint 4: summary, sites findings, rules-based recompute.
+ Sprint 9: OPS workflow (findings PATCH, batches, findings list).
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import (
    Organisation, ComplianceFinding, ComplianceRunBatch, InsightStatus,
    Site, Portefeuille, EntiteJuridique,
)
from services.compliance_engine import (
    recompute_site,
    recompute_portfolio,
    recompute_organisation,
)
from services.compliance_rules import (
    evaluate_organisation,
    get_summary,
    get_sites_findings,
    get_compliance_bundle,
    load_all_packs,
)
from middleware.auth import get_optional_auth, AuthContext

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
    org_id: Optional[int] = Query(None),
    entity_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/summary?org_id=&entity_id=&site_id=

    Aggregate compliance findings with scope filtering.
    Scope priority: site_id > entity_id > org_id.
    """
    if org_id is None and entity_id is None and site_id is None:
        org = db.query(Organisation).first()
        if not org:
            return {
                "total_sites": 0, "sites_ok": 0, "sites_nok": 0,
                "sites_unknown": 0, "pct_ok": 0,
                "findings_by_regulation": {}, "top_actions": [],
                "empty_reason": "NO_SITES",
            }
        org_id = org.id

    return get_summary(db, org_id or 0, entity_id=entity_id, site_id=site_id)


@router.get("/sites")
def compliance_sites(
    org_id: Optional[int] = Query(None),
    entity_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/sites?org_id=&entity_id=&site_id=&regulation=&status=&severity=

    Per-site findings list with scope filtering.
    """
    if org_id is None and entity_id is None and site_id is None:
        org = db.query(Organisation).first()
        if not org:
            return []
        org_id = org.id

    return get_sites_findings(db, org_id or 0, regulation, status, severity,
                              entity_id=entity_id, site_id=site_id)


@router.get("/bundle")
def compliance_bundle(
    org_id: Optional[int] = Query(None),
    entity_id: Optional[int] = Query(None),
    site_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/bundle?org_id=&entity_id=&site_id=

    Single-request bundle: summary + sites + empty_reason.
    Frontend must pass org_id explicitly for correct scope.
    """
    if org_id is None:
        org = db.query(Organisation).first()
        if not org:
            return get_compliance_bundle(db, 0)
        org_id = org.id

    return get_compliance_bundle(
        db, org_id,
        entity_id=entity_id, site_id=site_id,
        regulation=regulation, status=status, severity=severity,
    )


@router.post("/recompute-rules")
def recompute_rules(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    POST /api/compliance/recompute-rules?org_id=

    Evaluate all YAML rules for all sites of an organisation.
    Produces ComplianceFinding rows + ComplianceRunBatch (Sprint 9).
    """
    if org_id is None:
        org = db.query(Organisation).first()
        if not org:
            raise HTTPException(status_code=400, detail="Aucune organisation trouvee.")
        org_id = org.id

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
            "rules": [
                {"id": r["id"], "label": r["label"], "severity": r.get("severity")}
                for r in p["rules"]
            ],
        }
        for p in packs
    ]


# ========================================
# Sprint 9: OPS workflow
# ========================================


@router.get("/findings")
def list_findings(
    org_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    insight_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    GET /api/compliance/findings

    List all findings with workflow fields. Supports filters.
    """
    # Resolve org scope
    if auth:
        org_id = auth.org_id
    elif org_id is None:
        org = db.query(Organisation).first()
        if not org:
            return []
        org_id = org.id

    site_ids = [
        row[0] for row in
        db.query(Site.id)
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

    findings = q.all()

    # Build response with site_nom
    site_names = {}
    result = []
    for f in findings:
        if f.site_id not in site_names:
            site = db.query(Site).filter(Site.id == f.site_id).first()
            site_names[f.site_id] = site.nom if site else "?"
        actions = json.loads(f.recommended_actions_json) if f.recommended_actions_json else []
        result.append({
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
        })

    return result


@router.patch("/findings/{finding_id}")
def patch_finding(finding_id: int, data: FindingPatch, db: Session = Depends(get_db)):
    """
    PATCH /api/compliance/findings/{finding_id}

    Update finding workflow: status, owner, notes.
    """
    finding = db.query(ComplianceFinding).filter(ComplianceFinding.id == finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding non trouve")

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
def get_finding_detail(finding_id: int, db: Session = Depends(get_db)):
    """
    GET /api/compliance/findings/{finding_id}

    Detailed finding with audit fields (inputs, params, evidence, engine_version).
    """
    f = db.query(ComplianceFinding).filter(ComplianceFinding.id == finding_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")

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
