"""Constantes inviolables PROMEOS Sol — Source unique de vérité.

Ces valeurs sont auditées contre la doctrine et la réglementation.
Toute modification doit être justifiée en PR avec source officielle.

Référence doctrinale : §10 (Transformer la complexité), §13 (info fiable).
Référence engineering : SKILL.md PROMEOS — Constantes canoniques.
"""

# Phase L20.3 — helper defensive lazy-load déplacé en tête de fichier (avant
# Phase L20 : défini ligne ~145, posait problème pour migrer PRICE_FALLBACK
# ligne 132 qui en avait besoin avant sa définition).
import logging as _logging

from config.regulatory_sources_loader import get_term_value as _get_term_value

_logger = _logging.getLogger(__name__)


def _load_yaml_or_fallback(key: str, fallback: float) -> float:
    """Phase L16.4 — Defensive lazy-load avec fallback hardcoded (numeric).

    Évite crash module-load si YAML key manquante (CI fresh checkout, test
    isolation, etc.). Logue warning explicite pour détection drift YAML/code.
    """
    try:
        return float(_get_term_value(key))
    except (KeyError, ValueError, FileNotFoundError, TypeError) as e:
        _logger.warning(
            "doctrine.constants YAML lookup failed for %s (%s) — fallback to hardcoded %s",
            key,
            type(e).__name__,
            fallback,
        )
        return fallback


def _load_yaml_str_or_fallback(key: str, fallback: str) -> str:
    """Phase L24.2 — Variante string du helper defensive lazy-load.

    Pour les valeurs YAML non-numériques (dates ISO, references, labels).
    Pattern aligné `_load_yaml_or_fallback` (logging warning sur drift/missing).
    """
    try:
        value = _get_term_value(key)
        return str(value) if value is not None else fallback
    except (KeyError, ValueError, FileNotFoundError, TypeError) as e:
        _logger.warning(
            "doctrine.constants YAML str lookup failed for %s (%s) — fallback to hardcoded %s",
            key,
            type(e).__name__,
            fallback,
        )
        return fallback


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

# ─── BACS (Décret n°2020-887 + n°2025-1343) ────────────────────────────────
# Phase D-3 Tier 0 : sources documentées dans `backend/config/sources_reglementaires.yaml` :
#   - BACS_THRESHOLD_KW_2025 (290 kW initial — Décret 2020-887 art. R175-3)
#   - BACS_THRESHOLD_KW_2030 (70 kW abaissé — Décret 2025-1343 art. 1)
#   - BACS_DEADLINE_DATE (2027-01-01 équipement BACS)
#   - COMPLIANCE_BACS_PENALTY_EUR (1500 EUR/an/site — Décret 2020-887 art. R175-7)
# Doublon valeur 1500€ avec OPERAT_PENALTY_EUR : sources distinctes confirmées
# (BACS = art. R175-7 vs OPERAT = Circulaire DGEC 2024 + Décret 2019-771 art. 6).
BACS_PENALTY_EUR = (
    1500  # amende par site non conforme BACS — voir sources_reglementaires.yaml:COMPLIANCE_BACS_PENALTY_EUR
)
BACS_THRESHOLD_KW_INITIAL = 290  # seuil BACS bâtiments neufs Décret 2020-887 (en vigueur depuis 01/01/2025)
# Phase L24.2 audit fix P1 — lazy-load YAML SoT (avant : hardcoded production-path
# consommé par cascade_bacs_service.py:60 — drift silencieux scoring BACS si décret
# futur modifie le seuil). Mapping nom Python EXISTING → YAML 2030.
BACS_THRESHOLD_KW_EXISTING: int = int(
    _load_yaml_or_fallback("BACS_THRESHOLD_KW_2030", fallback=70)
)  # seuil BACS bâtiments existants Décret 2025-1343 (01/01/2030)
BACS_DEADLINE_EXISTING = "2030-01-01"  # deadline équipement BACS bâtiments existants >70 kW

# ─── OPERAT / Décret Tertiaire déclaration ─────────────────────────────────
# Phase D-3 Tier 0 : sources documentées dans `backend/config/sources_reglementaires.yaml` :
#   - COMPLIANCE_OPERAT_PENALTY_EUR (Circulaire DGEC 2024 + Décret 2019-771 art. 6)
#   - OPERAT_DECLARATION_DEADLINE (date butoir 30/09 annuelle, source ADEME OPERAT)
# Annexe I OPERAT (Arrêté 10/04/2020 NOR LOGL2005904A) = **426 sous-catégories**
# organisées en ~9 grandes familles (PAS "9 typologies" comme parfois cité par
# raccourci). Granularité réelle = 426 lignes — voir backend/config/operat_valeurs_absolues.yaml.
OPERAT_PENALTY_EUR = (
    1500  # amende par déclaration OPERAT manquante — voir sources_reglementaires.yaml:COMPLIANCE_OPERAT_PENALTY_EUR
)
# Deadline déclaration consommations N-1 = 30 septembre N (ADEME OPERAT — annuelle).
# Phase D-4 Tier 4+ P2 fix audit code-reviewer : helper dynamique évite hardcode 2026-only.
OPERAT_DECLARATION_DEADLINE = "2026-09-30"  # legacy alias (cohérent runtime à figer Phase E)
OPERAT_DECLARATION_DEADLINE_MONTH_DAY = "09-30"  # SoT cardinal — récurrence annuelle


def compute_operat_deadline(year: int) -> str:
    """Phase D-4 Tier 4+ : retourne la deadline OPERAT annuelle pour année N (déclaration N-1).

    Source : ADEME OPERAT — deadline 30 septembre N pour consommations N-1.
    Pattern Pilier 13 ADR-016 (constante réglementaire récurrente vs hardcode unique).

    Returns:
        Date ISO format YYYY-09-30.
    """
    return f"{year}-{OPERAT_DECLARATION_DEADLINE_MONTH_DAY}"


OPERAT_ANNEXE_I_SOUS_CATEGORIES_COUNT = (
    426  # Arrêté 10/04/2020 NOR LOGL2005904A — granularité réelle (9 grandes familles)
)

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
#
# Phase D-3 Tier 0 (audit réglementaire 2026-05-07) : sources documentées dans
# `backend/config/sources_reglementaires.yaml` clés APER_THRESHOLD_M2_SMALL/LARGE,
# APER_DEADLINE_SMALL/LARGE, APER_SOLAR_RATIO_PCT, APER_PENALTY_EUR_PER_M2_PER_YEAR.
# ⚠️ Cohérence chronologique Décret 2022-1726 vs Loi 2023-175 à VÉRIFIER Phase D-4
# (escalade humaine — voir RAPPORT_ESCALADE_HUMAINE_SOURCES_2026_05_07.md SOURCE 11).
# 2 échéances distinctes (cardinal P0-REG-002 audit) :
#   - parkings >10 000 m² (LARGE) : 01/07/2026 (échéance imminente)
#   - parkings 1500-10 000 m² (SMALL) : 01/07/2028 (cible PROMEOS mid-market)
APER_PENALTY_EUR_PER_M2_PER_YEAR = 20
APER_DEADLINE_DATE = "2028-01-01"  # legacy alias — préfère APER_DEADLINE_SMALL_PARKING_DATE
APER_DEADLINE_SMALL_PARKING_DATE = (
    "2028-07-01"  # parkings 1500-10000 m² — sources_reglementaires.yaml:APER_DEADLINE_SMALL
)
APER_DEADLINE_LARGE_PARKING_DATE = "2026-07-01"  # parkings >10000 m² — sources_reglementaires.yaml:APER_DEADLINE_LARGE
APER_PARKING_MIN_SURFACE_M2 = 1500  # seuil SMALL (Loi APER art. 40)
APER_PARKING_LARGE_SURFACE_M2 = 10000  # seuil LARGE (Loi APER art. 40 II)
APER_SOLAR_RATIO_PCT = 50.0  # taux minimum solarisation parking (Loi APER art. 40)

# ─── NEBCO (depuis 01/09/2025) ─────────────────────────────────────────────
NEBCO_THRESHOLD_KW_PER_STEP = 100
NEBCO_NOTIFICATION_DEADLINE_HOUR = "09:30"  # J-1
NEBCO_ACTIVATION_END_HOUR = "22:00"  # J

# ─── Accises (février 2026+, JORFTEXT000053407616) ─────────────────────────
# Taux selon catégorie AcciseCategorieElec (matrice v1 §4.6.B#16 ADR-D-05)
ACCISE_ELEC_T1_EUR_PER_MWH = 30.85  # MENAGES_ASSIMILES
ACCISE_ELEC_T2_EUR_PER_MWH = 26.58  # PME
# Phase L24.2 audit fix P1 — lazy-load YAML SoT (avant : hardcoded SANS clé YAML →
# drift silencieux garanti si LFI modifie taux HP). Phase L24.2 a créé la clé YAML
# `ACCISE_ELEC_HP_EUR_PER_MWH = 5.71` dans sources_reglementaires.yaml.
ACCISE_ELEC_HP_EUR_PER_MWH: float = _load_yaml_or_fallback(
    "ACCISE_ELEC_HP_EUR_PER_MWH", fallback=5.71
)  # HAUTE_PUISSANCE (>10 GWh/an industriel)
ACCISE_GAS_EUR_PER_MWH = 10.73

# ─── Audit SMÉ ─────────────────────────────────────────────────────────────
AUDIT_SME_THRESHOLD_GWH_PERIODIC = 2.75  # audit obligatoire tous les 4 ans
AUDIT_SME_THRESHOLD_GWH_ISO50001 = 23.6  # ISO 50001 obligatoire
# Phase L24.2 audit fix P1 — lazy-load YAML SoT (avant : hardcoded production-path
# consommé par persona_dashboard_service.py:189 — drift silencieux dashboard si
# YAML corrigé). Mapping nom Python AUDIT_SME_DEADLINE_DATE → YAML AUDIT_SME_DEADLINE_FIRST_AUDIT.
AUDIT_SME_DEADLINE_DATE: str = _load_yaml_str_or_fallback("AUDIT_SME_DEADLINE_FIRST_AUDIT", fallback="2026-10-11")

# ─── Pondérations RegOps ───────────────────────────────────────────────────
REGOPS_WEIGHTS_AUDIT_APPLICABLE = {"DT": 0.39, "BACS": 0.28, "APER": 0.17, "AUDIT": 0.16}
REGOPS_WEIGHTS_DEFAULT = {"DT": 0.45, "BACS": 0.30, "APER": 0.25}

# ─── Prix énergie ──────────────────────────────────────────────────────────
# Fallback pour calculs en absence de contrat — JAMAIS 0.18.
# Phase L20.3 audit fix P1 — lazy-load YAML SoT (avant : hardcoded dupliqué
# avec sources_reglementaires.yaml:296 = 0.068 → drift risk identique
# PRICE_ELEC_ETI Phase L15.1).
PRICE_FALLBACK_EUR_PER_KWH: float = _load_yaml_or_fallback("PRICE_FALLBACK_EUR_PER_KWH", fallback=0.068)

# Prix marginal énergie ETI tertiaire 2026 post-ARENH (médiane CRE T4 2025).
# Utilisé pour conversion gain MWh→€/an dans les heuristiques décisions/CEE.
# Phase L15.1 audit fix P1 — lazy-load YAML SoT (avant : valeur hardcoded 130.0
# DUPLIQUÉE entre doctrine/constants.py et sources_reglementaires.yaml).
# Phase L16.4 audit fix P1 — defensive fallback via _load_yaml_or_fallback
# (helper déplacé en tête fichier Phase L20.3).
# NOTE : valeur figée au process start. ParameterStore live-reload n'affecte
# pas cette constante. Utiliser get_term_value() directement pour valeur fresh.


PRICE_ELEC_ETI_2026_EUR_PER_MWH: float = _load_yaml_or_fallback("PRICE_ELEC_ETI_2026_EUR_PER_MWH", fallback=130.0)

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
# Phase L20.3 audit fix P1 — lazy-load YAML SoT (avant : hardcoded dupliqué
# avec sources_reglementaires.yaml:309 → drift risk identique L15.1).
PRICE_FLEX_NEBCO_EUR_PER_MWH: float = _load_yaml_or_fallback("PRICE_FLEX_NEBCO_EUR_PER_MWH", fallback=80.0)

# Heuristique fallback Flex eur/site/an pour estimation indicative quand
# FlexAssessment absent (médiane sites tertiaires NEBCO 100 kW pilotable).
# Phase L20.3 audit fix P1 — lazy-load YAML SoT (avant : hardcoded dupliqué
# avec sources_reglementaires.yaml:892 → drift risk identique L15.1).
FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR: float = _load_yaml_or_fallback(
    "FLEX_HEURISTIC_EUR_PER_SITE_PER_YEAR", fallback=4200.0
)

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
    "ACCISE_ELEC_HP_EUR_PER_MWH",
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
    "BACS_THRESHOLD_KW_INITIAL",
    "BACS_THRESHOLD_KW_EXISTING",
    "BACS_DEADLINE_EXISTING",
    "OPERAT_ANNEXE_I_SOUS_CATEGORIES_COUNT",
    "APER_DEADLINE_SMALL_PARKING_DATE",
    "APER_DEADLINE_LARGE_PARKING_DATE",
    "APER_PARKING_LARGE_SURFACE_M2",
    "APER_SOLAR_RATIO_PCT",
    "VNU_DATE_APPLICATION",
    "VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH",
    "VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH",
    "VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH",
    "CDC_PAS_MIN_MINUTES",
    "CDC_PAS_MAX_MINUTES",
    "PCS_GAZ_MIN_KWH_NM3",
    "PCS_GAZ_MAX_KWH_NM3",
    "OPERAT_DECLARATION_DEADLINE_MONTH_DAY",
    "compute_operat_deadline",
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


# ═══════════════════════════════════════════════════════════════════════════
# Phase D-3 Tier 0 RÉGLEMENTAIRE — VNU post-ARENH (audit cardinal 2026-05-07)
# ═══════════════════════════════════════════════════════════════════════════
# Source : `backend/config/sources_reglementaires.yaml` clés VNU_TARIF_UNITAIRE_2026_*,
# VNU_SEUIL_ACTIVATION_PRIX_BAS/HAUT_*. status="pending_source_verification" + confidence="low".
# Cross-check KB `reference_regulatory_landscape_2026_2050.md` confirme :
#   "VNU (Versement Nucléaire Universel) : tarif unitaire de minoration = 0 pour 2026"
#
# Le mécanisme VNU est ACTIF au 01/01/2026 (post-ARENH) mais NON-FACTURANT en 2026
# (tarif unitaire = 0). Les seuils 78/110 EUR/MWh proviennent de cost_simulator_2026.py
# (cohérent accord EDF-État 14/11/2023). Référence Décret 2026-55 + CRE délib 2026-52
# à VÉRIFIER Phase D-4 (escalade humaine — RAPPORT_ESCALADE_HUMAINE_SOURCES_2026_05_07.md).

VNU_DATE_APPLICATION = "2026-01-01"
"""Date d'application VNU post-ARENH (Décret 2026-55 + CRE délib 2026-52 — à confirmer Phase D-4)."""

VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH = 0.0
"""Tarif unitaire VNU 2026 = 0 EUR/MWh (status dormant — KB confirmé `reference_regulatory_landscape_2026_2050.md`)."""

VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH = 78.0
"""Seuil bas activation VNU si prix marché < seuil (CRE 2026-52 — pending verification)."""

VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH = 110.0
"""Seuil haut activation VNU côté upside fournisseur (CRE 2026-52 — pending verification)."""


# ═══════════════════════════════════════════════════════════════════════════
# Phase D-4 Tier 2 — Bornes range techniques DP gaz/élec (audit P1-C code-reviewer)
# ═══════════════════════════════════════════════════════════════════════════
# Source : Enedis ERDF SGED CDC 30/10 min (matrice v1 §4.6.B#8) +
#          GRTgaz/GRDF référentiel gaz naturel FR (matrice v1 §4.6.C#13).

CDC_PAS_MIN_MINUTES = 1
"""Pas temporel CDC Enedis minimum (1 min — granularité fine non standard)."""

CDC_PAS_MAX_MINUTES = 60
"""Pas temporel CDC Enedis maximum (60 min — relevé horaire standard).
Valeurs courantes : 10 (CDC fine), 30 (CDC standard 1/2h), 60 (horaire)."""

PCS_GAZ_MIN_KWH_NM3 = 9.0
"""PCS gaz minimum plausible (kWh/Nm³). Borne basse pour DOM/qualité dégradée."""

PCS_GAZ_MAX_KWH_NM3 = 13.0
"""PCS gaz maximum plausible (kWh/Nm³). Gaz naturel FR métropole typique 10.0-12.5."""
