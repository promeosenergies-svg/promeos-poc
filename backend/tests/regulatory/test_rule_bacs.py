"""PROMEOS — Tests Vague A.3 : BACSEvaluator (Décret 2020-887 + 2025-1343).

Couverture :
  - APPLICABLE     : au moins un bâtiment > BACS_THRESHOLD_KW_EXISTING (70 kW v1.0)
  - NOT_APPLICABLE : tous les bâtiments ≤ seuil
  - NOT_APPLICABLE : aucun bâtiment référencé
  - DATA_MISSING   : au moins un bâtiment sans cvc_power_kw
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from doctrine.constants import BACS_THRESHOLD_KW_EXISTING

from regulatory.applicability_types import ApplicabilityStatus, RuleCode
from regulatory.reason_codes import REASON_CODES
from regulatory.rules.bacs import BACSEvaluator


def _site(id: int = 1, nom: str = "Site Test"):
    return SimpleNamespace(id=id, nom=nom)


def _batiment(id: int = 1, cvc_power_kw=None):
    return SimpleNamespace(id=id, cvc_power_kw=cvc_power_kw)


def test_bacs_applicable_one_building_above_threshold():
    """Un bâtiment > seuil Tier 2 (70 kW) → APPLICABLE Tier 2 deadline 2030."""
    site = _site(nom="Toulouse")
    batiments = [_batiment(id=1, cvc_power_kw=120.0), _batiment(id=2, cvc_power_kw=40.0)]
    app = BACSEvaluator().evaluate(site, batiments)
    assert app.status == ApplicabilityStatus.APPLICABLE
    # Phase 3.8 P1-B (audit code-reviewer P3.7) : Tier 2 distinct du Tier 1
    assert app.reason_code == "BACS.APPLICABLE.TIER2_UPCOMING"
    assert app.deadline == date(2030, 1, 1)
    assert app.inputs_used["cvc_power_max_kw"] == 120.0
    assert app.inputs_used["threshold_kw"] == BACS_THRESHOLD_KW_EXISTING
    assert app.inputs_used["tier"] == "existing"


def test_bacs_applicable_tier1_above_290():
    """Phase 3.6 EE : bâtiment > 290 kW (Tier 1) → deadline expirée 01/01/2025."""
    site = _site(nom="GrosSite")
    batiments = [_batiment(id=1, cvc_power_kw=350.0)]
    app = BACSEvaluator().evaluate(site, batiments)
    assert app.status == ApplicabilityStatus.APPLICABLE
    assert app.inputs_used["tier"] == "initial"
    # Tier 1 deadline = 01/01/2025 (expirée)
    assert app.deadline == date(2025, 1, 1)
    assert "Tier 1" in app.reason_human or "expirée" in app.reason_human


def test_bacs_applicable_uses_max_power():
    """L'évaluateur statue sur le MAX des bâtiments (pas la somme)."""
    site = _site()
    batiments = [_batiment(cvc_power_kw=50), _batiment(cvc_power_kw=85)]
    app = BACSEvaluator().evaluate(site, batiments)
    assert app.status == ApplicabilityStatus.APPLICABLE


def test_bacs_not_applicable_all_below_threshold():
    """Tous bâtiments ≤ seuil → NOT_APPLICABLE."""
    site = _site(nom="Petit site")
    batiments = [_batiment(cvc_power_kw=30), _batiment(cvc_power_kw=50)]
    app = BACSEvaluator().evaluate(site, batiments)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "BACS.NOT_APPLICABLE.NO_SYSTEM_GT_THRESHOLD"


def test_bacs_not_applicable_at_threshold_strict():
    """Bâtiment = exactement seuil → NOT_APPLICABLE (comparaison stricte >)."""
    site = _site()
    batiments = [_batiment(cvc_power_kw=float(BACS_THRESHOLD_KW_EXISTING))]
    app = BACSEvaluator().evaluate(site, batiments)
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE


def test_bacs_not_applicable_no_buildings():
    """Aucun bâtiment référencé → NOT_APPLICABLE.NO_BUILDINGS."""
    site = _site(nom="Vide")
    app = BACSEvaluator().evaluate(site, [])
    assert app.status == ApplicabilityStatus.NOT_APPLICABLE
    assert app.reason_code == "BACS.NOT_APPLICABLE.NO_BUILDINGS"


def test_bacs_data_missing_cvc_power():
    """Bâtiment sans cvc_power_kw → DATA_MISSING.CVC_POWER."""
    site = _site()
    batiments = [_batiment(id=1, cvc_power_kw=None), _batiment(id=2, cvc_power_kw=100)]
    app = BACSEvaluator().evaluate(site, batiments)
    assert app.status == ApplicabilityStatus.DATA_MISSING
    assert app.reason_code == "BACS.DATA_MISSING.CVC_POWER"
    assert any("batiment.cvc_power_kw" in m for m in app.missing_inputs)


def test_bacs_reason_codes_in_whitelist():
    cases = [
        (_site(), [_batiment(cvc_power_kw=100)]),  # APPLICABLE
        (_site(), [_batiment(cvc_power_kw=30)]),  # NOT_APPLICABLE.NO_SYSTEM
        (_site(), []),  # NOT_APPLICABLE.NO_BUILDINGS
        (_site(), [_batiment(cvc_power_kw=None)]),  # DATA_MISSING
    ]
    for site, bats in cases:
        app = BACSEvaluator().evaluate(site, bats)
        assert app.reason_code in REASON_CODES, f"reason_code {app.reason_code} hors whitelist"


def test_bacs_evaluator_constants():
    e = BACSEvaluator()
    assert e.code == RuleCode.BACS
    assert e.scope == "site"
    assert "2020-887" in e.version
