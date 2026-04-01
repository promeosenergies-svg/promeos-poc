"""
PROMEOS — Archetype Recommendation Service
Recommandations HP/HC et tarif basées sur l'archétype du site.
15 archétypes × 732 NAF irriguent Patrimoine, Usages, Billing ET Achat.
"""

# Profils HP/HC par archétype (% HP / % HC)
_ARCHETYPE_PROFILES = {
    "bureau": {
        "hp_pct": 70,
        "hc_pct": 30,
        "profil": "journalier",
        "ths_pertinent": False,
        "description": "Consommation concentrée en heures ouvrées (8h-19h L-V)",
    },
    "commerce": {
        "hp_pct": 65,
        "hc_pct": 35,
        "profil": "journalier_etendu",
        "ths_pertinent": False,
        "description": "Consommation étendue (9h-21h L-S)",
    },
    "hotel": {
        "hp_pct": 55,
        "hc_pct": 45,
        "profil": "continu",
        "ths_pertinent": True,
        "description": "Consommation continue 24/7, pic soirée/matin",
    },
    "hotellerie": {
        "hp_pct": 55,
        "hc_pct": 45,
        "profil": "continu",
        "ths_pertinent": True,
        "description": "Consommation continue 24/7, pic soirée/matin",
    },
    "entrepot": {
        "hp_pct": 40,
        "hc_pct": 60,
        "profil": "plat",
        "ths_pertinent": True,
        "description": "Charge plate, forte proportion HC — contrat HC avantageux",
    },
    "logistique": {
        "hp_pct": 40,
        "hc_pct": 60,
        "profil": "plat",
        "ths_pertinent": True,
        "description": "Charge plate, forte proportion HC",
    },
    "usine": {
        "hp_pct": 45,
        "hc_pct": 55,
        "profil": "industriel",
        "ths_pertinent": True,
        "description": "Production continue ou 2×8, HC important — THS pertinent",
    },
    "industrie": {
        "hp_pct": 45,
        "hc_pct": 55,
        "profil": "industriel",
        "ths_pertinent": True,
        "description": "Production continue ou 2×8, HC important — THS pertinent",
    },
    "enseignement": {
        "hp_pct": 75,
        "hc_pct": 25,
        "profil": "scolaire",
        "ths_pertinent": False,
        "description": "Consommation scolaire (8h-18h L-V, vacances creuses)",
    },
    "sante": {
        "hp_pct": 50,
        "hc_pct": 50,
        "profil": "continu_medical",
        "ths_pertinent": True,
        "description": "Consommation continue avec pointe diurne — THS pertinent",
    },
    "magasin": {
        "hp_pct": 65,
        "hc_pct": 35,
        "profil": "journalier_etendu",
        "ths_pertinent": False,
        "description": "Consommation en horaires d'ouverture",
    },
    "copropriete": {
        "hp_pct": 50,
        "hc_pct": 50,
        "profil": "residentiel",
        "ths_pertinent": False,
        "description": "Profil résidentiel mixte",
    },
    "logement_social": {
        "hp_pct": 50,
        "hc_pct": 50,
        "profil": "residentiel",
        "ths_pertinent": False,
        "description": "Profil résidentiel mixte",
    },
    "collectivite": {
        "hp_pct": 65,
        "hc_pct": 35,
        "profil": "administratif",
        "ths_pertinent": False,
        "description": "Horaires administratifs, profil bureau étendu",
    },
}

# Recommandation stratégie d'achat par archétype
_STRATEGY_AFFINITY = {
    "bureau": "fixe",
    "commerce": "fixe",
    "hotel": "indexe",
    "hotellerie": "indexe",
    "entrepot": "spot",
    "logistique": "spot",
    "usine": "indexe",
    "industrie": "indexe",
    "enseignement": "fixe",
    "sante": "fixe",
    "magasin": "fixe",
    "copropriete": "fixe",
    "logement_social": "fixe",
    "collectivite": "fixe",
}


def get_archetype_recommendation(type_site: str) -> dict:
    """
    Retourne la recommandation HP/HC et stratégie d'achat pour un archétype.
    """
    profile = _ARCHETYPE_PROFILES.get(type_site, _ARCHETYPE_PROFILES["bureau"])
    strategy = _STRATEGY_AFFINITY.get(type_site, "fixe")

    return {
        "archetype": type_site,
        "profil_hp_hc": {
            "hp_pct": profile["hp_pct"],
            "hc_pct": profile["hc_pct"],
            "profil_type": profile["profil"],
            "ths_pertinent": profile["ths_pertinent"],
            "description": profile["description"],
        },
        "strategie_recommandee": strategy,
        "conseil": _build_conseil(type_site, profile, strategy),
    }


def _build_conseil(type_site: str, profile: dict, strategy: str) -> str:
    """Génère un conseil textuel adapté."""
    parts = []
    if profile["hc_pct"] >= 50:
        parts.append(
            f"Profil à dominante HC ({profile['hc_pct']}%) — privilégiez un contrat valorisant les heures creuses."
        )
    else:
        parts.append(f"Profil HP dominant ({profile['hp_pct']}%) — la négociation du prix HP est prioritaire.")

    if profile["ths_pertinent"]:
        parts.append("Le THS (Très Heures Super-creuses) est pertinent pour ce type de site.")

    strategy_labels = {"fixe": "prix fixe", "indexe": "indexé marché", "spot": "spot/ARENH+"}
    parts.append(f"Stratégie d'achat recommandée : {strategy_labels.get(strategy, strategy)}.")

    return " ".join(parts)
