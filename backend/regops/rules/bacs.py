"""
PROMEOS RegOps - Regle BACS (GTB/GTC)
"""
from datetime import date
from ..schemas import Finding


def evaluate(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
    findings = []

    # Get max CVC power from batiments
    cvc_powers = [b.cvc_power_kw for b in batiments if b.cvc_power_kw]
    if not cvc_powers:
        findings.append(Finding(
            regulation="BACS",
            rule_id="CVC_POWER_UNKNOWN",
            status="UNKNOWN",
            severity="HIGH",
            confidence="HIGH",
            legal_deadline=None,
            trigger_condition="No cvc_power_kw data in batiments",
            config_params_used={},
            inputs_used=[],
            missing_inputs=["cvc_power_kw"],
            explanation="Puissance CVC inconnue - impossible de determiner l'assujettissement BACS."
        ))
        return findings

    max_cvc_power = max(cvc_powers)
    thresholds = config.get("thresholds", {})
    high_threshold = thresholds.get("high_kw", 290)
    low_threshold = thresholds.get("low_kw", 70)

    if max_cvc_power <= low_threshold:
        findings.append(Finding(
            regulation="BACS",
            rule_id="OUT_OF_SCOPE",
            status="OUT_OF_SCOPE",
            severity="LOW",
            confidence="HIGH",
            legal_deadline=None,
            trigger_condition=f"cvc_power {max_cvc_power}kW <= {low_threshold}kW",
            config_params_used=thresholds,
            inputs_used=["cvc_power_kw"],
            missing_inputs=[],
            explanation=f"Puissance CVC {int(max_cvc_power)}kW: site non assujetti BACS."
        ))
        return findings

    # Determine deadline
    deadlines = config.get("deadlines", {})
    if max_cvc_power > high_threshold:
        deadline = date.fromisoformat(deadlines.get("above_290", "2025-01-01"))
        severity = "CRITICAL"
    else:
        deadline = date.fromisoformat(deadlines.get("above_70", "2030-01-01"))
        severity = "MEDIUM"

    # Check for BACS attestation
    bacs_attestations = [e for e in evidences if e.type and "ATTESTATION_BACS" in str(e.type)]
    has_valid_attestation = any(e.statut and "VALIDE" in str(e.statut) for e in bacs_attestations)

    if not has_valid_attestation:
        today = date.today()
        if today > deadline:
            status = "NON_COMPLIANT"
        else:
            status = "AT_RISK"

        findings.append(Finding(
            regulation="BACS",
            rule_id="BACS_NOT_INSTALLED",
            status=status,
            severity=severity,
            confidence="HIGH",
            legal_deadline=deadline,
            trigger_condition=f"cvc_power {max_cvc_power}kW, no valid BACS attestation",
            config_params_used={"threshold": high_threshold if max_cvc_power > high_threshold else low_threshold},
            inputs_used=["cvc_power_kw", "attestation_bacs"],
            missing_inputs=[],
            explanation=f"GTB/GTC obligatoire pour {int(max_cvc_power)}kW. Echeance: {deadline.isoformat()}."
        ))

    return findings
