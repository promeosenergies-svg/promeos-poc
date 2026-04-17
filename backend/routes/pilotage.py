"""
PROMEOS - Routes Pilotage des usages.

Endpoint Flex Ready (R) -- expose les 5 donnees standardisees (NF EN IEC 62746-4)
pour un site de demonstration.

Reference : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.pilotage.flex_ready import build_flex_ready_signals


router = APIRouter(prefix="/api/pilotage", tags=["Pilotage"])


# ---------------------------------------------------------------------------
# DEMO_SITES : fiches hardcodees pour la demo Flex Ready (R).
# Chaque fiche porte les 4 donnees statiques du standard (puissance max, prix
# tarif, puissance souscrite, vecteur energetique). Le 5e signal (empreinte
# carbone) vient de config/emission_factors.py. Le 1er signal (horloge) est
# genere au moment de l'appel.
# ---------------------------------------------------------------------------
DEMO_SITES: dict[str, dict[str, Any]] = {
    "retail-001": {
        "nom": "Hypermarche Montreuil",
        "puissance_max_instantanee_kw": 180.0,
        "prix_eur_kwh": 0.185,
        "puissance_souscrite_kva": 250,
        "energy_vector": "ELEC",
    },
    "bureau-001": {
        "nom": "Bureau Haussmann",
        "puissance_max_instantanee_kw": 95.0,
        "prix_eur_kwh": 0.172,
        "puissance_souscrite_kva": 144,
        "energy_vector": "ELEC",
    },
    "entrepot-001": {
        "nom": "Entrepot Rungis",
        "puissance_max_instantanee_kw": 320.0,
        "prix_eur_kwh": 0.158,
        "puissance_souscrite_kva": 400,
        "energy_vector": "ELEC",
    },
}


def _build_demo_site_ctx(site_id: str) -> dict[str, Any]:
    """
    Retourne la fiche DEMO_SITES pour `site_id`.
    Leve HTTP 404 si le site n'est pas dans la liste demo.
    """
    ctx = DEMO_SITES.get(site_id)
    if ctx is None:
        raise HTTPException(
            status_code=404,
            detail=f"Site demo inconnu : '{site_id}'. Sites disponibles : {sorted(DEMO_SITES.keys())}",
        )
    return ctx


@router.get("/flex-ready-signals/{site_id}")
def flex_ready_signals(site_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Expose les 5 signaux standardises Flex Ready (R) conformes NF EN IEC 62746-4.

    Les 5 donnees echangees GTB <-> marche (Barometre Flex 2026) :
        1. Horloge (pas 15 min min, bidirectionnel)
        2. Puissance max instantanee (kW)
        3. Prix fournisseur (EUR/kWh) -- fallback tarif si spot indisponible
        4. Puissance souscrite (kVA)
        5. Empreinte carbone (kgCO2e/kWh) -- source ADEME V23.6

    404 si le site n'est pas dans DEMO_SITES.
    """
    ctx = _build_demo_site_ctx(site_id)
    return build_flex_ready_signals(site_id=site_id, demo_site=ctx, db=db)
