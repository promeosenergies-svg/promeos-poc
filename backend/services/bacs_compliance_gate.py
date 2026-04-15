"""
PROMEOS — BACS Compliance Gate : evaluation prudente du statut BACS.

★ Matrice d'usage BACS (trois fonctions complémentaires) ★

| Fonction                                           | Rôle                                        | Quand l'utiliser                                  |
|----------------------------------------------------|---------------------------------------------|---------------------------------------------------|
| services.bacs_engine.evaluate_bacs(db, site_id)    | Moteur V2 complet (Putile, classe EN15232, | Production : recompute complet d'un site          |
|                                                    | TRI, inspections, score 0-100)             | → écrit BacsAssessment row + snapshots Site       |
| services.bacs_engine.evaluate_legacy(site,         | Adapter signature RegOps                   | Via regops/rules/bacs.py dans evaluate_site       |
|  batiments, evidences, config)                     | (Putile simple, fallback v1)               | → produit list[Finding] pour RegAssessment        |
| services.bacs_compliance_gate.evaluate_bacs_status | Gate prudente "jamais de CONFORME sans    | Endpoint /api/bacs/asset/{id}/gate-evaluation    |
|  (db, asset_id)                                    | preuve" (blockers, warnings, major)        | → audit compliance-officer, NE persiste QUE       |
|                                                    |                                             | BacsAsset.bacs_scope_status                       |

Logique de ce module : jamais de "conforme" si la preuve n'est pas démontrée.
Le gate lit la MÊME config YAML que l'engine V2 (regulations/bacs/v2.yaml) pour
garantir l'absence de dérive sur les seuils 290/70 kW et les deadlines.
"""

import logging
from typing import Optional, List
from sqlalchemy.orm import Session

from models.bacs_models import BacsAsset, BacsCvcSystem, BacsAssessment, BacsInspection
from services.bacs_engine import _load_bacs_config

logger = logging.getLogger("promeos.bacs.gate")


def _get_thresholds() -> tuple[int, int]:
    """Retourne (high_kw, low_kw) depuis regulations/bacs/v2.yaml — source unique."""
    cfg = _load_bacs_config()
    thresholds = cfg.get("thresholds_kw", {})
    return (int(thresholds.get("tier1", 290)), int(thresholds.get("tier2", 70)))


# Statuts BACS prudents
NOT_APPLICABLE = "not_applicable"
POTENTIALLY_IN_SCOPE = "potentially_in_scope"
IN_SCOPE_INCOMPLETE = "in_scope_incomplete"
REVIEW_REQUIRED = "review_required"
READY_FOR_REVIEW = "ready_for_internal_review"


def evaluate_bacs_status(db: Session, asset_id: int) -> dict:
    """Evalue le statut BACS d'un actif de facon prudente et tracable.

    JAMAIS de statut affirmatif sans preuve. Utilise les seuils V2 YAML
    (regulations/bacs/v2.yaml) — même source que services.bacs_engine.
    """
    seuil_haut, seuil_bas = _get_thresholds()

    asset = db.query(BacsAsset).filter(BacsAsset.id == asset_id).first()
    if not asset:
        return {"status": "error", "reason": "Asset introuvable"}

    warnings = []
    major_warnings = []
    blockers = []

    # 1. Eligibilite de base
    if not asset.is_tertiary_non_residential:
        asset.bacs_scope_status = NOT_APPLICABLE
        asset.bacs_scope_reason = "Batiment non tertiaire ou residentiel"
        db.flush()
        return _result(NOT_APPLICABLE, "Batiment non tertiaire", [], [], [])

    # 2. Systemes CVC
    systems = db.query(BacsCvcSystem).filter(BacsCvcSystem.asset_id == asset_id).all()
    if not systems:
        asset.bacs_scope_status = POTENTIALLY_IN_SCOPE
        asset.bacs_scope_reason = "Aucun systeme CVC inventorie"
        db.flush()
        return _result(POTENTIALLY_IN_SCOPE, "Inventaire CVC absent", [], ["Inventorier les systemes CVC"], [])

    # 3. Puissance
    putile_max = max((s.putile_kw_computed or 0) for s in systems)
    total_putile = sum(s.putile_kw_computed or 0 for s in systems)

    if total_putile < seuil_bas:
        asset.bacs_scope_status = NOT_APPLICABLE
        asset.bacs_scope_reason = f"Putile {total_putile:.0f} kW < {seuil_bas} kW"
        db.flush()
        return _result(NOT_APPLICABLE, f"Putile {total_putile:.0f} kW < seuil {seuil_bas} kW", [], [], [])

    # 4. Classe systeme
    unknown_class_systems = [s for s in systems if not s.system_class]
    unverified_class_systems = [s for s in systems if s.system_class and not s.system_class_verified]
    non_compliant_class = [s for s in systems if s.system_class in ("C", "D")]

    if unknown_class_systems:
        blockers.append(f"{len(unknown_class_systems)} systeme(s) sans classe GTB connue")
        major_warnings.append("Classe GTB inconnue — conformite BACS non demontrable")

    if unverified_class_systems:
        warnings.append(f"{len(unverified_class_systems)} systeme(s) avec classe non verifiee (declaratif)")

    if non_compliant_class:
        blockers.append(f"{len(non_compliant_class)} systeme(s) classe C ou D — non conforme")

    # 5. Inspections
    inspections = db.query(BacsInspection).filter(BacsInspection.asset_id == asset_id).all()
    completed = [i for i in inspections if i.status.value == "completed"]

    if not completed:
        blockers.append("Aucune inspection completee")
    else:
        last = max(completed, key=lambda i: i.inspection_date or i.created_at)
        if last.critical_findings_count and last.critical_findings_count > 0:
            blockers.append(f"Derniere inspection : {last.critical_findings_count} finding(s) critique(s)")

    # 6. Preuves / attestation
    assessment = (
        db.query(BacsAssessment)
        .filter(BacsAssessment.asset_id == asset_id)
        .order_by(BacsAssessment.assessed_at.desc())
        .first()
    )
    if not assessment:
        warnings.append("Aucune evaluation BACS enregistree")

    # 7. Performance / efficacite
    systems_without_baseline = [s for s in systems if not s.performance_baseline_kwh]
    if systems_without_baseline and total_putile >= seuil_bas:
        warnings.append(
            f"{len(systems_without_baseline)} systeme(s) sans baseline performance — perte efficacite non evaluable"
        )

    # 8. Decision finale prudente
    has_critical_inspection = any("critique" in b.lower() or "critical" in b.lower() for b in blockers)
    if blockers:
        if unknown_class_systems or non_compliant_class or has_critical_inspection:
            status = REVIEW_REQUIRED
            reason = "Blocages : " + " ; ".join(blockers)
        else:
            status = IN_SCOPE_INCOMPLETE
            reason = "Donnees insuffisantes : " + " ; ".join(blockers)
    elif major_warnings:
        status = REVIEW_REQUIRED
        reason = " ; ".join(major_warnings)
    elif not completed:
        status = IN_SCOPE_INCOMPLETE
        reason = "Inspection manquante"
    else:
        # Warnings mineurs ne bloquent pas : ready for review avec notes
        status = READY_FOR_REVIEW
        reason = f"Putile {total_putile:.0f} kW — pret pour revue interne"
        if warnings:
            reason += " (" + str(len(warnings)) + " point(s) d'attention)"

    asset.bacs_scope_status = status
    asset.bacs_scope_reason = reason[:200]
    db.flush()

    return _result(
        status,
        reason,
        blockers,
        warnings,
        major_warnings,
        {
            "putile_kw": total_putile,
            "systems_count": len(systems),
            "unknown_class_count": len(unknown_class_systems),
            "non_compliant_class_count": len(non_compliant_class),
            "inspections_completed": len(completed),
            "has_assessment": assessment is not None,
        },
    )


def _result(status, reason, blockers, warnings, major_warnings, details=None):
    return {
        "bacs_status": status,
        "reason": reason,
        "blockers": blockers,
        "warnings": warnings,
        "major_warnings": major_warnings,
        "details": details or {},
        "is_compliant_claim_allowed": status == READY_FOR_REVIEW and not blockers and not major_warnings,
    }
