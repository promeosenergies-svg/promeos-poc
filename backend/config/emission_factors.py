"""
PROMEOS — Facteurs d'emission CO2e par vecteur energetique.
Source unique : ADEME Base Carbone 2024.

Usage:
    from config.emission_factors import get_emission_factor, get_emission_source
    factor = get_emission_factor("ELEC")   # 0.0569
    factor = get_emission_factor("GAZ")    # 0.2270
"""

EMISSION_FACTORS = {
    "ELEC": {
        "kgco2e_per_kwh": 0.0569,
        "source": "ADEME Base Carbone 2024 — mix moyen FR",
        "year": 2024,
    },
    "GAZ": {
        "kgco2e_per_kwh": 0.2270,
        "source": "ADEME Base Carbone 2024 — gaz naturel",
        "year": 2024,
    },
}


def get_emission_factor(energy_vector: str) -> float:
    """Retourne le facteur en kgCO2e/kWh. Fallback ELEC si vecteur inconnu."""
    entry = EMISSION_FACTORS.get(energy_vector.upper(), EMISSION_FACTORS["ELEC"])
    return entry["kgco2e_per_kwh"]


def get_emission_source(energy_vector: str) -> str:
    """Retourne le label source pour affichage."""
    entry = EMISSION_FACTORS.get(energy_vector.upper(), EMISSION_FACTORS["ELEC"])
    return entry["source"]
