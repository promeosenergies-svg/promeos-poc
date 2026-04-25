"""
PROMEOS - Tests de base pour compute_potential_score.

Verifie :
  - interface stable (cles renvoyees, bornes 0-100)
  - effet des overrides conso_pointe_observee_pct / bacs_equipe
  - monotonicite : un meter BACS equipe n'a pas un score inferieur a un non-equipe
"""

from __future__ import annotations

import pytest

from services.pilotage.score_potential import compute_potential_score


EXPECTED_KEYS = {
    "score",
    "taux_decalable",
    "conso_pointe_pct",
    "bacs_factor",
    "used_calibration",
    "source",
}


def test_result_structure_is_stable():
    result = compute_potential_score("BUREAU_STANDARD")
    assert EXPECTED_KEYS <= result.keys(), f"cles manquantes : {EXPECTED_KEYS - result.keys()}"
    assert isinstance(result["score"], float)
    assert 0.0 <= result["score"] <= 100.0


def test_bacs_equipe_boosts_score():
    """A archetype egal, un site BACS equipe doit scorer >= non-equipe."""
    equipe = compute_potential_score("BUREAU_STANDARD", bacs_equipe=True)
    non_equipe = compute_potential_score("BUREAU_STANDARD", bacs_equipe=False)
    assert equipe["score"] >= non_equipe["score"]
    assert equipe["bacs_factor"] == pytest.approx(1.0)
    assert non_equipe["bacs_factor"] == pytest.approx(0.0)


def test_override_conso_pointe_observee():
    """Override de conso_pointe_observee_pct doit etre pris en compte."""
    # Bureau standard : pointe calibree = 0.28
    base = compute_potential_score("BUREAU_STANDARD")
    observee = compute_potential_score("BUREAU_STANDARD", conso_pointe_observee_pct=0.60)
    assert observee["conso_pointe_pct"] == pytest.approx(0.60)
    assert observee["score"] > base["score"], "plus de pointe observee -> plus de potentiel"


def test_score_is_bounded():
    """Score reste dans [0, 100] meme avec overrides extremes."""
    saturated = compute_potential_score(
        "LOGISTIQUE_FRIGO",
        conso_pointe_observee_pct=1.0,
        bacs_equipe=True,
    )
    assert 0.0 <= saturated["score"] <= 100.0
    zeroed = compute_potential_score(
        "BUREAU_STANDARD",
        conso_pointe_observee_pct=0.0,
        bacs_equipe=False,
    )
    assert 0.0 <= zeroed["score"] <= 100.0
