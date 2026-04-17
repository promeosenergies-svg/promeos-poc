"""
PROMEOS - ROI Flex Ready (R) : business case chiffre par site.

Cette brique complete `flex_ready.py` (conformite technique NF EN IEC 62746-4)
en exposant le gain financier annuel estime pour un site Flex Ready (R) pilote.

Elle repond a la seule question que les CFOs lisent :
    "Combien ce site gagne-t-il par an a etre Flex Ready (R) + pilote ?"

Trois composantes additives :

    1. Gain evitement pointe
        = (kW pilotable) x (heures pointe evitees / an) x (spread pointe EUR/MWh)
        Les heures pointe evitees sont la somme des largeurs des plages
        `plages_pointe_h` du calibrage Barometre Flex 2026, multipliees par
        un facteur d'effacement realiste (% de jours ouvrables ou l'effacement
        est reellement active).

    2. Valorisation decalage NEBCO
        = (kW decalable) x (heures fenetres favorables / an) x (spread moyen)
        Hypothese : 200 h/an de fenetres favorables (surplus PV, prix negatifs
        marginaux) avec spread moyen 60 EUR/MWh (Baro Flex 2026 + observatoire
        CRE T4 2025 : 513 h negatives en 2025).

    3. CEE BACS
        = (surface m2) x (forfait CEE BAT-TH-116 EUR/m2)
        Forfait 3,5 EUR/m2 (fiche CEE BAT-TH-116 "Systeme GTB" valorisation
        moyenne 2025-2026, hypothese conservatrice au milieu de la fourchette
        observee 2-5 EUR/m2 selon volume et cours du kWhc).

Confiance : "indicative" — les 3 composantes sont des ordres de grandeur
MVP, pas des engagements commerciaux. Les hypotheses sont toujours exposees
dans la payload (explainability).

Sources :
    - Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026)
    - Fiche CEE BAT-TH-116 (systeme GTB / BACS)
    - Observatoire CRE T4 2025 (513 h prix negatifs France 2025)
"""

from __future__ import annotations

from typing import Any, Optional

from services.pilotage.constants import ARCHETYPE_CALIBRATION_2024


# --- Hypotheses MVP (exposees dans la payload) -------------------------------

# Fenetres annuelles favorables au decalage NEBCO (surplus PV, prix negatifs
# marginaux, creux TURPE 7 favorables). Source : Barometre Flex 2026 + CRE T4 2025.
HEURES_FENETRES_FAVORABLES_AN: int = 200

# Spread moyen sur ces fenetres (EUR/MWh). Delta entre prix moyen et prix
# bas lors des fenetres favorables. Hypothese MVP conservatrice.
SPREAD_MOYEN_EUR_MWH: float = 60.0

# Spread pointe vs plage creuse (EUR/MWh). Ordre de grandeur 2025-2026 : les
# pointes hiver haute saison atteignent regulierement +120 EUR/MWh vs plage
# de base (Observatoire CRE, Bulletin marches gros T4 2025). Hypothese MVP.
SPREAD_POINTE_EUR_MWH: float = 120.0

# Nombre de jours effectifs par an ou l'effacement pointe est realisable
# (hors week-ends, jours feries, pannes GTB). ~200 jours ouvres typiques.
JOURS_EFFACEMENT_PAR_AN: int = 200

# Forfait CEE BAT-TH-116 (systeme GTB / BACS) en EUR/m2 de surface chauffee.
# Fiche CEE standardisee, valorisation moyenne 2025-2026.
CEE_BACS_EUR_M2: float = 3.5

# Archetype par defaut quand l'archetype fourni est inconnu du calibrage.
# BUREAU_STANDARD est le segment mediane / fallback le plus representatif.
_DEFAULT_ARCHETYPE: str = "BUREAU_STANDARD"


def _heures_pointe_par_jour(plages_pointe_h: list[tuple[int, int]]) -> int:
    """
    Somme des largeurs (en heures) des plages de pointe d'un archetype.

    Convention `plages_pointe_h` : liste de tuples (h_debut, h_fin) avec
    intervalle [h_debut, h_fin), donc largeur = h_fin - h_debut.
    """
    total = 0
    for h_debut, h_fin in plages_pointe_h:
        # Defense : si tuple inverse ou vide, contribution = 0 (pas d'erreur)
        if h_fin > h_debut:
            total += h_fin - h_debut
    return total


def compute_roi_flex_ready(
    site_id: str,
    demo_site: dict[str, Any],
    archetype_code: Optional[str] = None,
) -> dict[str, Any]:
    """
    Calcule le gain annuel estime (EUR) pour un site Flex Ready (R) pilote.

    Parametres
    ----------
    site_id : str
        Identifiant canonique du site (ex. "retail-001").
    demo_site : dict
        Fiche site (DEMO_SITES) avec au minimum :
            - puissance_max_instantanee_kw : float  (kW)
            - surface_m2                   : float  (m2, default 0 si absent)
            - archetype_code               : str    (optionnel, surcharge arg)
    archetype_code : str | None
        Code canonique d'archetype. Si None ou inconnu de
        `ARCHETYPE_CALIBRATION_2024`, fallback sur BUREAU_STANDARD.

    Retour
    ------
    dict avec :
      - site_id                    : str
      - archetype                  : str (archetype finalement utilise)
      - gain_annuel_total_eur      : float (somme des 3 composantes, arrondie)
      - composantes :
          - evitement_pointe_eur   : float
          - decalage_nebco_eur     : float
          - cee_bacs_eur           : float
      - hypotheses : dict (parametres MVP utilises, pour explainability)
      - confiance  : "indicative"
      - source     : citation courte Barometre Flex 2026 + fiche CEE
    """
    # 1. Resoudre l'archetype : priorite argument > fiche site > defaut.
    resolved_code = archetype_code or demo_site.get("archetype_code") or _DEFAULT_ARCHETYPE
    calib = ARCHETYPE_CALIBRATION_2024.get(resolved_code)
    if calib is None:
        # Archetype inconnu -> fallback BUREAU_STANDARD (toujours present)
        resolved_code = _DEFAULT_ARCHETYPE
        calib = ARCHETYPE_CALIBRATION_2024[_DEFAULT_ARCHETYPE]

    p_max_kw = float(demo_site.get("puissance_max_instantanee_kw", 0.0))
    surface_m2 = float(demo_site.get("surface_m2", 0.0))
    taux_decalable = float(calib["taux_decalable_moyen"])
    plages_pointe = calib["plages_pointe_h"]

    # --- Composante 1 : evitement pointe --------------------------------
    # kW pilotable = P max x taux decalable archetype
    # Heures pointe / an = somme largeurs plages x jours effaces par an
    # Gain EUR = kW pilotable x heures / an x spread EUR/MWh / 1000 (MWh->kWh)
    kw_pilotable = p_max_kw * taux_decalable
    heures_pointe_par_jour = _heures_pointe_par_jour(plages_pointe)
    heures_pointe_evitees_an = heures_pointe_par_jour * JOURS_EFFACEMENT_PAR_AN
    # Facteur d'effacement realiste : on ne peut effacer qu'une fraction des
    # heures pointe (GTB active, contraintes metier). On prend 10% de la
    # fenetre totale pointe x jours ouvres -- hypothese conservatrice MVP.
    # Formule finale : kWh decales = kw_pilotable x (heures_pointe_evitees_an x 0.1)
    #                 gain = kWh x spread / 1000
    #
    # NB : on garde la multiplication par 0.1 implicite dans le facteur
    # "heures pointe evitees" pour la lisibilite de la formule cible du spec.
    kwh_evites_an = kw_pilotable * heures_pointe_evitees_an * 0.1
    evitement_pointe_eur = kwh_evites_an * SPREAD_POINTE_EUR_MWH / 1000.0

    # --- Composante 2 : decalage NEBCO ----------------------------------
    # kW decalable = P max x taux decalable archetype (meme hypothese)
    # Heures fenetres favorables = 200 h/an (hypothese MVP)
    # Gain EUR = kW decalable x heures x spread / 1000
    kw_decalable = kw_pilotable  # meme assiette que le pilotable pointe
    kwh_decales_an = kw_decalable * HEURES_FENETRES_FAVORABLES_AN
    decalage_nebco_eur = kwh_decales_an * SPREAD_MOYEN_EUR_MWH / 1000.0

    # --- Composante 3 : CEE BACS ----------------------------------------
    # Forfait CEE BAT-TH-116 x surface m2. Si surface_m2 = 0 (non renseignee),
    # composante = 0 (pas de gain estime), pas une erreur.
    cee_bacs_eur = max(0.0, surface_m2) * CEE_BACS_EUR_M2

    # --- Total ---------------------------------------------------------
    gain_total = evitement_pointe_eur + decalage_nebco_eur + cee_bacs_eur

    return {
        "site_id": site_id,
        "archetype": resolved_code,
        "gain_annuel_total_eur": round(gain_total, 2),
        "composantes": {
            "evitement_pointe_eur": round(evitement_pointe_eur, 2),
            "decalage_nebco_eur": round(decalage_nebco_eur, 2),
            "cee_bacs_eur": round(cee_bacs_eur, 2),
        },
        "hypotheses": {
            "heures_fenetres_favorables_an": HEURES_FENETRES_FAVORABLES_AN,
            "spread_moyen_eur_mwh": SPREAD_MOYEN_EUR_MWH,
            "spread_pointe_eur_mwh": SPREAD_POINTE_EUR_MWH,
            "jours_effacement_par_an": JOURS_EFFACEMENT_PAR_AN,
            "cee_bacs_eur_m2": CEE_BACS_EUR_M2,
            "taux_decalable_archetype": taux_decalable,
            "heures_pointe_par_jour_archetype": heures_pointe_par_jour,
            "surface_m2": surface_m2,
            "puissance_max_kw": p_max_kw,
        },
        "confiance": "indicative",
        "source": "Baromètre Flex 2026 RTE/Enedis + fiche CEE BAT-TH-116",
    }
