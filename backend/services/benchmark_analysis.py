"""
PROMEOS — Benchmark Analysis Service
Compare IPE réel vs ADEME benchmarks, calcule surcoût estimé.
Utilisé par shadow billing et dashboard usages.
"""

from sqlalchemy.orm import Session
from config.patrimoine_assumptions import BENCHMARK_ADEME_KWH_M2_AN

# Mapping TypeSite → clé ADEME
_TYPE_TO_ADEME = {
    "bureau": "bureau",
    "bureaux": "bureau",
    "commerce": "commerce",
    "magasin": "commerce",
    "entrepot": "logistique",
    "logistique": "logistique",
    "usine": "industrie",
    "industrie": "industrie",
    "hotel": "hotellerie",
    "hotellerie": "hotellerie",
    "sante": "sante",
    "enseignement": "enseignement",
}


def compute_benchmark_analysis(
    type_site: str,
    surface_m2: float,
    total_kwh: float,
    price_eur_kwh: float = 0.068,
) -> dict:
    """
    Compare la consommation réelle au benchmark ADEME.

    Retourne :
    - ipe_reel : kWh/m²/an réel
    - benchmark : {median, bon, performant} du type
    - position : "performant" | "bon" | "median" | "au_dessus"
    - surcout_eur : surcoût estimé par rapport au niveau "bon"
    - economie_potentielle_pct : % de réduction possible
    """
    ipe_reel = round(total_kwh / surface_m2, 1) if surface_m2 > 0 else 0

    ademe_key = _TYPE_TO_ADEME.get(type_site, "bureau")
    benchmark = BENCHMARK_ADEME_KWH_M2_AN.get(ademe_key, BENCHMARK_ADEME_KWH_M2_AN["bureau"])

    median = benchmark["median"]
    bon = benchmark["bon"]
    performant = benchmark["performant"]

    if ipe_reel <= performant:
        position = "performant"
    elif ipe_reel <= bon:
        position = "bon"
    elif ipe_reel <= median:
        position = "median"
    else:
        position = "au_dessus"

    # Surcoût = (IPE réel - IPE bon) × surface × prix
    surplus_kwh = max(0, (ipe_reel - bon) * surface_m2)
    surcout_eur = round(surplus_kwh * price_eur_kwh)

    economie_pct = round((1 - bon / ipe_reel) * 100, 1) if ipe_reel > 0 else 0

    return {
        "ipe_reel_kwh_m2": ipe_reel,
        "benchmark": {
            "median": median,
            "bon": bon,
            "performant": performant,
            "source": benchmark.get("source", "ADEME ODP 2024"),
        },
        "position": position,
        "surplus_kwh": round(surplus_kwh),
        "surcout_eur": surcout_eur,
        "economie_potentielle_pct": max(0, economie_pct),
        "type_site": type_site,
        "ademe_category": ademe_key,
    }
