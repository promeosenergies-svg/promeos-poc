"""Vérifie que les constantes inviolables ont leurs valeurs attendues."""
from doctrine import constants as C


def test_co2_elec_factor():
    assert C.CO2_FACTOR_ELEC_KGCO2_PER_KWH == 0.052


def test_co2_gas_factor():
    assert C.CO2_FACTOR_GAS_KGCO2_PER_KWH == 0.227


def test_primary_energy_elec():
    assert C.PRIMARY_ENERGY_COEF_ELEC == 1.9


def test_dt_milestones_no_2026():
    assert 2026 not in C.DT_MILESTONES, "Aucun jalon DT en 2026 — règle doctrinale"
    assert C.DT_MILESTONES == {2030: -0.40, 2040: -0.50, 2050: -0.60}


def test_dt_penalties():
    assert C.DT_PENALTY_EUR == 7500
    assert C.DT_PENALTY_AT_RISK_EUR == 3750


def test_nebco_threshold():
    assert C.NEBCO_THRESHOLD_KW_PER_STEP == 100


def test_accises_feb_2026():
    assert C.ACCISE_ELEC_T1_EUR_PER_MWH == 30.85
    assert C.ACCISE_ELEC_T2_EUR_PER_MWH == 26.58
    assert C.ACCISE_GAS_EUR_PER_MWH == 10.73


def test_price_fallback_not_018():
    assert C.PRICE_FALLBACK_EUR_PER_KWH == 0.068
    assert C.PRICE_FALLBACK_EUR_PER_KWH != 0.18, "0.18 est une ancienne valeur prohibée"


def test_audit_sme_thresholds():
    assert C.AUDIT_SME_THRESHOLD_GWH_PERIODIC == 2.75
    assert C.AUDIT_SME_THRESHOLD_GWH_ISO50001 == 23.6
