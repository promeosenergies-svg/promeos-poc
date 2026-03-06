"""
PROMEOS Routes - RegOps endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from regops.engine import evaluate_site, persist_assessment
from regops.scoring import compute_regops_score, load_scoring_profile
from regops.data_quality import compute_data_quality
from regops.data_quality_specs import DATA_QUALITY_SPECS
from models import RegAssessment, Site, not_deleted
from services.compliance_score_service import compute_site_compliance_score, compute_portfolio_compliance

router = APIRouter(prefix="/api/regops", tags=["RegOps"])


@router.get("/site/{site_id}")
def get_site_assessment(site_id: int, db: Session = Depends(get_db)):
    """Evaluation RegOps complete d'un site (fresh compute)."""
    try:
        summary = evaluate_site(db, site_id)
        return {
            "site_id": summary.site_id,
            "global_status": summary.global_status,
            "compliance_score": summary.compliance_score,
            "next_deadline": summary.next_deadline.isoformat() if summary.next_deadline else None,
            "findings": [
                {
                    "regulation": f.regulation,
                    "rule_id": f.rule_id,
                    "status": f.status,
                    "severity": f.severity,
                    "confidence": f.confidence,
                    "legal_deadline": f.legal_deadline.isoformat() if f.legal_deadline else None,
                    "explanation": f.explanation,
                    "missing_inputs": f.missing_inputs,
                    "category": getattr(f, "category", "obligation"),
                }
                for f in summary.findings
            ],
            "actions": [
                {
                    "action_code": a.action_code,
                    "label": a.label,
                    "priority_score": a.priority_score,
                    "urgency_reason": a.urgency_reason,
                    "owner_role": a.owner_role,
                    "effort": a.effort,
                }
                for a in summary.actions
            ],
            "missing_data": summary.missing_data,
            "deterministic_version": summary.deterministic_version,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/site/{site_id}/cached")
def get_cached_assessment(site_id: int, db: Session = Depends(get_db)):
    """Retourne l'assessment en cache (rapide)."""
    assessment = (
        db.query(RegAssessment).filter(RegAssessment.object_type == "site", RegAssessment.object_id == site_id).first()
    )

    if not assessment:
        raise HTTPException(status_code=404, detail="No cached assessment")

    return {
        "site_id": site_id,
        "global_status": str(assessment.global_status).split(".")[-1],
        "compliance_score": assessment.compliance_score,
        "next_deadline": assessment.next_deadline.isoformat() if assessment.next_deadline else None,
        "computed_at": assessment.computed_at.isoformat(),
        "is_stale": assessment.is_stale,
    }


@router.post("/recompute")
def recompute_assessments(
    scope: str = Query("site", enum=["site", "all"]), site_id: int = Query(None), db: Session = Depends(get_db)
):
    """Trigger recompute (enqueue jobs ou execute directement)."""
    if scope == "site" and site_id:
        summary = evaluate_site(db, site_id)
        persist_assessment(db, summary)
        return {"recomputed": 1, "site_id": site_id}
    elif scope == "all":
        from regops.engine import evaluate_batch

        sites = not_deleted(db.query(Site), Site).all()
        summaries = evaluate_batch(db, [s.id for s in sites])
        for summary in summaries:
            persist_assessment(db, summary)
        return {"recomputed": len(summaries)}
    else:
        raise HTTPException(status_code=400, detail="Invalid scope or missing site_id")


@router.get("/score_explain")
def get_score_explain(
    scope_type: str = Query("site"),
    scope_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Score explain: detailed breakdown of compliance score computation."""
    if scope_type != "site":
        raise HTTPException(status_code=400, detail="Only scope_type=site supported")

    # Use unified A.2 score as source of truth
    a2_result = compute_site_compliance_score(db, scope_id)

    # Also run engine for findings-level detail (actions, missing data)
    try:
        summary = evaluate_site(db, scope_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # how_to_improve from findings
    how_to_improve = []
    for a in summary.actions[:5]:
        how_to_improve.append(
            {
                "action": a.label,
                "potential_gain": round(a.priority_score, 2),
                "regulation": a.action_code.split("_")[0] if "_" in a.action_code else a.action_code,
            }
        )

    return {
        "scope": {"type": scope_type, "id": scope_id},
        "score": a2_result.score,
        "confidence": a2_result.confidence,
        "formula": a2_result.formula,
        "breakdown": [
            {
                "framework": fs.framework,
                "score": fs.score,
                "weight": fs.weight,
                "available": fs.available,
                "source": fs.source,
            }
            for fs in a2_result.breakdown
        ],
        "critical_penalty": a2_result.critical_penalty,
        "frameworks_evaluated": a2_result.frameworks_evaluated,
        "frameworks_total": a2_result.frameworks_total,
        "dq_summary": {
            "missing_critical": summary.missing_data,
            "missing_optional": [],
        },
        "how_to_improve": how_to_improve,
    }


@router.get("/data_quality")
def get_data_quality(
    scope_type: str = Query("site"),
    scope_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Data quality gate: coverage, confidence, missing fields per regulation."""
    if scope_type != "site":
        raise HTTPException(status_code=400, detail="Only scope_type=site supported")

    report = compute_data_quality(db, scope_id)

    return {
        "scope": {"type": scope_type, "id": scope_id},
        "coverage_pct": report.coverage_pct,
        "confidence_score": report.confidence_score,
        "gate_status": report.gate_status,
        "missing_critical": report.missing_critical,
        "missing_optional": report.missing_optional,
        "per_regulation": report.per_regulation,
    }


@router.get("/data_quality/specs")
def get_data_quality_specs():
    """Return data quality field specs per regulation (for UI)."""
    return DATA_QUALITY_SPECS


@router.get("/dashboard")
def get_org_dashboard(
    org_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """KPIs org-level — score from unified A.2 service."""
    # Status counts from RegAssessment cache (findings-level, fast)
    assessments = db.query(RegAssessment).filter(RegAssessment.object_type == "site").all()

    total = len(assessments)
    compliant = sum(1 for a in assessments if "COMPLIANT" in str(a.global_status))
    at_risk = sum(1 for a in assessments if "AT_RISK" in str(a.global_status))
    non_compliant = sum(1 for a in assessments if "NON_COMPLIANT" in str(a.global_status))

    # Score from A.2 unified service (single source of truth)
    if org_id:
        portfolio = compute_portfolio_compliance(db, org_id)
        avg_score = portfolio["avg_score"]
    else:
        # Fallback: compute from cached assessments (legacy compat)
        avg_score = sum(a.compliance_score for a in assessments if a.compliance_score) / max(1, total)

    return {
        "total_sites": total,
        "sites_compliant": compliant,
        "sites_at_risk": at_risk,
        "sites_non_compliant": non_compliant,
        "avg_compliance_score": round(avg_score, 1),
    }
