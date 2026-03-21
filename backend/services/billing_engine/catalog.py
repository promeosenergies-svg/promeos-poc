"""
PROMEOS Billing Engine — Rate Catalog interface.
Single source of truth for all regulated rates.
Every rate is versioned, sourced, and traceable.

IMPORTANT: The rates below are structured placeholders based on TURPE 7
CRE deliberation structure. They MUST be verified against the official
CRE publication before any production use. Rates marked [TO_VERIFY]
need cross-checking with the actual CRE tariff tables.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import RateSource, TariffOption, TariffSegment

logger = logging.getLogger(__name__)

# ─── TURPE 7 Rate Structure ──────────────────────────────────────────────────
# Source: CRE délibération TURPE 7 HTA-BT (structure)
# WARNING: rates are indicative and must be verified against official CRE tables.
#
# For C4 BT, TURPE has 5 components:
#   1. Composante de gestion (EUR/an, fixe)
#   2. Composante de comptage (EUR/an, fixe, dépend du type de compteur)
#   3. Composante de soutirage fixe (EUR/kVA/an, proportionnelle à la puissance)
#   4. Composante de soutirage variable HPE (EUR/kWh)
#   5. Composante de soutirage variable HCE (EUR/kWh)
#
# For C5 BT:
#   1. Composante de gestion (EUR/an, fixe)
#   2. Composante de comptage (EUR/an, fixe)
#   3. Composante de soutirage Base/HP/HC (EUR/kWh)

TURPE7_RATES: Dict[str, Dict[str, Any]] = {
    # ══════════════════════════════════════════════════════════════════════
    # C4 BT > 36 kVA — Brochure TURPE 7 Enedis (1er août 2025)
    # Source: Délibération CRE n°2025-78 du 13 mars 2025
    # ══════════════════════════════════════════════════════════════════════
    "TURPE_GESTION_C4": {
        "rate": 217.80,  # Contrat unique
        "unit": "EUR/an",
        "source": "CRE TURPE 7 BT>36kVA — CG contrat unique (brochure p.13)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_GESTION_C4_CARD": {
        "rate": 249.84,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 BT>36kVA — CG CARD (brochure p.13)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_COMPTAGE_C4": {
        "rate": 283.27,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 BT>36kVA — CC mensuelle (brochure p.13)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # Soutirage fixe (b_i coefficients pondérateurs puissance) — CU
    "TURPE_SOUTIRAGE_FIXE_C4_CU_HPH": {
        "rate": 17.61,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA CU b_HPH (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_CU_HCH": {
        "rate": 15.96,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA CU b_HCH (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_CU_HPB": {
        "rate": 14.56,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA CU b_HPB (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_CU_HCB": {
        "rate": 11.98,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA CU b_HCB (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # Soutirage fixe — LU
    "TURPE_SOUTIRAGE_FIXE_C4_LU_HPH": {
        "rate": 30.16,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA LU b_HPH (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_LU_HCH": {
        "rate": 21.18,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA LU b_HCH (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_LU_HPB": {
        "rate": 16.64,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA LU b_HPB (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_LU_HCB": {
        "rate": 12.37,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT>36kVA LU b_HCB (brochure p.14)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # Soutirage variable (c_i coefficients pondérateurs énergie) — CU
    "TURPE_SOUTIRAGE_VAR_C4_CU_HPH": {
        "rate": 0.0691,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA CU c_HPH (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_CU_HCH": {
        "rate": 0.0421,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA CU c_HCH (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_CU_HPB": {
        "rate": 0.0213,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA CU c_HPB (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_CU_HCB": {
        "rate": 0.0152,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA CU c_HCB (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # Soutirage variable — LU
    "TURPE_SOUTIRAGE_VAR_C4_LU_HPH": {
        "rate": 0.0569,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA LU c_HPH (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_LU_HCH": {
        "rate": 0.0347,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA LU c_HCH (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_LU_HPB": {
        "rate": 0.0201,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA LU c_HPB (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_LU_HCB": {
        "rate": 0.0149,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT>36kVA LU c_HCB (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # CMDPS BT>36kVA
    "TURPE_CMDPS_C4": {
        "rate": 12.41,
        "unit": "EUR/h",
        "source": "CRE TURPE 7 BT>36kVA CMDPS = 12.41 × h (brochure p.15)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # ══════════════════════════════════════════════════════════════════════
    # C5 BT ≤ 36 kVA — Brochure TURPE 7 Enedis (1er août 2025)
    # ══════════════════════════════════════════════════════════════════════
    "TURPE_GESTION_C5": {
        "rate": 16.80,  # Contrat unique
        "unit": "EUR/an",
        "source": "CRE TURPE 7 BT≤36kVA — CG contrat unique (brochure p.16)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_GESTION_C5_CARD": {
        "rate": 18.00,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 BT≤36kVA — CG CARD (brochure p.16)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_COMPTAGE_C5": {
        "rate": 22.00,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 BT≤36kVA — CC bimestrielle Linky (brochure p.16)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # CACNC (compteur non communicant)
    "TURPE_CACNC_SOCLE": {
        "rate": 6.48,
        "unit": "EUR/bimestre",
        "source": "CRE TURPE 7 BT≤36kVA — CACNC socle (brochure p.17)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_CACNC_MAJORATION": {
        "rate": 4.14,
        "unit": "EUR/bimestre",
        "source": "CRE TURPE 7 BT≤36kVA — CACNC majoration (brochure p.17)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # Soutirage fixe (b coefficient puissance) — C5 BT
    "TURPE_SOUTIRAGE_FIXE_C5_CU4": {
        "rate": 10.11,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT≤36kVA CU4 b (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C5_MU4": {
        "rate": 12.12,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT≤36kVA MU4 b (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C5_LU": {
        "rate": 93.13,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT≤36kVA LU b (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C5_CU": {
        "rate": 11.07,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT≤36kVA CU (dérogatoire) b (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C5_MUDT": {
        "rate": 13.49,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 BT≤36kVA MUDT (dérogatoire) b (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # Soutirage variable — CU4 (4 plages)
    "TURPE_SOUTIRAGE_VAR_C5_CU4_HPH": {
        "rate": 0.0749,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA CU4 c_HPH (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C5_CU4_HCH": {
        "rate": 0.0397,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA CU4 c_HCH (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C5_CU4_HPB": {
        "rate": 0.0166,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA CU4 c_HPB (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C5_CU4_HCB": {
        "rate": 0.0116,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA CU4 c_HCB (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # Soutirage variable — MU4 (4 plages)
    "TURPE_SOUTIRAGE_VAR_C5_MU4_HPH": {
        "rate": 0.0700,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MU4 c_HPH (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C5_MU4_HCH": {
        "rate": 0.0373,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MU4 c_HCH (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C5_MU4_HPB": {
        "rate": 0.0161,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MU4 c_HPB (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C5_MU4_HCB": {
        "rate": 0.0111,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MU4 c_HCB (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # Soutirage variable — LU (sans différenciation temporelle)
    "TURPE_SOUTIRAGE_VAR_C5_LU": {
        "rate": 0.0125,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA LU c (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # Soutirage variable — CU dérogatoire (sans différenciation temporelle)
    "TURPE_SOUTIRAGE_VAR_C5_CU": {
        "rate": 0.0484,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA CU dérogatoire c (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # Soutirage variable — MUDT dérogatoire (2 plages HP/HC)
    "TURPE_SOUTIRAGE_VAR_C5_MUDT_HP": {
        "rate": 0.0494,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MUDT HP c (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C5_MUDT_HC": {
        "rate": 0.0350,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MUDT HC c (brochure p.18)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # Legacy aliases for backward compat (map old 2-period codes to MU4)
    "TURPE_SOUTIRAGE_C5_BASE": {
        "rate": 0.0484,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA CU dérogatoire (alias BASE legacy)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_C5_HP": {
        "rate": 0.0494,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MUDT HP (alias HP legacy)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_C5_HC": {
        "rate": 0.0350,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 BT≤36kVA MUDT HC (alias HC legacy)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # ══════════════════════════════════════════════════════════════════════
    # HTA — Brochure TURPE 7 Enedis (1er août 2025)
    # ══════════════════════════════════════════════════════════════════════
    "TURPE_GESTION_HTA": {
        "rate": 435.72,  # Contrat unique
        "unit": "EUR/an",
        "source": "CRE TURPE 7 HTA — CG contrat unique (brochure p.9)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_GESTION_HTA_CARD": {
        "rate": 499.80,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 HTA — CG CARD (brochure p.9)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_COMPTAGE_HTA": {
        "rate": 376.39,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 HTA — CC mensuelle (brochure p.9)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # HTA — Soutirage fixe CU pointe fixe (b_i) — 5 plages
    "TURPE_SOUTIRAGE_FIXE_HTA_CU_P": {
        "rate": 14.41,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA CU PF b_Pointe (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_CU_HPH": {
        "rate": 14.41,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA CU PF b_HPH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_CU_HCH": {
        "rate": 14.41,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA CU PF b_HCH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_CU_HPB": {
        "rate": 12.55,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA CU PF b_HPB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_CU_HCB": {
        "rate": 11.22,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA CU PF b_HCB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # HTA — Soutirage fixe LU pointe fixe (b_i) — 5 plages
    "TURPE_SOUTIRAGE_FIXE_HTA_LU_P": {
        "rate": 35.33,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA LU PF b_Pointe (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_LU_HPH": {
        "rate": 32.30,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA LU PF b_HPH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_LU_HCH": {
        "rate": 20.39,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA LU PF b_HCH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_LU_HPB": {
        "rate": 14.33,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA LU PF b_HPB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_HTA_LU_HCB": {
        "rate": 11.56,
        "unit": "EUR/kW/an",
        "source": "CRE TURPE 7 HTA LU PF b_HCB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.055,
    },
    # HTA — Soutirage variable CU pointe fixe (c_i)
    "TURPE_SOUTIRAGE_VAR_HTA_CU_P": {
        "rate": 0.0574,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA CU PF c_Pointe (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_CU_HPH": {
        "rate": 0.0423,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA CU PF c_HPH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_CU_HCH": {
        "rate": 0.0199,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA CU PF c_HCH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_CU_HPB": {
        "rate": 0.0101,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA CU PF c_HPB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_CU_HCB": {
        "rate": 0.0069,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA CU PF c_HCB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # HTA — Soutirage variable LU pointe fixe (c_i)
    "TURPE_SOUTIRAGE_VAR_HTA_LU_P": {
        "rate": 0.0265,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA LU PF c_Pointe (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_LU_HPH": {
        "rate": 0.0210,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA LU PF c_HPH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_LU_HCH": {
        "rate": 0.0147,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA LU PF c_HCH (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_LU_HPB": {
        "rate": 0.0092,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA LU PF c_HPB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_HTA_LU_HCB": {
        "rate": 0.0068,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 HTA LU PF c_HCB (brochure p.10)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # HTA — Énergie réactive (CER)
    "TURPE_CER_HTA_SOUTIRAGE": {
        "rate": 0.0244,
        "unit": "EUR/kVAr.h",
        "source": "CRE TURPE 7 HTA CER soutirage tg_phi_max=0.40 (brochure p.12)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_CER_HTA_INJECTION_SB": {
        "rate": 0.0239,
        "unit": "EUR/kVAr.h",
        "source": "CRE TURPE 7 HTA CER injection saison basse tg_phi_max=0.60 (brochure p.12)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    "TURPE_CER_HTA_INJECTION": {
        "rate": 0.0296,
        "unit": "EUR/kVAr.h",
        "source": "CRE TURPE 7 HTA CER injection hors bandeau (brochure p.12)",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # ── CTA ───────────────────────────────────────────────────────────────
    # Historique : 27.04% → 21.93% (arrêté 1er août 2021) → 15% (arrêté 1er fév 2026)
    "CTA_ELEC": {
        "rate": 21.93,
        "unit": "PCT",
        "source": "Arrêté CTA du 26 juillet 2021 — distribution élec 21.93%",
        "valid_from": "2021-08-01",
        "valid_to": "2026-01-31",
        "tva_rate": 0.055,
    },
    "CTA_ELEC_2026": {
        "rate": 15.00,
        "unit": "PCT",
        "source": "Arrêté CTA du 30 janvier 2026 — distribution élec 15%",
        "valid_from": "2026-02-01",
        "tva_rate": 0.055,
    },
    # ── Accise sur l'électricité ──────────────────────────────────────────
    # L'accise dépend de la tranche de consommation annuelle du site:
    #   T1: ≤ 250 MWh/an (particuliers, petits pro C5)
    #   T2: 250 MWh – 1 GWh/an (PME, C4 typique)
    #   T3: 1 – 50 GWh/an (gros C4, HTA)
    #
    # Historique taux T1 (≤250 MWh):
    #   jan 2025: 20,50 | fév-jul 2025: 26,23 | août 2025-jan 2026: 29,98
    #   fév 2026+: 30,85 (loi de finances 2026)
    # Historique taux T2 (250 MWh–1 GWh):
    #   jan 2025: 20,50 | fév-jul 2025: 25,69 | août 2025+: 25,79
    #
    # Vérifié sur factures réelles:
    #   ENGIE SUENO (C5, jan 2026): 29,98 ✓ — (C5, fév 2026): 30,85 ✓
    #   EDF Cannes BL (C4 108kW, oct 2025): 25,79 ✓
    # ── T1 (≤ 250 MWh/an) — C5 BT particuliers et petits pro ──
    "ACCISE_ELEC": {
        "rate": 0.02623,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2025 — accise T1 fév-jul 2025 (26.23 EUR/MWh)",
        "valid_from": "2025-02-01",
        "valid_to": "2025-07-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_JAN2025": {
        "rate": 0.02050,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2024 prolongée — accise tous segments jan 2025 (20.50 EUR/MWh)",
        "valid_from": "2025-01-01",
        "valid_to": "2025-01-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_AOUT2025": {
        "rate": 0.02998,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2025 — accise T1 août 2025+ (29.98 EUR/MWh) — vérifié facture ENGIE SUENO jan 2026",
        "valid_from": "2025-08-01",
        "valid_to": "2026-01-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_FEV2026": {
        "rate": 0.03085,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2026 — accise T1 fév 2026+ (30.85 EUR/MWh) — vérifié facture ENGIE SUENO fév 2026",
        "valid_from": "2026-02-01",
        "tva_rate": 0.20,
    },
    # ── T2 (250 MWh – 1 GWh/an) — PME, C4 BT >36 kVA typique ──
    "ACCISE_ELEC_T2": {
        "rate": 0.02569,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2025 — accise T2 fév-jul 2025 (25.69 EUR/MWh)",
        "valid_from": "2025-02-01",
        "valid_to": "2025-07-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_T2_AOUT2025": {
        "rate": 0.02579,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2025 — accise T2 août 2025+ (25.79 EUR/MWh) — vérifié facture EDF Cannes BL oct 2025",
        "valid_from": "2025-08-01",
        "tva_rate": 0.20,
    },
    # ── GAZ — ATRD (Distribution) ────────────────────────────────────────
    # Source : CRE délibération ATRD 6 (structure)
    "ATRD_GAZ_ABO_T1": {
        "rate": 54.72,
        "unit": "EUR/an",
        "source": "CRE ATRD 7 T1 (0-6 MWh/an) abonnement — délibération 01/07/2024 (incl. Rf)",
        "valid_from": "2024-07-01",
        "tva_rate": 0.055,
    },
    "ATRD_GAZ_ABO_T2": {
        "rate": 186.12,
        "unit": "EUR/an",
        "source": "CRE ATRD 7 T2 (6-300 MWh/an) abonnement — délibération 01/07/2024 (incl. Rf)",
        "valid_from": "2024-07-01",
        "tva_rate": 0.055,
    },
    "ATRD_GAZ_ABO_T3": {
        "rate": 1301.40,
        "unit": "EUR/an",
        "source": "CRE ATRD 7 T3 (300-5000 MWh/an) abonnement — délibération 01/07/2024 (incl. Rf)",
        "valid_from": "2024-07-01",
        "tva_rate": 0.055,
    },
    "ATRD_GAZ_VAR_T1": {
        "rate": 0.04494,
        "unit": "EUR/kWh",
        "source": "CRE ATRD 7 T1 variable (44.94 EUR/MWh) — délibération 01/07/2024",
        "valid_from": "2024-07-01",
        "tva_rate": 0.20,
    },
    "ATRD_GAZ_VAR_T2": {
        "rate": 0.01208,
        "unit": "EUR/kWh",
        "source": "CRE ATRD 7 T2 variable (12.08 EUR/MWh) — délibération 01/07/2024",
        "valid_from": "2024-07-01",
        "tva_rate": 0.20,
    },
    "ATRD_GAZ_VAR_T3": {
        "rate": 0.00869,
        "unit": "EUR/kWh",
        "source": "CRE ATRD 7 T3 variable (8.69 EUR/MWh) — délibération 01/07/2024",
        "valid_from": "2024-07-01",
        "tva_rate": 0.20,
    },
    # ── GAZ — ATRT (Transport) ────────────────────────────────────────
    "ATRT_GAZ": {
        "rate": 0.00267,
        "unit": "EUR/kWh",
        "source": "CRE ATRT variable (terme proportionnel à la consommation)",
        "valid_from": "2025-04-01",
        "tva_rate": 0.20,
    },
    # ── GAZ — CTA ─────────────────────────────────────────────────────
    "CTA_GAZ": {
        "rate": 20.80,
        "unit": "PCT",
        "source": "Arrêté CTA gaz — 20.80% de la part fixe ATRD (distribution)",
        "valid_from": "2024-07-01",
        "tva_rate": 0.055,
    },
    # ── GAZ — TICGN (accise) ──────────────────────────────────────────
    "TICGN": {
        "rate": 0.01639,
        "unit": "EUR/kWh",
        "source": "Accise gaz naturel (ex-TICGN) — 16.39 EUR/MWh au 01/02/2026",
        "valid_from": "2026-02-01",
        "tva_rate": 0.20,
    },
    # ── TVA ───────────────────────────────────────────────────────────────
    "TVA_NORMALE": {
        "rate": 0.20,
        "unit": "PCT",
        "source": "CGI art. 278",
        "valid_from": "2014-01-01",
        "tva_rate": None,
    },
    "TVA_REDUITE": {
        "rate": 0.055,
        "unit": "PCT",
        "source": "CGI art. 278-0 bis",
        "valid_from": "2014-01-01",
        "tva_rate": None,
    },
}

CATALOG_VERSION = "2026-03-21_turpe7_official_rates"


def _resolve_temporal_code(code: str, at_date: Optional[date]) -> str:
    """
    Resolve a rate code to its temporal variant based on at_date.
    Supports CTA_ELEC and ACCISE_ELEC temporal versioning.
    """
    if at_date is None:
        return code

    if code == "CTA_ELEC":
        if at_date >= date(2026, 2, 1) and "CTA_ELEC_2026" in TURPE7_RATES:
            return "CTA_ELEC_2026"
        return "CTA_ELEC"

    if code == "ACCISE_ELEC":
        if at_date < date(2025, 2, 1):
            return "ACCISE_ELEC_JAN2025"
        if at_date >= date(2026, 2, 1):
            return "ACCISE_ELEC_FEV2026"
        if at_date >= date(2025, 8, 1):
            return "ACCISE_ELEC_AOUT2025"
        return "ACCISE_ELEC"

    if code == "ACCISE_ELEC_T2":
        if at_date < date(2025, 2, 1):
            return "ACCISE_ELEC_JAN2025"
        if at_date >= date(2025, 8, 1):
            return "ACCISE_ELEC_T2_AOUT2025"
        return "ACCISE_ELEC_T2"

    return code


def get_rate(code: str, at_date: Optional[date] = None) -> float:
    """
    Get a rate from the catalog, with temporal resolution for CTA and accise.
    Raises KeyError if code unknown.
    Does NOT silently fall back — caller must handle missing rates.
    """
    resolved = _resolve_temporal_code(code, at_date)
    entry = TURPE7_RATES.get(resolved)
    if entry is None:
        raise KeyError(f"Rate code '{resolved}' (from '{code}') not found in billing engine catalog")
    return entry["rate"]


def get_rate_source(code: str, at_date: Optional[date] = None) -> RateSource:
    """Get a rate with full source traceability."""
    resolved = _resolve_temporal_code(code, at_date)
    entry = TURPE7_RATES.get(resolved)
    if entry is None:
        raise KeyError(f"Rate code '{resolved}' (from '{code}') not found in billing engine catalog")
    return RateSource(
        code=resolved,
        rate=entry["rate"],
        unit=entry["unit"],
        source=entry["source"],
        valid_from=entry.get("valid_from"),
        valid_to=entry.get("valid_to"),
        fallback_used=False,
    )


def get_tva_rate_for(code: str, at_date: Optional[date] = None) -> Optional[float]:
    """Get the TVA rate applicable to a given rate code."""
    resolved = _resolve_temporal_code(code, at_date)
    entry = TURPE7_RATES.get(resolved)
    if entry is None:
        return None
    return entry.get("tva_rate")


def list_rates() -> List[Dict[str, Any]]:
    """List all rates in the catalog (for /api/referentiel endpoint)."""
    return [{"code": code, **entry} for code, entry in TURPE7_RATES.items()]


def get_catalog_version() -> str:
    return CATALOG_VERSION


# ─── Segment & option resolution helpers ─────────────────────────────────────


def resolve_segment(subscribed_power_kva: Optional[float]) -> TariffSegment:
    """
    Resolve TURPE segment from subscribed power.
    Returns UNSUPPORTED for C3+ (>250 kVA).
    """
    if subscribed_power_kva is None or subscribed_power_kva <= 0:
        return TariffSegment.UNSUPPORTED
    if subscribed_power_kva > 250:
        return TariffSegment.C3_HTA  # Hors scope V1
    if subscribed_power_kva > 36:
        return TariffSegment.C4_BT
    return TariffSegment.C5_BT


def get_soutirage_fixe_code(segment: TariffSegment, option: TariffOption) -> Optional[str]:
    """Get the catalog code for soutirage fixe (C4 only — returns HPH as reference).

    TURPE 7 C4 BT uses 4 b_i coefficients (HPH, HCH, HPB, HCB).
    This returns the HPH code for backward compat; use get_soutirage_fixe_codes_4p
    for full 4-plage calculation.
    """
    if segment != TariffSegment.C4_BT:
        return None
    mapping = {
        TariffOption.LU: "TURPE_SOUTIRAGE_FIXE_C4_LU_HPH",
        TariffOption.CU: "TURPE_SOUTIRAGE_FIXE_C4_CU_HPH",
    }
    return mapping.get(option)


def get_soutirage_fixe_codes_4p(segment: TariffSegment, option: TariffOption) -> Dict[str, str]:
    """Get catalog codes for soutirage fixe b_i per period (4 plages).

    TURPE 7 formula: CS = b1×P1 + Σ bi×(Pi - Pi-1) + Σ ci×Ei
    Returns: {period_code: catalog_rate_code}
    """
    if segment == TariffSegment.C4_BT:
        opt_key = option.value  # CU or LU
        return {
            "HPH": f"TURPE_SOUTIRAGE_FIXE_C4_{opt_key}_HPH",
            "HCH": f"TURPE_SOUTIRAGE_FIXE_C4_{opt_key}_HCH",
            "HPB": f"TURPE_SOUTIRAGE_FIXE_C4_{opt_key}_HPB",
            "HCB": f"TURPE_SOUTIRAGE_FIXE_C4_{opt_key}_HCB",
        }
    return {}


def get_soutirage_variable_codes(segment: TariffSegment, option: TariffOption) -> Dict[str, str]:
    """Get catalog codes for variable soutirage rates by period.

    TURPE 7 uses 4 plages (HPH/HCH/HPB/HCB) for C4 and C5 CU4/MU4.
    Legacy 2-plage codes (HP/HC, BASE) kept for backward compat.
    Returns: {period_code: catalog_rate_code}
    """
    if segment == TariffSegment.C4_BT:
        opt_key = option.value  # CU or LU
        return {
            "HPH": f"TURPE_SOUTIRAGE_VAR_C4_{opt_key}_HPH",
            "HCH": f"TURPE_SOUTIRAGE_VAR_C4_{opt_key}_HCH",
            "HPB": f"TURPE_SOUTIRAGE_VAR_C4_{opt_key}_HPB",
            "HCB": f"TURPE_SOUTIRAGE_VAR_C4_{opt_key}_HCB",
        }

    elif segment == TariffSegment.C5_BT:
        if option == TariffOption.BASE:
            return {"BASE": "TURPE_SOUTIRAGE_C5_BASE"}
        elif option == TariffOption.HP_HC:
            # Legacy 2-plage (MUDT dérogatoire)
            return {
                "HP": "TURPE_SOUTIRAGE_C5_HP",
                "HC": "TURPE_SOUTIRAGE_C5_HC",
            }
        elif option == TariffOption.MU:
            # MU4 — 4 plages horosaisonnalisées
            return {
                "HPH": "TURPE_SOUTIRAGE_VAR_C5_MU4_HPH",
                "HCH": "TURPE_SOUTIRAGE_VAR_C5_MU4_HCH",
                "HPB": "TURPE_SOUTIRAGE_VAR_C5_MU4_HPB",
                "HCB": "TURPE_SOUTIRAGE_VAR_C5_MU4_HCB",
            }
        elif option == TariffOption.CU:
            # CU4 — 4 plages horosaisonnalisées
            return {
                "HPH": "TURPE_SOUTIRAGE_VAR_C5_CU4_HPH",
                "HCH": "TURPE_SOUTIRAGE_VAR_C5_CU4_HCH",
                "HPB": "TURPE_SOUTIRAGE_VAR_C5_CU4_HPB",
                "HCB": "TURPE_SOUTIRAGE_VAR_C5_CU4_HCB",
            }
        elif option == TariffOption.LU:
            return {"BASE": "TURPE_SOUTIRAGE_VAR_C5_LU"}

    elif segment == TariffSegment.C3_HTA:
        opt_key = option.value  # CU or LU
        return {
            "P": f"TURPE_SOUTIRAGE_VAR_HTA_{opt_key}_P",
            "HPH": f"TURPE_SOUTIRAGE_VAR_HTA_{opt_key}_HPH",
            "HCH": f"TURPE_SOUTIRAGE_VAR_HTA_{opt_key}_HCH",
            "HPB": f"TURPE_SOUTIRAGE_VAR_HTA_{opt_key}_HPB",
            "HCB": f"TURPE_SOUTIRAGE_VAR_HTA_{opt_key}_HCB",
        }

    return {}
