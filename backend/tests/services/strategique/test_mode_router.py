"""PROMEOS — Tests Vague B.3 : compute_strategic_mode cascade (5 modes).

Référence : `docs/adr/ADR-023-synthese-strategique-data-driven.md` §9.

Couverture cardinale :
  - Gate 1 prime sur tout (maturity < 60 % → DATA_INSUFFICIENT)
  - Gate 1 prime sur tout (unknown_ratio > 30 % → DATA_INSUFFICIENT)
  - Gate 2 — REGULATORY_DRIVEN si DT APPLICABLE + drift > 5
  - Gate 2 — REGULATORY_DRIVEN si BACS APPLICABLE + drift > 5
  - Gate 2 ne déclenche pas si drift = 0
  - Gate 3 — PROCUREMENT_DRIVEN si contrat < 90 j
  - Gate 3 — PROCUREMENT_DRIVEN si spot > 40 %
  - Gate 4 — OPPORTUNITY_DRIVEN si APER APPLICABLE
  - Gate 4 — OPPORTUNITY_DRIVEN si CEE > 50 k€
  - Default — PERFORMANCE_DRIVEN
  - Thresholds overrides custom
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from services.strategique.mode_router import compute_strategic_mode
from services.strategique.mode_thresholds import ModeThresholds, StrategicMode


# ── Helpers ────────────────────────────────────────────────────────────────


_DEFAULT_AUDIT = {
    "doctrine_version": "ADR-024-v1.0",
    "evaluated_at": datetime(2026, 5, 13, tzinfo=timezone.utc).isoformat(),
    "evaluator": "TestEvaluator",
    "evaluator_version": "TEST-v1.0",
    "data_source": "test.fixtures",
}


def _entry(rule: RuleCode, status: ApplicabilityStatus, scope_id: int = 1) -> RuleApplicability:
    reason_code_map = {
        ApplicabilityStatus.APPLICABLE: f"{rule.value}.APPLICABLE",
        ApplicabilityStatus.NOT_APPLICABLE: f"{rule.value}.NOT_APPLICABLE.SDP_LT_1000"
        if rule == RuleCode.DT
        else (
            f"{rule.value}.NOT_APPLICABLE.NO_SYSTEM_GT_THRESHOLD"
            if rule == RuleCode.BACS
            else (
                f"{rule.value}.NOT_APPLICABLE.PARKING_LT_1500"
                if rule == RuleCode.APER
                else (
                    f"{rule.value}.NOT_APPLICABLE.PME"
                    if rule == RuleCode.SME
                    else f"{rule.value}.NOT_APPLICABLE.EFFECTIF_LT_250"
                )
            )
        ),
        ApplicabilityStatus.UNKNOWN: "DT.UNKNOWN.USAGE_MIXTE",
        ApplicabilityStatus.DATA_MISSING: f"{rule.value}.DATA_MISSING.SURFACE"
        if rule == RuleCode.DT
        else (
            f"{rule.value}.DATA_MISSING.CVC_POWER"
            if rule == RuleCode.BACS
            else (
                f"{rule.value}.DATA_MISSING.PARKING_AREA"
                if rule == RuleCode.APER
                else f"{rule.value}.DATA_MISSING.EFFECTIF"
            )
        ),
    }
    missing = ["site.test"] if status == ApplicabilityStatus.DATA_MISSING else []
    return RuleApplicability(
        rule_code=rule,
        rule_version=f"{rule.value}-test-v2026-01-01",
        scope_level="site" if rule in (RuleCode.DT, RuleCode.BACS, RuleCode.APER) else "organisation",
        scope_id=scope_id,
        scope_label=f"Scope {scope_id}",
        status=status,
        reason_code=reason_code_map[status],
        reason_human=f"Test {rule.value} {status.value}",
        missing_inputs=missing,
        _audit=_DEFAULT_AUDIT,
    )


def _applicability_all_applicable() -> dict:
    """Tous les statuts APPLICABLE (un seul site)."""
    return {
        RuleCode.DT: [_entry(RuleCode.DT, ApplicabilityStatus.APPLICABLE)],
        RuleCode.BACS: [_entry(RuleCode.BACS, ApplicabilityStatus.APPLICABLE)],
        RuleCode.APER: [_entry(RuleCode.APER, ApplicabilityStatus.APPLICABLE)],
        RuleCode.SME: [_entry(RuleCode.SME, ApplicabilityStatus.APPLICABLE)],
        RuleCode.BEGES: [_entry(RuleCode.BEGES, ApplicabilityStatus.APPLICABLE)],
    }


def _applicability_all_not_applicable() -> dict:
    """Tous NOT_APPLICABLE."""
    return {
        RuleCode.DT: [_entry(RuleCode.DT, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.BACS: [_entry(RuleCode.BACS, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.APER: [_entry(RuleCode.APER, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.SME: [_entry(RuleCode.SME, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.BEGES: [_entry(RuleCode.BEGES, ApplicabilityStatus.NOT_APPLICABLE)],
    }


# ── Gate 1 — DATA_INSUFFICIENT ────────────────────────────────────────────


def test_gate1_maturity_below_threshold():
    """Maturité 0.55 → DATA_INSUFFICIENT."""
    mode = compute_strategic_mode(
        applicability=_applicability_all_applicable(),
        patrimoine_maturity=0.55,
        trajectory_drift_pct=20.0,  # même DT en dérive
    )
    assert mode == StrategicMode.DATA_INSUFFICIENT


def test_gate1_priority_over_regulatory():
    """Maturity faible prime sur Gate 2 (REGULATORY)."""
    mode = compute_strategic_mode(
        applicability=_applicability_all_applicable(),
        patrimoine_maturity=0.30,  # très faible
        trajectory_drift_pct=20.0,
        next_contract_end_days=10,
        unvalued_cee_k_eur=300,
    )
    assert mode == StrategicMode.DATA_INSUFFICIENT


def test_gate1_unknown_ratio_over_threshold():
    """unknown_ratio > 30 % → DATA_INSUFFICIENT (même si maturité ok)."""
    # 5 règles × 1 entrée. Si 2/5 = 40 % UNKNOWN, gate1 prime.
    app = {
        RuleCode.DT: [_entry(RuleCode.DT, ApplicabilityStatus.UNKNOWN)],
        RuleCode.BACS: [_entry(RuleCode.BACS, ApplicabilityStatus.DATA_MISSING)],
        RuleCode.APER: [_entry(RuleCode.APER, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.SME: [_entry(RuleCode.SME, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.BEGES: [_entry(RuleCode.BEGES, ApplicabilityStatus.NOT_APPLICABLE)],
    }
    mode = compute_strategic_mode(
        applicability=app,
        patrimoine_maturity=0.90,
        trajectory_drift_pct=0.0,
    )
    assert mode == StrategicMode.DATA_INSUFFICIENT


# ── Gate 2 — REGULATORY_DRIVEN ────────────────────────────────────────────


def test_gate2_dt_applicable_with_drift():
    """DT APPLICABLE + drift 8 → REGULATORY_DRIVEN."""
    mode = compute_strategic_mode(
        applicability=_applicability_all_applicable(),
        patrimoine_maturity=0.90,
        trajectory_drift_pct=8.0,
    )
    assert mode == StrategicMode.REGULATORY_DRIVEN


def test_gate2_bacs_applicable_with_drift():
    """BACS APPLICABLE (DT non) + drift → REGULATORY_DRIVEN."""
    app = _applicability_all_not_applicable()
    app[RuleCode.BACS] = [_entry(RuleCode.BACS, ApplicabilityStatus.APPLICABLE)]
    mode = compute_strategic_mode(
        applicability=app,
        patrimoine_maturity=0.90,
        trajectory_drift_pct=6.0,
    )
    assert mode == StrategicMode.REGULATORY_DRIVEN


def test_gate2_no_trigger_without_drift():
    """DT APPLICABLE mais drift = 0 → bascule sur gates suivants."""
    mode = compute_strategic_mode(
        applicability=_applicability_all_applicable(),
        patrimoine_maturity=0.90,
        trajectory_drift_pct=0.0,  # pas de dérive
    )
    assert mode != StrategicMode.REGULATORY_DRIVEN
    # APER applicable → OPPORTUNITY
    assert mode == StrategicMode.OPPORTUNITY_DRIVEN


def test_gate2_no_trigger_dt_not_applicable():
    """DT NOT_APPLICABLE même avec drift → pas REGULATORY (gate skip)."""
    app = _applicability_all_not_applicable()
    mode = compute_strategic_mode(
        applicability=app,
        patrimoine_maturity=0.90,
        trajectory_drift_pct=20.0,
    )
    assert mode == StrategicMode.PERFORMANCE_DRIVEN


# ── Gate 3 — PROCUREMENT_DRIVEN ──────────────────────────────────────────


def test_gate3_contract_end_soon():
    """next_contract_end_days = 60 → PROCUREMENT_DRIVEN."""
    app = _applicability_all_not_applicable()
    mode = compute_strategic_mode(
        applicability=app,
        patrimoine_maturity=0.90,
        trajectory_drift_pct=0.0,
        next_contract_end_days=60,
    )
    assert mode == StrategicMode.PROCUREMENT_DRIVEN


def test_gate3_high_spot_exposure():
    """spot_exposure_pct = 50 → PROCUREMENT_DRIVEN."""
    app = _applicability_all_not_applicable()
    mode = compute_strategic_mode(
        applicability=app,
        patrimoine_maturity=0.90,
        trajectory_drift_pct=0.0,
        spot_exposure_pct=50.0,
    )
    assert mode == StrategicMode.PROCUREMENT_DRIVEN


# ── Gate 4 — OPPORTUNITY_DRIVEN ──────────────────────────────────────────


def test_gate4_aper_applicable():
    """APER APPLICABLE (DT/BACS non) → OPPORTUNITY_DRIVEN."""
    app = _applicability_all_not_applicable()
    app[RuleCode.APER] = [_entry(RuleCode.APER, ApplicabilityStatus.APPLICABLE)]
    mode = compute_strategic_mode(
        applicability=app,
        patrimoine_maturity=0.90,
        trajectory_drift_pct=0.0,
    )
    assert mode == StrategicMode.OPPORTUNITY_DRIVEN


def test_gate4_unvalued_cee():
    """CEE > 50 k€ → OPPORTUNITY_DRIVEN."""
    app = _applicability_all_not_applicable()
    mode = compute_strategic_mode(
        applicability=app,
        patrimoine_maturity=0.90,
        unvalued_cee_k_eur=80.0,
    )
    assert mode == StrategicMode.OPPORTUNITY_DRIVEN


# ── Default — PERFORMANCE_DRIVEN ─────────────────────────────────────────


def test_default_performance_driven():
    """Aucun gate → PERFORMANCE_DRIVEN."""
    mode = compute_strategic_mode(
        applicability=_applicability_all_not_applicable(),
        patrimoine_maturity=0.85,
        trajectory_drift_pct=0.0,
        next_contract_end_days=500,
        spot_exposure_pct=10,
        unvalued_cee_k_eur=20,
    )
    assert mode == StrategicMode.PERFORMANCE_DRIVEN


# ── Thresholds override ──────────────────────────────────────────────────


def test_custom_thresholds_override():
    """ModeThresholds custom permettent d'expérimenter sans toucher la prod."""
    custom = ModeThresholds(MIN_PATRIMOINE_MATURITY=0.40)  # baissé pour test
    mode = compute_strategic_mode(
        applicability=_applicability_all_not_applicable(),
        patrimoine_maturity=0.50,
        thresholds=custom,
    )
    # Maturité 50 % > 40 % → pas DATA_INSUFFICIENT
    assert mode != StrategicMode.DATA_INSUFFICIENT


# ── StrategicMode enum exhaustif ─────────────────────────────────────────


def test_strategic_mode_5_members():
    """v1.0 = exactement 5 modes."""
    assert {m.value for m in StrategicMode} == {
        "regulatory_driven",
        "performance_driven",
        "procurement_driven",
        "opportunity_driven",
        "data_insufficient",
    }
