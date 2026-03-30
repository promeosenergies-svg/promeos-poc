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
from models import RegAssessment, Site, Portefeuille, EntiteJuridique, not_deleted
from services.compliance_score_service import (
    compute_site_compliance_score,
    compute_portfolio_compliance,
    sync_site_unified_score,
)

router = APIRouter(prefix="/api/regops", tags=["RegOps"])


@router.get("/site/{site_id}")
def get_site_assessment(site_id: int, db: Session = Depends(get_db)):
    """Evaluation RegOps complete d'un site (fresh compute + persist + sync A.2)."""
    try:
        summary = evaluate_site(db, site_id)
        persist_assessment(db, summary)
        sync_site_unified_score(db, site_id)
        db.commit()
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
        db.commit()
        return {"recomputed": 1, "site_id": site_id}
    elif scope == "all":
        from regops.engine import evaluate_batch

        sites = not_deleted(db.query(Site), Site).all()
        summaries = evaluate_batch(db, [s.id for s in sites])
        for summary in summaries:
            persist_assessment(db, summary)
        db.commit()
        return {"recomputed": len(summaries)}
    else:
        raise HTTPException(status_code=400, detail="Invalid scope or missing site_id")


_FRAMEWORK_LABELS = {
    "tertiaire_operat": {"label": "Decret Tertiaire", "next_deadline": "2026-09-30"},
    "bacs": {"label": "Decret BACS (GTB)", "next_deadline": "2030-01-01"},
    "aper": {"label": "Loi APER (solaire)", "next_deadline": "2028-07-01"},
}


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

    # Findings par framework (pour worst_finding et penalties_count)
    findings_by_fw = {}
    if hasattr(summary, "findings"):
        for f in summary.findings:
            fw = f.regulation.lower() if hasattr(f, "regulation") else "unknown"
            # Normaliser le nom
            for key in _FRAMEWORK_LABELS:
                if key.split("_")[0] in fw:
                    fw = key
                    break
            findings_by_fw.setdefault(fw, []).append(f)

    per_regulation = []
    formula_parts = []
    for fs in a2_result.breakdown:
        meta = _FRAMEWORK_LABELS.get(fs.framework, {"label": fs.framework, "next_deadline": None})
        fw_findings = findings_by_fw.get(fs.framework, [])
        penalties_count = len(fw_findings)
        worst_label = None
        if fw_findings:
            worst = max(fw_findings, key=lambda f: getattr(f, "priority_score", 0))
            worst_label = getattr(worst, "label", getattr(worst, "rule_id", None))

        per_regulation.append(
            {
                "regulation": fs.framework,
                "label": meta["label"],
                "weight": fs.weight,
                "sub_score": fs.score,
                "available": fs.available,
                "source": fs.source,
                "penalties_count": penalties_count,
                "worst_finding_label": worst_label,
                "next_deadline": meta["next_deadline"],
            }
        )
        formula_parts.append(f"{fs.score}x{fs.weight}")

    formula_str = f"Score = sum({' + '.join(formula_parts)}) - {a2_result.critical_penalty} penalty = {a2_result.score}"

    return {
        "scope": {"type": scope_type, "id": scope_id},
        "score": a2_result.score,
        "confidence": a2_result.confidence,
        "formula": a2_result.formula,
        "formula_explain": formula_str,
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
        "per_regulation": per_regulation,
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
    # Resolve site_ids for the org (same join chain as cockpit)
    site_query = not_deleted(db.query(Site.id), Site)
    if org_id:
        site_query = (
            site_query.join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == org_id)
        )
    site_ids = [row[0] for row in site_query.all()]

    # Status counts from RegAssessment cache (findings-level, fast)
    assessments = (
        db.query(RegAssessment).filter(RegAssessment.object_type == "site", RegAssessment.object_id.in_(site_ids)).all()
        if site_ids
        else []
    )

    total = len(assessments)
    compliant = sum(1 for a in assessments if "COMPLIANT" in str(a.global_status))
    at_risk = sum(1 for a in assessments if "AT_RISK" in str(a.global_status))
    non_compliant = sum(1 for a in assessments if "NON_COMPLIANT" in str(a.global_status))

    # Score from A.2 unified service (single source of truth)
    if org_id:
        portfolio = compute_portfolio_compliance(db, org_id)
        avg_score = portfolio["avg_score"]
    else:
        avg_score = sum(a.compliance_score for a in assessments if a.compliance_score) / max(1, total)

    return {
        "total_sites": total,
        "sites_compliant": compliant,
        "sites_at_risk": at_risk,
        "sites_non_compliant": non_compliant,
        "avg_compliance_score": round(avg_score, 1),
    }
