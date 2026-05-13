"""PROMEOS — Tests Vague A.4 : BEGESEvaluator (Loi Grenelle 2 art. 75)."""

from __future__ import annotations

from types import SimpleNamespace

from regulatory.applicability_types import ApplicabilityStatus, RuleCode
from regulatory.reason_codes import REASON_CODES
from regulatory.rules.beges import (
    BEGES_EFFECTIF_THRESHOLD_DOM,
    BEGES_EFFECTIF_THRESHOLD_METROPOLE,
    BEGESEvaluator,
)


def _org(id: int = 1, nom: str = "Org Test", effectif_total=None, pays="FR"):
    return SimpleNamespace(id=id, nom=nom, effectif_total=effectif_total, pays=pays)


def test_beges_applicable_metropole_above_500():
    """Effectif 720 + métropole → APPLICABLE.EFFECTIF_METROPOLE."""
    org = _org(effectif_total=720, pays="FR")
    app = BEGESEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "BEGES.APPLICABLE.EFFECTIF_METROPOLE"


def test_beges_applicable_metropole_at_threshold():
    """Effectif = 500 + métropole → APPLICABLE (seuil inclus)."""
    org = _org(effectif_total=BEGES_EFFECTIF_THRESHOLD_METROPOLE, pays="FR")
    app = BEGESEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.APPLICABLE


def test_beges_applicable_dom_above_250():
    """Effectif 280 + DOM (FR-DOM ou GP) → APPLICABLE.EFFECTIF_DOM."""
    for pays in ("FR-DOM", "GP", "MQ", "RE", "GF", "YT"):
        org = _org(effectif_total=280, pays=pays)
        app = BEGESEvaluator().evaluate(org)
        assert app.status == ApplicabilityStatus.APPLICABLE, f"pays {pays} should be DOM applicable"
        assert app.reason_code == "BEGES.APPLICABLE.EFFECTIF_DOM"


def test_beges_not_applicable_below_threshold_metropole():
    """Effectif 350 + métropole → NOT_APPLICABLE (seuil 500)."""
    org = _org(effectif_total=350, pays="FR")
    app = BEGESEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "BEGES.NOT_APPLICABLE.EFFECTIF_LT_250"


def test_beges_not_applicable_below_threshold_dom():
    """Effectif 200 + DOM → NOT_APPLICABLE (seuil 250 DOM)."""
    org = _org(effectif_total=200, pays="GP")
    app = BEGESEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE


def test_beges_data_missing():
    """Effectif None → DATA_MISSING."""
    org = _org(effectif_total=None)
    app = BEGESEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert app.reason_code == "BEGES.DATA_MISSING.EFFECTIF"
    assert "organisation.effectif_total" in app.missing_inputs


def test_beges_default_pays_metropole_when_none():
    """Pays absent → traité comme métropole (seuil 500)."""
    org = _org(effectif_total=520, pays=None)
    app = BEGESEvaluator().evaluate(org)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "BEGES.APPLICABLE.EFFECTIF_METROPOLE"


def test_beges_reason_codes_in_whitelist():
    cases = [
        _org(effectif_total=600, pays="FR"),  # APPLICABLE.METROPOLE
        _org(effectif_total=280, pays="GP"),  # APPLICABLE.DOM
        _org(effectif_total=200, pays="FR"),  # NOT_APPLICABLE
        _org(effectif_total=None),  # DATA_MISSING
    ]
    for org in cases:
        app = BEGESEvaluator().evaluate(org)
        assert app.reason_code in REASON_CODES, f"reason_code {app.reason_code} hors whitelist"


def test_beges_evaluator_constants():
    e = BEGESEvaluator()
    assert e.code == RuleCode.BEGES
    assert e.scope == "organisation"
