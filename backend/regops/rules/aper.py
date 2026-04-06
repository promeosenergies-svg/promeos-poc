"""
PROMEOS RegOps - Regle APER (photovoltaique parking + toiture)

Logique de couverture (PRO-18+) :
- Si au moins une Evidence VALIDE du bon type existe, on calcule le taux de
  couverture agrege (champ coverage_pct sur Evidence, 0-100).
- coverage_pct=None sur une Evidence VALIDE → traite comme 100% (retro-compatible).
- Couverture >= 50% → COMPLIANT (installation couvre la majorite de la surface).
- Couverture > 0% et < 50% → PARTIAL (installation partielle, risque reduit).
- Couverture = 0% ou aucune evidence → AT_RISK (comportement historique).
"""

from datetime import date
from ..schemas import Finding

# Evidence types that prove APER parking compliance (ombriere PV ou equivalent)
_PARKING_EVIDENCE_TYPES = {"ATTESTATION_OMBRIERE_PV"}

# Evidence types that prove APER roof compliance (PV ou vegetalisation)
_ROOF_EVIDENCE_TYPES = {"ATTESTATION_TOITURE_PV", "ATTESTATION_TOITURE_VEGETALISEE"}

# Seuil de couverture au-dela duquel le site est considere conforme (50%)
_COVERAGE_COMPLIANT_PCT = 50.0


def _compute_coverage(evidences: list, accepted_types: set) -> float | None:
    """Calcule le taux de couverture agrege a partir des preuves VALIDE.

    Retourne:
      - None  si aucune evidence VALIDE du bon type n'existe (= pas de preuve).
      - float (0-100) : meilleur taux de couverture parmi les evidences VALIDE.
        Si coverage_pct n'est pas renseigne sur l'evidence → traite comme 100%.
    """
    best_pct: float | None = None
    for e in evidences:
        if not e.type or not e.statut:
            continue
        if any(t in str(e.type) for t in accepted_types) and "VALIDE" in str(e.statut):
            # Retro-compatibilite : si coverage_pct absent ou None → 100%
            pct = getattr(e, "coverage_pct", None)
            if pct is None:
                pct = 100.0
            if best_pct is None or pct > best_pct:
                best_pct = pct
    return best_pct


def _coverage_status(coverage_pct: float | None) -> str:
    """Determine le statut APER en fonction du taux de couverture.

    >= 50% → COMPLIANT
    > 0%   → PARTIAL
    None/0 → AT_RISK
    """
    if coverage_pct is None:
        return "AT_RISK"
    if coverage_pct >= _COVERAGE_COMPLIANT_PCT:
        return "COMPLIANT"
    if coverage_pct > 0:
        return "PARTIAL"
    return "AT_RISK"


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

            # Calcul du taux de couverture parking (ombriere PV)
            parking_coverage = _compute_coverage(evidences, _PARKING_EVIDENCE_TYPES)
            parking_status = _coverage_status(parking_coverage)

            # APER: estimation conservative (20 EUR/m2 non couvert, plafond 20k EUR)
            if parking_area >= large:
                if parking_status == "AT_RISK":
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
                            trigger_condition=f"outdoor parking {parking_area}m2 >= {large}m2, no valid ombriere PV attestation",
                            config_params_used={"large_threshold_m2": large},
                            inputs_used=["parking_area_m2", "parking_type", "attestation_ombriere_pv"],
                            missing_inputs=[],
                            explanation=f"Parking exterieur {int(parking_area)}m2: ombrières PV obligatoires. Echeance: {deadline.isoformat()}.",
                            estimated_penalty_eur=est_penalty,
                            penalty_source="estimation",
                            penalty_basis=f"estimation: ~20 EUR/m2 non couvert, plafond 20k EUR",
                        )
                    )
                elif parking_status == "PARTIAL":
                    # Installation partielle : risque reduit mais non nul
                    deadline = date.fromisoformat(deadlines.get("parking_large", "2026-07-01"))
                    uncovered_pct = (100.0 - (parking_coverage or 0)) / 100.0
                    est_penalty = min(parking_area * 20.0 * uncovered_pct, 20000.0)
                    findings.append(
                        Finding(
                            regulation="APER",
                            rule_id="PARKING_LARGE_APER",
                            status="PARTIAL",
                            severity="MEDIUM",
                            confidence="MEDIUM",
                            legal_deadline=deadline,
                            trigger_condition=f"outdoor parking {parking_area}m2 >= {large}m2, ombriere PV partielle ({parking_coverage:.0f}%)",
                            config_params_used={"large_threshold_m2": large, "coverage_pct": parking_coverage},
                            inputs_used=["parking_area_m2", "parking_type", "attestation_ombriere_pv", "coverage_pct"],
                            missing_inputs=[],
                            explanation=f"Parking exterieur {int(parking_area)}m2: ombrière PV partielle ({parking_coverage:.0f}% couvert, seuil 50%). Echeance: {deadline.isoformat()}.",
                            estimated_penalty_eur=est_penalty,
                            penalty_source="estimation",
                            penalty_basis=f"estimation: ~20 EUR/m2 non couvert ({uncovered_pct:.0%}), plafond 20k EUR",
                        )
                    )
                # else: COMPLIANT → pas de finding AT_RISK (comportement existant preservé)
            elif parking_area >= medium:
                if parking_status == "AT_RISK":
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
                            trigger_condition=f"outdoor parking {parking_area}m2 >= {medium}m2, no valid ombriere PV attestation",
                            config_params_used={"medium_threshold_m2": medium},
                            inputs_used=["parking_area_m2", "parking_type", "attestation_ombriere_pv"],
                            missing_inputs=[],
                            explanation=f"Parking exterieur {int(parking_area)}m2: ombrières PV requises. Echeance: {deadline.isoformat()}.",
                            estimated_penalty_eur=est_penalty,
                            penalty_source="estimation",
                            penalty_basis=f"estimation: ~20 EUR/m2 non couvert, plafond 20k EUR",
                        )
                    )
                elif parking_status == "PARTIAL":
                    deadline = date.fromisoformat(deadlines.get("parking_medium", "2028-07-01"))
                    uncovered_pct = (100.0 - (parking_coverage or 0)) / 100.0
                    est_penalty = min(parking_area * 20.0 * uncovered_pct, 20000.0)
                    findings.append(
                        Finding(
                            regulation="APER",
                            rule_id="PARKING_MEDIUM_APER",
                            status="PARTIAL",
                            severity="LOW",
                            confidence="MEDIUM",
                            legal_deadline=deadline,
                            trigger_condition=f"outdoor parking {parking_area}m2 >= {medium}m2, ombriere PV partielle ({parking_coverage:.0f}%)",
                            config_params_used={"medium_threshold_m2": medium, "coverage_pct": parking_coverage},
                            inputs_used=["parking_area_m2", "parking_type", "attestation_ombriere_pv", "coverage_pct"],
                            missing_inputs=[],
                            explanation=f"Parking exterieur {int(parking_area)}m2: ombrière PV partielle ({parking_coverage:.0f}% couvert, seuil 50%). Echeance: {deadline.isoformat()}.",
                            estimated_penalty_eur=est_penalty,
                            penalty_source="estimation",
                            penalty_basis=f"estimation: ~20 EUR/m2 non couvert ({uncovered_pct:.0%}), plafond 20k EUR",
                        )
                    )
                # else: COMPLIANT → pas de finding

    # Roof check
    roof_area = site.roof_area_m2
    if roof_area and roof_area >= config.get("roof_threshold_m2", 500):
        # Calcul du taux de couverture toiture (PV ou vegetalisation)
        roof_coverage = _compute_coverage(evidences, _ROOF_EVIDENCE_TYPES)
        roof_status = _coverage_status(roof_coverage)

        if roof_status == "AT_RISK":
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
                    trigger_condition=f"roof_area {roof_area}m2 >= 500m2, no valid PV/vegetalisation attestation",
                    config_params_used={"roof_threshold_m2": 500},
                    inputs_used=["roof_area_m2", "attestation_toiture_pv", "attestation_toiture_vegetalisee"],
                    missing_inputs=[],
                    explanation=f"Toiture {int(roof_area)}m2: PV ou vegetalisation requise. Echeance: {deadline.isoformat()}.",
                    estimated_penalty_eur=est_penalty,
                    penalty_source="estimation",
                    penalty_basis=f"estimation: ~15 EUR/m2 non couvert, plafond 15k EUR",
                )
            )
        elif roof_status == "PARTIAL":
            # Toiture partiellement couverte
            deadline = date.fromisoformat(config.get("deadlines", {}).get("roof", "2028-01-01"))
            uncovered_pct = (100.0 - (roof_coverage or 0)) / 100.0
            est_penalty = min(roof_area * 15.0 * uncovered_pct, 15000.0)
            findings.append(
                Finding(
                    regulation="APER",
                    rule_id="ROOF_APER",
                    status="PARTIAL",
                    severity="LOW",
                    confidence="MEDIUM",
                    legal_deadline=deadline,
                    trigger_condition=f"roof_area {roof_area}m2 >= 500m2, PV/vegetalisation partielle ({roof_coverage:.0f}%)",
                    config_params_used={"roof_threshold_m2": 500, "coverage_pct": roof_coverage},
                    inputs_used=[
                        "roof_area_m2",
                        "attestation_toiture_pv",
                        "attestation_toiture_vegetalisee",
                        "coverage_pct",
                    ],
                    missing_inputs=[],
                    explanation=f"Toiture {int(roof_area)}m2: PV/vegetalisation partielle ({roof_coverage:.0f}% couvert, seuil 50%). Echeance: {deadline.isoformat()}.",
                    estimated_penalty_eur=est_penalty,
                    penalty_source="estimation",
                    penalty_basis=f"estimation: ~15 EUR/m2 non couvert ({uncovered_pct:.0%}), plafond 15k EUR",
                )
            )
        # else: COMPLIANT → pas de finding

    return findings
