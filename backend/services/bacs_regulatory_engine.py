"""
PROMEOS — BACS Regulatory Engine.

Couverture :
- Eligibilite complete (tertiaire, puissance, existant/neuf, renouvellement, ROI)
- Exigences fonctionnelles R.175-3
- Exploitation/maintenance R.175-4/5
- Inspection R.175-5-1
- Preuves documentaires
- Statut final prudent

JAMAIS de "conforme". Statuts toujours prudents et defendables.
"""

import json
import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models.bacs_models import BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection
from models.bacs_regulatory import BacsFunctionalRequirement, BacsExploitationStatus, BacsProofDocument

logger = logging.getLogger("promeos.bacs.regulatory")

SEUIL_HAUT = 290
SEUIL_BAS = 70
DEADLINE_290 = date(2025, 1, 1)
DEADLINE_70 = date(2030, 1, 1)

FUNCTIONAL_REQ_FIELDS = [
    "continuous_monitoring",
    "hourly_timestep",
    "functional_zones",
    "monthly_retention_5y",
    "reference_values",
    "efficiency_loss_detection",
    "interoperability",
    "manual_override",
    "autonomous_management",
    "data_ownership",
]

FUNCTIONAL_REQ_LABELS = {
    "continuous_monitoring": "Suivi et enregistrement continu",
    "hourly_timestep": "Pas de temps horaire",
    "functional_zones": "Logique par zone fonctionnelle",
    "monthly_retention_5y": "Conservation mensuelle 5 ans",
    "reference_values": "Valeurs de reference",
    "efficiency_loss_detection": "Detection pertes d'efficacite",
    "interoperability": "Interoperabilite (BACnet/KNX/OPC)",
    "manual_override": "Arret manuel possible",
    "autonomous_management": "Gestion autonome",
    "data_ownership": "Propriete/accessibilite des donnees",
}


def evaluate_full_bacs(db: Session, asset_id: int) -> dict:
    """Evaluation reglementaire BACS complete et prudente."""
    asset = db.query(BacsAsset).filter(BacsAsset.id == asset_id).first()
    if not asset:
        return {"error": "Asset introuvable"}

    # 1. Eligibilite
    eligibility = _evaluate_eligibility(db, asset)

    # 2. Exigences fonctionnelles
    functional = _evaluate_functional(db, asset_id)

    # 3. Exploitation / maintenance
    exploitation = _evaluate_exploitation(db, asset_id)

    # 4. Inspection
    inspection = _evaluate_inspection(db, asset_id)

    # 5. Preuves
    proofs = _evaluate_proofs(db, asset_id)

    # 6. Statut final
    final = _compute_final_status(eligibility, functional, exploitation, inspection, proofs)

    # Persist
    asset.bacs_scope_status = final["status"]
    asset.bacs_scope_reason = final["reason"][:200] if final["reason"] else None
    db.flush()

    return {
        "asset_id": asset_id,
        "eligibility": eligibility,
        "functional_requirements": functional,
        "exploitation": exploitation,
        "inspection": inspection,
        "proofs": proofs,
        "final_status": final["status"],
        "final_reason": final["reason"],
        "blockers": final["blockers"],
        "major_warnings": final["major_warnings"],
        "remediation": final.get("remediation", []),
        "is_compliant_claim_allowed": False,  # JAMAIS — par design
    }


# ── 1. Eligibilite ────────────────────────────────────────────────────


def _evaluate_eligibility(db, asset):
    if not asset.is_tertiary_non_residential:
        return {"in_scope": False, "reason": "Non tertiaire", "deadline": None, "tier": None}

    systems = db.query(BacsCvcSystem).filter(BacsCvcSystem.asset_id == asset.id).all()
    if not systems:
        return {"in_scope": None, "reason": "CVC non inventorie", "deadline": None, "tier": None}

    total_putile = sum(s.putile_kw_computed or 0 for s in systems)

    if total_putile < SEUIL_BAS:
        return {
            "in_scope": False,
            "reason": f"Putile {total_putile:.0f} kW < {SEUIL_BAS} kW",
            "deadline": None,
            "tier": None,
        }

    # Renouvellement
    renewal = False
    if asset.renewal_events_json:
        try:
            events = json.loads(asset.renewal_events_json)
            renewal = len(events) > 0
        except (json.JSONDecodeError, TypeError):
            pass

    # Construction neuve
    new_construction = asset.pc_date and asset.pc_date >= date(2023, 4, 9)

    if total_putile > SEUIL_HAUT:
        deadline = DEADLINE_290
        tier = "TIER1_290"
    else:
        deadline = DEADLINE_70
        tier = "TIER2_70"

    if new_construction:
        tier = "NEW_CONSTRUCTION"
        deadline = asset.pc_date
    elif renewal:
        tier = "RENEWAL"

    # TRI exemption
    last_assessment = (
        db.query(BacsAssessment)
        .filter(BacsAssessment.asset_id == asset.id)
        .order_by(BacsAssessment.assessed_at.desc())
        .first()
    )
    tri_exemption = last_assessment and last_assessment.tri_exemption_possible

    return {
        "in_scope": True,
        "reason": f"Putile {total_putile:.0f} kW — {tier}",
        "deadline": deadline.isoformat() if deadline else None,
        "tier": tier,
        "putile_kw": total_putile,
        "tri_exemption_possible": tri_exemption,
        "new_construction": new_construction,
        "renewal": renewal,
    }


# ── 2. Exigences fonctionnelles R.175-3 ───────────────────────────────


def _evaluate_functional(db, asset_id):
    req = db.query(BacsFunctionalRequirement).filter(BacsFunctionalRequirement.asset_id == asset_id).first()

    results = {}
    ok_count = 0
    total = len(FUNCTIONAL_REQ_FIELDS)

    for field in FUNCTIONAL_REQ_FIELDS:
        status = getattr(req, field, "not_demonstrated") if req else "not_demonstrated"
        results[field] = {
            "status": status,
            "label": FUNCTIONAL_REQ_LABELS[field],
        }
        if status == "ok":
            ok_count += 1

    return {
        "assessed": req is not None,
        "ok_count": ok_count,
        "total": total,
        "coverage_pct": round(ok_count / total * 100) if total else 0,
        "requirements": results,
        "all_demonstrated": ok_count == total,
    }


# ── 3. Exploitation / maintenance R.175-4/5 ───────────────────────────


def _evaluate_exploitation(db, asset_id):
    exp = db.query(BacsExploitationStatus).filter(BacsExploitationStatus.asset_id == asset_id).first()

    if not exp:
        return {
            "assessed": False,
            "written_procedures": "absent",
            "operator_trained": False,
            "control_points_defined": False,
            "repair_process_defined": False,
            "blockers": ["Exploitation/maintenance non evaluee"],
        }

    blockers = []
    if exp.written_procedures == "absent":
        blockers.append("Consignes ecrites absentes")
    if not exp.operator_trained:
        blockers.append("Formation exploitant non demontree")
    if not exp.control_points_defined:
        blockers.append("Points de controle non definis")

    return {
        "assessed": True,
        "written_procedures": exp.written_procedures,
        "operator_trained": exp.operator_trained,
        "training_date": exp.training_date.isoformat() if exp.training_date else None,
        "control_points_defined": exp.control_points_defined,
        "repair_process_defined": exp.repair_process_defined,
        "blockers": blockers,
    }


# ── 4. Inspection R.175-5-1 ───────────────────────────────────────────


def _evaluate_inspection(db, asset_id):
    inspections = db.query(BacsInspection).filter(BacsInspection.asset_id == asset_id).all()
    completed = [i for i in inspections if i.status.value == "completed"]

    if not completed:
        return {
            "has_inspection": False,
            "last_date": None,
            "next_due": None,
            "overdue": None,
            "report_compliant": None,
            "functional_analysis": None,
            "settings_evaluated": None,
            "critical_findings": 0,
            "blockers": ["Aucune inspection completee"],
        }

    last = max(completed, key=lambda i: i.inspection_date or i.created_at)
    today = date.today()
    overdue = last.due_next_date and last.due_next_date < today

    blockers = []
    if overdue:
        blockers.append(f"Inspection en retard (echeance {last.due_next_date})")
    if last.critical_findings_count and last.critical_findings_count > 0:
        blockers.append(f"{last.critical_findings_count} finding(s) critique(s)")
    if last.report_compliant is False:
        blockers.append("Rapport d'inspection non conforme")

    return {
        "has_inspection": True,
        "last_date": last.inspection_date.isoformat() if last.inspection_date else None,
        "next_due": last.due_next_date.isoformat() if last.due_next_date else None,
        "overdue": overdue,
        "inspection_type": getattr(last, "inspection_type", None),
        "report_compliant": getattr(last, "report_compliant", None),
        "functional_analysis": getattr(last, "functional_analysis_done", None),
        "settings_evaluated": getattr(last, "settings_evaluated", None),
        "critical_findings": last.critical_findings_count or 0,
        "blockers": blockers,
    }


# ── 5. Preuves ────────────────────────────────────────────────────────


def _evaluate_proofs(db, asset_id):
    proofs = db.query(BacsProofDocument).filter(BacsProofDocument.asset_id == asset_id).all()
    types_present = {p.document_type for p in proofs}

    expected = {"attestation_bacs", "rapport_inspection", "consignes", "formation"}
    missing = expected - types_present

    return {
        "count": len(proofs),
        "types_present": list(types_present),
        "expected_types": list(expected),
        "missing_types": list(missing),
        "coverage_pct": round((len(expected) - len(missing)) / len(expected) * 100) if expected else 0,
    }


# ── 6. Statut final ───────────────────────────────────────────────────


def _compute_final_status(eligibility, functional, exploitation, inspection, proofs):
    blockers = []
    major_warnings = []

    # Hors perimetre
    if eligibility["in_scope"] is False:
        return {"status": "not_applicable", "reason": eligibility["reason"], "blockers": [], "major_warnings": []}

    if eligibility["in_scope"] is None:
        return {
            "status": "potentially_in_scope",
            "reason": eligibility["reason"],
            "blockers": ["CVC non inventorie"],
            "major_warnings": [],
        }

    # Collecter tous les blockers
    if not functional["all_demonstrated"]:
        nb_missing = functional["total"] - functional["ok_count"]
        blockers.append(f"{nb_missing} exigence(s) fonctionnelle(s) non demontree(s)")

    blockers.extend(exploitation.get("blockers", []))
    blockers.extend(inspection.get("blockers", []))

    if proofs["missing_types"]:
        blockers.append(f"Preuves manquantes : {', '.join(proofs['missing_types'])}")

    # TRI exemption
    if eligibility.get("tri_exemption_possible"):
        major_warnings.append("Exemption TRI > 10 ans possible — a documenter")

    # Decision
    if blockers:
        status = "review_required"
        reason = f"{len(blockers)} blocker(s) — revue requise"
    else:
        status = "ready_for_internal_review"
        reason = f"Putile {eligibility.get('putile_kw', 0):.0f} kW — exigences couvertes — pret pour revue"

    # Remediation
    remediation = _build_remediation(blockers, functional, exploitation, inspection, proofs, eligibility)

    return {
        "status": status,
        "reason": reason,
        "blockers": blockers,
        "major_warnings": major_warnings,
        "remediation": remediation,
    }


# ── 7. Remediation ────────────────────────────────────────────────────


REMEDIATION_MAP = {
    "exigence": {
        "cause": "Exigences fonctionnelles R.175-3 non demontrees",
        "action": "Evaluer chaque exigence (suivi continu, pas horaire, zones, retention, etc.)",
        "proof": "Auto-evaluation documentee ou rapport d'inspection",
        "priority": "high",
    },
    "consignes": {
        "cause": "Consignes ecrites d'exploitation absentes",
        "action": "Rediger et approuver les consignes de verification periodique",
        "proof": "Document consignes signe par le responsable",
        "priority": "high",
    },
    "formation": {
        "cause": "Formation exploitant non demontree",
        "action": "Former l'exploitant et conserver l'attestation",
        "proof": "Attestation de formation avec date et organisme",
        "priority": "high",
    },
    "inspection": {
        "cause": "Inspection absente ou en retard",
        "action": "Planifier et realiser l'inspection reglementaire",
        "proof": "Rapport d'inspection",
        "priority": "critical",
    },
    "rapport": {
        "cause": "Rapport d'inspection non conforme",
        "action": "Faire corriger le rapport par l'inspecteur",
        "proof": "Rapport conforme",
        "priority": "high",
    },
    "finding_critique": {
        "cause": "Findings critiques non resolus",
        "action": "Traiter les non-conformites critiques identifiees",
        "proof": "Preuve de correction (photo, rapport, facture)",
        "priority": "critical",
    },
    "preuve": {
        "cause": "Preuves documentaires manquantes",
        "action": "Deposer les documents manquants dans le coffre BACS",
        "proof": "Documents types attendus",
        "priority": "medium",
    },
}


def _build_remediation(blockers, functional, exploitation, inspection, proofs, eligibility):
    items = []

    if not functional.get("all_demonstrated"):
        items.append(REMEDIATION_MAP["exigence"])

    for b in exploitation.get("blockers", []):
        if "consignes" in b.lower():
            items.append(REMEDIATION_MAP["consignes"])
        if "formation" in b.lower():
            items.append(REMEDIATION_MAP["formation"])

    for b in inspection.get("blockers", []):
        if "retard" in b.lower() or "inspection" in b.lower():
            items.append(REMEDIATION_MAP["inspection"])
        if "non conforme" in b.lower():
            items.append(REMEDIATION_MAP["rapport"])
        if "critique" in b.lower():
            items.append(REMEDIATION_MAP["finding_critique"])

    if proofs.get("missing_types"):
        items.append({**REMEDIATION_MAP["preuve"], "details": proofs["missing_types"]})

    # Dedup par cause
    seen = set()
    unique = []
    for item in items:
        if item["cause"] not in seen:
            seen.add(item["cause"])
            unique.append(item)

    return sorted(unique, key=lambda x: {"critical": 0, "high": 1, "medium": 2}.get(x["priority"], 3))
