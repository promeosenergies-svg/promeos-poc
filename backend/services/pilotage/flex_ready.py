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

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config.emission_factors import (
    get_emission_factor,
    get_emission_source,
)


class FlexReadySignalsResponse(BaseModel):
    """Reponse conforme NF EN IEC 62746-4 (marque Flex Ready (R) GIMELEC 2025)."""

    site_id: str = Field(..., description="Identifiant canonique du site")
    timestamp: str = Field(..., description="ISO 8601 Europe/Paris (horloge bidirectionnelle)")
    clock_resolution_min: int = Field(..., description="Resolution minimale (15 min norme)")
    puissance_max_instantanee_kw: float = Field(..., description="P max instantanee kW")
    prix_eur_kwh: float = Field(..., description="Prix (spot day-ahead ou tarif contractuel)")
    prix_source: str = Field(..., description="'entsoe_day_ahead' | 'fournisseur_tarif_base'")
    prix_age_hours: Optional[float] = Field(None, description="Age du prix spot (heures)")
    puissance_souscrite_kva: int = Field(..., description="P souscrite kVA (contrat GRD)")
    empreinte_carbone_kg_co2e_kwh: float = Field(..., description="Facteur emission kgCO2e/kWh")
    empreinte_source: str = Field(..., description="ID machine source ADEME")
    empreinte_source_label: str = Field(..., description="Label humain source")
    norme: str = Field(..., description="Norme de reference")
    conformite_flex_ready: bool = Field(..., description="True si 6 champs standard presents")


logger = logging.getLogger(__name__)

# Table de conformite NF EN IEC 62746-4 : champ payload <-> section norme
# Permet un audit formel de la conformite et evite le flag auto-proclame.
_FLEX_READY_FIELD_MAP: dict[str, str] = {
    "timestamp": "NF EN IEC 62746-4 §5.2.1 (horloge bidirectionnelle)",
    "clock_resolution_min": "NF EN IEC 62746-4 §5.2.1 (pas minimal 15 min)",
    "puissance_max_instantanee_kw": "NF EN IEC 62746-4 §5.2.2 (P max instantanee)",
    "prix_eur_kwh": "NF EN IEC 62746-4 §5.2.3 (signal prix)",
    "puissance_souscrite_kva": "NF EN IEC 62746-4 §5.2.4 (capacite contractuelle)",
    "empreinte_carbone_kg_co2e_kwh": "NF EN IEC 62746-4 §5.2.5 (empreinte carbone)",
}

# Fuseau reference France pour timestamps Flex Ready
_TZ_PARIS = ZoneInfo("Europe/Paris")

# Resolution minimale imposee par NF EN IEC 62746-4 (pas 15 min bidirectionnel)
_FLEX_READY_CLOCK_RESOLUTION_MIN = 15

# Norme de reference (affichee dans la payload pour audit)
_NORME = "NF EN IEC 62746-4"

# Age max d'un prix spot avant d'etre considere stale (fenetre day-ahead ~24h)
_PRIX_SPOT_MAX_AGE_H = 36


def _get_latest_spot(db: Session) -> Optional[tuple[float, float]]:
    """
    Retourne (prix_eur_kwh, age_hours) du dernier spot day-ahead FR, ou None.

    Age_hours permet au caller de detecter une donnee stale. Au-dela de
    `_PRIX_SPOT_MAX_AGE_H`, on considere la donnee trop ancienne et on retombe
    sur le tarif contractuel.

    Log warning sur exception (module indisponible, schema invalide) pour
    eviter d'avaler silencieusement les incidents prod.
    """
    try:
        from services.pilotage.connectors.entsoe_day_ahead import (
            get_latest_day_ahead_with_timestamp,
        )

        result = get_latest_day_ahead_with_timestamp(db)
    except ImportError as exc:
        logger.warning("flex_ready: ENTSO-E connector indisponible (%s)", exc)
        return None
    except Exception as exc:
        logger.warning("flex_ready: echec lecture spot (%s: %s)", type(exc).__name__, exc)
        return None

    if result is None:
        return None

    eur_mwh, delivery_start = result
    now_utc = datetime.now(timezone.utc)
    age = now_utc - delivery_start
    age_hours = age.total_seconds() / 3600.0
    if age_hours > _PRIX_SPOT_MAX_AGE_H:
        logger.info("flex_ready: spot trop ancien (%.1f h) -- fallback tarif", age_hours)
        return None
    return (round(eur_mwh / 1000.0, 5), round(age_hours, 2))


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
    if now is None:
        ts = datetime.now(_TZ_PARIS)
    elif now.tzinfo is None:
        # Convention : datetime naif injecte = UTC (safe default, pas interprete wall-clock)
        ts = now.replace(tzinfo=timezone.utc).astimezone(_TZ_PARIS)
    else:
        ts = now.astimezone(_TZ_PARIS)

    # Prix : priorite spot day-ahead reel frais, fallback tarif contractuel
    prix_contrat = float(demo_site["prix_eur_kwh"])
    spot_info = _get_latest_spot(db) if db is not None else None
    if spot_info is not None:
        prix_eur_kwh, prix_age_hours = spot_info
        prix_source = "entsoe_day_ahead"
    else:
        prix_eur_kwh = prix_contrat
        prix_source = "fournisseur_tarif_base"
        prix_age_hours = None

    # Empreinte carbone : source unique config/emission_factors.py (ADEME V23.6)
    energy_vector = str(demo_site.get("energy_vector", "ELEC")).upper()
    empreinte_kg_co2e_kwh = get_emission_factor(energy_vector)
    empreinte_source_label = get_emission_source(energy_vector)
    # Extrait l'ID machine (ex. "ADEME V23.6 2024" -> "ademe_v23.6_2024")
    empreinte_source = empreinte_source_label.lower().replace(" ", "_") if empreinte_source_label else "inconnu"

    payload = {
        "site_id": site_id,
        "timestamp": ts.isoformat(),
        "clock_resolution_min": _FLEX_READY_CLOCK_RESOLUTION_MIN,
        "puissance_max_instantanee_kw": float(demo_site["puissance_max_instantanee_kw"]),
        "prix_eur_kwh": round(float(prix_eur_kwh), 5),
        "prix_source": prix_source,
        "prix_age_hours": prix_age_hours,
        "puissance_souscrite_kva": int(demo_site["puissance_souscrite_kva"]),
        "empreinte_carbone_kg_co2e_kwh": round(float(empreinte_kg_co2e_kwh), 5),
        "empreinte_source": empreinte_source,
        "empreinte_source_label": empreinte_source_label,
        "norme": _NORME,
    }
    # Conformite calculee : tous les 6 champs standard presents et non-None
    payload["conformite_flex_ready"] = all(payload.get(field) is not None for field in _FLEX_READY_FIELD_MAP)
    return payload
