"""Constantes inviolables PROMEOS Sol — Source unique de vérité.

Ces valeurs sont auditées contre la doctrine et la réglementation.
Toute modification doit être justifiée en PR avec source officielle.

Référence doctrinale : §10 (Transformer la complexité), §13 (info fiable).
Référence engineering : SKILL.md PROMEOS — Constantes canoniques.
"""

# ─── Facteurs CO₂ (kgCO2e/kWh) ─────────────────────────────────────────────
# Sources :
#   - ELEC + GAZ NATUREL : ADEME Base Empreinte V23.6
#   - GNL (gaz naturel liquéfié) : Arrêté 01/08/2025 NOR ATDL2430864A
#     (annexe VII — ajout après 5e ligne tableau facteurs CO₂ vecteurs énergie)
CO2_FACTOR_ELEC_KGCO2_PER_KWH = 0.052
CO2_FACTOR_GAS_KGCO2_PER_KWH = 0.227
CO2_FACTOR_GNL_KGCO2_PER_KWH = 0.238

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

# ─── BACS (Décret n°2020-887) ──────────────────────────────────────────────
BACS_PENALTY_EUR = 1500  # amende par site non conforme BACS

# ─── OPERAT / Décret Tertiaire déclaration ─────────────────────────────────
OPERAT_PENALTY_EUR = 1500  # amende par déclaration OPERAT manquante (Circulaire DGEC 2024)
# Deadline déclaration consommations 2025 (Arrêté Tertiaire 2024-DGEC)
OPERAT_DECLARATION_DEADLINE = "2026-09-30"

# ─── Readiness score — pondérations backend ────────────────────────────────
# Source unique : frontends doivent consommer ces pondérations via /api/cockpit.
# Doctrine §8.1 : zero business logic in frontend.
READINESS_WEIGHT_DATA = 0.30
READINESS_WEIGHT_CONFORMITY = 0.40
READINESS_WEIGHT_ACTIONS = 0.30

# ─── APER (Loi 2023-175 art. 40 + Décret 2022-1726) ────────────────────────
# Phase 19.A : remontée de la constante côté backend (audit Phase 17 cumulée
# P0-NEW-2 — pénalité hardcodée frontend AperPage.jsx ligne 195 violait
# "zero business logic in frontend"). Sanction 20 €/m²/an applicable à partir
# du 01/01/2028 si non engagement de solarisation des parkings >1 500 m².
APER_PENALTY_EUR_PER_M2_PER_YEAR = 20
APER_DEADLINE_DATE = "2028-01-01"
APER_PARKING_MIN_SURFACE_M2 = 1500

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

# Prix marginal énergie ETI tertiaire 2026 post-ARENH (médiane CRE T4 2025).
# Utilisé pour conversion gain MWh→€/an dans les heuristiques décisions/CEE.
# Source : Observatoire CRE T4 2025 § ETI tertiaire post-ARENH.
PRICE_ELEC_ETI_2026_EUR_PER_MWH = 130.0

# Ratio facture 2026 vs 2024 post-ARENH (médiane CRE T4 2025 sur ETI tertiaire).
# Référence sectorielle indicative pour communication CFO.
# Phase 13.A P0-4 (audit véracité 5.5/10) : NE PLUS utiliser pour calculer un
# delta portfolio — l'agrégation circulaire `total / 1.225` retournait toujours
# +22,5 % par construction. Désormais le delta portfolio est calculé en
# agrégeant les `baseline_2024.fourniture_ht_eur` réels per-site (cf
# `routes/purchase_cost_simulation.py::get_cost_simulation_portfolio`).
POST_ARENH_RATIO_2026_VS_2024 = 1.225  # +22.5% médiane CRE T4 2025 (référence sectorielle)

# Prix marché effacement industriel/tertiaire 2026 (NEBCO + AOFD blend CRE T4 2025).
# Utilisé pour estimation Flex potential eur_year sur _facts.
PRICE_FLEX_NEBCO_EUR_PER_MWH = 80.0

# Heuristique fallback Flex eur/site/an pour estimation indicative quand
# FlexAssessment absent (médiane sites tertiaires NEBCO 100 kW pilotable).
FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR = 4_200

# ─── Benchmarks ────────────────────────────────────────────────────────────
OID_OFFICE_BENCHMARK_KWHEF_PER_M2_YEAR = 146  # OID 2022, ~25 300 bâtiments

# ─── Cockpit dual Sol2 ─────────────────────────────────────────────────────
# Seuil minimum de dimensions activées avant que le levier "data_activation"
# devienne prioritaire dans le moteur de leviers V37 (cf. lever_engine_service
# + data_activation_service). Sprint refonte cockpit dual sol2 — 29/04/2026.
COCKPIT_ACTIVATION_THRESHOLD = 3
# Heuristique V1 : opportunité d'optimisation = 1 % du montant facturé total.
# À remplacer Phase 2 par calcul rigoureux (CEE BAT-TH-* + référentiels).
COCKPIT_OPTIM_RATE_V1 = 0.01

# ─── Trajectoire 2030 — courbe d'apprentissage Phase 30 ────────────────────
# Modèle 3 phases pour la projection de l'effet des actions BACS/audit/APER
# sur la trajectoire DT. Avant Phase 30 : effet "step function" appliqué
# brutalement à due_date (chute -45 % en 1 an, narrative cassée).
# Après : (1) engagement linéaire today→due_date capé à TRAJECTORY_LEARNING_RATIO_ENGAGEMENT,
# (2) ramp-up post-due jusqu'à TRAJECTORY_LEARNING_RATIO_RAMP_UP sur
# TRAJECTORY_LEARNING_MONTHS_RAMP_UP, (3) régime nominal 100 %.
# Source : retours terrain BACS classe A/B (paramétrage GTB + apprentissage
# occupants ≈ 1,5 an) + audits CEE BAT-TH-116 SAS Promeos.
# Ref : Sprint Retro Cockpit Dual Sol2 — Phase 30 (audit utilisateur 2026-05-01).
TRAJECTORY_LEARNING_RATIO_ENGAGEMENT = 0.20
TRAJECTORY_LEARNING_RATIO_RAMP_UP = 0.75
TRAJECTORY_LEARNING_MONTHS_RAMP_UP = 18

# ─── Garde-fous unitaires ──────────────────────────────────────────────────
# ⚠️  0.0569 est un tarif TURPE 7 HPH (€/kWh), PAS un facteur CO₂.
# ⚠️  Ne JAMAIS utiliser PRICE_FALLBACK pour 0.18 (ancienne valeur prohibée).

__all__ = [
    "CO2_FACTOR_ELEC_KGCO2_PER_KWH",
    "CO2_FACTOR_GAS_KGCO2_PER_KWH",
    "CO2_FACTOR_GNL_KGCO2_PER_KWH",
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
    "PRICE_ELEC_ETI_2026_EUR_PER_MWH",
    "POST_ARENH_RATIO_2026_VS_2024",
    "PRICE_FLEX_NEBCO_EUR_PER_MWH",
    "FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR",
    "OID_OFFICE_BENCHMARK_KWHEF_PER_M2_YEAR",
    "COCKPIT_ACTIVATION_THRESHOLD",
    "COCKPIT_OPTIM_RATE_V1",
    "TRAJECTORY_LEARNING_RATIO_ENGAGEMENT",
    "TRAJECTORY_LEARNING_RATIO_RAMP_UP",
    "TRAJECTORY_LEARNING_MONTHS_RAMP_UP",
    "BACS_PENALTY_EUR",
    "OPERAT_PENALTY_EUR",
    "TURPE_7_DATE_APPLICATION",
    "TURPE_6_DATE_FIN",
    "CANONICAL_FTA_CODES_TURPE_7",
]


# ═══════════════════════════════════════════════════════════════════════════
# Phase D-2 hotfix Tier 1 — TURPE 7 dates + codes FTA canoniques CRE
# ═══════════════════════════════════════════════════════════════════════════
# Audit cardinal :
#   docs/audits/AUDIT_TURPE7_DATES_2026_05_07.md (P0.1)
#   docs/audits/AUDIT_CODES_FTA_TURPE7_2026_05_07.md (P0.2)
# Source : CRE délibération n°2025-78 du 13/03/2025 (publiée CRE 20/03/2025).
# Mouvement tarifaire EXCEPTIONNEL au 1er février 2025 (communiqué CRE 12/12/2024)
# au lieu du calendrier annuel habituel du 1er août.

TURPE_7_DATE_APPLICATION = "2025-02-01"
"""Date d'application TURPE 7 HTA-BT (mouvement exceptionnel CRE).

⚠️ Phase D-2 cardinal : ne pas confondre avec date publication JO (mars 2025)
ni avec calendrier annuel CRE habituel (1/08).
"""

TURPE_6_DATE_FIN = "2025-01-31"
"""Dernier jour TURPE 6 — la transition est close par le mouvement tarifaire
exceptionnel TURPE 7 du 1er février 2025."""

CANONICAL_FTA_CODES_TURPE_7 = (
    "BTINFCU4",  # C5 BT≤36kVA — courte util. 4 postes (HPH/HCH/HPE/HCE)
    "BTINFMU4",  # C5 BT≤36kVA — moyenne util. 4 postes
    "BTSUPCU",  # C4 BT>36kVA — courte util.
    "BTSUPLU",  # C4 BT>36kVA — longue util.
    "HTACU5",  # C3/C2 HTA — courte util. 5 postes (PTE/HPH/HCH/HPE/HCE)
    "HTALU5",  # C3/C2 HTA — longue util. 5 postes
)
"""Codes FTA canoniques CRE TURPE 7 (medium-confidence — Enum exhaustif sera figé
Phase D-3 post parsing PDF délibération 2025-78).

Préfixe segment : BTINF (C5) / BTSUP (C4) / HTA (C3-C2) / HTB (C1).
Suffixe durée : CU (courte) / MU (moyenne BT only) / LU (longue).
Suffixe nb postes : 4 (BT) ou 5 (HTA + PTE).

⚠️ Codes Phase D-1 (`BT_HCH_PRO`, `BT_BASE_PRO`, `BT_PRO_LU`, `HTA_LU_BASE_4P`)
inventés non canoniques — corrigés Phase D-2.2.
"""
