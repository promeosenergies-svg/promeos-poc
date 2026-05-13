"""PROMEOS — Tests Vague A.2 : DTEvaluator (Décret tertiaire 2019-771).

Couverture cardinale :
  - APPLICABLE     : surface ≥ 1000 m² + usage tertiaire valide
  - NOT_APPLICABLE : surface < 1000 m² (SDP_LT_1000)
  - NOT_APPLICABLE : usage hors tertiaire OPERAT (USAGE_NON_TERTIARY) — non
                     atteignable via OperatUsagePrincipalEnum v1.0, simulé
                     via str arbitraire
  - UNKNOWN        : usage MIXTE (qualification fine requise)
  - DATA_MISSING   : surface ou usage manquant

Bonus :
  - reason_codes dans whitelist REASON_CODES
  - _audit complet (5 clés)
  - immuabilité (FrozenInstanceError)
"""

from __future__ import annotations

import dataclasses
from datetime import date
from types import SimpleNamespace

import pytest

from regulatory.applicability_types import ApplicabilityStatus, RuleCode
from regulatory.reason_codes import REASON_CODES
from regulatory.rules.dt import DT_SDP_THRESHOLD_M2, DTEvaluator


def _site(id: int = 1, nom: str = "Site Test", tertiaire_area_m2=None, usage_principal=None):
    """Mock léger d'un Site (duck-typing via SimpleNamespace)."""
    return SimpleNamespace(id=id, nom=nom, tertiaire_area_m2=tertiaire_area_m2, usage_principal=usage_principal)


# ── Cas APPLICABLE ──────────────────────────────────────────────────────────


def test_dt_applicable_bureaux_large():
    """Site BUREAUX 2 000 m² → APPLICABLE."""
    site = _site(id=42, nom="Toulouse Entrepôt", tertiaire_area_m2=2000, usage_principal="BUREAUX")
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "DT.APPLICABLE"
    assert app.deadline == date(2030, 12, 31)
    assert app.confidence == 1.0
    assert app.scope_id == 42
    assert "Toulouse Entrepôt" in app.reason_human
    assert "Décret 2019-771 art. R175-1" in app.evidence_refs


def test_dt_applicable_all_tertiary_usages():
    """Tous les usages tertiaires v1.0 doivent statuer APPLICABLE si surface ≥ 1000."""
    for usage in (
        "BUREAUX",
        "COMMERCES",
        "ENSEIGNEMENT",
        "HOTELLERIE",
        "RESTAURATION",
        "SANTE",
        "SPORT_LOISIRS",
        "LOGISTIQUE",
    ):
        site = _site(id=1, nom=f"Site {usage}", tertiaire_area_m2=1500, usage_principal=usage)
        app = DTEvaluator().evaluate(site)
        assert app.status == ApplicabilityStatus.APPLICABLE, f"usage {usage} should be applicable"


def test_dt_applicable_enum_value_normalized():
    """L'évaluateur tolère un attribut Enum (value extraction)."""
    enum_like = SimpleNamespace(value="BUREAUX")
    site = _site(id=2, nom="Lyon", tertiaire_area_m2=1200, usage_principal=enum_like)
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.inputs_used["usage_principal"] == "BUREAUX"


# ── Cas NOT_APPLICABLE ─────────────────────────────────────────────────────


def test_dt_not_applicable_surface_below_threshold():
    """Site BUREAUX 850 m² → NOT_APPLICABLE.SDP_LT_1000."""
    site = _site(id=12, nom="Lyon Bureaux", tertiaire_area_m2=850, usage_principal="BUREAUX")
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "DT.NOT_APPLICABLE.SDP_LT_1000"
    assert app.deadline is None
    assert "850" in app.reason_human


def test_dt_not_applicable_exactly_under_threshold():
    """Site BUREAUX 999.99 m² → NOT_APPLICABLE (seuil strict)."""
    site = _site(id=13, nom="X", tertiaire_area_m2=DT_SDP_THRESHOLD_M2 - 0.01, usage_principal="BUREAUX")
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE


def test_dt_applicable_exactly_at_threshold():
    """Site BUREAUX 1 000 m² → APPLICABLE (seuil inclus)."""
    site = _site(id=14, nom="X", tertiaire_area_m2=DT_SDP_THRESHOLD_M2, usage_principal="BUREAUX")
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE


def test_dt_not_applicable_usage_non_tertiary():
    """Usage hors whitelist tertiaire → NOT_APPLICABLE.USAGE_NON_TERTIARY."""
    site = _site(id=15, nom="X", tertiaire_area_m2=2000, usage_principal="USINE_INDUSTRIELLE")
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "DT.NOT_APPLICABLE.USAGE_NON_TERTIARY"


# ── Cas UNKNOWN ────────────────────────────────────────────────────────────


def test_dt_unknown_usage_mixte():
    """Usage MIXTE → UNKNOWN (qualification fine requise)."""
    site = _site(id=7, nom="Paris Mixte", tertiaire_area_m2=2400, usage_principal="MIXTE")
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.UNKNOWN
    assert app.reason_code == "DT.UNKNOWN.USAGE_MIXTE"
    assert app.confidence == 0.5


# ── Cas DATA_MISSING ──────────────────────────────────────────────────────


def test_dt_data_missing_surface():
    """Surface absente → DATA_MISSING.SURFACE."""
    site = _site(id=99, nom="Nice Hôtel", tertiaire_area_m2=None, usage_principal="HOTELLERIE")
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert app.reason_code == "DT.DATA_MISSING.SURFACE"
    assert "site.tertiaire_area_m2" in app.missing_inputs


def test_dt_data_missing_usage():
    """Usage absent → DATA_MISSING.USAGE."""
    site = _site(id=100, nom="X", tertiaire_area_m2=1500, usage_principal=None)
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert app.reason_code == "DT.DATA_MISSING.USAGE"
    assert "site.usage_principal" in app.missing_inputs


def test_dt_data_missing_both():
    """Surface ET usage absents → DATA_MISSING (priorité surface)."""
    site = _site(id=101, nom="X", tertiaire_area_m2=None, usage_principal=None)
    app = DTEvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert "site.tertiaire_area_m2" in app.missing_inputs
    assert "site.usage_principal" in app.missing_inputs


# ── Discipline traçabilité ────────────────────────────────────────────────


def test_dt_reason_codes_all_in_whitelist():
    """Tous les reason_code produits par DTEvaluator doivent être dans REASON_CODES."""
    cases = [
        _site(id=1, tertiaire_area_m2=2000, usage_principal="BUREAUX"),  # APPLICABLE
        _site(id=2, tertiaire_area_m2=500, usage_principal="BUREAUX"),  # SDP_LT_1000
        _site(id=3, tertiaire_area_m2=2000, usage_principal="AUTRE"),  # USAGE_NON_TERTIARY
        _site(id=4, tertiaire_area_m2=2000, usage_principal="MIXTE"),  # UNKNOWN
        _site(id=5, tertiaire_area_m2=None, usage_principal="BUREAUX"),  # DATA_MISSING.SURFACE
        _site(id=6, tertiaire_area_m2=2000, usage_principal=None),  # DATA_MISSING.USAGE
    ]
    for site in cases:
        app = DTEvaluator().evaluate(site)
        assert app.reason_code in REASON_CODES, f"reason_code {app.reason_code} hors whitelist"


def test_dt_audit_complete():
    """_audit doit contenir les 5 clés requises."""
    site = _site(id=1, tertiaire_area_m2=2000, usage_principal="BUREAUX")
    app = DTEvaluator().evaluate(site)
    for key in ("doctrine_version", "evaluated_at", "evaluator", "evaluator_version", "data_source"):
        assert key in app._audit
    assert app._audit["evaluator"] == "DTEvaluator"
    assert app._audit["evaluator_version"] == "DT-2019-771-v2024-10-01"


def test_dt_result_immutable():
    """Le verdict est immuable (frozen=True)."""
    site = _site(id=1, tertiaire_area_m2=2000, usage_principal="BUREAUX")
    app = DTEvaluator().evaluate(site)
    with pytest.raises(dataclasses.FrozenInstanceError):
        app.status = ApplicabilityStatus.NOT_APPLICABLE  # type: ignore[misc]


def test_dt_evaluator_constants():
    """DTEvaluator expose code/version/scope corrects."""
    e = DTEvaluator()
    assert e.code == RuleCode.DT
    assert e.scope == "site"
    assert e.version == "DT-2019-771-v2024-10-01"
