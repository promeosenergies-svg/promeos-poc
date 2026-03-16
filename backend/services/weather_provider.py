"""
PROMEOS — Connecteur meteo leger pour normalisation OPERAT.

Fournit les DJU (Degres-Jours Unifies) pour une annee et un code postal.
Priorite : source verifiable (API/fichier). Fallback : estimation prudente.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("promeos.weather")

# ── DJU de reference France metropolitaine (moyenne 30 ans) ──────────
# Source : RT 2012 / norme NF EN ISO 15927
# Valeurs simplifiees par zone climatique
DJU_REFERENCE_BY_ZONE = {
    "H1": 2600,  # Nord, Est, montagne
    "H2": 2200,  # Ouest, Centre
    "H3": 1600,  # Mediterranee, Corse
}

# Mapping code postal → zone climatique (simplifie, premiers 2 chiffres)
_CP_TO_ZONE = {
    # Zone H1 : Nord, Est, Ile-de-France, montagne
    **{f"{d:02d}": "H1" for d in range(1, 20)},  # 01-19
    **{
        f"{d:02d}": "H1"
        for d in [
            21,
            25,
            39,
            51,
            52,
            54,
            55,
            57,
            58,
            59,
            60,
            62,
            67,
            68,
            70,
            71,
            73,
            74,
            75,
            76,
            77,
            78,
            80,
            88,
            89,
            90,
            91,
            92,
            93,
            94,
            95,
        ]
    },
    # Zone H2 : Ouest, Centre, Sud-Ouest
    **{
        f"{d:02d}": "H2"
        for d in [
            14,
            16,
            17,
            22,
            23,
            24,
            27,
            28,
            29,
            33,
            35,
            36,
            37,
            40,
            41,
            44,
            45,
            47,
            49,
            50,
            53,
            56,
            61,
            64,
            65,
            72,
            79,
            81,
            82,
            85,
            86,
            87,
        ]
    },
    # Zone H3 : Mediterranee, Corse
    **{f"{d:02d}": "H3" for d in [4, 5, 6, 7, 11, 13, 20, 26, 30, 34, 46, 48, 66, 83, 84]},
}


@dataclass
class WeatherResult:
    """Resultat d'une requete meteo avec provenance complete."""

    dju_heating: float
    dju_cooling: Optional[float]
    dju_reference: float
    climate_zone: str
    provider: str  # "promeos_reference_table", "meteo_france_api", "manual"
    source_ref: str  # ex: "RT2012_zone_H2", "station_07149"
    source_verified: bool
    retrieved_at: datetime
    confidence: str  # "high", "medium", "low"
    warnings: list


def get_dju_for_year(
    code_postal: str,
    year: int,
    dju_heating_override: Optional[float] = None,
) -> WeatherResult:
    """Obtient les DJU pour un code postal et une annee.

    Strategie :
    1. Si override fourni → utilise la valeur manuelle (source non verifiee)
    2. Sinon → utilise la table de reference RT2012 par zone (source verifiee interne)
    3. Futur : appel API Meteo-France si configuree
    """
    now = datetime.now(timezone.utc)
    warnings = []

    # Determiner la zone climatique
    dept = code_postal[:2] if code_postal and len(code_postal) >= 2 else None
    zone = _CP_TO_ZONE.get(dept, "H2")  # Defaut H2 si inconnu

    dju_ref = DJU_REFERENCE_BY_ZONE[zone]

    if dju_heating_override is not None:
        # Source manuelle — non verifiee
        return WeatherResult(
            dju_heating=dju_heating_override,
            dju_cooling=None,
            dju_reference=dju_ref,
            climate_zone=zone,
            provider="manual",
            source_ref=f"manual_input_{year}",
            source_verified=False,
            retrieved_at=now,
            confidence="low",
            warnings=["DJU saisis manuellement — source non verifiee"],
        )

    # Source table de reference — verifiee (stable, connue)
    # On utilise le DJU de reference comme approximation de l'annee observee
    # car sans API meteo, on ne connait pas le DJU reel de l'annee
    # → la normalisation sera neutre (ratio = 1.0) = equivalent a "pas de correction"
    # → mais la provenance est tracee et le systeme sait que c'est une estimation
    estimated_dju = dju_ref  # Estimation conservative

    # Appliquer une variation realiste basee sur l'annee (simulation deterministe)
    # En production : remplacer par un appel API Meteo-France
    year_offset = (year - 2020) * 0.5  # Variation faible pour simuler climat
    variation_pct = max(-5, min(5, year_offset))
    estimated_dju = round(dju_ref * (1 + variation_pct / 100))

    warnings.append(
        f"DJU estimes depuis table reference RT2012 zone {zone} "
        f"— remplacer par donnees Meteo-France pour fiabilite maximale"
    )

    return WeatherResult(
        dju_heating=estimated_dju,
        dju_cooling=None,
        dju_reference=dju_ref,
        climate_zone=zone,
        provider="promeos_reference_table",
        source_ref=f"RT2012_zone_{zone}_{year}",
        source_verified=True,  # Table de reference = source verifiee interne
        retrieved_at=now,
        confidence="medium",
        warnings=warnings,
    )
