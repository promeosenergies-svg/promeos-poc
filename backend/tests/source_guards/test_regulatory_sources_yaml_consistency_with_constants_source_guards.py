"""
PROMEOS — Source-guard cohérence sources_reglementaires.yaml ↔ constants Python (Sprint C-3 Phase 3.3).

Garantit que les valeurs canoniques exposées par le YAML SoT
(`backend/config/sources_reglementaires.yaml`) sont cohérentes avec les
constantes Python utilisées en runtime (`backend/config/emission_factors.py`,
`backend/doctrine/constants.py`).

Sans ce source-guard : risque de divergence silencieuse YAML / runtime
(ex: ADEME met à jour V23.7 → 0.054, on update YAML mais oublie
emission_factors.py → frontend affiche YAML mais backend calcule avec
ancienne valeur).

Patterns vérifiés :
- SG_REG_CONST_01 : facteurs CO2 (3 valeurs) cohérents YAML ↔ EMISSION_FACTORS
- SG_REG_CONST_02 : pénalités compliance cohérentes YAML ↔ doctrine.constants
- SG_REG_CONST_03 : seuils audit SMÉ cohérents YAML ↔ doctrine.constants
- SG_REG_CONST_04 : milestones DT cohérents YAML ↔ doctrine.constants
- SG_REG_CONST_05 : coefficient énergie primaire élec cohérents YAML ↔ doctrine.constants
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _yaml_value(term_id: str):
    """Helper : récupère value depuis YAML via loader canonical."""
    from config.regulatory_sources_loader import get_term_value

    return get_term_value(term_id)


# ─── SG_REG_CONST_01 : facteurs CO2 ─────────────────────────────────────────


def test_sg_reg_const_01_co2_factor_elec_matches_emission_factors():
    """YAML CO2_FACTOR_ELEC_KGCO2_PER_KWH == EMISSION_FACTORS['ELEC']['kgco2e_per_kwh']."""
    from config.emission_factors import EMISSION_FACTORS

    yaml_val = _yaml_value("CO2_FACTOR_ELEC_KGCO2_PER_KWH")
    py_val = EMISSION_FACTORS["ELEC"]["kgco2e_per_kwh"]
    assert yaml_val == py_val, (
        f"Divergence CO2 élec : YAML={yaml_val} vs emission_factors.py={py_val}. "
        f"Mettre à jour les 2 sources synchroniquement."
    )


def test_sg_reg_const_01_co2_factor_gaz_matches_emission_factors():
    from config.emission_factors import EMISSION_FACTORS

    yaml_val = _yaml_value("CO2_FACTOR_GAZ_NATUREL_KGCO2_PER_KWH")
    py_val = EMISSION_FACTORS["GAZ"]["kgco2e_per_kwh"]
    assert yaml_val == py_val, f"Divergence CO2 gaz : YAML={yaml_val} vs Python={py_val}"


# ─── SG_REG_CONST_02 : pénalités compliance ─────────────────────────────────


def test_sg_reg_const_02_dt_penalty_matches_doctrine():
    """YAML COMPLIANCE_DT_PENALTY_EUR == doctrine.constants.DT_PENALTY_EUR."""
    from doctrine.constants import DT_PENALTY_EUR

    yaml_val = _yaml_value("COMPLIANCE_DT_PENALTY_EUR")
    assert yaml_val == DT_PENALTY_EUR, f"Divergence DT penalty : YAML={yaml_val} vs doctrine.constants={DT_PENALTY_EUR}"


def test_sg_reg_const_02_dt_penalty_at_risk_matches_doctrine():
    from doctrine.constants import DT_PENALTY_AT_RISK_EUR

    yaml_val = _yaml_value("COMPLIANCE_DT_PENALTY_AT_RISK_EUR")
    assert yaml_val == DT_PENALTY_AT_RISK_EUR


def test_sg_reg_const_02_bacs_penalty_matches_doctrine():
    from doctrine.constants import BACS_PENALTY_EUR

    yaml_val = _yaml_value("COMPLIANCE_BACS_PENALTY_EUR")
    assert yaml_val == BACS_PENALTY_EUR


def test_sg_reg_const_02_operat_penalty_matches_doctrine():
    from doctrine.constants import OPERAT_PENALTY_EUR

    yaml_val = _yaml_value("COMPLIANCE_OPERAT_PENALTY_EUR")
    assert yaml_val == OPERAT_PENALTY_EUR


# ─── SG_REG_CONST_03 : seuils audit SMÉ ─────────────────────────────────────


def test_sg_reg_const_03_audit_sme_threshold_periodic_matches_doctrine():
    """YAML AUDIT_SME_THRESHOLD_GWH_PERIODIC == doctrine.AUDIT_SME_THRESHOLD_GWH_PERIODIC."""
    from doctrine.constants import AUDIT_SME_THRESHOLD_GWH_PERIODIC

    yaml_val = _yaml_value("AUDIT_SME_THRESHOLD_GWH_PERIODIC")
    assert yaml_val == AUDIT_SME_THRESHOLD_GWH_PERIODIC


# ─── SG_REG_CONST_04 : milestones DT ────────────────────────────────────────


def test_sg_reg_const_04_dt_milestones_match_doctrine():
    """YAML DT_MILESTONE_2030/40/50 cohérents avec doctrine.DT_MILESTONES."""
    from doctrine.constants import DT_MILESTONES

    # doctrine.DT_MILESTONES = {2030: -0.40, 2040: -0.50, 2050: -0.60}
    # YAML expose en pourcentage signé (-40.0, -50.0, -60.0)
    expected_yaml_values = {2030: -40.0, 2040: -50.0, 2050: -60.0}
    expected_py_values = {2030: -0.40, 2040: -0.50, 2050: -0.60}

    for year, py_val in DT_MILESTONES.items():
        assert py_val == expected_py_values[year], f"doctrine DT_MILESTONES[{year}]={py_val} drifté"

    for year, expected_yaml in expected_yaml_values.items():
        yaml_val = _yaml_value(f"DT_MILESTONE_{year}_PCT")
        assert yaml_val == expected_yaml, f"YAML DT_MILESTONE_{year}_PCT={yaml_val} ≠ {expected_yaml}"

    # Cohérence sémantique : YAML pct/100 == doctrine ratio
    for year in DT_MILESTONES:
        yaml_pct = _yaml_value(f"DT_MILESTONE_{year}_PCT")
        py_ratio = DT_MILESTONES[year]
        assert yaml_pct / 100 == py_ratio, (
            f"Divergence YAML pct vs doctrine ratio pour {year}: "
            f"YAML={yaml_pct}% (ratio={yaml_pct / 100}) vs doctrine={py_ratio}"
        )


# ─── SG_REG_CONST_05 : coefficient énergie primaire ─────────────────────────


def test_sg_reg_const_05_primary_energy_coef_elec_matches_doctrine():
    from doctrine.constants import PRIMARY_ENERGY_COEF_ELEC

    yaml_val = _yaml_value("PRIMARY_ENERGY_COEF_ELEC")
    assert yaml_val == PRIMARY_ENERGY_COEF_ELEC


def test_sg_reg_const_05_primary_energy_coef_gas_matches_doctrine():
    from doctrine.constants import PRIMARY_ENERGY_COEF_GAS

    yaml_val = _yaml_value("PRIMARY_ENERGY_COEF_GAS")
    assert yaml_val == PRIMARY_ENERGY_COEF_GAS
