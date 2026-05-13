"""PROMEOS — Tests Vague C.1-C.4 : 3 builders prioritaires + stubs.

Couverture :
  - RegulatoryDrivenBuilder produit un payload complet (clés ADR-023 §3)
  - PerformanceDrivenBuilder idem
  - DataInsufficientBuilder idem
  - 3 KPIs strictement
  - 2 charts strictement
  - dossier_p1 contient scenarios + timeline + proof_pills + verdict
  - verdict.constraint et verdict.opportunity non vides
  - footer.version_tags inclut "Assujettissement v1.0"
  - Stubs Procurement/Opportunity lèvent NotImplementedError
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from regulatory.applicability_types import (
    ApplicabilityStatus,
    RuleApplicability,
    RuleCode,
)
from services.strategique.builders import (
    IMPLEMENTED_MODES,
    MODE_BUILDERS,
    DataInsufficientBuilder,
    OpportunityDrivenBuilder,
    PerformanceDrivenBuilder,
    ProcurementDrivenBuilder,
    RegulatoryDrivenBuilder,
)
from services.strategique.mode_thresholds import StrategicMode


_AUDIT = {
    "doctrine_version": "ADR-024-v1.0",
    "evaluated_at": datetime(2026, 5, 13, tzinfo=timezone.utc).isoformat(),
    "evaluator": "TestEvaluator",
    "evaluator_version": "TEST-v1.0",
    "data_source": "test.fixtures",
}


def _entry(rule: RuleCode, status: ApplicabilityStatus, scope_id: int = 1, missing=()) -> RuleApplicability:
    reasons = {
        ApplicabilityStatus.APPLICABLE: f"{rule.value}.APPLICABLE",
        ApplicabilityStatus.NOT_APPLICABLE: f"{rule.value}.NOT_APPLICABLE.PME"
        if rule in (RuleCode.SME,)
        else f"{rule.value}.NOT_APPLICABLE.SDP_LT_1000",
        ApplicabilityStatus.UNKNOWN: "DT.UNKNOWN.USAGE_MIXTE",
        ApplicabilityStatus.DATA_MISSING: f"{rule.value}.DATA_MISSING.SURFACE",
    }
    return RuleApplicability(
        rule_code=rule,
        rule_version=f"{rule.value}-test-v2026-01-01",
        scope_level="site" if rule in (RuleCode.DT, RuleCode.BACS, RuleCode.APER) else "organisation",
        scope_id=scope_id,
        scope_label=f"Scope {scope_id}",
        status=status,
        reason_code=reasons[status],
        reason_human="test",
        missing_inputs=list(missing) if status == ApplicabilityStatus.DATA_MISSING else [],
        _audit=_AUDIT,
    )


def _applicability_helios() -> dict:
    """HELIOS : DT APPLICABLE + SMÉ APPLICABLE."""
    return {
        RuleCode.DT: [_entry(RuleCode.DT, ApplicabilityStatus.APPLICABLE)],
        RuleCode.BACS: [_entry(RuleCode.BACS, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.APER: [_entry(RuleCode.APER, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.SME: [_entry(RuleCode.SME, ApplicabilityStatus.APPLICABLE)],
        RuleCode.BEGES: [_entry(RuleCode.BEGES, ApplicabilityStatus.NOT_APPLICABLE)],
    }


def _applicability_meridian() -> dict:
    """MERIDIAN : tous NOT_APPLICABLE → PERFORMANCE par défaut."""
    return {
        RuleCode.DT: [_entry(RuleCode.DT, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.BACS: [_entry(RuleCode.BACS, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.APER: [_entry(RuleCode.APER, ApplicabilityStatus.NOT_APPLICABLE)],
        RuleCode.SME: [_entry(RuleCode.SME, ApplicabilityStatus.APPLICABLE)],
        RuleCode.BEGES: [_entry(RuleCode.BEGES, ApplicabilityStatus.NOT_APPLICABLE)],
    }


def _applicability_onboarding() -> dict:
    """Onboarding : majorité DATA_MISSING → DATA_INSUFFICIENT."""
    return {
        RuleCode.DT: [_entry(RuleCode.DT, ApplicabilityStatus.DATA_MISSING, missing=["site.tertiaire_area_m2"])],
        RuleCode.BACS: [_entry(RuleCode.BACS, ApplicabilityStatus.DATA_MISSING, missing=["batiment.cvc_power_kw"])],
        RuleCode.APER: [_entry(RuleCode.APER, ApplicabilityStatus.DATA_MISSING, missing=["site.parking_area_m2"])],
        RuleCode.SME: [_entry(RuleCode.SME, ApplicabilityStatus.DATA_MISSING, missing=["organisation.effectif_total"])],
        RuleCode.BEGES: [
            _entry(RuleCode.BEGES, ApplicabilityStatus.DATA_MISSING, missing=["organisation.effectif_total"])
        ],
    }


REQUIRED_PAYLOAD_KEYS = {
    "strategic_mode",
    "applicability",
    "patrimoine_maturity",
    "verdict",
    "hero",
    "kpis",
    "charts",
    "dossier_p1",
    "queue_p2_p3",
    "continuity",
    "footer",
    "_audit",
}


# ── Tests par builder ────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity,expected_mode",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88, "regulatory_driven"),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85, "performance_driven"),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30, "data_insufficient"),
    ],
)
def test_builder_payload_has_required_keys(builder_cls, applicability, maturity, expected_mode):
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    missing = REQUIRED_PAYLOAD_KEYS - set(payload.keys())
    assert not missing, f"Clés manquantes dans payload {builder_cls.__name__}: {missing}"
    assert payload["strategic_mode"] == expected_mode


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30),
    ],
)
def test_builder_kpis_exactly_3(builder_cls, applicability, maturity):
    """Loi L11 : exactement 3 KPIs."""
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    assert len(payload["kpis"]) == 3, f"{builder_cls.__name__} doit avoir 3 KPIs"


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30),
    ],
)
def test_builder_charts_exactly_2(builder_cls, applicability, maturity):
    """Loi L11 : exactement 2 charts."""
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    assert len(payload["charts"]) == 2, f"{builder_cls.__name__} doit avoir 2 charts"


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30),
    ],
)
def test_builder_dossier_p1_complete(builder_cls, applicability, maturity):
    """dossier_p1 doit contenir les blocs cardinaux."""
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    dp1 = payload["dossier_p1"]
    for key in (
        "priority",
        "category",
        "question",
        "recommendation",
        "proof_pills",
        "scenarios",
        "timeline",
        "proof_sidebar",
        "why_promeos",
        "links",
    ):
        assert key in dp1, f"dossier_p1.{key} manquant pour {builder_cls.__name__}"
    assert len(dp1["scenarios"]) == 3
    assert any(s.get("recommended") for s in dp1["scenarios"]), (
        f"Au moins un scénario doit être recommended (B canonique)"
    )


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30),
    ],
)
def test_builder_verdict_non_empty(builder_cls, applicability, maturity):
    """verdict.constraint et opportunity non vides."""
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    for side in ("constraint", "opportunity"):
        v = payload["verdict"][side]
        assert v["label"] and v["statement"] and v["detail"], f"verdict.{side} doit être complet"


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30),
    ],
)
def test_builder_footer_version_tags(builder_cls, applicability, maturity):
    """footer.version_tags inclut le tag canonique."""
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    tags = payload["footer"]["version_tags"]
    assert "Assujettissement v1.0" in tags
    assert "Synthèse stratégique v1.0" in tags


# ── KPI trace complete (AP-stratX6) ──────────────────────────────────────


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30),
    ],
)
def test_builder_kpi_trace_complete(builder_cls, applicability, maturity):
    """Chaque KPI doit avoir source/formula/scope/freshness (AP-stratX6)."""
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    for kpi in payload["kpis"]:
        assert "trace" in kpi, f"KPI {kpi.get('id')} sans trace"
        for field in ("source", "formula", "scope", "freshness"):
            assert field in kpi["trace"], f"KPI {kpi['id']} trace.{field} manquant"


# ── Queue P2/P3 cardinality ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "builder_cls,applicability,maturity",
    [
        (RegulatoryDrivenBuilder, _applicability_helios(), 0.88),
        (PerformanceDrivenBuilder, _applicability_meridian(), 0.85),
        (DataInsufficientBuilder, _applicability_onboarding(), 0.30),
    ],
)
def test_builder_queue_p2p3_3_to_5(builder_cls, applicability, maturity):
    """queue_p2_p3 doit avoir 3-5 entrées (Loi L11 strict)."""
    payload = builder_cls().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=maturity,
    )
    assert 3 <= len(payload["queue_p2_p3"]) <= 5, f"queue_p2_p3 hors range 3-5 pour {builder_cls.__name__}"


# ── Phase 3.6 Vague BB : Procurement + Opportunity implémentés ─────────


def test_procurement_builder_implemented(monkeypatch):
    """Phase 3.6 : ProcurementDrivenBuilder retourne un payload complet."""
    monkeypatch.setattr(
        "services.strategique.builders.procurement.compute_next_contract_end",
        lambda db, oid: {"days": 60, "contract_id": 1, "fournisseur": "EDF", "source": "computed"},
    )
    monkeypatch.setattr(
        "services.strategique.builders.procurement.compute_spot_exposure",
        lambda db, oid: {"pct": 45.0, "contrats_count": 2, "source": "computed"},
    )
    payload = ProcurementDrivenBuilder().build(
        db=MagicMock(),
        org_id=1,
        applicability=_applicability_meridian(),
        patrimoine_maturity=0.85,
    )
    assert payload["strategic_mode"] == "procurement_driven"
    assert len(payload["kpis"]) == 3
    assert len(payload["charts"]) == 2
    assert "verdict" in payload and payload["verdict"]["constraint"]["statement"]


def test_opportunity_builder_implemented(monkeypatch):
    """Phase 3.6 : OpportunityDrivenBuilder retourne un payload complet."""
    monkeypatch.setattr(
        "services.strategique.builders.opportunity.compute_unvalued_cee_keur",
        lambda db, oid: {"k_eur": 25.0, "actions_count": 3, "source": "computed"},
    )
    applicability = _applicability_meridian()
    applicability[RuleCode.APER] = [_entry(RuleCode.APER, ApplicabilityStatus.APPLICABLE)]
    payload = OpportunityDrivenBuilder().build(
        db=MagicMock(),
        org_id=1,
        applicability=applicability,
        patrimoine_maturity=0.85,
    )
    assert payload["strategic_mode"] == "opportunity_driven"
    assert len(payload["kpis"]) == 3
    assert len(payload["charts"]) == 2


# ── MODE_BUILDERS dispatcher ─────────────────────────────────────────────


def test_mode_builders_dispatcher_complete():
    assert set(MODE_BUILDERS.keys()) == set(StrategicMode)


def test_implemented_modes_all_5_phase_3_6():
    """Phase 3.6 Vague BB : 5 modes implémentés (plus de fallback runtime)."""
    assert IMPLEMENTED_MODES == frozenset(StrategicMode)
