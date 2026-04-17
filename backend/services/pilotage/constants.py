"""
PROMEOS - Constantes pilotage : regles archetypes + calibrage Enedis 2024.

Deux dictionnaires :

1. ARCHETYPE_RULES
   Regles legeres de detection (signatures hebdomadaires, plages de pointe,
   signal de talon) utilisees par `usage_detector.detect_archetype()`.
   Historiquement hardcodees, conservees pour le fallback de detection.

2. ARCHETYPE_CALIBRATION_2024
   Calibrage quantitatif officiel issu du Barometre Flex 2026 (RTE / Enedis /
   GIMELEC, avril 2026). Alimente le scoring du potentiel pilotable :

     - taux_decalable_moyen       : part moyenne de conso decalable / effacable
     - plages_pointe_h            : plages horaires ou concentree la pointe
     - conso_journaliere_pointe_pct : part de la conso journaliere en pointe
     - bacs_penetration_2024      : taux d'equipement GTB/BACS 2024 (ref Enedis)
     - source                     : citation courte de la source

Sources primaires :
    - Barometre Flex 2026, RTE / Enedis / GIMELEC (avril 2026)
    - Enedis Open Data 2024 (taux BACS par segment tertiaire)
    - CRE - deliberation 2025-122 (modulation negative obligatoire 15/04/2026)

Les cles canoniques suivent la taxonomie `ARCHETYPE_TO_USAGES` du moteur flex
(`services.flex.flexibility_scoring_engine`). Pour les segments sans equivalent
direct (COMMERCE_SPECIALISE, HOTELLERIE), on aligne sur les codes publics du
Barometre afin de faciliter la lecture ; le resolveur archetype normalise.
"""

from __future__ import annotations


# --- 1. Regles archetypes (detection signatures) -----------------------------

# Heuristiques legeres : plages typiques de fonctionnement, continuite,
# presence d'un talon froid. Utilisees par usage_detector pour classifier un
# compteur inconnu en complement de la resolution NAF / KB.
#
# NB : le champ `plages_pointe_h` est partage avec ARCHETYPE_CALIBRATION_2024
# mais la source primaire reste le Barometre Flex 2026 (voir section 2).
ARCHETYPE_RULES: dict[str, dict] = {
    "BUREAU_STANDARD": {
        "horaires_ouverture": (7, 20),
        "continu_24_7": False,
        "talon_froid_attendu": False,
        "label": "Bureaux / tertiaire standard",
    },
    "COMMERCE_ALIMENTAIRE": {
        "horaires_ouverture": (8, 21),
        "continu_24_7": True,  # froid 24h/24
        "talon_froid_attendu": True,
        "label": "Commerce alimentaire / GMS",
    },
    "COMMERCE_SPECIALISE": {
        "horaires_ouverture": (10, 20),
        "continu_24_7": False,
        "talon_froid_attendu": False,
        "label": "Commerce non alimentaire",
    },
    "LOGISTIQUE_FRIGO": {
        "horaires_ouverture": (0, 24),
        "continu_24_7": True,
        "talon_froid_attendu": True,
        "label": "Logistique frigorifique",
    },
    "ENSEIGNEMENT": {
        "horaires_ouverture": (8, 18),
        "continu_24_7": False,
        "talon_froid_attendu": False,
        "label": "Enseignement",
    },
    "SANTE": {
        "horaires_ouverture": (0, 24),
        "continu_24_7": True,
        "talon_froid_attendu": False,
        "label": "Sante",
    },
    "HOTELLERIE": {
        "horaires_ouverture": (0, 24),
        "continu_24_7": True,
        "talon_froid_attendu": False,
        "label": "Hotellerie / hebergement",
    },
    "INDUSTRIE_LEGERE": {
        "horaires_ouverture": (6, 18),
        "continu_24_7": False,
        "talon_froid_attendu": False,
        "label": "Industrie legere",
    },
}


# --- 2. Calibrage Barometre Flex 2026 ----------------------------------------

# Source principale : Barometre Flex 2026 (RTE / Enedis / GIMELEC, avril 2026).
# Chiffres officiels 2024 (annee de reference du barometre) :
#   - BACS %             : taux d'equipement GTB/BACS conforme decret tertiaire
#   - taux_decalable     : part moyenne de conso decalable / effacable (%)
#   - plages_pointe_h    : tranches horaires [heure_debut, heure_fin) de pointe
#   - conso_pointe_pct   : part de la conso journaliere concentree sur la pointe
#
# Conventions :
#   - taux_decalable_moyen est une FRACTION (0.0 a 1.0), pas un pourcentage.
#   - plages_pointe_h est une liste de tuples (h_debut, h_fin) avec 0 <= h < 24.
#     Les plages utilisent la convention [debut, fin) -- fin exclusif.
#   - conso_journaliere_pointe_pct est une FRACTION (0.0 a 1.0).
#   - bacs_penetration_2024 est une FRACTION (0.0 a 1.0).
ARCHETYPE_CALIBRATION_2024: dict[str, dict] = {
    "BUREAU_STANDARD": {
        "taux_decalable_moyen": 0.30,
        "plages_pointe_h": [(7, 10), (17, 20)],
        "conso_journaliere_pointe_pct": 0.28,
        "bacs_penetration_2024": 0.17,
        "source": "Baromètre Flex 2026 RTE/Enedis/GIMELEC - Bureaux",
    },
    "COMMERCE_ALIMENTAIRE": {
        # Froid commercial predominant + ECS : potentiel decalable eleve.
        "taux_decalable_moyen": 0.45,
        "plages_pointe_h": [(10, 20)],
        "conso_journaliere_pointe_pct": 0.55,
        "bacs_penetration_2024": 0.17,  # fourchette 15-19%, mediane retenue
        "source": "Baromètre Flex 2026 RTE/Enedis/GIMELEC - Commerces alimentaires",
    },
    "COMMERCE_SPECIALISE": {
        "taux_decalable_moyen": 0.25,
        "plages_pointe_h": [(10, 19)],
        "conso_journaliere_pointe_pct": 0.45,
        "bacs_penetration_2024": 0.17,
        "source": "Baromètre Flex 2026 RTE/Enedis/GIMELEC - Commerces non alimentaires",
    },
    "LOGISTIQUE_FRIGO": {
        # Froid inertie 24h/24 : gisement le plus important.
        "taux_decalable_moyen": 0.55,
        "plages_pointe_h": [(0, 24)],
        "conso_journaliere_pointe_pct": 1.0,
        "bacs_penetration_2024": 0.23,
        "source": "Baromètre Flex 2026 RTE/Enedis/GIMELEC - Logistique frigorifique",
    },
    "ENSEIGNEMENT": {
        "taux_decalable_moyen": 0.20,
        "plages_pointe_h": [(8, 17)],
        "conso_journaliere_pointe_pct": 0.50,
        "bacs_penetration_2024": 0.13,
        "source": "Baromètre Flex 2026 RTE/Enedis/GIMELEC - Enseignement",
    },
    "SANTE": {
        # Contraintes medicales fortes : faible decalabilite.
        "taux_decalable_moyen": 0.15,
        "plages_pointe_h": [(0, 24)],
        "conso_journaliere_pointe_pct": 1.0,
        "bacs_penetration_2024": 0.40,
        "source": "Baromètre Flex 2026 RTE/Enedis/GIMELEC - Sante",
    },
    "HOTELLERIE": {
        # Clim + ECS : double pointe matin/soir.
        "taux_decalable_moyen": 0.35,
        "plages_pointe_h": [(6, 10), (18, 23)],
        "conso_journaliere_pointe_pct": 0.48,
        "bacs_penetration_2024": 0.11,
        "source": "Baromètre Flex 2026 RTE/Enedis/GIMELEC - Hotellerie",
    },
    "INDUSTRIE_LEGERE": {
        "taux_decalable_moyen": 0.35,
        "plages_pointe_h": [(6, 18)],
        "conso_journaliere_pointe_pct": 0.60,
        "bacs_penetration_2024": 0.20,  # estimation GIMELEC (non publie par Enedis)
        "source": "Baromètre Flex 2026 GIMELEC - Industrie legere (estimation)",
    },
}


# Bornes de sanity check (utilisees par les tests et par le scoring defensif).
TAUX_DECALABLE_MIN = 0.10
TAUX_DECALABLE_MAX = 0.60


# --- 3. Creneaux TURPE 7 HC saisonnalises ------------------------------------
#
# Source officielle : Barometre Flex 2026 (RTE / Enedis / GIMELEC / Think
# Smartgrids / IGNES / ACTEE / IFPEB / SBA), avril 2026.
#
# Le TURPE 7 d'Enedis introduit a partir de decembre 2026 (phase 2, 22,8 M
# clients residentiels + pro <= 36 kVA) des creneaux Heures Creuses
# saisonnalises ete / hiver destines a "favoriser" ou "exclure" certaines
# plages horaires :
#
#   Saison BASSE (ete, 1/04 -> 31/10)
#     A FAVORISER : 2h-6h  + 11h-17h  (heures solaires, surplus PV)
#     A EXCLURE   : 7h-11h + 18h-23h  (montees matin / pic soir)
#
#   Saison HAUTE (hiver, 1/11 -> 31/03)
#     A FAVORISER : 2h-6h  + 21h-24h  (creux nocturnes)
#     A EXCLURE   : 7h-11h + 17h-21h  (pointe matin + pic soir)
#
# Convention : chaque tuple (h_debut, h_fin) designe l'intervalle horaire
# [h_debut, h_fin) sur l'heure locale Europe/Paris. Les creneaux sont un
# INDICE ADDITIONNEL, pas un substitut au signal prix : le moteur de
# detection `classify_slots` les utilise uniquement pour trancher les slots
# marginaux (prix au centre de la distribution).
HC_TURPE7_FAVORABLE: dict[str, list[tuple[int, int]]] = {
    "ete": [(2, 6), (11, 17)],
    "hiver": [(2, 6), (21, 24)],
}
HC_TURPE7_EXCLURE: dict[str, list[tuple[int, int]]] = {
    "ete": [(7, 11), (18, 23)],
    "hiver": [(7, 11), (17, 21)],
}

# Saison basse = avril (4) a octobre (10) inclus. Hors de cet ensemble ->
# saison haute (hiver). Convention Enedis TURPE 7 : 1/04 -> 31/10 ete.
SAISON_BASSE_MOIS: set[int] = {4, 5, 6, 7, 8, 9, 10}  # avril-octobre


def get_calibration(archetype_code: str) -> dict | None:
    """Retourne le calibrage 2024 pour un archetype, ou None si absent."""
    return ARCHETYPE_CALIBRATION_2024.get(archetype_code)


# --- Fallbacks transverses partages entre flex_ready.py et routes/pilotage.py --
#
# Tarif de base fallback pour un Site reel sans EnergyContract rattache.
# Calibre sur moyenne TRVE tertiaire BT 2026. Doctrine "indicative" : le
# payload porte la trace `prix_source="site_sans_contrat_fallback"` quand
# cette valeur est retenue.
#
# Source unique : evite toute derive entre `_load_flex_ready_ctx` (routes) et
# `build_flex_ready_signals` (service).
TARIF_BASE_FALLBACK_EUR_KWH: float = 0.175


# --- 4. Mapping TypeSite -> archetype + puissance pilotable median ----------
#
# Utilise par le seed et le wiring automatique quand un Site n'a ni archetype
# renseigne manuellement ni correspondance canonique sur le nom. Les valeurs
# kW sont des medianes calibrees Barometre Flex 2026 par segment tertiaire.
#
# Garder en sync avec ARCHETYPE_CALIBRATION_2024 : toutes les cles de droite
# doivent exister dans ARCHETYPE_CALIBRATION_2024 (ou fallback BUREAU_STANDARD).
TYPESITE_ARCHETYPE_FALLBACK: dict[str, tuple[str, float]] = {
    # TypeSite.value -> (archetype_code, puissance_pilotable_kw_median)
    "magasin": ("COMMERCE_ALIMENTAIRE", 80.0),
    "commerce": ("COMMERCE_SPECIALISE", 40.0),
    "bureau": ("BUREAU_STANDARD", 50.0),
    "entrepot": ("LOGISTIQUE_FRIGO", 60.0),
    "usine": ("INDUSTRIE_LEGERE", 150.0),
    "hotel": ("HOTELLERIE", 45.0),
    "sante": ("SANTE", 70.0),
    "enseignement": ("ENSEIGNEMENT", 35.0),
}


# Sites canoniques de la demo -- donnees exactes recommandees par l'equipe
# produit (Hypermarche Montreuil, Tour Haussmann, Entrepot Rungis). Utilise
# par le seed pour forcer le match sur les 3 sites vedettes.
CANONICAL_SITE_PILOTAGE: dict[str, tuple[str, float]] = {
    # Nom normalise (lowercase + accents strippes) -> (archetype, kw)
    "carrefour montreuil": ("COMMERCE_ALIMENTAIRE", 220.0),
    "hypermarche montreuil": ("COMMERCE_ALIMENTAIRE", 220.0),
    "tour haussmann": ("BUREAU_STANDARD", 120.0),
    "bureau haussmann": ("BUREAU_STANDARD", 120.0),
    "entrepot rungis": ("LOGISTIQUE_FRIGO", 85.0),
}
