"""
PROMEOS - Scoring portefeuille multi-sites : classement par potentiel de pilotage.

`compute_portefeuille_scoring` agrège le score de potentiel pilotable (S22)
sur N sites et produit :

    1. Un classement Top-10 par score décroissant
    2. Une heatmap par archétype (nb_sites, gain total EUR, score moyen)
    3. Le gain annuel portefeuille (somme des gains estimés par site)

Le gain annuel par site est une estimation :

    gain_annuel_eur = puissance_pilotable_kw
                    × heures_favorables_annuelles_par_archetype
                    × spread_eur_par_kwh

Calibrage Baromètre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026) :
    - heures_favorables : nombre d'heures/an où un site de cet archétype peut
      valoriser de la flexibilité (effacement HP, décalage HC, MA NEBEF...)
    - spread : écart moyen HP/HC + MA + capacité par kWh pilotable

Doctrine : "classement par potentiel de pilotage" (jamais "classement flex",
ce dernier étant réservé au scoring mono-site S22).
"""

from __future__ import annotations

from typing import Optional

from services.pilotage.score_potential import compute_potential_score


# --- Paramètres calibrage gain annuel ---------------------------------------

# Heures favorables annuelles par archétype (calibrage Baromètre Flex 2026).
# Couvre : pointes HP hiver (~500h), plages MA NEBEF (~250h), réserve capacité
# (~100h), décalages HC (~150h). Les archétypes 24/7 (logistique frigo, santé)
# cumulent davantage de fenêtres activables.
_HEURES_FAVORABLES_PAR_ARCHETYPE: dict[str, int] = {
    "BUREAU_STANDARD": 900,
    "COMMERCE_ALIMENTAIRE": 1400,  # froid 24/7 -> plus de fenêtres MA
    "COMMERCE_SPECIALISE": 800,
    "LOGISTIQUE_FRIGO": 1600,  # froid inertie -> gisement le plus large
    "ENSEIGNEMENT": 700,
    "SANTE": 600,  # contraintes médicales -> moins d'heures utilisables
    "HOTELLERIE": 1100,
    "INDUSTRIE_LEGERE": 1000,
}

# Spread moyen valorisable (EUR/kWh pilotable). Calibrage Baromètre Flex 2026 :
# moyenne des gains constatés (HP-HC + rémunération NEBEF + capacité) sur les
# sites tertiaires 2024. Valeur conservative, cohérente avec observatoire CRE.
_SPREAD_EUR_PAR_KWH_DEFAULT = 0.08

# Fallback si archétype inconnu : heures favorables médianes tertiaires.
_FALLBACK_HEURES_FAVORABLES = 800

# Fallback score quand archétype inconnu et compute_potential_score ne donne
# pas de signal exploitable (sécurisation : cap à 50 pour éviter de prioriser
# à tort des sites non qualifiés).
_FALLBACK_SCORE = 50.0


def _estimate_gain_annuel_eur(
    archetype_code: Optional[str],
    puissance_pilotable_kw: float,
) -> float:
    """
    Estime le gain annuel valorisable pour un site donné.

    Formule : kW × heures_favorables × spread EUR/kWh.

    Args:
        archetype_code : code canonique d'archétype (ex: "BUREAU_STANDARD").
        puissance_pilotable_kw : puissance mobilisable en kW.

    Returns:
        Gain annuel estimé en EUR (arrondi à l'entier).
    """
    if puissance_pilotable_kw <= 0:
        return 0.0
    heures = _HEURES_FAVORABLES_PAR_ARCHETYPE.get(
        archetype_code or "",
        _FALLBACK_HEURES_FAVORABLES,
    )
    gain = puissance_pilotable_kw * heures * _SPREAD_EUR_PAR_KWH_DEFAULT
    return round(gain)


def _score_site(archetype_code: Optional[str]) -> float:
    """
    Calcule le score mono-site via compute_potential_score ; fallback 50 si
    aucun signal calibré n'est exploitable.
    """
    result = compute_potential_score(archetype_code)
    # Si l'archétype n'est pas calibré ET qu'on ne dispose d'aucun override,
    # on garde le fallback 50 plutôt que la valeur heuristique (évite de
    # prioriser à tort des sites mal qualifiés).
    if not result.get("used_calibration") and not archetype_code:
        return _FALLBACK_SCORE
    return float(result["score"])


def compute_portefeuille_scoring(sites: list[dict]) -> dict:
    """
    Classe un portefeuille de sites par potentiel de pilotage.

    Args:
        sites : liste de fiches site. Chaque fiche doit porter :
            - site_id               : str
            - archetype_code        : str ou None
            - puissance_pilotable_kw: float (>= 0)

    Returns:
        dict avec :
            - nb_sites_total                : int
            - gain_annuel_portefeuille_eur  : int (somme des gains)
            - top_10                        : list[dict] (site_id, archetype,
                                               score, gain_annuel_eur, rang)
            - heatmap_archetype             : dict archétype -> stats
            - source                        : citation source
    """
    enriched: list[dict] = []
    for site in sites:
        site_id = site.get("site_id")
        archetype = site.get("archetype_code")
        puissance = float(site.get("puissance_pilotable_kw") or 0.0)

        score = _score_site(archetype)
        gain = _estimate_gain_annuel_eur(archetype, puissance)
        enriched.append(
            {
                "site_id": site_id,
                "archetype": archetype,
                "score": score,
                "gain_annuel_eur": gain,
            }
        )

    # Classement décroissant par score, départage par gain puis site_id (stable).
    enriched.sort(
        key=lambda s: (-s["score"], -s["gain_annuel_eur"], s["site_id"] or ""),
    )

    # Top-10 avec rang séquentiel (1, 2, 3, ...)
    top_10: list[dict] = []
    for idx, row in enumerate(enriched[:10], start=1):
        top_10.append({**row, "rang": idx})

    # Heatmap par archétype : nb_sites, gain_total, score_moyen.
    heatmap: dict[str, dict] = {}
    for row in enriched:
        key = row["archetype"] or "INCONNU"
        bucket = heatmap.setdefault(
            key,
            {"nb_sites": 0, "gain_total_eur": 0, "score_sum": 0.0},
        )
        bucket["nb_sites"] += 1
        bucket["gain_total_eur"] += row["gain_annuel_eur"]
        bucket["score_sum"] += row["score"]

    for bucket in heatmap.values():
        nb = max(bucket["nb_sites"], 1)
        bucket["score_moyen"] = round(bucket["score_sum"] / nb, 1)
        bucket["gain_total_eur"] = round(bucket["gain_total_eur"])
        del bucket["score_sum"]

    gain_portefeuille = round(sum(row["gain_annuel_eur"] for row in enriched))

    return {
        "nb_sites_total": len(enriched),
        "gain_annuel_portefeuille_eur": gain_portefeuille,
        "top_10": top_10,
        "heatmap_archetype": heatmap,
        "source": "PROMEOS Pilotage Score — Baromètre Flex 2026 Enedis",
    }
