"""
PROMEOS — Benchmarks ADEME — source unique de vérité.
Source : ADEME Base Empreinte V23.6, OID 2022.

Ce fichier est LA référence. Ne pas dupliquer ces valeurs ailleurs.
"""

from typing import Dict

# Par type de bâtiment (kWh/m²/an énergie finale)
BENCHMARK_BY_BUILDING_TYPE: Dict[str, Dict[str, float]] = {
    "bureau": {"median": 210, "bon": 150, "performant": 100, "source": "ADEME ODP Bureaux 2024"},
    "bureaux": {"median": 210, "bon": 150, "performant": 100, "source": "ADEME ODP Bureaux 2024"},
    "commerce": {"median": 330, "bon": 250, "performant": 180, "source": "ADEME ODP Commerce 2024"},
    "logistique": {"median": 80, "bon": 50, "performant": 30, "source": "ADEME ODP Logistique 2024"},
    "entrepot": {"median": 80, "bon": 50, "performant": 30, "source": "ADEME ODP Logistique 2024"},
    "industrie": {"median": 180, "bon": 120, "performant": 80, "source": "ADEME ODP Industrie 2024"},
    "hotellerie": {"median": 280, "bon": 200, "performant": 140, "source": "ADEME ODP Hôtellerie 2024"},
    "hotel": {"median": 280, "bon": 200, "performant": 140, "source": "ADEME ODP Hôtellerie 2024"},
    "sante": {"median": 250, "bon": 180, "performant": 120, "source": "ADEME ODP Santé 2024"},
    "enseignement": {"median": 140, "bon": 100, "performant": 70, "source": "ADEME ODP Enseignement 2024"},
}

# Par usage individuel (kWh/m²/an, décomposition bureau tertiaire typique ~210 kWh/m²)
BENCHMARK_BY_USAGE: Dict[str, int] = {
    "Chauffage": 90,
    "CVC": 90,
    "Climatisation": 25,
    "Éclairage": 30,
    "IT & Bureautique": 18,
    "Ventilation": 12,
    "Cuisine": 15,
}
