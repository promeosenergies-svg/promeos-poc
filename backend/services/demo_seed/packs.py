"""
PROMEOS - Demo Pack Definitions
Helios: 5 sites E2E (bureaux, industrie, hotel, ecole) — demo canonique
Tertiaire: 10 buildings (bureaux, ecoles, hopitaux, hotels) — legacy
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
    "Avenue de la Republique",
    "Rue Victor Hugo",
    "Boulevard Gambetta",
    "Rue de la Liberte",
    "Avenue Jean Jaures",
    "Rue Pasteur",
    "Place de la Mairie",
    "Rue du Commerce",
    "Boulevard Haussmann",
    "Rue de Rivoli",
    "Avenue des Champs",
    "Rue Nationale",
]


PACKS = {
    "tertiaire": {
        "visible": False,  # V55: legacy — hidden from UI, kept for tests/rollback
        "label": "SCI Les Terrasses — Tertiaire",
        "description": "10 batiments: bureaux, ecoles, hopital, hotel.",
        "org": {"nom": "SCI Les Terrasses", "type_client": "tertiaire", "siren": "888777666"},
        "entites": [
            {
                "nom": "SCI Les Terrasses SARL",
                "siren": "888777666",
                "siret": "88877766600012",
                "naf_code": "6820B",
                "region_code": "IDF",
            },
        ],
        "portefeuilles": [
            {"nom": "Bureaux & Services", "description": "Bureaux et services tertiaires"},
            {"nom": "Equipements publics", "description": "Ecoles, hopital, hotel"},
        ],
        "sizes": {
            "S": {"sites_per_pf": [5, 5]},  # 10 sites
            "M": {"sites_per_pf": [10, 10]},  # 20 sites
        },
        "site_groups": [
            {
                "prefix": "Bureau",
                "type_site": "bureau",
                "naf": "6820B",
                "surface_range": (800, 5000),
                "psub_range": (40, 200),
                "profile": "office",
                "employees_range": (20, 150),
                "cvc_w_per_m2": (25, 60),
                "parking_range": (500, 2000),
                "parking_type": "underground",
                "roof_pct": (0.3, 0.5),
                "annual_kwh_range": (100000, 1500000),
                "gas_pct": 0.4,
            },
            {
                "prefix": "Equipement",
                "type_site": "enseignement",
                "naf": "8520Z",
                "surface_range": (1500, 8000),
                "psub_range": (50, 250),
                "profiles": ["school", "hospital", "hotel", "office", "school"],
                "employees_range": (30, 300),
                "cvc_w_per_m2": (30, 80),
                "parking_range": (500, 3000),
                "parking_type": "outdoor",
                "roof_pct": (0.4, 0.7),
                "annual_kwh_range": (200000, 3000000),
                "gas_pct": 0.6,
            },
        ],
        "invoices_count": 5,
        "actions_count": 8,
    },
    # ══════════════════════════════════════════════════════════════════════════
    # HELIOS — Demo E2E canonique (V52)
    # 3 entites, 5 sites, 7 batiments, couvre toutes les briques PROMEOS
    # ══════════════════════════════════════════════════════════════════════════
    "helios": {
        "visible": True,
        "is_default": True,
        "label": "Groupe HELIOS — Mixte (E2E)",
        "description": "3 entites, 5 sites, 7 batiments. Bureaux, industrie, hotel, ecole.",
        "org": {"nom": "Groupe HELIOS", "type_client": "mixte", "siren": "123456789"},
        "entites": [
            {
                "nom": "HELIOS Immobilier SAS",
                "siren": "123456789",
                "siret": "12345678900014",
                "naf_code": "6820B",
                "region_code": "IDF",
            },
            {
                "nom": "HELIOS Industrie SARL",
                "siren": "234567890",
                "siret": "23456789000028",
                "naf_code": "2511Z",
                "region_code": "ARA",
            },
            {
                "nom": "HELIOS Services SCI",
                "siren": "345678901",
                "siret": "34567890100015",
                "naf_code": "6820A",
                "region_code": "PACA",
            },
        ],
        "portefeuilles": [
            {"nom": "Siege & Bureaux", "description": "Siege social et bureaux regionaux", "entite_idx": 0},
            {"nom": "Sites Industriels", "description": "Usines et entrepots", "entite_idx": 1},
            {"nom": "Patrimoine Tertiaire", "description": "Hotels, ecoles", "entite_idx": 2},
        ],
        "sizes": {"S": {}},
        "sites_explicit": [
            {
                "nom": "Siege HELIOS Paris",
                "portefeuille_idx": 0,
                "ville": "Paris",
                "cp": "75008",
                "region": "IDF",
                "lat": 48.8738,
                "lon": 2.2950,
                "type_site": "bureau",
                "profile": "office",
                "naf": "6820B",
                "surface_m2": 3500,
                "tertiaire_area_m2": 3500,
                "employees": 120,
                "psub_kva": 200,
                "annual_kwh": 800000,
                "cvc_kw": 300,
                "parking_m2": 1200,
                "roof_m2": 800,
                "parking_type": "underground",
                "operat_status": "SUBMITTED",
                "buildings": [
                    {"nom": "Batiment A — Siege", "surface_m2": 2000, "annee": 1995, "cvc_kw": 200},
                    {"nom": "Batiment B — Annexe", "surface_m2": 1500, "annee": 2010, "cvc_kw": 100},
                ],
                "gas": True,
            },
            {
                "nom": "Bureau Regional Lyon",
                "portefeuille_idx": 0,
                "ville": "Lyon",
                "cp": "69002",
                "region": "ARA",
                "lat": 45.7580,
                "lon": 4.8320,
                "type_site": "bureau",
                "profile": "office",
                "naf": "6820B",
                "surface_m2": 1200,
                "tertiaire_area_m2": 1200,
                "employees": 35,
                "psub_kva": 80,
                "annual_kwh": 350000,
                "cvc_kw": 50,
                "parking_m2": 400,
                "roof_m2": 300,
                "parking_type": "outdoor",
                "operat_status": "IN_PROGRESS",
                "buildings": [
                    {"nom": "Batiment principal", "surface_m2": 1200, "annee": 2005, "cvc_kw": 50},
                ],
                "gas": False,
            },
            {
                "nom": "Usine HELIOS Toulouse",
                "portefeuille_idx": 1,
                "ville": "Toulouse",
                "cp": "31100",
                "region": "OCC",
                "lat": 43.5780,
                "lon": 1.4020,
                "type_site": "entrepot",
                "profile": "warehouse",
                "naf": "2511Z",
                "surface_m2": 6000,
                "tertiaire_area_m2": None,
                "employees": 85,
                "psub_kva": 400,
                "annual_kwh": 2500000,
                "cvc_kw": 150,
                "parking_m2": 2000,
                "roof_m2": 3000,
                "parking_type": "outdoor",
                "operat_status": None,
                "buildings": [
                    {"nom": "Batiment industriel", "surface_m2": 6000, "annee": 1988, "cvc_kw": 150},
                ],
                "gas": True,
            },
            {
                "nom": "Hotel Helios Nice",
                "portefeuille_idx": 2,
                "ville": "Nice",
                "cp": "06000",
                "region": "PACA",
                "lat": 43.7050,
                "lon": 7.2650,
                "type_site": "hotel",
                "profile": "hotel",
                "naf": "5510Z",
                "surface_m2": 4000,
                "tertiaire_area_m2": 4000,
                "employees": 60,
                "psub_kva": 250,
                "annual_kwh": 1200000,
                "cvc_kw": 280,
                "parking_m2": 800,
                "roof_m2": 600,
                "parking_type": "underground",
                "operat_status": "NOT_STARTED",
                "buildings": [
                    {"nom": "Batiment hotel", "surface_m2": 4000, "annee": 2000, "cvc_kw": 280},
                ],
                "gas": True,
            },
            {
                "nom": "Ecole Jules Ferry Marseille",
                "portefeuille_idx": 2,
                "ville": "Marseille",
                "cp": "13005",
                "region": "PACA",
                "lat": 43.2950,
                "lon": 5.3950,
                "type_site": "enseignement",
                "profile": "school",
                "naf": "8520Z",
                "surface_m2": 2800,
                "tertiaire_area_m2": 2800,
                "employees": 45,
                "psub_kva": 150,
                "annual_kwh": 600000,
                "cvc_kw": 120,
                "parking_m2": 600,
                "roof_m2": 1200,
                "parking_type": "outdoor",
                "operat_status": "IN_PROGRESS",
                "buildings": [
                    {"nom": "Batiment principal — Ecole", "surface_m2": 2000, "annee": 1975, "cvc_kw": 80},
                    {"nom": "Gymnase", "surface_m2": 800, "annee": 2015, "cvc_kw": 40},
                ],
                "gas": False,
            },
        ],
        # Billing: explicit contracts per site
        "contracts_spec": [
            # S0 Siege Paris — elec fixe long, gaz indexe 90j
            {
                "site_idx": 0,
                "type": "elec",
                "supplier": "EDF",
                "strategy": "fixe",
                "start": "2024-01-01",
                "end": "2026-12-31",
                "price": 0.1450,
                "fee": 180,
                "auto_renew": True,
            },
            {
                "site_idx": 0,
                "type": "gaz",
                "supplier": "Engie",
                "strategy": "indexe",
                "start": "2023-06-01",
                "end": "EXPIRING_90",
                "price": 0.0850,
                "fee": 60,
                "auto_renew": False,
            },
            # S1 Bureau Lyon — elec fixe 60j urgent, gaz spot 30j critique
            {
                "site_idx": 1,
                "type": "elec",
                "supplier": "TotalEnergies",
                "strategy": "fixe",
                "start": "2024-07-01",
                "end": "EXPIRING_SOON",
                "price": 0.1680,
                "fee": 45,
                "auto_renew": False,
            },
            {
                "site_idx": 1,
                "type": "gaz",
                "supplier": "Eni",
                "strategy": "spot",
                "start": "2024-03-01",
                "end": "EXPIRING_30",
                "price": 0.0720,
                "fee": 35,
                "auto_renew": False,
            },
            # S2 Usine Toulouse — elec indexe 180j, gaz hybride 90j
            {
                "site_idx": 2,
                "type": "elec",
                "supplier": "Vattenfall",
                "strategy": "indexe",
                "start": "2024-01-01",
                "end": "EXPIRING_180",
                "price": 0.1320,
                "fee": 120,
                "auto_renew": True,
            },
            {
                "site_idx": 2,
                "type": "gaz",
                "supplier": "Eni",
                "strategy": "hybride",
                "start": "2024-01-01",
                "end": "EXPIRING_90",
                "price": 0.0780,
                "fee": 50,
                "auto_renew": False,
            },
            # S3 Hotel Nice — elec fixe 180j, gaz indexe 1an
            {
                "site_idx": 3,
                "type": "elec",
                "supplier": "EDF",
                "strategy": "fixe",
                "start": "2024-01-01",
                "end": "EXPIRING_180",
                "price": 0.1550,
                "fee": 95,
                "auto_renew": True,
            },
            {
                "site_idx": 3,
                "type": "gaz",
                "supplier": "Engie",
                "strategy": "indexe",
                "start": "2024-01-01",
                "end": "2026-12-31",
                "price": 0.0900,
                "fee": 40,
                "auto_renew": False,
            },
            # S4 Ecole Marseille — elec fixe long
            {
                "site_idx": 4,
                "type": "elec",
                "supplier": "Engie",
                "strategy": "fixe",
                "start": "2024-09-01",
                "end": "2027-08-31",
                "price": 0.1380,
                "fee": 55,
                "auto_renew": True,
            },
        ],
        "readings_frequency": "monthly",
        "readings_months": 60,
        "hourly_days": 730,  # V85: 2 ans d'historique horaire (signature energetique, EMS Explorer)
        "min15_days": 365,  # V107: 365 jours 15-min (world-class demo realism)
        "invoices_count": 60,  # V87: 12 mois x 5 sites = historique annuel complet
        "actions_count": 15,
    },
}


def get_pack(pack_name: str) -> dict:
    """Get pack definition by name."""
    return PACKS.get(pack_name)


def list_packs(include_hidden: bool = False) -> list:
    """List available packs. Only visible packs by default."""
    return [
        {
            "key": k,
            "label": v["label"],
            "description": v["description"],
            "sizes": list(v["sizes"].keys()),
            "is_default": v.get("is_default", False),
        }
        for k, v in PACKS.items()
        if include_hidden or v.get("visible", True)
    ]
