"""
PROMEOS — Service PCS (Pouvoir Calorifique Supérieur) gaz naturel

Conversion m³ → kWh selon le PCS régional.
Source: GRTgaz / GRDF — valeurs moyennes annuelles par grande région.
"""

# PCS moyen par code région (kWh/m³ à 25°C, pression standard)
# Valeurs indicatives — les opérateurs publient des PCS journaliers.
_PCS_PAR_REGION: dict[str, float] = {
    "IDF": 11.21,  # Île-de-France
    "HDF": 11.19,  # Hauts-de-France
    "NOR": 11.17,  # Normandie
    "BRE": 11.08,  # Bretagne
    "PDL": 11.10,  # Pays de la Loire
    "CVL": 11.15,  # Centre-Val de Loire
    "BFC": 11.16,  # Bourgogne-Franche-Comté
    "GES": 11.18,  # Grand Est
    "NAQ": 11.12,  # Nouvelle-Aquitaine
    "OCC": 11.14,  # Occitanie
    "ARA": 11.20,  # Auvergne-Rhône-Alpes
    "PAC": 11.22,  # Provence-Alpes-Côte d'Azur
    "COR": 11.10,  # Corse (peu de gaz réseau)
}

# Valeur par défaut France métropolitaine
_PCS_DEFAULT = 11.2


def pcs_for_region(region_code: str | None = None) -> float:
    """Retourne le PCS (kWh/m³) pour un code région.

    Args:
        region_code: Code ISO 3166-2 simplifié (IDF, HDF, etc.) ou None.

    Returns:
        PCS en kWh/m³.
    """
    if region_code:
        return _PCS_PAR_REGION.get(region_code.upper(), _PCS_DEFAULT)
    return _PCS_DEFAULT


def m3_to_kwh(volume_m3: float, region_code: str | None = None) -> float:
    """Convertit un volume de gaz en m³ vers kWh.

    Args:
        volume_m3: Volume en mètres cubes.
        region_code: Code région pour le PCS local.

    Returns:
        Énergie en kWh.
    """
    pcs = pcs_for_region(region_code)
    return round(volume_m3 * pcs, 2)


def list_regions() -> list[dict]:
    """Liste toutes les régions avec leur PCS."""
    return [{"region_code": code, "pcs_kwh_m3": pcs} for code, pcs in sorted(_PCS_PAR_REGION.items())]
