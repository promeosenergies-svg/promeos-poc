"""
PROMEOS Routes - RegOps endpoints
"""

import logging
from datetime import date, datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from middleware.auth import get_optional_auth, AuthContext
from services.iam_scope import check_site_access, get_effective_org_id
from regops.engine import evaluate_site, persist_assessment
from regops.scoring import compute_regops_score, load_scoring_profile
from regops.data_quality import compute_data_quality
from regops.data_quality_specs import DATA_QUALITY_SPECS
from models import RegAssessment, Site, Portefeuille, EntiteJuridique, Organisation, not_deleted
from services.compliance_score_service import (
    compute_site_compliance_score,
    compute_portfolio_compliance,
    sync_site_unified_score,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/regops", tags=["RegOps"])


@router.get("/site/{site_id}")
def get_site_assessment(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Evaluation RegOps complete d'un site (fresh compute + persist + sync A.2)."""
    check_site_access(auth, site_id)
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
def get_cached_assessment(
    site_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Retourne l'assessment en cache (rapide)."""
    check_site_access(auth, site_id)
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
    scope: str = Query("site", enum=["site", "all"]),
    site_id: int = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Trigger recompute (enqueue jobs ou execute directement)."""
    if scope == "site" and site_id:
        check_site_access(auth, site_id)
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
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Score explain: detailed breakdown of compliance score computation."""
    if scope_type == "site":
        check_site_access(auth, scope_id)
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
        "_meta": {
            "note": "Detail pedagogique — poids canoniques DT 45% / BACS 30% / APER 25% (regs.yaml)",
            "score_global_sot": "RegAssessment.compliance_score via engine.py (S1+S3)",
            "module": "compliance_score_service (A.2 unifie)",
        },
    }


@router.get("/data_quality")
def get_data_quality(
    scope_type: str = Query("site"),
    scope_id: int = Query(...),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Data quality gate: coverage, confidence, missing fields per regulation."""
    if scope_type == "site":
        check_site_access(auth, scope_id)
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
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """KPIs org-level — score from unified A.2 service."""
    effective_org_id = get_effective_org_id(auth, org_id)
    # Resolve site_ids for the org (same join chain as cockpit)
    site_query = not_deleted(db.query(Site.id), Site)
    if effective_org_id:
        site_query = (
            site_query.join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .filter(EntiteJuridique.organisation_id == effective_org_id)
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
    if effective_org_id:
        portfolio = compute_portfolio_compliance(db, effective_org_id)
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


# ── Cockpit Deadline Banner (CX Gap #3) ──────────────────────────────────


@router.get("/audit-deadline-status")
def get_audit_deadline_status(
    org_id: int = Query(None),
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """Endpoint leger pour le DeadlineBanner cockpit."""
    effective_org_id = get_effective_org_id(auth, org_id)
    if not effective_org_id:
        return {"show_banner": False}

    from services.audit_sme_service import get_audit_sme_assessment

    assessment = get_audit_sme_assessment(db, effective_org_id)
    obligation = assessment.get("obligation", "AUCUNE")
    jours = assessment.get("jours_restants")
    show = obligation != "AUCUNE" and jours is not None and jours < 365

    urgency = "medium"
    if jours is not None:
        if jours < 90:
            urgency = "critical"
        elif jours < 180:
            urgency = "high"

    return {
        "deadline": "2026-10-11",
        "days_remaining": jours,
        "obligation": obligation,
        "statut": assessment.get("statut"),
        "conso_gwh": assessment.get("conso", {}).get("annuelle_moy_gwh", 0),
        "estimated_penalty_eur": 15000 if obligation != "AUCUNE" else 0,
        "show_banner": show,
        "urgency": urgency,
    }


# ── Audit Energetique / SME (Loi 2025-391) ──────────────────────────────────


@router.get("/organisations/{organisation_id}/audit-sme")
def get_audit_sme(
    organisation_id: int,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Evaluation complete Audit Energetique / SME pour une organisation.

    Source : Loi n 2025-391 du 30 avril 2025 (art. L.233-1 code de l'energie)
    Deadline premier audit : 11 octobre 2026
    """
    effective_org_id = get_effective_org_id(auth, organisation_id)
    from services.audit_sme_service import get_audit_sme_assessment

    return get_audit_sme_assessment(db, effective_org_id)


@router.get("/audit-sme/scope")
def get_audit_sme_scope(
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Liste toutes les organisations dans le perimetre Audit/SME avec leur statut.
    Pre-fetches AuditEnergetique records to avoid N+1.
    """
    from models.audit_sme import AuditEnergetique
    from services.audit_sme_service import get_audit_sme_assessment

    org_query = db.query(Organisation).filter(Organisation.actif == True)  # noqa: E712
    if auth and auth.org_id:
        org_query = org_query.filter(Organisation.id == auth.org_id)
    organisations = org_query.all()

    # Bulk-fetch all AuditEnergetique records (avoids N individual queries)
    org_ids = [org.id for org in organisations]
    all_audits = (
        db.query(AuditEnergetique).filter(AuditEnergetique.organisation_id.in_(org_ids)).all() if org_ids else []
    )
    audit_by_org = {a.organisation_id: a for a in all_audits}

    results = []
    for org in organisations:
        try:
            assessment = get_audit_sme_assessment(db, org.id, _prefetched_audit=audit_by_org.get(org.id))
            if assessment["obligation"] != "AUCUNE":
                results.append(
                    {
                        "organisation_id": org.id,
                        "organisation_nom": org.nom,
                        "obligation": assessment["obligation"],
                        "statut": assessment["statut"],
                        "conso_gwh": assessment["conso"]["annuelle_moy_gwh"],
                        "jours_restants": assessment["jours_restants"],
                        "urgence": assessment["urgence"],
                        "score": assessment["score_audit_sme"],
                    }
                )
        except Exception as exc:
            logger.warning("Audit/SME assessment failed for org %d: %s", org.id, exc)

    ordre = {"EN_RETARD": 0, "A_REALISER": 1, "EN_COURS": 2, "CONFORME": 3, "NON_CONCERNE": 4}
    results.sort(key=lambda r: ordre.get(r["statut"], 5))

    return {
        "n_organisations": len(organisations),
        "n_concernees": len(results),
        "organisations": results,
        "source": "audit_sme_service",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


class AuditSmeUpdate(BaseModel):
    auditeur_identifie: Optional[bool] = None
    audit_realise: Optional[bool] = None
    date_dernier_audit: Optional[date] = None
    plan_action_publie: Optional[bool] = None
    transmission_realisee: Optional[bool] = None
    sme_certifie_iso50001: Optional[bool] = None
    date_certification_sme: Optional[date] = None
    organisme_certificateur: Optional[str] = None

    model_config = {"extra": "forbid"}


@router.patch("/organisations/{organisation_id}/audit-sme")
def update_audit_sme_record(
    organisation_id: int,
    payload: AuditSmeUpdate,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_optional_auth),
):
    """
    Met a jour le statut Audit/SME d'une organisation (action manuelle).
    """
    from models.audit_sme import AuditEnergetique
    from services.audit_sme_service import get_audit_sme_assessment

    effective_org_id = get_effective_org_id(auth, organisation_id)
    audit = db.query(AuditEnergetique).filter_by(organisation_id=effective_org_id).first()

    if not audit:
        audit = AuditEnergetique(
            organisation_id=effective_org_id,
            date_premier_audit_limite=date(2026, 10, 11),
        )
        db.add(audit)

    updates = payload.model_dump(exclude_unset=True)
    for field, val in updates.items():
        setattr(audit, field, val)

    db.commit()
    db.refresh(audit)

    return get_audit_sme_assessment(db, effective_org_id)
