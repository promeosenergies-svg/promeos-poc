"""
PROMEOS RegOps - Regle Tertiaire/OPERAT
"""

from datetime import date, datetime
from ..schemas import Finding


def evaluate(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
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
            )
        )

    return findings
