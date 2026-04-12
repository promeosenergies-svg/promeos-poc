"""
Recommandation de strategie d'achat d'energie via archetype flex canonique.

Entree : archetype (UPPER) + profil CDC agrege (P_max, facteur_forme, baseload %).
Sortie : strategie (fixe/indexe/spot/mix/PPA) + composition optimale + justification.

Source : analyse CRE 2025 + Les Echos marche electricite + archetype_recommendation.py
(ancienne taxonomie lowercase, remplacee ici par les codes canoniques flex).
"""

from dataclasses import dataclass
from typing import Optional


# --- Profils d'achat par archetype canonique flex ---

# Chaque entree decrit :
# - hp_pct / hc_pct : repartition typique de la consommation
# - strategy : strategie recommandee dominante
# - rationale : justification metier
# - composition : {fixe, indexe, spot, ppa} en % somme=100 (melange optimal)
# - green_recommended : booleen (obligations RSE / CBAM / CSRD)
# - ppa_eligible : booleen (conso > 500 MWh/an typiquement)

ARCHETYPE_PURCHASE_PROFILES: dict[str, dict] = {
    "BUREAU_STANDARD": {
        "hp_pct": 70,
        "hc_pct": 30,
        "strategy": "fixe",
        "rationale": "Profil HP dominant, conso predictible, budget annuel fige : privilegier le fixe pour visibilite comptable.",
        "composition": {"fixe": 70, "indexe": 20, "spot": 10, "ppa": 0},
        "green_recommended": True,
        "ppa_eligible": False,
    },
    "HOTEL_HEBERGEMENT": {
        "hp_pct": 55,
        "hc_pct": 45,
        "strategy": "indexe",
        "rationale": "Forte saisonnalite (occupation), besoin de suivre le marche pour lisser les variations de charge.",
        "composition": {"fixe": 40, "indexe": 40, "spot": 20, "ppa": 0},
        "green_recommended": True,
        "ppa_eligible": False,
    },
    "ENSEIGNEMENT": {
        "hp_pct": 80,
        "hc_pct": 20,
        "strategy": "fixe",
        "rationale": "Utilisation concentree jours ouvres et periodes scolaires : fixe optimal pour la prevision budgetaire.",
        "composition": {"fixe": 80, "indexe": 15, "spot": 5, "ppa": 0},
        "green_recommended": True,
        "ppa_eligible": False,
    },
    "ENSEIGNEMENT_SUP": {
        "hp_pct": 65,
        "hc_pct": 35,
        "strategy": "mix",
        "rationale": "Campus avec data center + residences : mix indispensable pour couvrir baseload (fixe) et flexibilite (spot).",
        "composition": {"fixe": 50, "indexe": 25, "spot": 15, "ppa": 10},
        "green_recommended": True,
        "ppa_eligible": True,
    },
    "SANTE": {
        "hp_pct": 60,
        "hc_pct": 40,
        "strategy": "fixe",
        "rationale": "Service 24/7, contrainte de securite d'approvisionnement maximale : fixe indispensable.",
        "composition": {"fixe": 85, "indexe": 10, "spot": 5, "ppa": 0},
        "green_recommended": True,
        "ppa_eligible": True,
    },
    "LOGISTIQUE_SEC": {
        "hp_pct": 50,
        "hc_pct": 50,
        "strategy": "indexe",
        "rationale": "Baseload faible, pointes logistiques : indexation permet de beneficier des prix creux.",
        "composition": {"fixe": 35, "indexe": 40, "spot": 25, "ppa": 0},
        "green_recommended": False,
        "ppa_eligible": False,
    },
    "LOGISTIQUE_FRIGO": {
        "hp_pct": 55,
        "hc_pct": 45,
        "strategy": "mix",
        "rationale": "Baseload froid eleve et stable : mix fixe (securite froid) + spot (optimiser jour/nuit).",
        "composition": {"fixe": 55, "indexe": 25, "spot": 15, "ppa": 5},
        "green_recommended": False,
        "ppa_eligible": True,
    },
    "COMMERCE_ALIMENTAIRE": {
        "hp_pct": 60,
        "hc_pct": 40,
        "strategy": "mix",
        "rationale": "Froid 24/7 + horaires magasin variables : mix fixe/indexe pour profil hybride.",
        "composition": {"fixe": 60, "indexe": 25, "spot": 10, "ppa": 5},
        "green_recommended": True,
        "ppa_eligible": True,
    },
    "RESTAURANT": {
        "hp_pct": 60,
        "hc_pct": 40,
        "strategy": "fixe",
        "rationale": "Marge faible, sensibilite prix critique : fixe pour proteger la rentabilite du point de vente.",
        "composition": {"fixe": 75, "indexe": 15, "spot": 10, "ppa": 0},
        "green_recommended": False,
        "ppa_eligible": False,
    },
    "INDUSTRIE_LEGERE": {
        "hp_pct": 55,
        "hc_pct": 45,
        "strategy": "indexe",
        "rationale": "Process arretables, sensibilite forte au prix marginal : indexation + flex NEBCO.",
        "composition": {"fixe": 40, "indexe": 35, "spot": 20, "ppa": 5},
        "green_recommended": False,
        "ppa_eligible": True,
    },
    "INDUSTRIE_LOURDE": {
        "hp_pct": 50,
        "hc_pct": 50,
        "strategy": "fixe",
        "rationale": "Process continu 24/7, arrets couteux, securite approvisionnement critique : fixe pluriannuel.",
        "composition": {"fixe": 75, "indexe": 15, "spot": 0, "ppa": 10},
        "green_recommended": False,
        "ppa_eligible": True,
    },
    "DATA_CENTER": {
        "hp_pct": 50,
        "hc_pct": 50,
        "strategy": "ppa",
        "rationale": "Baseload massif 24/7, PUE critique, engagement RE100 : PPA long terme + baseload fixe.",
        "composition": {"fixe": 30, "indexe": 10, "spot": 0, "ppa": 60},
        "green_recommended": True,
        "ppa_eligible": True,
    },
    "SPORT_LOISIR": {
        "hp_pct": 60,
        "hc_pct": 40,
        "strategy": "indexe",
        "rationale": "Piscines et salles a forte saisonnalite : indexation pour absorber les variations de frequentation.",
        "composition": {"fixe": 50, "indexe": 30, "spot": 20, "ppa": 0},
        "green_recommended": True,
        "ppa_eligible": False,
    },
    "COLLECTIVITE": {
        "hp_pct": 70,
        "hc_pct": 30,
        "strategy": "fixe",
        "rationale": "Commande publique, budget annuel vote : fixe pluriannuel pour securiser la ligne budgetaire.",
        "composition": {"fixe": 75, "indexe": 15, "spot": 0, "ppa": 10},
        "green_recommended": True,
        "ppa_eligible": True,
    },
    "COPROPRIETE": {
        "hp_pct": 50,
        "hc_pct": 50,
        "strategy": "fixe",
        "rationale": "Parties communes, gestion collective, aversion risque : fixe pour simplicite comptable.",
        "composition": {"fixe": 85, "indexe": 15, "spot": 0, "ppa": 0},
        "green_recommended": True,
        "ppa_eligible": False,
    },
    "DEFAULT": {
        "hp_pct": 65,
        "hc_pct": 35,
        "strategy": "fixe",
        "rationale": "Profil par defaut : fixe pour minimiser l'exposition marche sans historique.",
        "composition": {"fixe": 70, "indexe": 20, "spot": 10, "ppa": 0},
        "green_recommended": False,
        "ppa_eligible": False,
    },
}


# Garde de coherence : la taxonomie doit couvrir les memes archetypes que le moteur flex.
def _assert_archetype_coverage() -> None:
    from services.flex.flexibility_scoring_engine import ARCHETYPE_TO_USAGES as _canonical

    missing = set(_canonical.keys()) - set(ARCHETYPE_PURCHASE_PROFILES.keys())
    if missing:
        raise RuntimeError(f"strategy_recommender: archetypes manquants vs flex engine : {sorted(missing)}")


_assert_archetype_coverage()


# --- Ajustements selon profil CDC mesure ---

# Seuil (kW) de P_max sous lequel le site n'est pas eligible au spot
# (marche de gros inaccessible en direct)
P_MAX_MIN_SPOT_KW = 250.0

# Seuil P_max pour recommander PPA (eligibilite economique)
P_MAX_MIN_PPA_KW = 500.0

# Facteur de forme de reference :
# < 0.30 : profil tres pointu (pointes) -> eviter spot
# > 0.60 : profil lisse (baseload) -> spot et PPA OK
FF_POINTU = 0.30
FF_LISSE = 0.60


@dataclass
class PurchaseRecommendation:
    archetype_code: str
    strategy: str
    rationale: str
    composition: dict[str, int]
    green_recommended: bool
    ppa_eligible: bool
    hp_pct: int
    hc_pct: int
    cdc_profile_snapshot: dict
    adjustments: list[str]


def recommend_purchase_strategy(
    archetype_code: str,
    P_max_kw: float = 0.0,
    facteur_forme: Optional[float] = None,
    annual_kwh: Optional[float] = None,
) -> PurchaseRecommendation:
    """
    Recommande une strategie d'achat d'energie pour un site donne.

    Args:
        archetype_code: code canonique flex (BUREAU_STANDARD, DATA_CENTER, etc.)
        P_max_kw: puissance maximale du site (sinon fallback base archetype)
        facteur_forme: E_totale / (P_max x T_heures), [0, 1] — ajuste fixe/spot
        annual_kwh: conso annuelle (pour eligibilite PPA)

    Returns:
        PurchaseRecommendation avec composition ajustee.
    """
    profile = ARCHETYPE_PURCHASE_PROFILES.get(archetype_code, ARCHETYPE_PURCHASE_PROFILES["DEFAULT"])

    composition = dict(profile["composition"])
    adjustments: list[str] = []

    # Ajustement P_max : si sous seuil spot, basculer spot -> indexe
    if P_max_kw and P_max_kw < P_MAX_MIN_SPOT_KW and composition.get("spot", 0) > 0:
        composition["indexe"] = composition.get("indexe", 0) + composition["spot"]
        composition["spot"] = 0
        adjustments.append(f"P_max={P_max_kw:.0f} kW < {P_MAX_MIN_SPOT_KW:.0f} kW : spot realloue sur indexe.")

    # Ajustement PPA : si sous seuil eligibilite, basculer PPA -> fixe
    ppa_eligible_effective = profile["ppa_eligible"]
    if composition.get("ppa", 0) > 0:
        if (P_max_kw and P_max_kw < P_MAX_MIN_PPA_KW) or (annual_kwh and annual_kwh < 500_000):
            composition["fixe"] = composition.get("fixe", 0) + composition["ppa"]
            composition["ppa"] = 0
            ppa_eligible_effective = False
            adjustments.append("PPA non eligible (puissance ou conso insuffisante) : realloue sur fixe.")

    # Ajustement facteur de forme : profil pointu -> eviter spot, privilegier fixe
    if facteur_forme is not None:
        if facteur_forme < FF_POINTU and composition.get("spot", 0) > 0:
            surplus = composition["spot"] // 2
            composition["fixe"] = composition.get("fixe", 0) + surplus
            composition["spot"] = composition["spot"] - surplus
            adjustments.append(
                f"Facteur de forme {facteur_forme:.2f} < {FF_POINTU} (profil pointu) : spot reduit au profit du fixe."
            )
        elif facteur_forme > FF_LISSE and composition.get("fixe", 0) > 0:
            surplus = min(composition["fixe"] // 4, 15)
            composition["spot"] = composition.get("spot", 0) + surplus
            composition["fixe"] = composition["fixe"] - surplus
            adjustments.append(
                f"Facteur de forme {facteur_forme:.2f} > {FF_LISSE} (profil lisse) : spot augmente pour optimiser."
            )

    # Normalisation (somme = 100)
    total = sum(composition.values())
    if total != 100 and total > 0:
        composition = {k: round(v * 100 / total) for k, v in composition.items()}

    return PurchaseRecommendation(
        archetype_code=archetype_code,
        strategy=profile["strategy"],
        rationale=profile["rationale"],
        composition=composition,
        green_recommended=profile["green_recommended"],
        ppa_eligible=ppa_eligible_effective,
        hp_pct=profile["hp_pct"],
        hc_pct=profile["hc_pct"],
        cdc_profile_snapshot={
            "P_max_kw": round(P_max_kw, 1) if P_max_kw else None,
            "facteur_forme": round(facteur_forme, 2) if facteur_forme is not None else None,
            "annual_kwh": round(annual_kwh, 0) if annual_kwh else None,
        },
        adjustments=adjustments,
    )
