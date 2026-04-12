"""
Moteur de score de flexibilite par usage.

SOURCES :
- Matrice usages x mecanismes : PDF "Analyse mecanismes flexibilite" (2026)
- Deep-research docs flexibilite France 2026+
- RM-5-NEBCO-V01 (RTE, 01/09/2025) : seuil 100 kW/pas
- RTE Bilan electrique 2025 : 513h prix negatifs

LOGIQUE DE SCORE (0.0 - 1.0) :
Score flexibilite = moyenne ponderee de 5 dimensions :
  1. Pilotabilite       (30%) : capacite technique a moduler
  2. NEBCO-compatibilite(25%) : eligibilite NEBCO directe ou via agregation
  3. Valeur tarifaire   (20%) : gain HP/HC, dynamique, puissance souscrite
  4. Facilite d'acces   (15%) : instrumentation requise (simple - complexe)
  5. Duree d'activation (10%) : duree soutenable (plus long = plus flexible)

Score global site = max(scores usages detectes) + bonus_multi_usages (max +15%)
"""

from dataclasses import dataclass, field
from datetime import datetime

from services.power.nebco_eligibility_engine import SEUIL_NEBCO_KW  # 100 kW, RM-5-NEBCO-V01


# --- Constantes issues des sources officielles ---
PRIX_NEGATIF_SEUIL_EUR_MWH = -10.0  # RTE/CRE : seuil alerte anticipation
PRIX_POSITIF_SEUIL_EUR_MWH = 100.0  # RTE Bilan 2025 : seuil alerte effacement
HEURES_NEGATIVES_2025 = 513  # RTE Bilan electrique 2025


# --- Referentiel 15 usages ---

USAGE_PROFILES = {
    "CVC_HVAC": {
        "label": "CVC / HVAC (chauffage, ventilation, climatisation)",
        "pilotabilite": 0.80,
        "duree_max_h": 4.0,
        "impact_confort": "MOYEN",
        "inertie_thermique": True,
        "instrumentation_requise": "GTB/BACS + capteurs T\u00b0",
        "nebco_compat": "PORTFOLIO",
        "valeur_tarifaire": 0.85,
        "facilite_acces": 0.70,
        "mecanismes": ["NEBCO", "RESERVE_COMP", "AOFD", "FLEX_LOCALE", "HP_HC", "TEMPO"],
        "modulations": ["EFFACEMENT", "ANTICIPATION"],
        "priorite_promeos": "HAUTE",
    },
    "ECS": {
        "label": "Eau Chaude Sanitaire (ballons thermiques)",
        "pilotabilite": 0.90,
        "duree_max_h": 8.0,
        "impact_confort": "FAIBLE",
        "inertie_thermique": True,
        "instrumentation_requise": "Contacteur + relev\u00e9 Linky",
        "nebco_compat": "OUI_AGR",
        "valeur_tarifaire": 0.90,
        "facilite_acces": 0.90,
        "mecanismes": ["HP_HC", "NEBCO", "DYNAMIQUE", "TEMPO"],
        "modulations": ["EFFACEMENT", "ANTICIPATION"],
        "heures_solaires_applicable": True,
        "priorite_promeos": "HAUTE",
    },
    "FROID_COMMERCIAL": {
        "label": "Froid commercial (vitrines, chambres froides GMS)",
        "pilotabilite": 0.90,
        "duree_max_h": 2.0,
        "impact_confort": "FAIBLE",
        "inertie_thermique": True,
        "instrumentation_requise": "Supervision froid + sondes T\u00b0 + PLC/BACnet",
        "nebco_compat": "OUI_MULTISITE",
        "valeur_tarifaire": 0.80,
        "facilite_acces": 0.70,
        "mecanismes": ["NEBCO", "RESERVE_COMP", "AOFD", "FLEX_LOCALE", "HP_HC"],
        "modulations": ["EFFACEMENT"],
        "priorite_promeos": "HAUTE",
    },
    "FROID_INDUSTRIEL": {
        "label": "Froid industriel / entrep\u00f4ts logistiques",
        "pilotabilite": 0.80,
        "duree_max_h": 3.0,
        "impact_confort": "MOYEN",
        "inertie_thermique": True,
        "instrumentation_requise": "SCADA + capteurs T\u00b0 + mod\u00e8les thermiques",
        "nebco_compat": "OUI_SITE_GROS",
        "valeur_tarifaire": 0.80,
        "facilite_acces": 0.60,
        "mecanismes": ["NEBCO", "RESERVE_COMP", "CAPACITE", "AOFD", "FLEX_LOCALE"],
        "modulations": ["EFFACEMENT"],
        "priorite_promeos": "HAUTE",
    },
    "AIR_COMPRIME": {
        "label": "Air comprim\u00e9 (compresseurs + r\u00e9servoirs)",
        "pilotabilite": 0.75,
        "duree_max_h": 0.75,
        "impact_confort": "MOYEN",
        "inertie_thermique": False,
        "instrumentation_requise": "Capteurs pression + commande surcompresseur",
        "nebco_compat": "OUI_SITE_GROS",
        "valeur_tarifaire": 0.70,
        "facilite_acces": 0.65,
        "mecanismes": ["NEBCO", "RESERVE_COMP", "AOFD"],
        "modulations": ["EFFACEMENT"],
        "priorite_promeos": "MOYENNE",
    },
    "POMPES": {
        "label": "Pompes et syst\u00e8mes hydrauliques",
        "pilotabilite": 0.70,
        "duree_max_h": 2.0,
        "impact_confort": "MOYEN",
        "inertie_thermique": False,
        "instrumentation_requise": "Variateurs de vitesse + capteurs pression + SCADA",
        "nebco_compat": "PORTFOLIO",
        "valeur_tarifaire": 0.65,
        "facilite_acces": 0.60,
        "mecanismes": ["NEBCO", "RESERVE_COMP", "AFFRR_VARIATEUR", "AOFD"],
        "modulations": ["EFFACEMENT"],
        "priorite_promeos": "MOYENNE",
    },
    "IRVE": {
        "label": "IRVE (recharge v\u00e9hicules \u00e9lectriques)",
        "pilotabilite": 0.95,
        "duree_max_h": 8.0,
        "impact_confort": "FAIBLE",
        "inertie_thermique": False,
        "instrumentation_requise": "Bornes intelligentes OCPP + API + donn\u00e9es r\u00e9servation",
        "nebco_compat": "OUI_NATURELLE",
        "valeur_tarifaire": 0.90,
        "facilite_acces": 0.85,
        "mecanismes": ["NEBCO", "RESERVE_COMP", "AFFRR_BATTERIES", "HP_HC", "DYNAMIQUE", "FLEX_LOCALE"],
        "modulations": ["EFFACEMENT", "ANTICIPATION", "REPORT"],
        "heures_solaires_applicable": True,
        "priorite_promeos": "HAUTE",
    },
    "BATTERIES": {
        "label": "Batteries stationnaires (BESS)",
        "pilotabilite": 1.0,
        "duree_max_h": 4.0,
        "impact_confort": "NUL",
        "inertie_thermique": False,
        "instrumentation_requise": "EMS + mesure SOC + contr\u00f4le bidirectionnel",
        "nebco_compat": "OUI_MULTI",
        "valeur_tarifaire": 0.95,
        "facilite_acces": 0.70,
        "mecanismes": ["NEBCO_ANTICIPATION", "RESERVE_RAPIDE", "AFFRR", "CAPACITE", "AOFD", "FLEX_LOCALE"],
        "modulations": ["EFFACEMENT", "ANTICIPATION", "REPORT"],
        "signal_prix_negatifs": True,
        "priorite_promeos": "HAUTE",
    },
    "STOCKAGE_THERM": {
        "label": "Stockage thermique (pr\u00e9-chauffe/pr\u00e9-refroidissement)",
        "pilotabilite": 0.85,
        "duree_max_h": 12.0,
        "impact_confort": "FAIBLE",
        "inertie_thermique": True,
        "instrumentation_requise": "GTB + mod\u00e8le thermique + inertie calcul\u00e9e",
        "nebco_compat": "OUI_DISCIPLINE",
        "valeur_tarifaire": 0.85,
        "facilite_acces": 0.65,
        "mecanismes": ["NEBCO", "HP_HC", "DYNAMIQUE"],
        "modulations": ["EFFACEMENT", "ANTICIPATION"],
        "priorite_promeos": "HAUTE",
    },
    "PV_COUPLAGE": {
        "label": "Photovolta\u00efque + gestion surplus",
        "pilotabilite": 0.70,
        "duree_max_h": 8.0,
        "impact_confort": "FAIBLE",
        "inertie_thermique": False,
        "instrumentation_requise": "Mesure production + onduleurs pilotables + EMS",
        "nebco_compat": "INDIRECT",
        "valeur_tarifaire": 0.75,
        "facilite_acces": 0.70,
        "mecanismes": ["NEBCO_ANTICIPATION", "AOFD", "CAPACITE", "FLEX_LOCALE"],
        "modulations": ["ANTICIPATION"],
        "signal_prix_negatifs": True,
        "priorite_promeos": "HAUTE",
    },
    "PROCESS_BATCH": {
        "label": "Process batch (fours, machines, production planifiable)",
        "pilotabilite": 0.75,
        "duree_max_h": 4.0,
        "impact_confort": "MOYEN",
        "inertie_thermique": False,
        "instrumentation_requise": "MES/SCADA + planification ERP",
        "nebco_compat": "OUI_PLANIF",
        "valeur_tarifaire": 0.70,
        "facilite_acces": 0.50,
        "mecanismes": ["NEBCO_REPORT", "AOFD", "CAPACITE"],
        "modulations": ["REPORT"],
        "priorite_promeos": "MOYENNE",
    },
    "PROCESS_CONTINU": {
        "label": "Process continu (arr\u00eats co\u00fbteux)",
        "pilotabilite": 0.20,
        "duree_max_h": 0.1,
        "impact_confort": "HAUT",
        "inertie_thermique": False,
        "instrumentation_requise": "SCADA + instrumentation lourde",
        "nebco_compat": "NON",
        "valeur_tarifaire": 0.30,
        "facilite_acces": 0.30,
        "mecanismes": ["RESERVE_RAPIDE_PARTIEL"],
        "modulations": [],
        "priorite_promeos": "FAIBLE",
        "nogo_nebco": True,
    },
    "DATA_CENTER": {
        "label": "Data centers / salles IT",
        "pilotabilite": 0.30,
        "duree_max_h": 0.1,
        "impact_confort": "CRITIQUE",
        "inertie_thermique": False,
        "instrumentation_requise": "Monitoring temps r\u00e9el + onduleurs + groupes secours",
        "nebco_compat": "VIA_UPS",
        "valeur_tarifaire": 0.40,
        "facilite_acces": 0.40,
        "mecanismes": ["NEBCO_VIA_UPS", "RESERVE_RAPIDE_BATTERIES"],
        "modulations": ["EFFACEMENT"],
        "priorite_promeos": "FAIBLE",
    },
    "ECLAIRAGE": {
        "label": "\u00c9clairage non critique",
        "pilotabilite": 0.70,
        "duree_max_h": 999,
        "impact_confort": "FAIBLE",
        "inertie_thermique": False,
        "instrumentation_requise": "GTB + relais",
        "nebco_compat": "RAREMENT",
        "valeur_tarifaire": 0.50,
        "facilite_acces": 0.80,
        "mecanismes": ["HP_HC"],
        "modulations": ["EFFACEMENT"],
        "priorite_promeos": "BASSE",
    },
    "CHAINES_FRIGO": {
        "label": "Cha\u00eenes logistiques frigorifiques (transport + stockage)",
        "pilotabilite": 0.65,
        "duree_max_h": 1.0,
        "impact_confort": "MOYEN",
        "inertie_thermique": True,
        "instrumentation_requise": "IoT + BMS + coordination multi-sites",
        "nebco_compat": "OUI_ZONE",
        "valeur_tarifaire": 0.70,
        "facilite_acces": 0.55,
        "mecanismes": ["NEBCO", "AOFD", "FLEX_LOCALE"],
        "modulations": ["EFFACEMENT"],
        "priorite_promeos": "MOYENNE",
    },
}


# --- Poids de scoring ---

SCORE_WEIGHTS = {
    "pilotabilite": 0.30,
    "nebco_compat": 0.25,
    "valeur_tarifaire": 0.20,
    "facilite_acces": 0.15,
    "duree_norm": 0.10,
}

NEBCO_DIRECT_THRESHOLD = 0.7  # score NEBCO >= ce seuil = eligible direct
NEBCO_SUBTHRESHOLD_CAP = 0.5  # plafond score NEBCO quand P_max < SEUIL_NEBCO_KW

ARCHETYPE_TO_USAGES = {
    "BUREAU_STANDARD": ["CVC_HVAC", "ECS", "ECLAIRAGE", "IRVE"],
    "HOTEL_HEBERGEMENT": ["CVC_HVAC", "ECS", "FROID_COMMERCIAL", "IRVE", "ECLAIRAGE"],
    "ENSEIGNEMENT": ["CVC_HVAC", "ECS", "ECLAIRAGE"],
    "LOGISTIQUE_SEC": ["CVC_HVAC", "IRVE", "AIR_COMPRIME", "ECLAIRAGE"],
    "COMMERCE_ALIMENTAIRE": ["FROID_COMMERCIAL", "CVC_HVAC", "ECLAIRAGE", "IRVE"],
    "INDUSTRIE_LEGERE": ["CVC_HVAC", "AIR_COMPRIME", "POMPES", "PROCESS_BATCH", "IRVE"],
    "INDUSTRIE_LOURDE": ["PROCESS_CONTINU", "CVC_HVAC", "POMPES", "AIR_COMPRIME"],
    "DATA_CENTER": ["DATA_CENTER", "CVC_HVAC", "BATTERIES"],
    "LOGISTIQUE_FRIGO": ["FROID_INDUSTRIEL", "CHAINES_FRIGO", "IRVE", "CVC_HVAC"],
    "SANTE": ["CVC_HVAC", "ECS", "ECLAIRAGE"],
    # 5 archetypes ajoutes (couverture naf_resolver complete)
    "COPROPRIETE": ["CVC_HVAC", "ECS", "ECLAIRAGE", "IRVE"],
    "RESTAURANT": ["FROID_COMMERCIAL", "ECS", "CVC_HVAC", "ECLAIRAGE"],
    "SPORT_LOISIR": ["ECS", "CVC_HVAC", "POMPES", "IRVE", "ECLAIRAGE"],
    "ENSEIGNEMENT_SUP": ["CVC_HVAC", "ECS", "ECLAIRAGE", "DATA_CENTER", "IRVE"],
    "COLLECTIVITE": ["CVC_HVAC", "ECS", "ECLAIRAGE", "IRVE"],
    "DEFAULT": ["CVC_HVAC", "ECS", "ECLAIRAGE"],
}

NEBCO_COMPAT_SCORE = {
    "OUI_NATURELLE": 1.0,
    "OUI_MULTI": 1.0,
    "OUI_MULTISITE": 0.9,
    "OUI_SITE_GROS": 0.85,
    "OUI_AGR": 0.80,
    "OUI_PLANIF": 0.75,
    "OUI_DISCIPLINE": 0.70,
    "OUI_ZONE": 0.70,
    "PORTFOLIO": 0.60,
    "INDIRECT": 0.50,
    "VIA_UPS": 0.30,
    "RAREMENT": 0.20,
    "NON": 0.0,
}


# --- Fonctions de scoring ---


@dataclass
class FlexibilityScore:
    usage_code: str
    usage_label: str
    score_global: float
    score_pilotabilite: float
    score_nebco: float
    score_tarifaire: float
    score_facilite: float
    score_duree: float
    mecanismes: list[str]
    modulations: list[str]
    nebco_compat: str
    priorite: str
    nogo_nebco: bool = False
    signal_prix_negatifs: bool = False
    heures_solaires: bool = False
    instrumentation_requise: str = ""
    source: str = "flexibility_scoring_engine"
    computed_at: str = field(default_factory=lambda: datetime.now().isoformat())


def score_usage(usage_code: str, P_max_kw: float = 0.0) -> FlexibilityScore:
    """
    Calcule le score de flexibilite pour un usage donne.
    P_max_kw : puissance max du site (influence la NEBCO-compatibilite directe)
    """
    profile = USAGE_PROFILES.get(usage_code)
    if not profile:
        raise ValueError(f"Usage inconnu : {usage_code}. Codes valides : {list(USAGE_PROFILES.keys())}")

    # Score NEBCO (ajuste par P_max si disponible)
    nebco_compat = profile["nebco_compat"]
    score_nebco_raw = NEBCO_COMPAT_SCORE.get(nebco_compat, NEBCO_SUBTHRESHOLD_CAP)

    # P_max < 100 kW : plafond NEBCO (pas d'acces direct au marche)
    if P_max_kw > 0 and P_max_kw < SEUIL_NEBCO_KW and nebco_compat != "NON":
        score_nebco_raw = min(score_nebco_raw, NEBCO_SUBTHRESHOLD_CAP)

    # Score duree normalisee (max 12h = 1.0)
    duree_norm = min(profile["duree_max_h"] / 12.0, 1.0)

    # Score global pondere
    score = (
        profile["pilotabilite"] * SCORE_WEIGHTS["pilotabilite"]
        + score_nebco_raw * SCORE_WEIGHTS["nebco_compat"]
        + profile["valeur_tarifaire"] * SCORE_WEIGHTS["valeur_tarifaire"]
        + profile["facilite_acces"] * SCORE_WEIGHTS["facilite_acces"]
        + duree_norm * SCORE_WEIGHTS["duree_norm"]
    )

    return FlexibilityScore(
        usage_code=usage_code,
        usage_label=profile["label"],
        score_global=round(score, 3),
        score_pilotabilite=profile["pilotabilite"],
        score_nebco=round(score_nebco_raw, 3),
        score_tarifaire=profile["valeur_tarifaire"],
        score_facilite=profile["facilite_acces"],
        score_duree=round(duree_norm, 3),
        mecanismes=profile["mecanismes"],
        modulations=profile.get("modulations", []),
        nebco_compat=nebco_compat,
        priorite=profile.get("priorite_promeos", "MOYENNE"),
        nogo_nebco=profile.get("nogo_nebco", False),
        signal_prix_negatifs=profile.get("signal_prix_negatifs", False),
        heures_solaires=profile.get("heures_solaires_applicable", False),
        instrumentation_requise=profile["instrumentation_requise"],
    )


def _empty_site_result(archetype_code: str, P_max_kw: float) -> dict:
    """Resultat vide pour un site sans usages evaluables."""
    return {
        "score_global_site": 0.0,
        "usages_scores": [],
        "top_usages": [],
        "mecanismes_accessibles": [],
        "nebco_eligible_direct": False,
        "signal_prix_negatifs": False,
        "potentiel_heures_solaires": False,
        "n_usages_evalues": 0,
        "heures_negatives_france_2025": HEURES_NEGATIVES_2025,
        "seuils_alerte": {
            "prix_negatif_eur_mwh": PRIX_NEGATIF_SEUIL_EUR_MWH,
            "prix_positif_eur_mwh": PRIX_POSITIF_SEUIL_EUR_MWH,
        },
        "archetype_code": archetype_code,
        "P_max_kw": P_max_kw,
        "source": "flexibility_scoring_engine",
        "confidence": 0.0,
        "computed_at": datetime.now().isoformat(),
    }


def score_site_flex(
    usages_detectes: list[str],
    P_max_kw: float = 0.0,
    archetype_code: str = "DEFAULT",
) -> dict:
    """
    Score de flexibilite global d'un site a partir de ses usages detectes.

    Returns :
    - score_global_site : 0.0 - 1.0
    - top_usages : top 5 usages prioritaires
    - mecanismes_accessibles : union des mecanismes compatibles
    - nebco_eligible_direct : True si au moins 1 usage eligible direct
    - signal_prix_negatifs : True si au moins 1 usage beneficie des prix negatifs
    - potentiel_heures_solaires : True si usage avec heures_solaires_applicable (ECS, IRVE)
    """
    scores = (
        [score_usage(code, P_max_kw) for code in usages_detectes if code in USAGE_PROFILES] if usages_detectes else []
    )

    if not scores:
        return _empty_site_result(archetype_code, P_max_kw)

    # Score site = max des scores individuels + bonus multi-usages
    max_score = max(s.score_global for s in scores)
    n_usages_hauts = sum(1 for s in scores if s.score_global >= 0.6)
    bonus_multi = min(n_usages_hauts * 0.05, 0.15)
    score_global = round(min(1.0, max_score + bonus_multi), 3)

    scores_sorted = sorted(scores, key=lambda s: s.score_global, reverse=True)

    mecanismes = sorted(set(m for s in scores for m in s.mecanismes))

    nebco_direct = any(NEBCO_COMPAT_SCORE.get(s.nebco_compat, 0) >= NEBCO_DIRECT_THRESHOLD for s in scores)
    prix_negatifs = any(s.signal_prix_negatifs for s in scores)
    heures_solaires = any(s.heures_solaires for s in scores)

    return {
        "score_global_site": score_global,
        "n_usages_evalues": len(scores),
        "top_usages": [
            {
                "code": s.usage_code,
                "label": s.usage_label,
                "score": s.score_global,
                "priorite": s.priorite,
                "mecanismes": s.mecanismes,
                "nebco_compat": s.nebco_compat,
                "modulations": s.modulations,
                "nogo_nebco": s.nogo_nebco,
            }
            for s in scores_sorted[:5]
        ],
        "usages_scores": [{"code": s.usage_code, "score": s.score_global, "nebco": s.nebco_compat} for s in scores],
        "mecanismes_accessibles": mecanismes,
        "nebco_eligible_direct": nebco_direct,
        "signal_prix_negatifs": prix_negatifs,
        "potentiel_heures_solaires": heures_solaires,
        "heures_negatives_france_2025": HEURES_NEGATIVES_2025,
        "seuils_alerte": {
            "prix_negatif_eur_mwh": PRIX_NEGATIF_SEUIL_EUR_MWH,
            "prix_positif_eur_mwh": PRIX_POSITIF_SEUIL_EUR_MWH,
        },
        "archetype_code": archetype_code,
        "P_max_kw": P_max_kw,
        "source": "flexibility_scoring_engine",
        "confidence": 0.85,
        "computed_at": datetime.now().isoformat(),
    }


def get_usages_par_archetype(archetype_code: str) -> list[str]:
    """Retourne la liste d'usages probables selon l'archetype NAF du site."""
    return ARCHETYPE_TO_USAGES.get(archetype_code, ARCHETYPE_TO_USAGES["DEFAULT"])


def detect_prix_negatif_signal(prix_spot_eur_mwh: float) -> dict:
    """
    Interprete un signal de prix spot pour generer une recommandation NEBCO.

    Prix negatifs -> hausse de conso recommandee (NEBCO anticipation/report).
    Prix tres eleves -> baisse de conso recommandee (NEBCO effacement).

    Source : RTE Bilan 2025 (513h prix negatifs), CRE rapport surveillance 2024.
    """
    if prix_spot_eur_mwh <= PRIX_NEGATIF_SEUIL_EUR_MWH:
        return {
            "signal": "PRIX_NEGATIF",
            "valeur_eur_mwh": prix_spot_eur_mwh,
            "action_recommandee": "AUGMENTER_CONSO",
            "modulation_nebco": "ANTICIPATION",
            "usages_cibles": ["BATTERIES", "IRVE", "STOCKAGE_THERM", "ECS"],
            "message": (
                f"Prix spot {prix_spot_eur_mwh:.0f} \u20ac/MWh \u2014 signal anticipation NEBCO. "
                "Charger les batteries, IRVE et stockages thermiques maintenant."
            ),
            "urgence": "HAUTE" if prix_spot_eur_mwh <= -30 else "NORMALE",
            "source": "RTE marche spot J-1",
        }
    elif prix_spot_eur_mwh >= PRIX_POSITIF_SEUIL_EUR_MWH:
        return {
            "signal": "PRIX_ELEVE",
            "valeur_eur_mwh": prix_spot_eur_mwh,
            "action_recommandee": "BAISSER_CONSO",
            "modulation_nebco": "EFFACEMENT",
            "usages_cibles": ["CVC_HVAC", "FROID_COMMERCIAL", "AIR_COMPRIME", "IRVE"],
            "message": (
                f"Prix spot {prix_spot_eur_mwh:.0f} \u20ac/MWh \u2014 signal effacement NEBCO. "
                "Reduire la consommation des usages flexibles maintenant."
            ),
            "urgence": "HAUTE" if prix_spot_eur_mwh >= 200 else "NORMALE",
            "source": "RTE marche spot J-1",
        }
    else:
        return {
            "signal": "NEUTRE",
            "valeur_eur_mwh": prix_spot_eur_mwh,
            "action_recommandee": "AUCUNE",
            "usages_cibles": [],
            "message": f"Prix spot {prix_spot_eur_mwh:.0f} \u20ac/MWh \u2014 pas de signal particulier.",
        }
