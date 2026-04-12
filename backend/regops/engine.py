"""
PROMEOS RegOps - Engine orchestrateur  ★ SOURCE DE VÉRITÉ ★

Coordonne 3 obligations réglementaires (tertiaire_operat, bacs, aper)
+ CEE P6 (incentif financier — hints uniquement, non inclus dans le score)
+ scoring unifié A.2 + cache RegAssessment.

C'est ce moteur qui alimente :
  - GET /api/regops/site/{id}          → évaluation fraîche
  - GET /api/regops/site/{id}/cached   → cache RegAssessment
  - compliance_score_service.py        → lit RegAssessment pour score 0-100
  - ConformitePage.jsx                 → via /api/compliance/bundle qui lit
                                         les ComplianceFinding produits par
                                         compliance_rules.py (même base YAML).

Les 3 autres moteurs existent pour des raisons historiques :
  - compliance_engine.py  → LEGACY (snapshots Site, backward-compat)
  - compliance_rules.py   → évaluateur YAML → ComplianceFinding rows
  - bacs_engine.py        → BACS V2 spécialisé (Putile, TRI, inspections)

Config scoring : regops/config/regs.yaml (poids, seuils, pénalités).
"""

import yaml
import os
from pathlib import Path
from datetime import date, datetime, timezone
from collections import defaultdict
from sqlalchemy.orm import Session

import logging

from models import Site, Batiment, Obligation, Evidence, RegAssessment, RegStatus
from models import Portefeuille, EntiteJuridique, not_deleted
from .schemas import Finding, Action, SiteSummary
from .completeness import check_required_inputs
from .versioning import compute_deterministic_version, compute_data_version
from .scoring import compute_regops_score  # kept for score_explain detail only
from .rules import tertiaire_operat, bacs, aper, cee_p6
from .config.legal_refs import get_legal_ref

_logger = logging.getLogger(__name__)


# Cache for YAML configs
_config_cache = {}


def _load_configs():
    """Load all YAML configs (cached)."""
    if _config_cache:
        return _config_cache

    config_dir = Path(__file__).parent / "config"

    with open(config_dir / "regs.yaml", encoding="utf-8") as f:
        _config_cache["regs"] = yaml.safe_load(f)

    with open(config_dir / "naf_profiles.yaml", encoding="utf-8") as f:
        _config_cache["naf_profiles"] = yaml.safe_load(f)

    with open(config_dir / "location_profiles.yaml", encoding="utf-8") as f:
        _config_cache["location_profiles"] = yaml.safe_load(f)

    with open(config_dir / "cee_p6_catalog.yaml", encoding="utf-8") as f:
        _config_cache["cee_p6_catalog"] = yaml.safe_load(f)

    return _config_cache


# ── Post-scoring Audit/SME (Loi 2025-391) ────────────────────────────────────


def _get_audit_sme_score_for_site(db: Session, site_id: int, org_id: int | None = None) -> tuple[float | None, bool]:
    """Recupere le score Audit/SME de l'organisation du site.

    Args:
        org_id: pre-resolved org_id (avoids N+1 in batch). If None, resolved on the fly.
    """
    try:
        from services.audit_sme_service import get_audit_sme_assessment

        if org_id is None:
            from services.scope_utils import resolve_org_id_from_site

            org_id = resolve_org_id_from_site(db, site_id)
        if not org_id:
            return (None, False)

        assessment = get_audit_sme_assessment(db, org_id)
        applicable = assessment.get("obligation") not in ("AUCUNE", "NON_DETERMINE", None)
        statut = assessment.get("statut")
        if applicable and statut not in ("CONFORME", "A_REALISER", "EN_RETARD", "EN_COURS"):
            return (None, False)
        score = assessment.get("score_audit_sme")
        return (score, applicable) if applicable else (None, False)

    except Exception as exc:
        _logger.debug("audit_sme score for site %d: %s", site_id, exc)
        return (None, False)


def _apply_audit_sme_to_compliance_score(
    raw_compliance_score: float,
    score_audit_sme: float | None,
    audit_sme_applicable: bool,
) -> tuple[float, dict]:
    """Applique le score Audit/SME au score compliance RegOps."""
    if not audit_sme_applicable or score_audit_sme is None:
        return (
            raw_compliance_score,
            {
                "audit_sme_applicable": False,
                "raw_compliance_score": raw_compliance_score,
                "score_audit_sme": None,
                "composite_score": raw_compliance_score,
            },
        )

    WEIGHT_AUDIT_SME = 0.16
    WEIGHT_FINDINGS = 0.84

    composite = raw_compliance_score * WEIGHT_FINDINGS + score_audit_sme * 100 * WEIGHT_AUDIT_SME
    composite = round(max(0.0, min(100.0, composite)), 2)

    return (
        composite,
        {
            "audit_sme_applicable": True,
            "raw_compliance_score": raw_compliance_score,
            "score_audit_sme": score_audit_sme,
            "weight_findings": WEIGHT_FINDINGS,
            "weight_audit_sme": WEIGHT_AUDIT_SME,
            "composite_score": composite,
        },
    )


def _check_usage_disagg_coverage(db: Session, site_id: int) -> dict:
    """Verifie si la decomposition CDC est disponible et fiable pour le site."""
    try:
        from services.analytics.usage_disaggregation import disaggregate_site
        from datetime import date, timedelta

        result = disaggregate_site(db, site_id, date.today() - timedelta(days=365), date.today())
        return {
            "available": len(result.usages) > 0,
            "n_usages": len(result.usages),
            "confidence": result.confidence_global,
            "method": result.method,
            "total_kwh": result.total_kwh,
        }
    except Exception as exc:
        _logger.debug("usage disagg check failed for site %d: %s", site_id, exc)
        return {"available": False, "n_usages": 0, "confidence": "none"}


def evaluate_site(db: Session, site_id: int, *, org_id: int | None = None) -> SiteSummary:
    """
    Evaluate un site avec les 4 reglementations.
    Retourne un SiteSummary complet.

    Args:
        org_id: pre-resolved org_id (avoids per-site join in batch mode).
    """
    # Load site + related data
    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} not found")

    batiments = db.query(Batiment).filter(Batiment.site_id == site_id).all()
    evidences = db.query(Evidence).filter(Evidence.site_id == site_id).all()
    obligations = db.query(Obligation).filter(Obligation.site_id == site_id).all()

    # Load configs
    configs = _load_configs()
    regs = configs["regs"]

    # Run 4 rule engines
    all_findings = []
    all_findings.extend(tertiaire_operat.evaluate(site, batiments, evidences, regs.get("tertiaire_operat", {}), db=db))
    all_findings.extend(bacs.evaluate(site, batiments, evidences, regs.get("bacs", {})))
    all_findings.extend(aper.evaluate(site, batiments, evidences, regs.get("aper", {})))
    all_findings.extend(cee_p6.evaluate(site, batiments, evidences, regs.get("cee_p6", {})))

    # Check completeness for missing data actions
    missing_data = []
    for reg_name in ["tertiaire_operat", "bacs", "aper"]:
        reg_config = regs.get(reg_name, {})
        missing = check_required_inputs(site, batiments, reg_config)
        missing_data.extend(missing)
    missing_data = list(set(missing_data))  # Deduplicate

    # Compute global status (worst finding status)
    status_severity = {
        "COMPLIANT": 0,
        "OUT_OF_SCOPE": 1,
        "EXEMPTION_POSSIBLE": 2,
        "AT_RISK": 3,
        "NON_COMPLIANT": 4,
        "UNKNOWN": 5,
    }
    worst_status = "COMPLIANT"
    for f in all_findings:
        if status_severity.get(f.status, 0) > status_severity.get(worst_status, 0):
            worst_status = f.status

    # Compute compliance score via unified A.2 service (single source of truth)
    from services.compliance_score_service import compute_site_compliance_score

    a2_result = compute_site_compliance_score(db, site_id)
    compliance_score = a2_result.score
    confidence_score = round(a2_result.frameworks_evaluated / a2_result.frameworks_total * 100, 1)

    # Post-scoring Audit/SME (Loi 2025-391) — org-level, fail-safe
    score_audit_sme, audit_sme_applicable = _get_audit_sme_score_for_site(db, site_id, org_id=org_id)
    compliance_score, audit_sme_detail = _apply_audit_sme_to_compliance_score(
        compliance_score, score_audit_sme, audit_sme_applicable
    )
    if audit_sme_applicable:
        _logger.info(
            "audit_sme post-scoring site=%d: raw=%.1f composite=%.1f audit_score=%s",
            site_id,
            audit_sme_detail.get("raw_compliance_score", 0),
            audit_sme_detail.get("composite_score", 0),
            score_audit_sme,
        )

    scoring = regs.get("scoring", {})
    severity_weights = scoring.get("severity_weights", {})
    confidence_weights = scoring.get("confidence_weights", {})

    # Next deadline
    deadlines = [f.legal_deadline for f in all_findings if f.legal_deadline]
    next_deadline = min(deadlines) if deadlines else None

    # Generate actions from findings
    actions = []
    for i, f in enumerate(all_findings):
        if f.status in ["AT_RISK", "NON_COMPLIANT", "UNKNOWN"]:
            priority_score = severity_weights.get(f.severity.lower(), 10) * confidence_weights.get(
                f.confidence.lower(), 1.0
            )
            if f.legal_deadline:
                days_to_deadline = (f.legal_deadline - date.today()).days
                if days_to_deadline < 90:
                    priority_score *= 1.5

            action = Action(
                action_code=f.rule_id,
                label=f.explanation,
                priority_score=priority_score,
                urgency_reason=f"Echeance: {f.legal_deadline.isoformat()}"
                if f.legal_deadline
                else "Pas d'echeance specifique",
                owner_role="Energy Manager",
                effort="MEDIUM",
                roi_hint=None,
                cee_p6_hints=None,
                is_ai_suggestion=False,
            )
            actions.append(action)

    # Sort actions by priority DESC
    actions.sort(key=lambda a: a.priority_score, reverse=True)

    # Versioning
    deterministic_version = compute_deterministic_version(regs, {})
    data_version = compute_data_version(site, obligations, evidences)

    return SiteSummary(
        site_id=site_id,
        global_status=worst_status,
        compliance_score=compliance_score,
        confidence_score=confidence_score,
        next_deadline=next_deadline,
        findings=all_findings,
        actions=actions,
        missing_data=missing_data,
        deterministic_version=deterministic_version,
        scoring_profile_id="compliance_score_service_a2",
    )


def evaluate_batch(db: Session, site_ids: list[int] = None) -> list[SiteSummary]:
    """
    Bulk evaluation — pre-fetches org_ids to avoid N+1 on Site→Org join.
    """
    base_q = not_deleted(db.query(Site), Site)
    if site_ids is None:
        sites = base_q.all()
    else:
        sites = base_q.filter(Site.id.in_(site_ids)).all()

    # Pre-fetch org_id for all sites in one query (avoids N+1 in _get_audit_sme_score_for_site)
    batch_site_ids = [s.id for s in sites]
    org_rows = (
        (
            not_deleted(
                not_deleted(
                    db.query(Site.id, EntiteJuridique.organisation_id).join(
                        Portefeuille, Portefeuille.id == Site.portefeuille_id
                    ),
                    Portefeuille,
                ).join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id),
                EntiteJuridique,
            )
            .filter(Site.id.in_(batch_site_ids))
            .all()
        )
        if batch_site_ids
        else []
    )
    org_id_by_site = {row[0]: row[1] for row in org_rows}

    summaries = []
    for site in sites:
        try:
            summary = evaluate_site(db, site.id, org_id=org_id_by_site.get(site.id))
            summaries.append(summary)
        except Exception as e:
            print(f"Error evaluating site {site.id}: {e}")
            continue

    return summaries


def persist_assessment(db: Session, summary: SiteSummary):
    """
    Upsert RegAssessment cache row.
    """
    import json

    existing = (
        db.query(RegAssessment)
        .filter(RegAssessment.object_type == "site", RegAssessment.object_id == summary.site_id)
        .first()
    )

    findings_json = json.dumps(
        [
            {
                "regulation": f.regulation,
                "rule_id": f.rule_id,
                "status": f.status,
                "severity": f.severity,
                "confidence": f.confidence,
                "legal_deadline": f.legal_deadline.isoformat() if f.legal_deadline else None,
                "explanation": f.explanation,
                "category": getattr(f, "category", "obligation"),
                "estimated_penalty_eur": getattr(f, "estimated_penalty_eur", None),
                "penalty_source": getattr(f, "penalty_source", None),
                "penalty_basis": getattr(f, "penalty_basis", None),
                "legal_ref": getattr(f, "legal_ref", None) or get_legal_ref(f.rule_id),
            }
            for f in summary.findings
        ]
    )

    actions_json = json.dumps(
        [
            {
                "action_code": a.action_code,
                "label": a.label,
                "priority_score": a.priority_score,
                "urgency_reason": a.urgency_reason,
            }
            for a in summary.actions[:10]
        ]
    )  # Top 10 only

    missing_data_json = json.dumps(summary.missing_data)

    if existing:
        existing.computed_at = datetime.now(timezone.utc)
        existing.global_status = RegStatus[summary.global_status]
        existing.compliance_score = summary.compliance_score
        existing.next_deadline = summary.next_deadline
        existing.findings_json = findings_json
        existing.top_actions_json = actions_json
        existing.missing_data_json = missing_data_json
        existing.deterministic_version = summary.deterministic_version
        _site_obj = db.query(Site).filter(Site.id == summary.site_id).first()
        _batiments = db.query(Batiment).filter(Batiment.site_id == summary.site_id).all()
        _evidences = db.query(Evidence).filter(Evidence.site_id == summary.site_id).all()
        existing.data_version = compute_data_version(_site_obj, _batiments, _evidences)
        existing.is_stale = False
    else:
        _site_obj = db.query(Site).filter(Site.id == summary.site_id).first()
        _batiments = db.query(Batiment).filter(Batiment.site_id == summary.site_id).all()
        _evidences = db.query(Evidence).filter(Evidence.site_id == summary.site_id).all()
        assessment = RegAssessment(
            object_type="site",
            object_id=summary.site_id,
            computed_at=datetime.now(timezone.utc),
            global_status=RegStatus[summary.global_status],
            compliance_score=summary.compliance_score,
            next_deadline=summary.next_deadline,
            findings_json=findings_json,
            top_actions_json=actions_json,
            missing_data_json=missing_data_json,
            deterministic_version=summary.deterministic_version,
            data_version=compute_data_version(_site_obj, _batiments, _evidences),
            is_stale=False,
        )
        db.add(assessment)

    db.flush()  # Flush only — la transaction est contrôlée par l'appelant
