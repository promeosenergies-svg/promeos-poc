"""
PROMEOS RegOps - Regle Tertiaire/OPERAT
"""

import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from ..schemas import Finding

_logger = logging.getLogger(__name__)


def evaluate(site, batiments: list, evidences: list, config: dict, *, db: Optional[Session] = None) -> list[Finding]:
    findings = []

    # Check scope
    tertiaire_area = site.tertiaire_area_m2
    scope_threshold = config.get("scope_threshold_m2", 1000)

    if tertiaire_area is None:
        findings.append(
            Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="SCOPE_UNKNOWN",
                status="UNKNOWN",
                severity="HIGH",
                confidence="HIGH",
                legal_deadline=None,
                trigger_condition=f"tertiaire_area_m2 is None",
                config_params_used={"scope_threshold_m2": scope_threshold},
                inputs_used=[],
                missing_inputs=["tertiaire_area_m2"],
                explanation="Impossible de determiner l'assujettissement sans la surface tertiaire.",
            )
        )
        return findings

    if tertiaire_area < scope_threshold:
        findings.append(
            Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="OUT_OF_SCOPE",
                status="OUT_OF_SCOPE",
                severity="LOW",
                confidence="HIGH",
                legal_deadline=None,
                trigger_condition=f"tertiaire_area_m2 < {scope_threshold}",
                config_params_used={"scope_threshold_m2": scope_threshold},
                inputs_used=["tertiaire_area_m2"],
                missing_inputs=[],
                explanation=f"Site non assujetti (surface {int(tertiaire_area)}m2 < {scope_threshold}m2).",
            )
        )
        return findings

    # Site is in scope - check deadlines
    deadlines = config.get("deadlines", {})
    attestation_deadline = date.fromisoformat(deadlines.get("attestation_display", "2026-07-01"))
    declaration_deadline = date.fromisoformat(deadlines.get("declaration_2025", "2026-09-30"))

    # Penalties from config
    penalties = config.get("penalties", {})
    penalty_non_declaration = penalties.get("non_declaration", 7500)
    penalty_non_affichage = penalties.get("non_affichage", 1500)

    # Check OPERAT status
    operat_status = site.operat_status
    if operat_status is None or str(operat_status) == "OperatStatus.NOT_STARTED":
        findings.append(
            Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="OPERAT_NOT_STARTED",
                status="AT_RISK",
                severity="HIGH",
                confidence="HIGH",
                legal_deadline=declaration_deadline,
                trigger_condition="operat_status is NOT_STARTED or None",
                config_params_used=deadlines,
                inputs_used=["operat_status"],
                missing_inputs=[],
                explanation=f"Declaration OPERAT non demarree. Echeance: {declaration_deadline.isoformat()}.",
                estimated_penalty_eur=float(penalty_non_declaration),
                penalty_source="regs.yaml",
                penalty_basis=f"non_declaration: {penalty_non_declaration} EUR/site",
            )
        )

    # Check annual_kwh_total
    if site.annual_kwh_total is None:
        findings.append(
            Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="ENERGY_DATA_MISSING",
                status="AT_RISK",
                severity="MEDIUM",
                confidence="HIGH",
                legal_deadline=None,
                trigger_condition="annual_kwh_total is None",
                config_params_used={},
                inputs_used=[],
                missing_inputs=["annual_kwh_total"],
                explanation="Donnees de consommation annuelle manquantes pour trajectoire 2030.",
                estimated_penalty_eur=float(penalty_non_declaration),
                penalty_source="regs.yaml",
                penalty_basis=f"non_declaration: {penalty_non_declaration} EUR/site (risque indirect)",
            )
        )

    # Check multi-occupied
    if site.is_multi_occupied:
        findings.append(
            Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="MULTI_OCCUPIED_GOVERNANCE",
                status="AT_RISK",
                severity="MEDIUM",
                confidence="MEDIUM",
                legal_deadline=None,
                trigger_condition="is_multi_occupied is True",
                config_params_used={},
                inputs_used=["is_multi_occupied"],
                missing_inputs=[],
                explanation="Site multi-occupant: coordination requise entre occupants pour declaration.",
                estimated_penalty_eur=float(penalty_non_affichage),
                penalty_source="regs.yaml",
                penalty_basis=f"non_affichage: {penalty_non_affichage} EUR/site (risque coordination)",
            )
        )

    # Check trajectory (on_track / off_track for 2030)
    if db is not None:
        trajectory_finding = _evaluate_trajectory(db, site, config, declaration_deadline, penalty_non_declaration)
        if trajectory_finding is not None:
            findings.append(trajectory_finding)

    return findings


def _evaluate_trajectory(
    db: Session, site, config: dict, declaration_deadline: date, penalty_non_declaration: float
) -> Optional[Finding]:
    """Call dt_trajectory_service to compute on_track/off_track status for 2030."""
    try:
        from services.dt_trajectory_service import compute_site_trajectory

        result = compute_site_trajectory(db, site.id)

        avancement = result.avancement_2030
        reduction_pct = result.reduction_pct

        # Skip if trajectory cannot be evaluated (no baseline or no current data)
        if avancement is None:
            return Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="TRAJECTORY_NOT_EVALUABLE",
                status="UNKNOWN",
                severity="MEDIUM",
                confidence="LOW",
                legal_deadline=declaration_deadline,
                trigger_condition="trajectory compute returned avancement_2030=None",
                config_params_used={},
                inputs_used=["site_id"],
                missing_inputs=["conso_reference_kwh", "conso_actuelle_kwh"],
                explanation=f"Trajectoire 2030 non evaluable: {result.message or 'donnees insuffisantes'}.",
            )

        if avancement >= 100:
            # On track — informational finding
            return Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="TRAJECTORY_ON_TRACK",
                status="COMPLIANT",
                severity="LOW",
                confidence=result.confidence.upper(),
                legal_deadline=None,
                trigger_condition=f"avancement_2030={avancement}% >= 100%",
                config_params_used={},
                inputs_used=["conso_reference_kwh", "conso_actuelle_kwh"],
                missing_inputs=[],
                explanation=(
                    f"Trajectoire 2030 respectee: reduction {reduction_pct}% "
                    f"(avancement {avancement}% de l'objectif -40%)."
                ),
            )
        else:
            # Off track — site is behind the -40% target for 2030
            return Finding(
                regulation="TERTIAIRE_OPERAT",
                rule_id="TRAJECTORY_OFF_TRACK",
                status="AT_RISK",
                severity="HIGH",
                confidence=result.confidence.upper(),
                legal_deadline=declaration_deadline,
                trigger_condition=f"avancement_2030={avancement}% < 100%",
                config_params_used={},
                inputs_used=["conso_reference_kwh", "conso_actuelle_kwh"],
                missing_inputs=[],
                explanation=(
                    f"Trajectoire 2030 non respectee: reduction {reduction_pct}% "
                    f"(avancement {avancement}% de l'objectif -40%). "
                    f"Ecart a combler avant {declaration_deadline.isoformat()}."
                ),
                estimated_penalty_eur=float(penalty_non_declaration),
                penalty_source="regs.yaml",
                penalty_basis=f"non_declaration: {penalty_non_declaration} EUR/site (risque trajectoire)",
            )

    except Exception as exc:
        _logger.warning("trajectory evaluation failed for site %d: %s", site.id, exc, exc_info=True)
        return None
