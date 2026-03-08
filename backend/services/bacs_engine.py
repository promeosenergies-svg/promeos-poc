"""
PROMEOS - BACS Engine v2 (Decret n°2020-887)
Moteur complet: Putile, calendrier reglementaire, TRI exemption, inspections.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import yaml
from sqlalchemy.orm import Session

from models import (
    Site,
    Batiment,
    Evidence,
    TypeEvidence,
    StatutEvidence,
    BacsAsset,
    BacsCvcSystem,
    BacsAssessment,
    BacsInspection,
    CvcSystemType,
    CvcArchitecture,
    BacsTriggerReason,
    InspectionStatus,
)
from regops.schemas import Finding

ENGINE_VERSION = "bacs_v2.0"

# ── Load reference config from YAML (Decret n°2020-887) ──
_BACS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "regulations", "bacs", "v2.yaml")
_BACS_CONFIG = None


def _load_bacs_config() -> dict:
    global _BACS_CONFIG
    if _BACS_CONFIG is None:
        with open(_BACS_CONFIG_PATH, "r", encoding="utf-8") as f:
            _BACS_CONFIG = yaml.safe_load(f)
    return _BACS_CONFIG


def _get_deadlines() -> dict:
    cfg = _load_bacs_config()
    return {
        290: date.fromisoformat(cfg["deadlines"]["tier1"]),
        70: date.fromisoformat(cfg["deadlines"]["tier2"]),
    }


def _get_renewal_cutoff() -> date:
    cfg = _load_bacs_config()
    return date.fromisoformat(cfg["renewal_cutoff"])


# Legacy constants (kept for backward-compat in tests)
DEADLINE_290 = date(2025, 1, 1)
DEADLINE_70 = date(2030, 1, 1)
RENEWAL_CUTOFF = date(2023, 4, 9)


# ────────────────────────────────────────────
# Putile calculation
# ────────────────────────────────────────────


def compute_putile(systems: list[BacsCvcSystem]) -> dict:
    """
    Compute Puissance Utile (Putile) from CVC systems inventory.

    Rules:
    - Per channel (heating / cooling):
      - CASCADE or NETWORK architecture → sum of all unit kW
      - INDEPENDENT architecture → max of unit kW
    - Final Putile = max(putile_heating, putile_cooling)
    - Ventilation systems are ignored for threshold computation.

    Returns dict with putile_heating_kw, putile_cooling_kw, putile_kw, method, trace.
    """
    per_channel = {"heating": [], "cooling": []}
    trace_steps = []

    for sys in systems:
        if sys.system_type == CvcSystemType.VENTILATION:
            trace_steps.append(f"Skip ventilation system id={sys.id}")
            continue

        channel = sys.system_type.value  # "heating" or "cooling"
        units = _parse_units(sys.units_json)
        kw_values = [u.get("kw", 0) for u in units if u.get("kw", 0) > 0]

        if not kw_values:
            trace_steps.append(f"System id={sys.id} ({channel}/{sys.architecture.value}): no valid units")
            continue

        if sys.architecture in (CvcArchitecture.CASCADE, CvcArchitecture.NETWORK):
            channel_kw = sum(kw_values)
            method = "sum"
        else:  # INDEPENDENT
            channel_kw = max(kw_values)
            method = "max"

        trace_steps.append(
            f"System id={sys.id} ({channel}/{sys.architecture.value}): {method}({kw_values}) = {channel_kw} kW"
        )
        per_channel.setdefault(channel, []).append(channel_kw)

    putile_heating = sum(per_channel.get("heating", []))
    putile_cooling = sum(per_channel.get("cooling", []))
    putile_kw = max(putile_heating, putile_cooling) if (putile_heating or putile_cooling) else 0.0

    trace_steps.append(f"Putile heating={putile_heating} kW, cooling={putile_cooling} kW")
    trace_steps.append(f"Putile final = max(heating, cooling) = {putile_kw} kW")

    return {
        "putile_heating_kw": putile_heating,
        "putile_cooling_kw": putile_cooling,
        "putile_kw": putile_kw,
        "method": "max_channel",
        "trace": trace_steps,
    }


def _parse_units(units_json: Optional[str]) -> list[dict]:
    """Parse units JSON safely."""
    if not units_json:
        return []
    try:
        data = json.loads(units_json)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


# ────────────────────────────────────────────
# Obligation determination
# ────────────────────────────────────────────


def determine_obligation(
    putile_kw: float,
    pc_date: Optional[date],
    renewal_events: list[dict],
    config: dict,
) -> dict:
    """
    Determine BACS obligation based on Putile, construction date, renewal events.

    Rules:
    - Putile > 290 kW (existing) → obligated, deadline 2025-01-01
    - Putile > 70 kW (existing) → obligated, deadline 2030-01-01
    - Putile <= 70 kW → not obligated (OUT_OF_SCOPE)
    - New construction post 09/04/2023 → obligated immediately
    - CVC renewal post 09/04/2023 → triggers obligation

    Returns dict with is_obligated, threshold, deadline, trigger_reason.
    """
    high_kw = config.get("high_kw", 290)
    low_kw = config.get("low_kw", 70)

    deadlines = _get_deadlines()
    renewal_cutoff = _get_renewal_cutoff()

    # Check new construction post 2023-04-09
    if pc_date and pc_date >= renewal_cutoff:
        return {
            "is_obligated": True,
            "threshold": 0,
            "deadline": pc_date,
            "trigger_reason": BacsTriggerReason.NEW_CONSTRUCTION,
        }

    # Check CVC renewal post 2023-04-09
    for evt in renewal_events:
        evt_date_str = evt.get("date", "")
        try:
            evt_date = date.fromisoformat(evt_date_str)
        except (ValueError, TypeError):
            continue
        if evt_date >= renewal_cutoff:
            return {
                "is_obligated": True,
                "threshold": low_kw,
                "deadline": evt_date,
                "trigger_reason": BacsTriggerReason.RENEWAL,
            }

    # Threshold-based
    if putile_kw > high_kw:
        return {
            "is_obligated": True,
            "threshold": high_kw,
            "deadline": deadlines.get(290, DEADLINE_290),
            "trigger_reason": BacsTriggerReason.THRESHOLD_290,
        }
    elif putile_kw > low_kw:
        return {
            "is_obligated": True,
            "threshold": low_kw,
            "deadline": deadlines.get(70, DEADLINE_70),
            "trigger_reason": BacsTriggerReason.THRESHOLD_70,
        }
    else:
        return {
            "is_obligated": False,
            "threshold": low_kw,
            "deadline": None,
            "trigger_reason": None,
        }


# ────────────────────────────────────────────
# TRI exemption
# ────────────────────────────────────────────


def compute_tri(context: dict) -> dict:
    """
    Compute TRI (Temps de Retour sur Investissement) for BACS exemption.

    Inputs (via context dict):
    - cout_bacs_eur: cost of BACS installation
    - aides_pct: subsidies percentage (0-100)
    - conso_kwh: annual consumption kWh
    - gain_pct: expected gain percentage (0-100)
    - prix_kwh: energy price EUR/kWh

    TRI > 10 years → exemption possible.
    Returns dict with tri_years, exemption_possible, inputs, trace.
    """
    cout_bacs = context.get("cout_bacs_eur")
    aides_pct = context.get("aides_pct", 0)
    conso_kwh = context.get("conso_kwh")
    gain_pct = context.get("gain_pct")
    prix_kwh = context.get("prix_kwh")

    # Check required inputs
    if cout_bacs is None or conso_kwh is None or gain_pct is None or prix_kwh is None:
        return {
            "tri_years": None,
            "exemption_possible": None,
            "inputs": context,
            "trace": ["Missing required TRI inputs"],
        }

    if prix_kwh <= 0 or gain_pct <= 0 or conso_kwh <= 0:
        return {
            "tri_years": None,
            "exemption_possible": None,
            "inputs": context,
            "trace": ["Invalid TRI inputs (zero or negative)"],
        }

    cout_net = cout_bacs * (1.0 - aides_pct / 100.0)
    economies_annuelles = conso_kwh * (gain_pct / 100.0) * prix_kwh
    tri_years = round(cout_net / economies_annuelles, 2) if economies_annuelles > 0 else None

    exemption_possible = tri_years is not None and tri_years > 10

    trace = [
        f"cout_net = {cout_bacs} * (1 - {aides_pct}/100) = {cout_net:.2f} EUR",
        f"economies = {conso_kwh} * {gain_pct}/100 * {prix_kwh} = {economies_annuelles:.2f} EUR/an",
        f"TRI = {cout_net:.2f} / {economies_annuelles:.2f} = {tri_years} ans",
        f"Exemption possible = {exemption_possible} (seuil > 10 ans)",
    ]

    return {
        "tri_years": tri_years,
        "exemption_possible": exemption_possible,
        "inputs": context,
        "trace": trace,
    }


# ────────────────────────────────────────────
# Inspection schedule
# ────────────────────────────────────────────

INSPECTION_PERIOD_YEARS = 5


def compute_inspection_schedule(
    deadline_date: Optional[date],
    inspections: list[BacsInspection],
) -> dict:
    """
    Compute next inspection due date and overdue status.

    Rules:
    - Max periodicity: 5 years
    - First inspection due: deadline_date (obligation start)
    - Subsequent: last inspection_date + 5 years
    """
    today = date.today()

    if not deadline_date:
        return {
            "next_due": None,
            "is_overdue": False,
            "history": [],
        }

    completed = sorted(
        [i for i in inspections if i.status == InspectionStatus.COMPLETED and i.inspection_date],
        key=lambda i: i.inspection_date,
    )
    history = [
        {"date": i.inspection_date.isoformat(), "report": i.report_ref, "status": i.status.value} for i in completed
    ]

    if completed:
        last = completed[-1]
        next_due = last.inspection_date + timedelta(days=INSPECTION_PERIOD_YEARS * 365)
    else:
        next_due = deadline_date

    is_overdue = today > next_due

    return {
        "next_due": next_due,
        "is_overdue": is_overdue,
        "history": history,
    }


# ────────────────────────────────────────────
# Main orchestrator
# ────────────────────────────────────────────


def evaluate_bacs(db: Session, site_id: int, tri_context: Optional[dict] = None) -> Optional[BacsAssessment]:
    """
    Full BACS evaluation for a site.

    1. Load BacsAsset (or return None if not configured)
    2. Load CVC systems
    3. Compute Putile
    4. Determine obligation
    5. Compute TRI if context provided
    6. Compute inspection schedule
    7. Generate findings with full audit trail
    8. Persist BacsAssessment (upsert: delete old + insert new)
    9. Return assessment
    """
    asset = db.query(BacsAsset).filter(BacsAsset.site_id == site_id).first()
    if not asset:
        return None

    systems = db.query(BacsCvcSystem).filter(BacsCvcSystem.asset_id == asset.id).all()
    inspections = db.query(BacsInspection).filter(BacsInspection.asset_id == asset.id).all()

    # 1. Putile
    putile_result = compute_putile(systems)
    putile_kw = putile_result["putile_kw"]

    # Update putile on each system
    for sys in systems:
        units = _parse_units(sys.units_json)
        kw_values = [u.get("kw", 0) for u in units if u.get("kw", 0) > 0]
        if sys.system_type == CvcSystemType.VENTILATION or not kw_values:
            sys.putile_kw_computed = 0
        elif sys.architecture in (CvcArchitecture.CASCADE, CvcArchitecture.NETWORK):
            sys.putile_kw_computed = sum(kw_values)
        else:
            sys.putile_kw_computed = max(kw_values)
        sys.putile_calc_trace_json = json.dumps({"method": sys.architecture.value, "kw_values": kw_values})
        sys.engine_version = ENGINE_VERSION

    # 2. Obligation
    renewal_events = _parse_json(asset.renewal_events_json) or []
    config = {"high_kw": 290, "low_kw": 70}
    obligation = determine_obligation(putile_kw, asset.pc_date, renewal_events, config)

    # 3. TRI
    tri_result = compute_tri(tri_context or {})

    # 4. Inspection schedule
    inspection_sched = compute_inspection_schedule(obligation["deadline"], inspections)

    # 5. Generate findings
    findings = _generate_findings(asset, putile_result, obligation, tri_result, inspection_sched)

    # 6. Compute scores
    compliance_score = _compute_compliance_score(obligation, tri_result, inspection_sched)
    confidence = _compute_confidence(systems, asset, tri_result)

    # 7. Persist assessment (upsert)
    db.query(BacsAssessment).filter(BacsAssessment.asset_id == asset.id).delete()

    assessment = BacsAssessment(
        asset_id=asset.id,
        assessed_at=datetime.now(timezone.utc),
        threshold_applied=obligation["threshold"],
        is_obligated=obligation["is_obligated"],
        deadline_date=obligation["deadline"],
        trigger_reason=obligation.get("trigger_reason"),
        tri_exemption_possible=tri_result.get("exemption_possible"),
        tri_years=tri_result.get("tri_years"),
        confidence_score=confidence,
        compliance_score=compliance_score,
        findings_json=json.dumps([_finding_to_dict(f) for f in findings]),
        rule_id="BACS_V2_FULL",
        inputs_json=json.dumps(
            {
                "putile": putile_result,
                "obligation": {
                    k: str(v) if isinstance(v, (date, BacsTriggerReason)) else v for k, v in obligation.items()
                },
                "tri": {k: str(v) if isinstance(v, date) else v for k, v in tri_result.items() if k != "trace"},
            }
        ),
        params_json=json.dumps(config),
        evidence_json=json.dumps(
            {
                "putile_trace": putile_result["trace"],
                "tri_trace": tri_result.get("trace", []),
                "inspection_history": inspection_sched.get("history", []),
            }
        ),
        engine_version=ENGINE_VERSION,
    )
    db.add(assessment)
    db.flush()

    return assessment


def _generate_findings(asset, putile_result, obligation, tri_result, inspection_sched) -> list[Finding]:
    """Generate Finding list from engine results."""
    findings = []
    putile_kw = putile_result["putile_kw"]

    if not obligation["is_obligated"]:
        findings.append(
            Finding(
                regulation="BACS",
                rule_id="BACS_V2_OUT_OF_SCOPE",
                status="OUT_OF_SCOPE",
                severity="LOW",
                confidence="HIGH",
                legal_deadline=None,
                trigger_condition=f"Putile {putile_kw} kW <= seuil {obligation['threshold']} kW",
                config_params_used={"threshold": obligation["threshold"]},
                inputs_used=["cvc_inventory", "putile_kw"],
                missing_inputs=[],
                explanation=f"Puissance utile {putile_kw:.0f} kW: site non assujetti au decret BACS.",
            )
        )
        return findings

    # Obligated
    trigger = obligation.get("trigger_reason")
    trigger_label = trigger.value if trigger else "unknown"
    deadline = obligation["deadline"]
    today = date.today()

    if today > deadline:
        status = "NON_COMPLIANT"
        severity = "CRITICAL"
    else:
        days_left = (deadline - today).days
        if days_left <= 180:
            status = "AT_RISK"
            severity = "HIGH"
        else:
            status = "AT_RISK"
            severity = "MEDIUM"

    bacs_penalty = 7500.0  # regs.yaml: bacs.penalties.non_compliance

    findings.append(
        Finding(
            regulation="BACS",
            rule_id="BACS_V2_OBLIGATION",
            status=status,
            severity=severity,
            confidence="HIGH",
            legal_deadline=deadline,
            trigger_condition=f"Putile {putile_kw:.0f} kW, trigger={trigger_label}",
            config_params_used={"threshold": obligation["threshold"]},
            inputs_used=["cvc_inventory", "putile_kw", "pc_date", "renewal_events"],
            missing_inputs=[],
            explanation=(
                f"GTB/GTC obligatoire: Putile {putile_kw:.0f} kW "
                f"(seuil {obligation['threshold']} kW, declencheur: {trigger_label}). "
                f"Echeance: {deadline.isoformat()}."
            ),
            estimated_penalty_eur=bacs_penalty,
            penalty_source="regs.yaml",
            penalty_basis=f"non_compliance: {int(bacs_penalty)} EUR/site",
        )
    )

    # TRI exemption finding
    if tri_result.get("exemption_possible") is True:
        findings.append(
            Finding(
                regulation="BACS",
                rule_id="BACS_V2_TRI_EXEMPTION",
                status="EXEMPTION_POSSIBLE",
                severity="LOW",
                confidence="MEDIUM",
                legal_deadline=deadline,
                trigger_condition=f"TRI = {tri_result['tri_years']} ans > 10 ans",
                config_params_used={"tri_threshold_years": 10},
                inputs_used=["cout_bacs_eur", "aides_pct", "conso_kwh", "gain_pct", "prix_kwh"],
                missing_inputs=[],
                explanation=(
                    f"TRI de {tri_result['tri_years']} ans > 10 ans: exemption possible (article R. 175-7 du CCH)."
                ),
            )
        )
    elif tri_result.get("tri_years") is not None:
        findings.append(
            Finding(
                regulation="BACS",
                rule_id="BACS_V2_TRI_NO_EXEMPTION",
                status=status,
                severity=severity,
                confidence="MEDIUM",
                legal_deadline=deadline,
                trigger_condition=f"TRI = {tri_result['tri_years']} ans <= 10 ans",
                config_params_used={"tri_threshold_years": 10},
                inputs_used=["cout_bacs_eur", "aides_pct", "conso_kwh", "gain_pct", "prix_kwh"],
                missing_inputs=[],
                explanation=(f"TRI de {tri_result['tri_years']} ans <= 10 ans: pas d'exemption, GTB/GTC requise."),
                estimated_penalty_eur=bacs_penalty,
                penalty_source="regs.yaml",
                penalty_basis=f"non_compliance: {int(bacs_penalty)} EUR/site",
            )
        )

    # Inspection finding
    if inspection_sched.get("is_overdue"):
        findings.append(
            Finding(
                regulation="BACS",
                rule_id="BACS_V2_INSPECTION_OVERDUE",
                status="NON_COMPLIANT",
                severity="HIGH",
                confidence="HIGH",
                legal_deadline=inspection_sched["next_due"],
                trigger_condition=f"Inspection overdue since {inspection_sched['next_due'].isoformat()}",
                config_params_used={"period_years": INSPECTION_PERIOD_YEARS},
                inputs_used=["inspection_history"],
                missing_inputs=[],
                explanation=(
                    f"Inspection quinquennale BACS en retard. Echeance: {inspection_sched['next_due'].isoformat()}."
                ),
                estimated_penalty_eur=bacs_penalty,
                penalty_source="regs.yaml",
                penalty_basis=f"non_compliance: {int(bacs_penalty)} EUR/site (inspection)",
            )
        )

    return findings


def _compute_compliance_score(obligation, tri_result, inspection_sched) -> float:
    """Compute a 0-100 BACS sub-score (composante du score unifie A.2).
    Le score GLOBAL du site est calcule par compliance_score_service.py.
    Ne PAS confondre avec le compliance_score_composite du site."""
    if not obligation["is_obligated"]:
        return 100.0

    score = 0.0  # Start at 0 for obligated sites

    # TRI exemption gives partial credit
    if tri_result.get("exemption_possible"):
        score += 60.0

    # No overdue inspection
    if not inspection_sched.get("is_overdue"):
        score += 20.0

    # Deadline in the future
    deadline = obligation.get("deadline")
    if deadline and date.today() <= deadline:
        score += 20.0

    return min(100.0, score)


def _compute_confidence(systems, asset, tri_result) -> float:
    """Compute confidence score (0-1)."""
    factors = []

    # CVC inventory present
    factors.append(1.0 if systems else 0.3)

    # PC date present
    factors.append(1.0 if asset.pc_date else 0.7)

    # TRI data available
    if tri_result.get("tri_years") is not None:
        factors.append(1.0)
    else:
        factors.append(0.5)

    return round(sum(factors) / len(factors), 2) if factors else 0.5


def _finding_to_dict(f: Finding) -> dict:
    """Serialize Finding to JSON-safe dict."""
    d = {
        "regulation": f.regulation,
        "rule_id": f.rule_id,
        "status": f.status,
        "severity": f.severity,
        "confidence": f.confidence,
        "legal_deadline": f.legal_deadline.isoformat() if f.legal_deadline else None,
        "trigger_condition": f.trigger_condition,
        "config_params_used": f.config_params_used,
        "inputs_used": f.inputs_used,
        "missing_inputs": f.missing_inputs,
        "explanation": f.explanation,
        "estimated_penalty_eur": getattr(f, "estimated_penalty_eur", None),
        "penalty_source": getattr(f, "penalty_source", None),
        "penalty_basis": getattr(f, "penalty_basis", None),
    }
    return d


def _parse_json(text: Optional[str]):
    """Parse JSON text safely."""
    if not text:
        return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


# ────────────────────────────────────────────
# Legacy wrapper for regops/rules/bacs.py
# ────────────────────────────────────────────


def evaluate_legacy(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
    """
    Legacy wrapper: called by regops/rules/bacs.py evaluate().
    Uses simple max(cvc_power_kw) approach when BacsAsset not configured.
    Falls back to the v1 logic.
    """
    # Build virtual systems from batiments for putile calc
    from models import CvcArchitecture, CvcSystemType

    virtual_systems = []
    for b in batiments:
        if b.cvc_power_kw and b.cvc_power_kw > 0:
            sys = BacsCvcSystem(
                id=b.id,
                system_type=CvcSystemType.HEATING,
                architecture=CvcArchitecture.INDEPENDENT,
                units_json=json.dumps([{"label": b.nom, "kw": b.cvc_power_kw}]),
            )
            virtual_systems.append(sys)

    putile_result = compute_putile(virtual_systems)
    putile_kw = putile_result["putile_kw"]

    thresholds = config.get("thresholds", {})
    obligation = determine_obligation(
        putile_kw,
        pc_date=None,
        renewal_events=[],
        config={"high_kw": thresholds.get("high_kw", 290), "low_kw": thresholds.get("low_kw", 70)},
    )

    if not obligation["is_obligated"]:
        if putile_kw == 0:
            return [
                Finding(
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
                    explanation="Puissance CVC inconnue - impossible de determiner l'assujettissement BACS.",
                )
            ]
        return [
            Finding(
                regulation="BACS",
                rule_id="OUT_OF_SCOPE",
                status="OUT_OF_SCOPE",
                severity="LOW",
                confidence="HIGH",
                legal_deadline=None,
                trigger_condition=f"cvc_power {putile_kw}kW <= {obligation['threshold']}kW",
                config_params_used=thresholds,
                inputs_used=["cvc_power_kw"],
                missing_inputs=[],
                explanation=f"Puissance CVC {int(putile_kw)}kW: site non assujetti BACS.",
            )
        ]

    # Obligated — check attestation
    deadline = obligation["deadline"]
    severity = "CRITICAL" if putile_kw > thresholds.get("high_kw", 290) else "MEDIUM"

    bacs_attestations = [e for e in evidences if e.type and "ATTESTATION_BACS" in str(e.type)]
    has_valid = any(e.statut and "VALIDE" in str(e.statut) for e in bacs_attestations)

    if has_valid:
        return []

    today = date.today()
    status = "NON_COMPLIANT" if today > deadline else "AT_RISK"

    return [
        Finding(
            regulation="BACS",
            rule_id="BACS_NOT_INSTALLED",
            status=status,
            severity=severity,
            confidence="HIGH",
            legal_deadline=deadline,
            trigger_condition=f"cvc_power {putile_kw}kW, no valid BACS attestation",
            config_params_used={"threshold": obligation["threshold"]},
            inputs_used=["cvc_power_kw", "attestation_bacs"],
            missing_inputs=[],
            explanation=f"GTB/GTC obligatoire pour {int(putile_kw)}kW. Echeance: {deadline.isoformat()}.",
        )
    ]
