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
    APER_DEADLINE_LARGE_PARKING_DATE,
    APER_DEADLINE_SMALL_PARKING_DATE,
    APER_PARKING_LARGE_SURFACE_M2,
    APER_PARKING_MIN_SURFACE_M2,
    APER_PENALTY_EUR_PER_M2_PER_YEAR,
    APER_SOLAR_RATIO_PCT,
    DT_PENALTY_AT_RISK_EUR,
    DT_PENALTY_EUR,
    OPERAT_DECLARATION_DEADLINE,
    OPERAT_PENALTY_EUR,
    PRICE_FALLBACK_EUR_PER_KWH,
    PRIMARY_ENERGY_COEF_ELEC,
    PRIMARY_ENERGY_COEF_GAS,
    READINESS_WEIGHT_ACTIONS,
    READINESS_WEIGHT_CONFORMITY,
    READINESS_WEIGHT_DATA,
    VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH,
    VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH,
    VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH,
)

router = APIRouter(prefix="/api/config", tags=["Config"])

# Phase L28.1a audit fix P0 — VNU seuils consommés depuis doctrine.constants
# (lazy-load YAML SoT). Avant : hardcode `_VNU_SEUIL_BAS_EUR_MWH = 78.0` qui
# créait un triangle de drift (YAML → doctrine.constants → ROUTE bypass → frontend).
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
            "seuil_bas_eur_mwh": VNU_SEUIL_ACTIVATION_PRIX_BAS_EUR_PER_MWH,
            "seuil_haut_eur_mwh": VNU_SEUIL_ACTIVATION_PRIX_HAUT_EUR_PER_MWH,
            "tarif_unitaire_2026_eur_mwh": VNU_TARIF_UNITAIRE_2026_EUR_PER_MWH,
            "source": _VNU_SOURCE,
            "label": "Versement pour Non-Usage",
            "activation": "2027 si EPEX dépasse seuil",
        },
        "aper": {
            "penalite_eur_m2_an": APER_PENALTY_EUR_PER_M2_PER_YEAR,
            "surface_min_m2": APER_PARKING_MIN_SURFACE_M2,
            "surface_large_m2": APER_PARKING_LARGE_SURFACE_M2,
            "solar_ratio_pct": APER_SOLAR_RATIO_PCT,
            # Phase L33.1 audit fix P0 — deadline_iso (legacy alias APER_DEADLINE_DATE)
            # divergeait de 6 mois vs SoT YAML (2028-01-01 vs 2028-07-01). Désormais
            # consomme APER_DEADLINE_SMALL_PARKING_DATE (lazy-load YAML SoT) +
            # exposition deadline_large_iso (parkings >10000 m² IMMINENT 2026-07-01).
            "deadline_iso": APER_DEADLINE_SMALL_PARKING_DATE,
            "deadline_large_iso": APER_DEADLINE_LARGE_PARKING_DATE,
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
        "dt": {
            "penalty_eur": DT_PENALTY_EUR,
            "penalty_at_risk_eur": DT_PENALTY_AT_RISK_EUR,
            "source": "Décret 2019-771 art. 9 + L.173-2 CCH",
            "label": "Décret Tertiaire — sanctions",
        },
        "primary_energy": {
            "coef_elec": PRIMARY_ENERGY_COEF_ELEC,
            "coef_gas": PRIMARY_ENERGY_COEF_GAS,
            "source": "Arrêté ministériel 13/04/2023 (NOR LOGL2005904A)",
            "label": "Coefficient énergie primaire RE2020",
        },
        # Phase L33.2 audit fix P0 SECURITY — labels génériques (Reviewer #3 META-AUDIT) :
        # ne pas révéler "Doctrine PROMEOS Sol §15" / "internal_fallback" qui
        # exposeraient la nature heuristique interne aux concurrents (Deepki/Metron).
        "readiness_weights": {
            "data": READINESS_WEIGHT_DATA,
            "conformity": READINESS_WEIGHT_CONFORMITY,
            "actions": READINESS_WEIGHT_ACTIONS,
            "source": "Pondérations applicatives PROMEOS",
            "label": "Pondérations Readiness score",
        },
        "price_fallback": {
            "eur_per_kwh": PRICE_FALLBACK_EUR_PER_KWH,
            "eur_per_mwh": round(PRICE_FALLBACK_EUR_PER_KWH * 1000, 2),
            "source": "Prix indicatif marché ETI (référence interne)",
            "label": "Prix fallback indicatif",
        },
        "doctrine": (
            "Seuils réglementaires SoT backend. Jamais hardcoder côté frontend : "
            "fetcher cet endpoint au mount via RegulatoryConstantsContext."
        ),
    }
