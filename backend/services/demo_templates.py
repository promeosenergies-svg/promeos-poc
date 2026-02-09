"""
PROMEOS - Demo Templates
Pre-built demo data profiles for different client types.
"""

DEMO_PROFILES = {
    "casino_retail": {
        "id": "casino_retail",
        "label": "Casino Retail (120 sites)",
        "description": "Grande distribution : 90 magasins + 30 sites logistique/bureaux",
        "organisation": {
            "nom": "Groupe Casino",
            "type_client": "retail",
        },
        "portefeuilles": [
            {"nom": "Retail IDF", "nb_sites": 50},
            {"nom": "Retail Sud", "nb_sites": 40},
            {"nom": "Bureaux & Logistique", "nb_sites": 30},
        ],
        "stats_preview": {
            "total_sites": 120,
            "sites_non_conformes": "~25%",
            "risque_financier": "~300k EUR",
            "bacs_concernes": "~80 sites",
        },
    },
    "industriel": {
        "id": "industriel",
        "label": "Groupe Industriel (80 sites)",
        "description": "Industrie manufacturiere : usines + entrepots haute puissance",
        "organisation": {
            "nom": "Groupe Renault Industries",
            "type_client": "industrie",
        },
        "portefeuilles": [
            {"nom": "Usines Nord", "nb_sites": 30},
            {"nom": "Usines Sud", "nb_sites": 25},
            {"nom": "Logistique", "nb_sites": 25},
        ],
        "stats_preview": {
            "total_sites": 80,
            "sites_non_conformes": "~30%",
            "risque_financier": "~200k EUR",
            "bacs_concernes": "~60 sites",
        },
    },
    "mixte": {
        "id": "mixte",
        "label": "Patrimoine Mixte (200 sites)",
        "description": "Portfolio mixte : bureaux + commerces + entrepots",
        "organisation": {
            "nom": "Fonciere Omnium",
            "type_client": "tertiaire",
        },
        "portefeuilles": [
            {"nom": "Bureaux IDF", "nb_sites": 60},
            {"nom": "Commerces", "nb_sites": 80},
            {"nom": "Logistique", "nb_sites": 60},
        ],
        "stats_preview": {
            "total_sites": 200,
            "sites_non_conformes": "~20%",
            "risque_financier": "~500k EUR",
            "bacs_concernes": "~120 sites",
        },
    },
}


def get_all_templates():
    return list(DEMO_PROFILES.values())


def get_template(template_id: str):
    return DEMO_PROFILES.get(template_id)
