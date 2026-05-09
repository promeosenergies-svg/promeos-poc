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


def test_sg_reg_const_01_co2_factor_gaz_matches_doctrine_constants():
    """Phase L27.1 audit fix P1 — Ferme la chaîne mirror FR/EN.

    Le mapping `CO2_FACTOR_GAZ_NATUREL_KGCO2_PER_KWH` (YAML, convention FR) →
    `CO2_FACTOR_GAS_KGCO2_PER_KWH` (Python, convention EN) est implicite via
    le lazy-load Phase L26.1. Ce test rend la traçabilité explicite et
    empêche tout drift de mapping silencieux (renommage YAML ou Python).
    """
    from doctrine.constants import CO2_FACTOR_GAS_KGCO2_PER_KWH

    yaml_val = _yaml_value("CO2_FACTOR_GAZ_NATUREL_KGCO2_PER_KWH")
    assert yaml_val == CO2_FACTOR_GAS_KGCO2_PER_KWH, (
        f"Divergence mapping FR/EN CO2_GAZ : YAML CO2_FACTOR_GAZ_NATUREL_KGCO2_PER_KWH={yaml_val} "
        f"vs doctrine.constants.CO2_FACTOR_GAS_KGCO2_PER_KWH={CO2_FACTOR_GAS_KGCO2_PER_KWH}. "
        f"Mapping FR(YAML)→EN(Python) cardinal — synchroniser les 2 sources."
    )


def test_sg_reg_const_01_co2_factor_elec_matches_doctrine_constants():
    """Phase L27.1 audit fix P1 — Ferme la chaîne mirror CO2 elec doctrine."""
    from doctrine.constants import CO2_FACTOR_ELEC_KGCO2_PER_KWH

    yaml_val = _yaml_value("CO2_FACTOR_ELEC_KGCO2_PER_KWH")
    assert yaml_val == CO2_FACTOR_ELEC_KGCO2_PER_KWH, (
        f"Divergence CO2 elec doctrine : YAML={yaml_val} vs "
        f"doctrine.constants.CO2_FACTOR_ELEC_KGCO2_PER_KWH={CO2_FACTOR_ELEC_KGCO2_PER_KWH}."
    )


def test_sg_reg_const_01_co2_factor_gnl_matches_doctrine_constants():
    """Phase L27.1 audit fix P1 — Ferme la chaîne mirror CO2 GNL doctrine."""
    from doctrine.constants import CO2_FACTOR_GNL_KGCO2_PER_KWH

    yaml_val = _yaml_value("CO2_FACTOR_GNL_KGCO2_PER_KWH")
    assert yaml_val == CO2_FACTOR_GNL_KGCO2_PER_KWH, (
        f"Divergence CO2 GNL doctrine : YAML={yaml_val} vs "
        f"doctrine.constants.CO2_FACTOR_GNL_KGCO2_PER_KWH={CO2_FACTOR_GNL_KGCO2_PER_KWH}."
    )


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


def test_sg_reg_const_06_accise_elec_t1_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : ACCISE_ELEC_T1 cohérent YAML ↔ doctrine.constants."""
    from doctrine import constants as DC

    yaml_val = _yaml_value("ACCISE_ELEC_T1_EUR_PER_MWH")
    py_val = DC.ACCISE_ELEC_T1_EUR_PER_MWH
    assert yaml_val == py_val, (
        f"Divergence ACCISE_ELEC_T1 : YAML={yaml_val} vs doctrine.constants.py={py_val}. "
        f"Source LFI 2025 — synchroniser les 2 sources."
    )


def test_sg_reg_const_06_accise_elec_t2_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : ACCISE_ELEC_T2 cohérent YAML ↔ doctrine.constants."""
    from doctrine import constants as DC

    yaml_val = _yaml_value("ACCISE_ELEC_T2_EUR_PER_MWH")
    py_val = DC.ACCISE_ELEC_T2_EUR_PER_MWH
    assert yaml_val == py_val, (
        f"Divergence ACCISE_ELEC_T2 : YAML={yaml_val} vs doctrine.constants.py={py_val}. "
        f"Source LFI 2025 — synchroniser les 2 sources."
    )


def test_sg_reg_const_07_regops_weight_dt_default_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : REGOPS_WEIGHT_DT_DEFAULT cohérent YAML ↔ doctrine."""
    from doctrine import constants as DC

    yaml_val = _yaml_value("REGOPS_WEIGHT_DT_DEFAULT")
    py_val = DC.REGOPS_WEIGHTS_DEFAULT["DT"]
    assert yaml_val == py_val, (
        f"Divergence REGOPS_WEIGHT_DT_DEFAULT : YAML={yaml_val} vs "
        f"doctrine.constants.REGOPS_WEIGHTS_DEFAULT['DT']={py_val}."
    )


def test_sg_reg_const_07_regops_weight_bacs_default_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : REGOPS_WEIGHT_BACS_DEFAULT cohérent YAML ↔ doctrine."""
    from doctrine import constants as DC

    yaml_val = _yaml_value("REGOPS_WEIGHT_BACS_DEFAULT")
    py_val = DC.REGOPS_WEIGHTS_DEFAULT["BACS"]
    assert yaml_val == py_val, (
        f"Divergence REGOPS_WEIGHT_BACS_DEFAULT : YAML={yaml_val} vs "
        f"doctrine.constants.REGOPS_WEIGHTS_DEFAULT['BACS']={py_val}."
    )


def test_sg_reg_const_07_regops_weight_aper_default_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : REGOPS_WEIGHT_APER_DEFAULT cohérent YAML ↔ doctrine."""
    from doctrine import constants as DC

    yaml_val = _yaml_value("REGOPS_WEIGHT_APER_DEFAULT")
    py_val = DC.REGOPS_WEIGHTS_DEFAULT["APER"]
    assert yaml_val == py_val, (
        f"Divergence REGOPS_WEIGHT_APER_DEFAULT : YAML={yaml_val} vs "
        f"doctrine.constants.REGOPS_WEIGHTS_DEFAULT['APER']={py_val}."
    )


def test_sg_reg_const_08_readiness_weight_data_pct_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : READINESS_WEIGHT_DATA cohérent YAML (en %) ↔ doctrine (en décimal).

    Conversion cardinal : YAML PCT (30.0) = doctrine décimal (0.30) × 100.
    """
    from doctrine import constants as DC

    yaml_pct = _yaml_value("READINESS_WEIGHT_DATA_PCT")
    py_decimal = DC.READINESS_WEIGHT_DATA
    expected_pct = py_decimal * 100
    assert yaml_pct == expected_pct, (
        f"Divergence READINESS_WEIGHT_DATA : YAML={yaml_pct}% vs "
        f"doctrine.constants.READINESS_WEIGHT_DATA × 100 = {expected_pct}%."
    )


def test_sg_reg_const_08_readiness_weight_conformity_pct_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : READINESS_WEIGHT_CONFORMITY cohérent."""
    from doctrine import constants as DC

    yaml_pct = _yaml_value("READINESS_WEIGHT_CONFORMITY_PCT")
    expected_pct = DC.READINESS_WEIGHT_CONFORMITY * 100
    assert yaml_pct == expected_pct, (
        f"Divergence READINESS_WEIGHT_CONFORMITY : YAML={yaml_pct}% vs doctrine.constants × 100 = {expected_pct}%."
    )


def test_sg_reg_const_08_readiness_weight_actions_pct_matches_doctrine():
    """Sprint C-5 Phase 5.4 — Extension SG : READINESS_WEIGHT_ACTIONS cohérent."""
    from doctrine import constants as DC

    yaml_pct = _yaml_value("READINESS_WEIGHT_ACTIONS_PCT")
    expected_pct = DC.READINESS_WEIGHT_ACTIONS * 100
    assert yaml_pct == expected_pct, (
        f"Divergence READINESS_WEIGHT_ACTIONS : YAML={yaml_pct}% vs doctrine.constants × 100 = {expected_pct}%."
    )


def test_sg_reg_const_05_primary_energy_coef_gas_matches_doctrine():
    from doctrine.constants import PRIMARY_ENERGY_COEF_GAS

    yaml_val = _yaml_value("PRIMARY_ENERGY_COEF_GAS")
    assert yaml_val == PRIMARY_ENERGY_COEF_GAS


# ─── SG_REG_CONST_09 : Phase L28.1a — VNU + APER + miroirs L26 manquants ────


def test_sg_reg_const_09_vnu_seuil_haut_matches_doctrine():
    """Phase L28.1a audit fix P1 — Ferme la chaîne mirror VNU_SEUIL_HAUT."""
    from doctrine.constants import VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH

    yaml_val = _yaml_value("VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH")
    assert yaml_val == VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH, (
        f"Divergence VNU_SEUIL_HAUT : YAML={yaml_val} vs doctrine={VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH}"
    )


def test_sg_reg_const_09_vnu_tarif_unitaire_matches_doctrine():
    """Phase L28.1a audit fix P1 — Ferme la chaîne mirror VNU_TARIF_UNITAIRE."""
    from doctrine.constants import VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH

    yaml_val = _yaml_value("VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH")
    assert yaml_val == VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH, (
        f"Divergence VNU_TARIF : YAML={yaml_val} vs doctrine={VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH}"
    )


def test_sg_reg_const_09_aper_parking_min_matches_doctrine():
    """Phase L28.1a audit fix P1 — Ferme la chaîne mirror APER_PARKING_MIN (mapping THRESHOLD_M2_SMALL → MIN_SURFACE_M2)."""
    from doctrine.constants import APER_PARKING_MIN_SURFACE_M2

    yaml_val = _yaml_value("APER_THRESHOLD_M2_SMALL")
    assert yaml_val == APER_PARKING_MIN_SURFACE_M2, (
        f"Divergence APER_PARKING_MIN : YAML APER_THRESHOLD_M2_SMALL={yaml_val} vs "
        f"doctrine.APER_PARKING_MIN_SURFACE_M2={APER_PARKING_MIN_SURFACE_M2}"
    )


def test_sg_reg_const_09_aper_parking_large_matches_doctrine():
    """Phase L28.1a audit fix P1 — Ferme la chaîne mirror APER_PARKING_LARGE."""
    from doctrine.constants import APER_PARKING_LARGE_SURFACE_M2

    yaml_val = _yaml_value("APER_THRESHOLD_M2_LARGE")
    assert yaml_val == APER_PARKING_LARGE_SURFACE_M2, (
        f"Divergence APER_PARKING_LARGE : YAML APER_THRESHOLD_M2_LARGE={yaml_val} vs "
        f"doctrine.APER_PARKING_LARGE_SURFACE_M2={APER_PARKING_LARGE_SURFACE_M2}"
    )


def test_sg_reg_const_09_aper_solar_ratio_matches_doctrine():
    """Phase L28.1a audit fix P1 — Ferme la chaîne mirror APER_SOLAR_RATIO_PCT."""
    from doctrine.constants import APER_SOLAR_RATIO_PCT

    yaml_val = _yaml_value("APER_SOLAR_RATIO_PCT")
    assert yaml_val == APER_SOLAR_RATIO_PCT, (
        f"Divergence APER_SOLAR_RATIO : YAML={yaml_val} vs doctrine={APER_SOLAR_RATIO_PCT}"
    )


def test_sg_reg_const_09_aper_penalty_matches_doctrine():
    """Phase L28.1a audit fix P1 — Ferme la chaîne mirror APER_PENALTY."""
    from doctrine.constants import APER_PENALTY_EUR_PER_M2_PER_YEAR

    yaml_val = _yaml_value("APER_PENALTY_EUR_PER_M2_PER_YEAR")
    assert yaml_val == APER_PENALTY_EUR_PER_M2_PER_YEAR, (
        f"Divergence APER_PENALTY : YAML={yaml_val} vs doctrine={APER_PENALTY_EUR_PER_M2_PER_YEAR}"
    )
