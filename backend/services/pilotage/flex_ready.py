"""
PROMEOS - Signaux Flex Ready (R) conformes NF EN IEC 62746-4.

Le standard Flex Ready (R) (marque GIMELEC / Think Smartgrids, Barometre Flex 2026
RTE/Enedis) definit 5 donnees echangees entre la GTB d'un batiment et les acteurs
marche (fournisseurs, agregateurs, GRD) :

    1. Horloge             -- pas 15 min minimum, bidirectionnel
    2. Puissance max instantanee (kW)
    3. Prix                -- tarif fournisseur (EUR/kWh)
    4. Puissance souscrite (kVA)
    5. Empreinte carbone   -- facteur kgCO2e/kWh

Cette brique expose ces 5 donnees pour un site donne. En mode demo, elle
utilise les valeurs hardcodees de DEMO_SITES (voir routes/pilotage.py).
Fallback gracieux : si une donnee reelle (ex. prix spot ENTSO-E) est
absente en DB, on retombe sur le tarif contractuel du site.

Norme de reference : NF EN IEC 62746-4 (interface GTB <-> marche, OpenADR).
Source calibrage : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from config.emission_factors import (
    get_emission_factor,
    get_emission_source,
)

# Fuseau reference France pour timestamps Flex Ready
_TZ_PARIS = ZoneInfo("Europe/Paris")

# Resolution minimale imposee par NF EN IEC 62746-4 (pas 15 min bidirectionnel)
_FLEX_READY_CLOCK_RESOLUTION_MIN = 15

# Norme de reference (affichee dans la payload pour audit)
_NORME = "NF EN IEC 62746-4"


def _get_latest_spot_eur_kwh(db: Session) -> Optional[float]:
    """
    Retourne le dernier prix spot day-ahead FR en EUR/kWh, ou None.
    Encapsule le connecteur ENTSO-E pour ne pas faire crasher la route si
    le module est indisponible (fallback gracieux).
    """
    try:
        from services.pilotage.connectors.entsoe_day_ahead import (
            get_latest_day_ahead_eur_mwh,
        )

        eur_mwh = get_latest_day_ahead_eur_mwh(db)
        if eur_mwh is None:
            return None
        return round(eur_mwh / 1000.0, 5)
    except Exception:
        return None


def build_flex_ready_signals(
    site_id: str,
    demo_site: dict[str, Any],
    db: Optional[Session] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Construit le payload Flex Ready (R) pour un site demo.

    Parametres
    ----------
    site_id : str
        Identifiant canonique du site (ex. "retail-001").
    demo_site : dict
        Fiche site hardcodee (DEMO_SITES) avec au minimum :
            - puissance_max_instantanee_kw : float
            - prix_eur_kwh                 : float (tarif contractuel fallback)
            - puissance_souscrite_kva      : int
            - energy_vector                : "ELEC" | "GAZ" (optionnel, defaut ELEC)
    db : Session, optionnel
        Session DB pour interroger le prix spot reel. Si None ou echec,
        on retombe sur le tarif contractuel (`prix_eur_kwh`).
    now : datetime, optionnel
        Injection d'horloge pour les tests. Defaut : datetime.now(Europe/Paris).

    Retour
    ------
    dict conforme au standard Flex Ready (R) -- 5 donnees + metadonnees de trace.
    """
    ts = now or datetime.now(_TZ_PARIS)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=_TZ_PARIS)

    # Prix : priorite spot day-ahead reel, fallback tarif contractuel
    prix_contrat = float(demo_site["prix_eur_kwh"])
    prix_spot: Optional[float] = _get_latest_spot_eur_kwh(db) if db is not None else None
    if prix_spot is not None:
        prix_eur_kwh = prix_spot
        prix_source = "entsoe_day_ahead"
    else:
        prix_eur_kwh = prix_contrat
        prix_source = "fournisseur_tarif_base"

    # Empreinte carbone : source unique config/emission_factors.py (ADEME V23.6)
    energy_vector = str(demo_site.get("energy_vector", "ELEC")).upper()
    empreinte_kg_co2e_kwh = get_emission_factor(energy_vector)
    empreinte_source = "ademe_2024"  # cf. EMISSION_FACTORS[*].year = 2024
    empreinte_source_label = get_emission_source(energy_vector)

    return {
        "site_id": site_id,
        "timestamp": ts.isoformat(),
        "clock_resolution_min": _FLEX_READY_CLOCK_RESOLUTION_MIN,
        "puissance_max_instantanee_kw": float(demo_site["puissance_max_instantanee_kw"]),
        "prix_eur_kwh": round(float(prix_eur_kwh), 5),
        "prix_source": prix_source,
        "puissance_souscrite_kva": int(demo_site["puissance_souscrite_kva"]),
        "empreinte_carbone_kg_co2e_kwh": round(float(empreinte_kg_co2e_kwh), 5),
        "empreinte_source": empreinte_source,
        "empreinte_source_label": empreinte_source_label,
        "conformite_flex_ready": True,
        "norme": _NORME,
    }
