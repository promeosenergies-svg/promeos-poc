"""
PROMEOS - Routes API Compliance Engine
Endpoint to trigger recomputation of site conformity snapshots.
+ Sprint 4: summary, sites findings, rules-based recompute.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from models import Organisation
from services.compliance_engine import (
    recompute_site,
    recompute_portfolio,
    recompute_organisation,
)
from services.compliance_rules import (
    evaluate_organisation,
    get_summary,
    get_sites_findings,
    load_all_packs,
)

router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


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
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/summary?org_id=

    Aggregate compliance findings for an organisation.
    If org_id is not provided, uses the first organisation.
    """
    if org_id is None:
        org = db.query(Organisation).first()
        if not org:
            return {
                "total_sites": 0, "sites_ok": 0, "sites_nok": 0,
                "sites_unknown": 0, "pct_ok": 0,
                "findings_by_regulation": {}, "top_actions": [],
            }
        org_id = org.id

    return get_summary(db, org_id)


@router.get("/sites")
def compliance_sites(
    org_id: Optional[int] = Query(None),
    regulation: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    GET /api/compliance/sites?org_id=&regulation=&status=&severity=

    Per-site findings list with filters.
    """
    if org_id is None:
        org = db.query(Organisation).first()
        if not org:
            return []
        org_id = org.id

    return get_sites_findings(db, org_id, regulation, status, severity)


@router.post("/recompute-rules")
def recompute_rules(
    org_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    POST /api/compliance/recompute-rules?org_id=

    Evaluate all YAML rules for all sites of an organisation.
    Produces ComplianceFinding rows.
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
