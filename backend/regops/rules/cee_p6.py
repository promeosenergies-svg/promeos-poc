"""
PROMEOS RegOps - Regle CEE P6 (hints mapping)
"""

from ..schemas import Finding


def evaluate(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
    """
    CEE P6: Pas de reglementation stricte, juste des hints/opportunites.
    Retourne une liste vide ou des suggestions basees sur le profil du site.
    """
    findings = []

    # Example: si surface > 5000m2 et pas de GTB => opportunity CEE BAT-TH-158
    cvc_powers = [b.cvc_power_kw for b in batiments if b.cvc_power_kw]
    if cvc_powers and max(cvc_powers) > 100 and site.surface_m2 and site.surface_m2 > 5000:
        bacs_attestations = [e for e in evidences if e.type and "ATTESTATION_BACS" in str(e.type)]
        if not bacs_attestations:
            findings.append(
                Finding(
                    regulation="CEE_P6",
                    rule_id="CEE_OPPORTUNITY_GTB",
                    status="COMPLIANT",  # Not a compliance issue
                    severity="LOW",
                    confidence="MEDIUM",
                    legal_deadline=None,
                    trigger_condition="Large site without GTB",
                    config_params_used={},
                    inputs_used=["surface_m2", "cvc_power_kw"],
                    missing_inputs=[],
                    explanation="Opportunite CEE BAT-TH-158 (systeme GTB): economies estimees 35 kWh/m2/an.",
                )
            )

    return findings
