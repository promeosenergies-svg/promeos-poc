"""
PROMEOS — Routes Config : regulatory constants

GET /api/config/regulatory-constants

Expose les seuils réglementaires VNU/APER/TURPE depuis les SoTs canoniques
(doctrine/constants.py + referentials/market_tariffs_2026.yaml) au frontend.

Objectif : supprimer les constantes hardcodées dans CockpitDecision.jsx et
autres pages frontend (VNU 78/110 €/MWh, APER 20 €/m²/an, etc.).

Doctrine §8.1 : zero business logic in frontend — tout seuil réglementaire
servi par le backend, jamais inline dans le JSX.
"""

from __future__ import annotations

from fastapi import APIRouter

from doctrine.constants import (
    APER_DEADLINE_DATE,
    APER_PARKING_MIN_SURFACE_M2,
    APER_PENALTY_EUR_PER_M2_PER_YEAR,
    OPERAT_DECLARATION_DEADLINE,
    OPERAT_PENALTY_EUR,
)

router = APIRouter(prefix="/api/config", tags=["Config"])

# Seuils VNU issus de referentials/market_tariffs_2026.yaml
# (SoT marché — même valeurs exposées par /api/market/tariffs via TariffType.VNU)
_VNU_SEUIL_BAS_EUR_MWH = 78.0
_VNU_SEUIL_HAUT_EUR_MWH = 110.0
_VNU_SOURCE = "LF 2025 art. 17, décrets 2025-909/910, CRE 2025-268"

# TURPE 7 — reprogrammation HC méridiennes (note documentaire, pas de seuil numérique)
_TURPE7_HC_SOURCE = "CRE 2025-78, brochure Enedis p.13-14"
_TURPE7_HC_PLAGE = "11h-17h"


@router.get("/regulatory-constants")
def get_regulatory_constants() -> dict:
    """Retourne les seuils réglementaires canoniques pour le frontend.

    Sources :
      - VNU : referentials/market_tariffs_2026.yaml (LF 2025 art. 17)
      - APER : doctrine/constants.py (Loi 2023-175 art. 40 + Décret 2022-1726)
      - OPERAT : doctrine/constants.py (Arrêté Tertiaire 2024-DGEC)
      - TURPE 7 HC : CRE 2025-78

    Response shape utilisée par RegulatoryConstantsContext (FE).
    """
    return {
        "vnu": {
            "seuil_bas_eur_mwh": _VNU_SEUIL_BAS_EUR_MWH,
            "seuil_haut_eur_mwh": _VNU_SEUIL_HAUT_EUR_MWH,
            "source": _VNU_SOURCE,
            "label": "Versement Nucléaire Universel",
            "activation": "2027 si EPEX dépasse seuil",
        },
        "aper": {
            "penalite_eur_m2_an": APER_PENALTY_EUR_PER_M2_PER_YEAR,
            "surface_min_m2": APER_PARKING_MIN_SURFACE_M2,
            "deadline_iso": APER_DEADLINE_DATE,
            "source": "Loi 2023-175 art. 40 + Décret 2022-1726",
            "label": "APER — solarisation parkings",
        },
        "turpe7_hc": {
            "plage_meridienne": _TURPE7_HC_PLAGE,
            "source": _TURPE7_HC_SOURCE,
            "label": "TURPE 7 reprogrammation HC méridiennes",
        },
        "operat": {
            "penalite_eur": OPERAT_PENALTY_EUR,
            "deadline_declaration_iso": OPERAT_DECLARATION_DEADLINE,
            "source": "Arrêté Tertiaire 2024-DGEC",
            "label": "OPERAT — déclaration consommations 2025",
        },
        "doctrine": (
            "Seuils réglementaires SoT backend. Jamais hardcoder côté frontend : "
            "fetcher cet endpoint au mount via RegulatoryConstantsContext."
        ),
    }
