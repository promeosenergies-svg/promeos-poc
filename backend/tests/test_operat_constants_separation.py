"""Tests unitaires Conformite S1 OPERAT/DEET — constantes + validation.

Tests fonctionnels des helpers et regles definies dans
`backend/config/operat_constants.py` (S1 #324 Chantiers 1+2+3).

Couverture :
  T1. Constantes OPERAT CO2 (Annexe VII) exposees + valeurs verbatim Legifrance.
  T2. Constantes EP OPERAT Art.16 exposees + valeurs verbatim.
  T3. Helpers fail-closed sur vecteur/typologie inconnu.
  T4. Validation annee de reference (plage 2010-2022 + cas batiment neuf).
  T5. TRI threshold par typologie (30/15/10).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_t1_emission_factors_operat_values():
    """Annexe VII tableau VII-2 — valeurs verbatim Legifrance."""
    from config.operat_constants import (
        EMISSION_FACTORS_OPERAT,
        get_operat_emission_factor,
    )

    # Valeur D1 confirmee Legifrance.
    assert EMISSION_FACTORS_OPERAT["ELEC"]["kgco2e_per_kwh"] == 0.064
    assert EMISSION_FACTORS_OPERAT["GAZ"]["kgco2e_per_kwh"] == 0.227
    assert EMISSION_FACTORS_OPERAT["FIOUL"]["kgco2e_per_kwh"] == 0.324
    # Helper d'acces.
    assert get_operat_emission_factor("ELEC") == 0.064
    assert get_operat_emission_factor("elec") == 0.064  # case-insensitive
    # Source citee.
    assert "Annexe VII" in EMISSION_FACTORS_OPERAT["ELEC"]["source"]


def test_t2_ep_coefficients_operat_values():
    """EP Article 16 — changement de source energetique."""
    from config.operat_constants import (
        EP_COEFFICIENTS_OPERAT,
        get_operat_ep_coefficient,
    )

    # Valeur D2 confirmee Legifrance Annexe VII Article 16.
    assert EP_COEFFICIENTS_OPERAT["ELEC"]["coeff_ep"] == 2.3
    assert EP_COEFFICIENTS_OPERAT["GAZ"]["coeff_ep"] == 1.0
    assert EP_COEFFICIENTS_OPERAT["BOIS"]["coeff_ep"] == 0.0
    # Helper.
    assert get_operat_ep_coefficient("ELEC") == 2.3


def test_t3_helpers_fail_closed_on_unknown_vector():
    """Doctrine 'aucun fallback silencieux' : KeyError attendu."""
    from config.operat_constants import (
        get_operat_emission_factor,
        get_operat_ep_coefficient,
        get_operat_tri_threshold,
    )

    with pytest.raises(KeyError, match="non couvert"):
        get_operat_emission_factor("URANIUM")
    with pytest.raises(KeyError, match="non couvert"):
        get_operat_ep_coefficient("HYDROGEN")
    with pytest.raises(KeyError, match="inconnue"):
        get_operat_tri_threshold("MAGIC_TRAVAUX")


def test_t4_reference_year_validation():
    """Article 3.I — plage 2010-2022 + cas batiment neuf post-2022."""
    from config.operat_constants import is_valid_operat_reference_year
    from datetime import date

    current_year = date.today().year

    # Cas standard : plage [2010 ; 2022].
    assert is_valid_operat_reference_year(2010) is True
    assert is_valid_operat_reference_year(2019) is True
    assert is_valid_operat_reference_year(2022) is True
    assert is_valid_operat_reference_year(2009) is False  # trop ancien
    assert is_valid_operat_reference_year(2023) is False  # > 2022 sans flag
    assert is_valid_operat_reference_year(current_year) is False  # idem

    # Cas batiment neuf (is_first_full_year=True) : plage [2010 ; current_year].
    assert is_valid_operat_reference_year(2023, is_first_full_year=True) is True
    assert is_valid_operat_reference_year(current_year, is_first_full_year=True) is True
    assert is_valid_operat_reference_year(current_year + 1, is_first_full_year=True) is False  # futur
    assert is_valid_operat_reference_year(2009, is_first_full_year=True) is False  # avant 2010


def test_t5_tri_thresholds_by_typology():
    """Article 11.I — 30/15/10 par typologie."""
    from config.operat_constants import (
        OPERAT_TRI_TYPOLOGIES,
        get_operat_tri_threshold,
    )

    assert get_operat_tri_threshold("STRUCTURAL_ENVELOPE") == 30
    assert get_operat_tri_threshold("ENERGY_EQUIPMENT") == 15
    assert get_operat_tri_threshold("OPTIMIZATION_SYSTEM") == 10

    # Toutes les typologies ont un label_fr et une source citee.
    for typo, meta in OPERAT_TRI_TYPOLOGIES.items():
        assert "label_fr" in meta and meta["label_fr"]
        assert "Article 11.I" in meta["source"]
        assert meta["source_url"].startswith("https://www.legifrance.gouv.fr/")


def test_t6_butoir_and_fallback_documented():
    """Butoir 30/09/2027 + regle fallback documentes textuellement."""
    from config.operat_constants import (
        OPERAT_REFERENCE_YEAR_DEADLINE_ISO,
        OPERAT_REFERENCE_YEAR_DEADLINE_LABEL,
        OPERAT_REFERENCE_YEAR_FALLBACK_RULE,
    )

    assert OPERAT_REFERENCE_YEAR_DEADLINE_ISO == "2027-09-30"
    assert "30 septembre 2027" in OPERAT_REFERENCE_YEAR_DEADLINE_LABEL
    assert (
        "premiere annee pleine d'exploitation" in OPERAT_REFERENCE_YEAR_FALLBACK_RULE.lower()
        or "première année pleine d'exploitation" in OPERAT_REFERENCE_YEAR_FALLBACK_RULE.lower()
    )
    assert "Article 3.I" in OPERAT_REFERENCE_YEAR_FALLBACK_RULE
