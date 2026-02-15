"""
PROMEOS RegOps - Data Quality Specs
Per-regulation required/optional field specifications.
Same pattern as QUESTION_BANK in intake_engine.py.
"""

DATA_QUALITY_SPECS = {
    "tertiaire_operat": {
        "critical": ["tertiaire_area_m2", "operat_status", "annual_kwh_total"],
        "optional": ["is_multi_occupied", "naf_code", "surface_m2"],
    },
    "bacs": {
        "critical": ["cvc_power_kw", "bacs_systems_present"],
        "optional": ["has_bacs_attestation", "has_bacs_derogation", "bacs_scope_basis"],
        # Extended BACS v2 fields are resolved by bacs_engine DQ (not generic gate):
        # critical_ext: is_tertiary_non_residential, pc_date, cvc_inventory, cvc_architecture
        # important_ext: conso_2_ans_kwh, prix_kwh, cout_bacs_eur, aides_pct
    },
    "aper": {
        "critical": ["parking_area_m2", "roof_area_m2"],
        "optional": ["parking_type"],
    },
    "cee_p6": {
        "critical": [],
        "optional": ["naf_code", "annual_kwh_total"],
    },
}
