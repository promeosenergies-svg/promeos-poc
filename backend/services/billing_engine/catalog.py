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
    # ── C4 BT — Longue Utilisation (LU) ──────────────────────────────────
    "TURPE_GESTION_C4": {
        "rate": 303.36,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 C4 BT [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.055,
    },
    "TURPE_COMPTAGE_C4": {
        "rate": 394.68,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 C4 BT [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.055,
    },
    # Soutirage fixe — dépend de l'option tarifaire
    "TURPE_SOUTIRAGE_FIXE_C4_LU": {
        "rate": 29.76,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 C4 BT LU [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_MU": {
        "rate": 21.12,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 C4 BT MU [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_FIXE_C4_CU": {
        "rate": 9.00,
        "unit": "EUR/kVA/an",
        "source": "CRE TURPE 7 C4 BT CU [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.055,
    },
    # Soutirage variable — LU (HPE / HCE)
    "TURPE_SOUTIRAGE_VAR_C4_LU_HPE": {
        "rate": 0.0441,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C4 BT LU HPE [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_LU_HCE": {
        "rate": 0.0295,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C4 BT LU HCE [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    # Soutirage variable — MU (HP / HC)
    "TURPE_SOUTIRAGE_VAR_C4_MU_HP": {
        "rate": 0.0441,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C4 BT MU HP [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_MU_HC": {
        "rate": 0.0295,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C4 BT MU HC [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    # Soutirage variable — CU (HP / HC)
    "TURPE_SOUTIRAGE_VAR_C4_CU_HP": {
        "rate": 0.0519,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C4 BT CU HP [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_VAR_C4_CU_HC": {
        "rate": 0.0334,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C4 BT CU HC [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    # ── C5 BT ────────────────────────────────────────────────────────────
    "TURPE_GESTION_C5": {
        "rate": 18.48,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 C5 BT",
        "valid_from": "2025-02-01",
        "tva_rate": 0.055,
    },
    "TURPE_COMPTAGE_C5": {
        "rate": 18.24,
        "unit": "EUR/an",
        "source": "CRE TURPE 7 C5 BT [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.055,
    },
    "TURPE_SOUTIRAGE_C5_BASE": {
        "rate": 0.0453,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C5 BT Base",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_C5_HP": {
        "rate": 0.0525,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C5 BT HP [TO_VERIFY]",
        "valid_from": "2025-02-01",
        "tva_rate": 0.20,
    },
    "TURPE_SOUTIRAGE_C5_HC": {
        "rate": 0.0357,
        "unit": "EUR/kWh",
        "source": "CRE TURPE 7 C5 BT HC [TO_VERIFY]",
        "valid_from": "2025-02-01",
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
    # ── Accise ────────────────────────────────────────────────────────────
    # PME (37-250 kVA) : jan 2025 = 20.50 €/MWh, fév-jul 2025 = 26.23, août+ 2025 = 29.98
    # Taux par défaut = fév-jul 2025 (période la plus courante pour factures en cours)
    "ACCISE_ELEC": {
        "rate": 0.02623,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2025 — accise PME fév-jul 2025 (26.23 EUR/MWh)",
        "valid_from": "2025-02-01",
        "valid_to": "2025-07-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_JAN2025": {
        "rate": 0.02050,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2024 prolongée — accise PME jan 2025 (20.50 EUR/MWh)",
        "valid_from": "2025-01-01",
        "valid_to": "2025-01-31",
        "tva_rate": 0.20,
    },
    "ACCISE_ELEC_AOUT2025": {
        "rate": 0.02998,
        "unit": "EUR/kWh",
        "source": "Loi de finances 2025 + majoration ZNI — accise PME août+ 2025 (29.98 EUR/MWh)",
        "valid_from": "2025-08-01",
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

CATALOG_VERSION = "2026-03-11_engine_v2.1_lockdown"


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
        if at_date < date(2025, 2, 1) and "ACCISE_ELEC_JAN2025" in TURPE7_RATES:
            return "ACCISE_ELEC_JAN2025"
        if at_date >= date(2025, 8, 1) and "ACCISE_ELEC_AOUT2025" in TURPE7_RATES:
            return "ACCISE_ELEC_AOUT2025"
        return "ACCISE_ELEC"

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
    """Get the catalog code for soutirage fixe (C4 only)."""
    if segment != TariffSegment.C4_BT:
        return None
    mapping = {
        TariffOption.LU: "TURPE_SOUTIRAGE_FIXE_C4_LU",
        TariffOption.MU: "TURPE_SOUTIRAGE_FIXE_C4_MU",
        TariffOption.CU: "TURPE_SOUTIRAGE_FIXE_C4_CU",
    }
    return mapping.get(option)


def get_soutirage_variable_codes(segment: TariffSegment, option: TariffOption) -> Dict[str, str]:
    """
    Get catalog codes for variable soutirage rates by period.
    Returns: {period_code: catalog_rate_code}
    """
    if segment == TariffSegment.C4_BT:
        if option == TariffOption.LU:
            return {
                "HPE": "TURPE_SOUTIRAGE_VAR_C4_LU_HPE",
                "HCE": "TURPE_SOUTIRAGE_VAR_C4_LU_HCE",
            }
        elif option == TariffOption.MU:
            return {
                "HP": "TURPE_SOUTIRAGE_VAR_C4_MU_HP",
                "HC": "TURPE_SOUTIRAGE_VAR_C4_MU_HC",
            }
        elif option == TariffOption.CU:
            return {
                "HP": "TURPE_SOUTIRAGE_VAR_C4_CU_HP",
                "HC": "TURPE_SOUTIRAGE_VAR_C4_CU_HC",
            }

    elif segment == TariffSegment.C5_BT:
        if option == TariffOption.BASE:
            return {"BASE": "TURPE_SOUTIRAGE_C5_BASE"}
        elif option == TariffOption.HP_HC:
            return {
                "HP": "TURPE_SOUTIRAGE_C5_HP",
                "HC": "TURPE_SOUTIRAGE_C5_HC",
            }

    return {}
