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
    # ── Historique bouclier tarifaire 2023 ──
    "ACCISE_ELEC_2023": {
        "rate": 0.01000,
        "unit": "EUR/kWh",
        "source": "Bouclier tarifaire 2023 — accise réduite tous segments (10 EUR/MWh)",
        "valid_from": "2023-01-01",
        "valid_to": "2024-01-31",
        "tva_rate": 0.20,
    },
    # ── Historique 2024 (fin bouclier, arrêté 25/01/2024) ──
    "ACCISE_ELEC_2024": {
        "rate": 0.02100,
        "unit": "EUR/kWh",
        "source": "Arrêté 25/01/2024 (art. 92 LFI 2024) — accise T1 ménages 21 EUR/MWh",
        "valid_from": "2024-02-01",
        "valid_to": "2024-12-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_T2_2024": {
        "rate": 0.02050,
        "unit": "EUR/kWh",
        "source": "Arrêté 25/01/2024 (art. 92 LFI 2024) — accise T2 PME 20.50 EUR/MWh",
        "valid_from": "2024-02-01",
        "valid_to": "2024-12-31",
        "tva_rate": 0.20,
    },
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
        "source": "Loi de finances 2025 — accise T2 août 2025-jan 2026 (25.79 EUR/MWh) — vérifié facture EDF Cannes BL oct 2025",
        "valid_from": "2025-08-01",
        "valid_to": "2026-01-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_T2_FEV2026": {
        "rate": 0.02658,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2026 — accise T2 fév 2026+ (26.58 EUR/MWh)",
        "valid_from": "2026-02-01",
        "tva_rate": 0.20,
    },
    # ── GAZ — ATRD (Distribution) — ATRD7 (01/07/2024 →) ───────────────
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
    # ── GAZ — ATRD6 historique (01/07/2023 → 30/06/2024) ─────────────
    # Source : CRE délibération n°2023-123 du 10 mai 2023
    # Z2023 = IPC(4.20%) + X(-1.90%) + k(+2.00%) = +4.30%
    # Y2023 = 1.0415, Rf T1/T2 = 8.76 €/an, Rf T3 = 98.40 €/an
    "ATRD6_GAZ_ABO_T1": {
        "rate": 42.24,
        "unit": "EUR/an",
        "source": "CRE ATRD 6 T1 (0-6 MWh/an) abonnement — délibération n°2023-123 01/07/2023 (incl. Rf 8.76€)",
        "valid_from": "2023-07-01",
        "valid_to": "2024-06-30",
        "tva_rate": 0.055,
    },
    "ATRD6_GAZ_ABO_T2": {
        "rate": 139.44,
        "unit": "EUR/an",
        "source": "CRE ATRD 6 T2 (6-300 MWh/an) abonnement — délibération n°2023-123 01/07/2023 (incl. Rf 8.76€)",
        "valid_from": "2023-07-01",
        "valid_to": "2024-06-30",
        "tva_rate": 0.055,
    },
    "ATRD6_GAZ_ABO_T3": {
        "rate": 982.92,
        "unit": "EUR/an",
        "source": "CRE ATRD 6 T3 (300-5000 MWh/an) abonnement — délibération n°2023-123 01/07/2023 (incl. Rf 98.40€)",
        "valid_from": "2023-07-01",
        "valid_to": "2024-06-30",
        "tva_rate": 0.055,
    },
    "ATRD6_GAZ_VAR_T1": {
        "rate": 0.03323,
        "unit": "EUR/kWh",
        "source": "CRE ATRD 6 T1 variable (33.23 EUR/MWh) — délibération n°2023-123 01/07/2023",
        "valid_from": "2023-07-01",
        "valid_to": "2024-06-30",
        "tva_rate": 0.20,
    },
    "ATRD6_GAZ_VAR_T2": {
        "rate": 0.00893,
        "unit": "EUR/kWh",
        "source": "CRE ATRD 6 T2 variable (8.93 EUR/MWh) — délibération n°2023-123 01/07/2023",
        "valid_from": "2023-07-01",
        "valid_to": "2024-06-30",
        "tva_rate": 0.20,
    },
    "ATRD6_GAZ_VAR_T3": {
        "rate": 0.00642,
        "unit": "EUR/kWh",
        "source": "CRE ATRD 6 T3 variable (6.42 EUR/MWh) — délibération n°2023-123 01/07/2023",
        "valid_from": "2023-07-01",
        "valid_to": "2024-06-30",
        "tva_rate": 0.20,
    },
    # ── GAZ — ATRT (Transport) ────────────────────────────────────────
    "ATRT_GAZ_2023": {
        "rate": 0.00240,
        "unit": "EUR/kWh",
        "source": "CRE ATRT7 — terme proportionnel transport gaz (~2.40 EUR/MWh, 2023-2025)",
        "valid_from": "2023-07-01",
        "valid_to": "2025-03-31",
        "tva_rate": 0.20,
    },
    "ATRT_GAZ": {
        "rate": 0.00267,
        "unit": "EUR/kWh",
        "source": "CRE ATRT8 — terme proportionnel transport (2.67 EUR/MWh, avr 2025+)",
        "valid_from": "2025-04-01",
        "tva_rate": 0.20,
    },
    # ── GAZ — TDN (Terme de Débit Normalisé) ────────────────────────
    # Applicable 01/07/2026 aux clients T1/T2/T3 dont le débit normalisé
    # est > 40 Nm³/h. Tarif : 5,52 EUR/an par Nm³/h de débit normalisé.
    # Source : GRDF sites.grdf.fr/web/terme-debit-normalise
    #          CRE délibération n°2025-161 du 19/06/2025 (prestations GRD)
    # Non applicable B2C (99% à 6 ou 10 Nm³/h).
    "TDN_GAZ": {
        "rate": 5.52,
        "unit": "EUR/an/Nm3h",
        "source": "CRE/GRDF — TDN 5.52 EUR/an/Nm³/h au 01/07/2026 (sites > 40 Nm³/h)",
        "valid_from": "2026-07-01",
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
    "TICGN_2023": {
        "rate": 0.00841,
        "unit": "EUR/kWh",
        "source": "Bouclier tarifaire 2023 — TICGN réduite 8.41 EUR/MWh",
        "valid_from": "2023-01-01",
        "valid_to": "2023-12-31",
        "tva_rate": 0.20,
    },
    "TICGN_2024": {
        "rate": 0.01637,
        "unit": "EUR/kWh",
        "source": "Art. 64 LFI 2024 — fin bouclier, TICGN 16.37 EUR/MWh (2024-2025)",
        "valid_from": "2024-01-01",
        "valid_to": "2026-01-31",
        "tva_rate": 0.20,
    },
    "TICGN": {
        "rate": 0.01639,
        "unit": "EUR/kWh",
        "source": "Accise gaz naturel (ex-TICGN) — 16.39 EUR/MWh au 01/02/2026",
        "valid_from": "2026-02-01",
        "tva_rate": 0.20,
    },
    # ── CAPACITÉ (Mécanisme de capacité) ───────────────────────────────
    # Obligation fournisseur répercutée au client B2B. Prix = résultat
    # des enchères de garanties de capacité. Réforme acheteur unique
    # RTE prévue nov. 2026 (loi de finances 2025).
    # Prix enchères 2026 : 3,15 €/MW (enchère 06/03/2025 pour livraison 2026).
    # Conversion en EUR/kWh : prix_MW × coefficient_obligation / 8760h
    # Coefficient obligation moyen B2B ≈ 1.2 (pro-rata consommation pointe)
    # → 3.15 × 1.2 / 8760 ≈ 0.00043 EUR/kWh
    "CAPACITE_ELEC": {
        "rate": 0.00043,
        "unit": "EUR/kWh",
        "source": "Enchères capacité RTE 06/03/2025 — 3.15 EUR/MW × coeff 1.2 / 8760h ≈ 0.43 EUR/MWh",
        "valid_from": "2026-01-01",
        "tva_rate": 0.20,
    },
    "CAPACITE_ELEC_2025": {
        "rate": 0.00000,
        "unit": "EUR/kWh",
        "source": "Enchères capacité RTE 2025 — 0 EUR/MW (prix nul en 2025)",
        "valid_from": "2025-01-01",
        "valid_to": "2025-12-31",
        "tva_rate": 0.20,
    },
    # ── CAPACITÉ — Réforme acheteur unique RTE (nov 2026) ──────────────
    "CAPACITE_ELEC_NOV2026": {
        "rate": 0.00043,
        "unit": "EUR/kWh",
        "source": "Réforme capacité RTE acheteur unique (nov 2026) — placeholder = enchères 2026 (3.15 EUR/MW)",
        "valid_from": "2026-11-01",
        "tva_rate": 0.20,
    },
    # ── CPB (Certificats de Production de Biogaz) — shadow ────────────
    # Obligation fournisseur gaz depuis 01/01/2026 (Décret 2024-718).
    # 0.0041 CPB/MWh PCS × ~85 EUR/CPB estimé ≈ 0.35 EUR/MWh.
    "CPB_GAZ_2026": {
        "rate": 0.00035,
        "unit": "EUR/kWh",
        "source": "Décret 2024-718 — CPB 0.0041/MWh × ~85 EUR/CPB ≈ 0.35 EUR/MWh (estimation shadow)",
        "valid_from": "2026-01-01",
        "tva_rate": 0.20,
    },
    # ── STOCKAGE GAZ (ATS3 — terme tarifaire stockage souterrain) ────
    # Inclus dans ATRT, explicité comme shadow component pour traçabilité.
    # Source: CRE délibérations ATS3 2025/2026
    "STOCKAGE_GAZ_2025": {
        "rate": 0.00038,
        "unit": "EUR/kWh",
        "source": "CRE ATS3 2025 — terme stockage 331.44 EUR/MWh/j/an (shadow, inclus dans ATRT)",
        "valid_from": "2025-04-01",
        "valid_to": "2026-03-31",
        "tva_rate": 0.20,
    },
    "STOCKAGE_GAZ_2026": {
        "rate": 0.00046,
        "unit": "EUR/kWh",
        "source": "CRE ATS3 2026 estimé — +20% vs 2025 (shadow, inclus dans ATRT)",
        "valid_from": "2026-04-01",
        "tva_rate": 0.20,
    },
    # ── CEE (shadow — coût implicite estimatif) ──────────────────────
    # Pas une ligne facture dédiée. Estimé pour décomposition pédagogique.
    "CEE_P5_SHADOW": {
        "rate": 0.0050,
        "unit": "EUR/kWh",
        "source": "Estimation PROMEOS — coût CEE P5 implicite ~5 EUR/MWh (780 TWhc/an)",
        "valid_from": "2022-01-01",
        "valid_to": "2025-12-31",
        "tva_rate": 0.20,
    },
    "CEE_P6_SHADOW": {
        "rate": 0.0065,
        "unit": "EUR/kWh",
        "source": "Estimation PROMEOS — coût CEE P6 implicite ~6.5 EUR/MWh (1050 TWhc/an, +35% vs P5)",
        "valid_from": "2026-01-01",
        "tva_rate": 0.20,
    },
    # ── GAZ — ELD (péréquation nationale LFI 2026, 01/07/2026) ──────
    # Taux ELD convergeront vers GRDF. Entrées à ajouter quand CRE publie.
    # Pattern: ATRD_GAZ_ABO_T2_REGIE_STRASBOURG, etc.
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

CATALOG_VERSION = "2026-03-22_v2.2_c3hta_stockage_cee_perequation_capacite_reforme"


def _resolve_temporal_code(code: str, at_date: Optional[date]) -> str:
    """
    Resolve a rate code to its temporal variant based on at_date.
    Supports CTA_ELEC, ACCISE_ELEC, and ATRD_GAZ temporal versioning.
    """
    if at_date is None:
        return code

    # ── ATRD GAZ : ATRD6 (01/07/2023 → 30/06/2024) vs ATRD7 (01/07/2024 →) ──
    if code.startswith("ATRD_GAZ_") and at_date < date(2024, 7, 1):
        atrd6_code = code.replace("ATRD_GAZ_", "ATRD6_GAZ_")
        if atrd6_code in TURPE7_RATES:
            return atrd6_code

    if code == "CTA_ELEC":
        if at_date >= date(2026, 2, 1) and "CTA_ELEC_2026" in TURPE7_RATES:
            return "CTA_ELEC_2026"
        return "CTA_ELEC"

    if code == "ACCISE_ELEC":
        if at_date < date(2024, 2, 1):
            return "ACCISE_ELEC_2023"
        if at_date < date(2025, 1, 1):
            return "ACCISE_ELEC_2024"
        if at_date < date(2025, 2, 1):
            return "ACCISE_ELEC_JAN2025"
        if at_date >= date(2026, 2, 1):
            return "ACCISE_ELEC_FEV2026"
        if at_date >= date(2025, 8, 1):
            return "ACCISE_ELEC_AOUT2025"
        return "ACCISE_ELEC"

    if code == "ACCISE_ELEC_T2":
        if at_date < date(2024, 2, 1):
            return "ACCISE_ELEC_2023"  # Bouclier : même taux tous segments
        if at_date < date(2025, 1, 1):
            return "ACCISE_ELEC_T2_2024"
        if at_date < date(2025, 2, 1):
            return "ACCISE_ELEC_JAN2025"
        if at_date >= date(2026, 2, 1):
            return "ACCISE_ELEC_T2_FEV2026"
        if at_date >= date(2025, 8, 1):
            return "ACCISE_ELEC_T2_AOUT2025"
        return "ACCISE_ELEC_T2"

    if code == "CAPACITE_ELEC":
        if at_date < date(2026, 1, 1):
            return "CAPACITE_ELEC_2025"
        if at_date >= date(2026, 11, 1):
            return "CAPACITE_ELEC_NOV2026"
        return "CAPACITE_ELEC"

    if code == "STOCKAGE_GAZ":
        if at_date >= date(2026, 4, 1):
            return "STOCKAGE_GAZ_2026"
        return "STOCKAGE_GAZ_2025"

    if code == "CEE_SHADOW":
        if at_date >= date(2026, 1, 1):
            return "CEE_P6_SHADOW"
        return "CEE_P5_SHADOW"

    if code == "ATRT_GAZ":
        if at_date < date(2025, 4, 1):
            return "ATRT_GAZ_2023"
        return "ATRT_GAZ"

    if code == "TICGN":
        if at_date < date(2024, 1, 1):
            return "TICGN_2023"
        if at_date < date(2026, 2, 1):
            return "TICGN_2024"
        return "TICGN"

    if code == "CPB_SHADOW":
        if at_date >= date(2026, 1, 1):
            return "CPB_GAZ_2026"
        return code  # Pas de rate pré-2026 → KeyError attendu

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
    """Get the TVA rate applicable to a given rate code.

    Depuis le 1er août 2025 (LFI 2025, art. 20), la TVA à taux réduit (5,5%)
    sur l'abonnement, la CTA et les composantes fixes TURPE est supprimée.
    Toutes ces composantes passent à 20% (directive UE, CGI art. 278).
    Source : service-public.fr, bofip ACTU-2025-00057, energie-info.fr
    """
    resolved = _resolve_temporal_code(code, at_date)
    entry = TURPE7_RATES.get(resolved)
    if entry is None:
        return None
    base_tva = entry.get("tva_rate")
    # ── Résolution temporelle TVA : suppression taux réduit 5,5% → 20% ──
    # Applicable au 01/08/2025 sur abonnement, CTA, TURPE fixe (gestion,
    # comptage, soutirage fixe). LFI 2025 art. 20, directive UE.
    if (
        at_date is not None and at_date >= date(2025, 8, 1) and base_tva is not None and base_tva < 0.10  # was 5.5%
    ):
        # Composantes concernées : TURPE gestion, comptage, soutirage fixe,
        # CTA, abonnement fournisseur. Identifiées par tva_rate == 0.055.
        # La TVA_NORMALE et TVA_REDUITE sont des constantes, pas des composantes.
        if code not in ("TVA_NORMALE", "TVA_REDUITE"):
            return 0.20
    return base_tva


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
    """Get the catalog code for soutirage fixe (C4/HTA — returns HPH as reference).

    TURPE 7 C4 BT uses 4 b_i coefficients (HPH, HCH, HPB, HCB).
    TURPE 7 HTA uses 5 b_i coefficients (P, HPH, HCH, HPB, HCB).
    This returns the HPH code for backward compat; use get_soutirage_fixe_codes_5p
    for full multi-plage calculation.
    """
    if segment == TariffSegment.C4_BT:
        mapping = {
            TariffOption.LU: "TURPE_SOUTIRAGE_FIXE_C4_LU_HPH",
            TariffOption.CU: "TURPE_SOUTIRAGE_FIXE_C4_CU_HPH",
        }
        return mapping.get(option)
    if segment == TariffSegment.C3_HTA:
        mapping = {
            TariffOption.LU: "TURPE_SOUTIRAGE_FIXE_HTA_LU_HPH",
            TariffOption.CU: "TURPE_SOUTIRAGE_FIXE_HTA_CU_HPH",
        }
        return mapping.get(option)
    return None


def get_soutirage_fixe_codes_4p(segment: TariffSegment, option: TariffOption) -> Dict[str, str]:
    """Get catalog codes for soutirage fixe b_i per period (4 plages C4).

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


def get_soutirage_fixe_codes_5p(segment: TariffSegment, option: TariffOption) -> Dict[str, str]:
    """Get catalog codes for soutirage fixe b_i per period (5 plages HTA: P+HPH+HCH+HPB+HCB).

    TURPE 7 HTA formula: CS = Σ bi×Pi (5 plages, EUR/kW/an).
    Returns: {period_code: catalog_rate_code}
    Falls back to get_soutirage_fixe_codes_4p for C4 BT.
    """
    if segment == TariffSegment.C3_HTA and option in (TariffOption.CU, TariffOption.LU):
        opt_key = option.value  # CU or LU
        return {
            "P": f"TURPE_SOUTIRAGE_FIXE_HTA_{opt_key}_P",
            "HPH": f"TURPE_SOUTIRAGE_FIXE_HTA_{opt_key}_HPH",
            "HCH": f"TURPE_SOUTIRAGE_FIXE_HTA_{opt_key}_HCH",
            "HPB": f"TURPE_SOUTIRAGE_FIXE_HTA_{opt_key}_HPB",
            "HCB": f"TURPE_SOUTIRAGE_FIXE_HTA_{opt_key}_HCB",
        }
    return get_soutirage_fixe_codes_4p(segment, option)


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


# ─── Résolution saisonnière ──────────────────────────────────────────────────


def get_season_for_date(d: date) -> str:
    """Retourne la saison TURPE pour une date donnée.

    Returns:
        "HIVER" (saison haute, nov-mars) ou "ETE" (saison basse, avr-oct)

    Source: CRE TURPE 7, délibération n°2025-78.
    """
    from .turpe_calendar import get_season

    return get_season(d)
