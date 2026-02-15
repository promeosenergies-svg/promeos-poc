"""
PROMEOS - Demo Pack Definitions
Casino: 36/72 sites retail (hypermarches, proximite, logistique)
Tertiaire: 10 buildings (bureaux, ecoles, hopitaux, hotels)
"""


_VILLES = [
    ("Paris", "75001", "IDF", 48.8566, 2.3522),
    ("Lyon", "69001", "ARA", 45.7640, 4.8357),
    ("Marseille", "13001", "PACA", 43.2965, 5.3698),
    ("Toulouse", "31000", "OCC", 43.6047, 1.4442),
    ("Bordeaux", "33000", "NAQ", 44.8378, -0.5792),
    ("Nantes", "44000", "PDL", 47.2184, -1.5536),
    ("Lille", "59000", "HDF", 50.6292, 3.0573),
    ("Strasbourg", "67000", "GE", 48.5734, 7.7521),
    ("Montpellier", "34000", "OCC", 43.6108, 3.8767),
    ("Rennes", "35000", "BRE", 48.1173, -1.6778),
    ("Nice", "06000", "PACA", 43.7102, 7.2620),
    ("Grenoble", "38000", "ARA", 45.1885, 5.7245),
]

_RUES = [
    "Avenue de la Republique", "Rue Victor Hugo", "Boulevard Gambetta",
    "Rue de la Liberte", "Avenue Jean Jaures", "Rue Pasteur",
    "Place de la Mairie", "Rue du Commerce", "Boulevard Haussmann",
    "Rue de Rivoli", "Avenue des Champs", "Rue Nationale",
]


PACKS = {
    "casino": {
        "label": "Groupe Casino — Retail",
        "description": "Hypermarches, proximite, entrepots. 3 portefeuilles.",
        "org": {"nom": "Groupe Casino", "type_client": "retail", "siren": "554008671"},
        "entites": [
            {"nom": "Casino France SAS", "siren": "554008671", "siret": "55400867100014",
             "naf_code": "4711F", "region_code": "ARA"},
        ],
        "portefeuilles": [
            {"nom": "Hypermarches", "description": "Hypermarches Casino France"},
            {"nom": "Proximite", "description": "Magasins Casino Proximite"},
            {"nom": "Logistique", "description": "Entrepots et plateformes logistiques"},
        ],
        "sizes": {
            "S": {"sites_per_pf": [12, 12, 12]},   # 36 sites
            "M": {"sites_per_pf": [24, 24, 24]},    # 72 sites
        },
        "site_groups": [
            {
                "prefix": "Hypermarche", "type_site": "commerce", "naf": "4711F",
                "surface_range": (3000, 12000), "psub_range": (100, 500),
                "profile": "retail", "employees_range": (50, 200),
                "cvc_w_per_m2": (30, 80), "parking_range": (1500, 5000),
                "parking_type": "outdoor", "roof_pct": (0.4, 0.8),
                "annual_kwh_range": (500000, 5000000),
                "gas_pct": 1.0,  # 100% have gas
            },
            {
                "prefix": "Casino Proxi", "type_site": "commerce", "naf": "4711F",
                "surface_range": (800, 2500), "psub_range": (30, 120),
                "profile": "retail", "employees_range": (5, 30),
                "cvc_w_per_m2": (20, 60), "parking_range": (200, 1000),
                "parking_type": "unknown", "roof_pct": (0.3, 0.6),
                "annual_kwh_range": (100000, 800000),
                "gas_pct": 0.3,
            },
            {
                "prefix": "Entrepot", "type_site": "entrepot", "naf": "5210B",
                "surface_range": (2000, 8000), "psub_range": (40, 200),
                "profile": "warehouse", "employees_range": (10, 80),
                "cvc_w_per_m2": (10, 40), "parking_range": (800, 3000),
                "parking_type": "outdoor", "roof_pct": (0.5, 0.9),
                "annual_kwh_range": (200000, 2000000),
                "gas_pct": 0.5,
            },
        ],
        "invoices_count": 15,
        "actions_count": 12,
    },
    "tertiaire": {
        "label": "SCI Les Terrasses — Tertiaire",
        "description": "10 batiments: bureaux, ecoles, hopital, hotel.",
        "org": {"nom": "SCI Les Terrasses", "type_client": "tertiaire", "siren": "888777666"},
        "entites": [
            {"nom": "SCI Les Terrasses SARL", "siren": "888777666", "siret": "88877766600012",
             "naf_code": "6820B", "region_code": "IDF"},
        ],
        "portefeuilles": [
            {"nom": "Bureaux & Services", "description": "Bureaux et services tertiaires"},
            {"nom": "Equipements publics", "description": "Ecoles, hopital, hotel"},
        ],
        "sizes": {
            "S": {"sites_per_pf": [5, 5]},   # 10 sites
            "M": {"sites_per_pf": [10, 10]},  # 20 sites
        },
        "site_groups": [
            {
                "prefix": "Bureau", "type_site": "bureau", "naf": "6820B",
                "surface_range": (800, 5000), "psub_range": (40, 200),
                "profile": "office", "employees_range": (20, 150),
                "cvc_w_per_m2": (25, 60), "parking_range": (500, 2000),
                "parking_type": "underground", "roof_pct": (0.3, 0.5),
                "annual_kwh_range": (100000, 1500000),
                "gas_pct": 0.4,
            },
            {
                "prefix": "Equipement", "type_site": "enseignement", "naf": "8520Z",
                "surface_range": (1500, 8000), "psub_range": (50, 250),
                "profiles": ["school", "hospital", "hotel", "office", "school"],
                "employees_range": (30, 300),
                "cvc_w_per_m2": (30, 80), "parking_range": (500, 3000),
                "parking_type": "outdoor", "roof_pct": (0.4, 0.7),
                "annual_kwh_range": (200000, 3000000),
                "gas_pct": 0.6,
            },
        ],
        "invoices_count": 5,
        "actions_count": 8,
    },
}


def get_pack(pack_name: str) -> dict:
    """Get pack definition by name."""
    return PACKS.get(pack_name)


def list_packs() -> list:
    """List available packs."""
    return [
        {"key": k, "label": v["label"], "description": v["description"],
         "sizes": list(v["sizes"].keys())}
        for k, v in PACKS.items()
    ]
