"""Constantes inviolables PROMEOS Sol — Source unique de vérité.

Ces valeurs sont auditées contre la doctrine et la réglementation.
Toute modification doit être justifiée en PR avec source officielle.

Référence doctrinale : §10 (Transformer la complexité), §13 (info fiable).
Référence engineering : SKILL.md PROMEOS — Constantes canoniques.
"""

# ─── Facteurs CO₂ (kgCO2e/kWh) ─────────────────────────────────────────────
# Source : ADEME Base Empreinte V23.6
CO2_FACTOR_ELEC_KGCO2_PER_KWH = 0.052
CO2_FACTOR_GAS_KGCO2_PER_KWH = 0.227

# ─── Énergie primaire ──────────────────────────────────────────────────────
# Coefficient en vigueur depuis janvier 2026
PRIMARY_ENERGY_COEF_ELEC = 1.9
PRIMARY_ENERGY_COEF_GAS = 1.0

# ─── Décret Tertiaire (Décret n°2019-771) ──────────────────────────────────
# IMPORTANT : aucun jalon 2026. Les jalons réglementaires sont 2030/2040/2050.
DT_MILESTONES = {2030: -0.40, 2040: -0.50, 2050: -0.60}
DT_PENALTY_EUR = 7500
DT_PENALTY_AT_RISK_EUR = 3750
DT_REF_YEAR_DEFAULT = 2020  # année de référence par défaut pour la baseline

# ─── NEBCO (depuis 01/09/2025) ─────────────────────────────────────────────
NEBCO_THRESHOLD_KW_PER_STEP = 100
NEBCO_NOTIFICATION_DEADLINE_HOUR = "09:30"  # J-1
NEBCO_ACTIVATION_END_HOUR = "22:00"  # J

# ─── Accises (février 2026+, JORFTEXT000053407616) ─────────────────────────
ACCISE_ELEC_T1_EUR_PER_MWH = 30.85
ACCISE_ELEC_T2_EUR_PER_MWH = 26.58
ACCISE_GAS_EUR_PER_MWH = 10.73

# ─── Audit SMÉ ─────────────────────────────────────────────────────────────
AUDIT_SME_THRESHOLD_GWH_PERIODIC = 2.75  # audit obligatoire tous les 4 ans
AUDIT_SME_THRESHOLD_GWH_ISO50001 = 23.6  # ISO 50001 obligatoire
AUDIT_SME_DEADLINE_DATE = "2026-10-11"

# ─── Pondérations RegOps ───────────────────────────────────────────────────
REGOPS_WEIGHTS_AUDIT_APPLICABLE = {"DT": 0.39, "BACS": 0.28, "APER": 0.17, "AUDIT": 0.16}
REGOPS_WEIGHTS_DEFAULT = {"DT": 0.45, "BACS": 0.30, "APER": 0.25}

# ─── Prix énergie ──────────────────────────────────────────────────────────
# Fallback pour calculs en absence de contrat — JAMAIS 0.18
PRICE_FALLBACK_EUR_PER_KWH = 0.068

# ─── Benchmarks ────────────────────────────────────────────────────────────
OID_OFFICE_BENCHMARK_KWHEF_PER_M2_YEAR = 146  # OID 2022, ~25 300 bâtiments

# ─── Garde-fous unitaires ──────────────────────────────────────────────────
# ⚠️  0.0569 est un tarif TURPE 7 HPH (€/kWh), PAS un facteur CO₂.
# ⚠️  Ne JAMAIS utiliser PRICE_FALLBACK pour 0.18 (ancienne valeur prohibée).

__all__ = [
    "CO2_FACTOR_ELEC_KGCO2_PER_KWH",
    "CO2_FACTOR_GAS_KGCO2_PER_KWH",
    "PRIMARY_ENERGY_COEF_ELEC",
    "PRIMARY_ENERGY_COEF_GAS",
    "DT_MILESTONES",
    "DT_PENALTY_EUR",
    "DT_PENALTY_AT_RISK_EUR",
    "DT_REF_YEAR_DEFAULT",
    "NEBCO_THRESHOLD_KW_PER_STEP",
    "NEBCO_NOTIFICATION_DEADLINE_HOUR",
    "NEBCO_ACTIVATION_END_HOUR",
    "ACCISE_ELEC_T1_EUR_PER_MWH",
    "ACCISE_ELEC_T2_EUR_PER_MWH",
    "ACCISE_GAS_EUR_PER_MWH",
    "AUDIT_SME_THRESHOLD_GWH_PERIODIC",
    "AUDIT_SME_THRESHOLD_GWH_ISO50001",
    "AUDIT_SME_DEADLINE_DATE",
    "REGOPS_WEIGHTS_AUDIT_APPLICABLE",
    "REGOPS_WEIGHTS_DEFAULT",
    "PRICE_FALLBACK_EUR_PER_KWH",
    "OID_OFFICE_BENCHMARK_KWHEF_PER_M2_YEAR",
]
