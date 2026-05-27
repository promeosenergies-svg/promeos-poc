"""
PROMEOS — Facteurs d'emission CO2e par vecteur energetique (ADEME).
Source unique ADEME pour Bilan GES, CSRD scope 2 location-based, comptabilite
carbone produit. Tous les services qui font du reporting carbone non-OPERAT
doivent importer depuis ici.

ATTENTION — separation OPERAT / ADEME (S1 cleanup #324, 2026-05-27) :
  Pour les calculs OPERAT / DEET (Decret Tertiaire) utiliser EXCLUSIVEMENT
  `config.operat_constants.EMISSION_FACTORS_OPERAT` (0.064 kgCO2/kWh elec).
  L'arrete 10/04/2020 Annexe VII impose ses propres facteurs. Melanger
  silencieusement ADEME et OPERAT est un bug.

Valeurs officielles :
  ADEME Base Empreinte V23.6 (juillet 2025)
  Electricite : 0.052 kgCO2e/kWh — mix moyen annuel France, ACV
  Gaz naturel : 0.227 kgCO2e/kWh — PCI, combustion + amont

Verification :
  Source 1 : ADEME Base Empreinte V23.6 (base-empreinte.ademe.fr) → 0.0520
  Source 2 : RTE Bilan Electrique 2024 → 21.7 gCO2eq/kWh direct, 30.2 cycle de vie
  Source 3 : ADEME Bilans GES (bilans-ges.ademe.fr) → coherent
  Arbitrage : 0.052 retenu (ADEME primaire, confirmee x3)
  Note : l'ancien 0.0569 n'est retrouve dans aucune source ADEME actuelle.

Usage:
    from config.emission_factors import get_emission_factor, get_emission_source
    factor = get_emission_factor("ELEC")   # 0.052
    factor = get_emission_factor("GAZ")    # 0.227
"""

# Phase 12.bis correction P0 mini-audit Phase 12 — version ADEME extraite
# en constante pour centraliser les références "ADEME Vxx" dans le codebase
# narrative (cf services/narrative/persona_context.py CSR_MANAGER focus_text).
# Quand ADEME publie une nouvelle version (V24+), changer ici met à jour
# automatiquement toutes les citations narrative.
EMISSION_FACTORS_VERSION: str = "V23.6"
EMISSION_FACTORS_DATE: str = "juillet 2025"  # Date publication ADEME

EMISSION_FACTORS = {
    "ELEC": {
        "kgco2e_per_kwh": 0.052,
        "source": f"ADEME Base Empreinte {EMISSION_FACTORS_VERSION} — electricite reseau France, mix moyen annuel, ACV",
        "year": 2024,
    },
    "GAZ": {
        "kgco2e_per_kwh": 0.227,
        "source": f"ADEME Base Empreinte {EMISSION_FACTORS_VERSION} — gaz naturel PCI, combustion + amont",
        "year": 2024,
    },
}


# ── Penalites reglementaires (Decret n2019-771 art. 9 + Code construction L174-1) ──
# Étape 9 P0-B : alias vers la SoT canonique doctrine/constants.py.
# Avant : BASE_PENALTY_EURO = 7_500 inline + DT_PENALTY_EUR doctrine = dual SoT
# silencieux (audit /simplify). Si la pénalité change (Loi de finances 2026),
# une seule constante doit évoluer. Le commentaire historique "Non-declaration
# OPERAT" était trompeur — c'est bien la pénalité DT non-conforme (OPERAT a sa
# propre constante OPERAT_PENALTY_EUR=1500 dans doctrine).
from doctrine.constants import (
    BACS_THRESHOLD_KW_EXISTING,
    BACS_THRESHOLD_KW_INITIAL,
    DT_PENALTY_AT_RISK_EUR,
    DT_PENALTY_EUR,
)

BASE_PENALTY_EURO = DT_PENALTY_EUR  # 7 500 € — DT site non conforme (alias)
A_RISQUE_PENALTY_RATIO = 0.5  # 50% pour sites a risque
A_RISQUE_PENALTY_EURO = DT_PENALTY_AT_RISK_EUR  # 3 750 € — alias canonique

# ── Seuils BACS (Decret n2020-887, Art. R175-2) ────────────────────────
# Phase L28.1a audit fix P1 — alias vers doctrine.constants SoT YAML lazy-load
# (avant : 290.0 / 70.0 hardcoded en parallèle de doctrine — drift silencieux).
BACS_SEUIL_HAUT = float(BACS_THRESHOLD_KW_INITIAL)  # 290.0 kW CVC, deadline 2025-01-01
BACS_SEUIL_BAS = float(BACS_THRESHOLD_KW_EXISTING)  # 70.0 kW CVC, deadline 2030-01-01


def get_emission_factor(energy_vector: str) -> float:
    """Retourne le facteur en kgCO2e/kWh. Fallback ELEC si vecteur inconnu."""
    entry = EMISSION_FACTORS.get(energy_vector.upper(), EMISSION_FACTORS["ELEC"])
    return entry["kgco2e_per_kwh"]


def get_emission_source(energy_vector: str) -> str:
    """Retourne le label source pour affichage."""
    entry = EMISSION_FACTORS.get(energy_vector.upper(), EMISSION_FACTORS["ELEC"])
    return entry["source"]
