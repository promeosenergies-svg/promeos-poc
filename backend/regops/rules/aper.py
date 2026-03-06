"""
PROMEOS RegOps - Regle APER (photovoltaique parking + toiture)
"""

from datetime import date
from ..schemas import Finding


def evaluate(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
    findings = []

    # Parking check
    parking_area = site.parking_area_m2
    parking_type = site.parking_type

    if parking_area and parking_area > 0:
        # Check parking type
        if parking_type is None or str(parking_type) != "ParkingType.OUTDOOR":
            findings.append(
                Finding(
                    regulation="APER",
                    rule_id="PARKING_NOT_OUTDOOR",
                    status="OUT_OF_SCOPE",
                    severity="LOW",
                    confidence="HIGH",
                    legal_deadline=None,
                    trigger_condition=f"parking_type is {parking_type}",
                    config_params_used={},
                    inputs_used=["parking_type"],
                    missing_inputs=[],
                    explanation="Parking non exterieur: APER non applicable.",
                )
            )
        else:
            # Outdoor parking - check thresholds
            thresholds = config.get("parking_thresholds", {})
            large = thresholds.get("large_m2", 10000)
            medium = thresholds.get("medium_m2", 1500)
            deadlines = config.get("deadlines", {})

            # APER: estimation conservative (20 EUR/m2 non couvert, plafond 20k EUR)
            if parking_area >= large:
                deadline = date.fromisoformat(deadlines.get("parking_large", "2026-07-01"))
                est_penalty = min(parking_area * 20.0, 20000.0)
                findings.append(
                    Finding(
                        regulation="APER",
                        rule_id="PARKING_LARGE_APER",
                        status="AT_RISK",
                        severity="HIGH",
                        confidence="HIGH",
                        legal_deadline=deadline,
                        trigger_condition=f"outdoor parking {parking_area}m2 >= {large}m2",
                        config_params_used={"large_threshold_m2": large},
                        inputs_used=["parking_area_m2", "parking_type"],
                        missing_inputs=[],
                        explanation=f"Parking exterieur {int(parking_area)}m2: ombrières PV obligatoires. Echeance: {deadline.isoformat()}.",
                        estimated_penalty_eur=est_penalty,
                        penalty_source="estimation",
                        penalty_basis=f"estimation: ~20 EUR/m2 non couvert, plafond 20k EUR",
                    )
                )
            elif parking_area >= medium:
                deadline = date.fromisoformat(deadlines.get("parking_medium", "2028-07-01"))
                est_penalty = min(parking_area * 20.0, 20000.0)
                findings.append(
                    Finding(
                        regulation="APER",
                        rule_id="PARKING_MEDIUM_APER",
                        status="AT_RISK",
                        severity="MEDIUM",
                        confidence="HIGH",
                        legal_deadline=deadline,
                        trigger_condition=f"outdoor parking {parking_area}m2 >= {medium}m2",
                        config_params_used={"medium_threshold_m2": medium},
                        inputs_used=["parking_area_m2", "parking_type"],
                        missing_inputs=[],
                        explanation=f"Parking exterieur {int(parking_area)}m2: ombrières PV requises. Echeance: {deadline.isoformat()}.",
                        estimated_penalty_eur=est_penalty,
                        penalty_source="estimation",
                        penalty_basis=f"estimation: ~20 EUR/m2 non couvert, plafond 20k EUR",
                    )
                )

    # Roof check
    roof_area = site.roof_area_m2
    if roof_area and roof_area >= config.get("roof_threshold_m2", 500):
        deadline = date.fromisoformat(config.get("deadlines", {}).get("roof", "2028-01-01"))
        est_penalty = min(roof_area * 15.0, 15000.0)
        findings.append(
            Finding(
                regulation="APER",
                rule_id="ROOF_APER",
                status="AT_RISK",
                severity="MEDIUM",
                confidence="MEDIUM",
                legal_deadline=deadline,
                trigger_condition=f"roof_area {roof_area}m2 >= 500m2",
                config_params_used={"roof_threshold_m2": 500},
                inputs_used=["roof_area_m2"],
                missing_inputs=[],
                explanation=f"Toiture {int(roof_area)}m2: PV ou vegetalisation requise. Echeance: {deadline.isoformat()}.",
                estimated_penalty_eur=est_penalty,
                penalty_source="estimation",
                penalty_basis=f"estimation: ~15 EUR/m2 non couvert, plafond 15k EUR",
            )
        )

    return findings
