"""PROMEOS — Tests Vague A.3 : APEREvaluator (Loi 2023-175 art. 40).

Couverture :
  - APPLICABLE.PARKING       : parking_area_m2 ≥ 1500 (SMALL/LARGE)
  - APPLICABLE.TOITURE       : roof_area_m2 ≥ 500 (sans parking éligible)
  - NOT_APPLICABLE.PARKING_LT_1500 : parking renseigné mais < 1500
  - NOT_APPLICABLE.NO_ELIGIBLE_AREA: ni parking ni toiture éligibles
  - DATA_MISSING.PARKING_AREA: parking ET toiture tous deux absents
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from regulatory.applicability_types import ApplicabilityStatus, RuleCode
from regulatory.reason_codes import REASON_CODES
from regulatory.rules.aper import (
    APER_DEADLINE_LARGE,
    APER_DEADLINE_SMALL,
    APER_PARKING_LARGE_M2,
    APER_PARKING_THRESHOLD_M2,
    APER_ROOF_THRESHOLD_M2,
    APEREvaluator,
)


def _site(id: int = 1, nom: str = "Site Test", parking_area_m2=None, roof_area_m2=None):
    return SimpleNamespace(id=id, nom=nom, parking_area_m2=parking_area_m2, roof_area_m2=roof_area_m2)


# ── APPLICABLE.PARKING ─────────────────────────────────────────────────────


def test_aper_applicable_parking_small():
    """Parking 5 000 m² → APPLICABLE.PARKING category SMALL deadline 2028."""
    site = _site(nom="Toulouse", parking_area_m2=5000)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "APER.APPLICABLE.PARKING"
    assert app.deadline == APER_DEADLINE_SMALL
    assert app.inputs_used["category"] == "SMALL"


def test_aper_applicable_parking_large():
    """Parking 12 000 m² → APPLICABLE.PARKING category LARGE deadline 2026."""
    site = _site(parking_area_m2=12000)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.deadline == APER_DEADLINE_LARGE
    assert app.inputs_used["category"] == "LARGE"


def test_aper_applicable_parking_at_threshold():
    """Parking = 1 500 m² → APPLICABLE.PARKING (seuil inclus)."""
    site = _site(parking_area_m2=APER_PARKING_THRESHOLD_M2)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE


# ── APPLICABLE.TOITURE ─────────────────────────────────────────────────────


def test_aper_applicable_toiture():
    """Pas de parking éligible mais toiture ≥ 500 → APPLICABLE.TOITURE."""
    site = _site(parking_area_m2=None, roof_area_m2=800)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.reason_code == "APER.APPLICABLE.TOITURE"


def test_aper_applicable_toiture_at_threshold():
    """Toiture = 500 m² → APPLICABLE.TOITURE (seuil inclus)."""
    site = _site(parking_area_m2=None, roof_area_m2=APER_ROOF_THRESHOLD_M2)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.APPLICABLE


def test_aper_parking_priority_over_roof():
    """Parking éligible prime sur toiture éligible (reason_code parking)."""
    site = _site(parking_area_m2=2000, roof_area_m2=800)
    app = APEREvaluator().evaluate(site)
    assert app.reason_code == "APER.APPLICABLE.PARKING"


# ── NOT_APPLICABLE ─────────────────────────────────────────────────────────


def test_aper_not_applicable_parking_below_threshold():
    """Parking 1 200 m² + pas de toiture → NOT_APPLICABLE.PARKING_LT_1500."""
    site = _site(parking_area_m2=1200, roof_area_m2=200)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "APER.NOT_APPLICABLE.PARKING_LT_1500"


def test_aper_not_applicable_no_eligible_area():
    """Pas de parking + toiture < 500 → NOT_APPLICABLE.NO_ELIGIBLE_AREA."""
    site = _site(parking_area_m2=None, roof_area_m2=300)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "APER.NOT_APPLICABLE.NO_ELIGIBLE_AREA"


# ── DATA_MISSING ───────────────────────────────────────────────────────────


def test_aper_data_missing_both_areas():
    """Parking ET toiture tous deux None → DATA_MISSING."""
    site = _site(parking_area_m2=None, roof_area_m2=None)
    app = APEREvaluator().evaluate(site)
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert app.reason_code == "APER.DATA_MISSING.PARKING_AREA"
    assert "site.parking_area_m2" in app.missing_inputs
    assert "site.roof_area_m2" in app.missing_inputs


# ── Discipline traçabilité ────────────────────────────────────────────────


def test_aper_reason_codes_in_whitelist():
    cases = [
        _site(parking_area_m2=2000),  # APPLICABLE.PARKING
        _site(roof_area_m2=800),  # APPLICABLE.TOITURE
        _site(parking_area_m2=1000, roof_area_m2=100),  # NOT_APPLICABLE.PARKING_LT_1500
        _site(parking_area_m2=None, roof_area_m2=300),  # NOT_APPLICABLE.NO_ELIGIBLE_AREA
        _site(),  # DATA_MISSING
    ]
    for site in cases:
        app = APEREvaluator().evaluate(site)
        assert app.reason_code in REASON_CODES, f"reason_code {app.reason_code} hors whitelist"


def test_aper_evaluator_constants():
    e = APEREvaluator()
    assert e.code == RuleCode.APER
    assert e.scope == "site"
    assert "2023-175" in e.version
