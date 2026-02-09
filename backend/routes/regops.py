"""
PROMEOS Routes - RegOps endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from regops.engine import evaluate_site, persist_assessment
from models import RegAssessment, Site

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
                    "missing_inputs": f.missing_inputs
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
                    "effort": a.effort
                }
                for a in summary.actions
            ],
            "missing_data": summary.missing_data,
            "deterministic_version": summary.deterministic_version
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/site/{site_id}/cached")
def get_cached_assessment(site_id: int, db: Session = Depends(get_db)):
    """Retourne l'assessment en cache (rapide)."""
    assessment = db.query(RegAssessment).filter(
        RegAssessment.object_type == "site",
        RegAssessment.object_id == site_id
    ).first()

    if not assessment:
        raise HTTPException(status_code=404, detail="No cached assessment")

    return {
        "site_id": site_id,
        "global_status": str(assessment.global_status).split(".")[-1],
        "compliance_score": assessment.compliance_score,
        "next_deadline": assessment.next_deadline.isoformat() if assessment.next_deadline else None,
        "computed_at": assessment.computed_at.isoformat(),
        "is_stale": assessment.is_stale
    }


@router.post("/recompute")
def recompute_assessments(
    scope: str = Query("site", enum=["site", "all"]),
    site_id: int = Query(None),
    db: Session = Depends(get_db)
):
    """Trigger recompute (enqueue jobs ou execute directement)."""
    if scope == "site" and site_id:
        summary = evaluate_site(db, site_id)
        persist_assessment(db, summary)
        return {"recomputed": 1, "site_id": site_id}
    elif scope == "all":
        from regops.engine import evaluate_batch
        sites = db.query(Site).all()
        summaries = evaluate_batch(db, [s.id for s in sites])
        for summary in summaries:
            persist_assessment(db, summary)
        return {"recomputed": len(summaries)}
    else:
        raise HTTPException(status_code=400, detail="Invalid scope or missing site_id")


@router.get("/dashboard")
def get_org_dashboard(db: Session = Depends(get_db)):
    """KPIs org-level."""
    assessments = db.query(RegAssessment).filter(RegAssessment.object_type == "site").all()

    total = len(assessments)
    compliant = sum(1 for a in assessments if "COMPLIANT" in str(a.global_status))
    at_risk = sum(1 for a in assessments if "AT_RISK" in str(a.global_status))
    non_compliant = sum(1 for a in assessments if "NON_COMPLIANT" in str(a.global_status))

    avg_score = sum(a.compliance_score for a in assessments) / total if total > 0 else 0

    return {
        "total_sites": total,
        "sites_compliant": compliant,
        "sites_at_risk": at_risk,
        "sites_non_compliant": non_compliant,
        "avg_compliance_score": round(avg_score, 1)
    }
