"""
PROMEOS — Routes Config : emission factors

GET /api/config/emission-factors

Expose la source unique `config/emission_factors.py` au frontend via HTTP.
Objectif : supprimer le hardcode `CO2E_FACTOR_KG_PER_KWH` dans
`frontend/src/pages/consumption/constants.js` en laissant le backend
servir les facteurs ADEME via une API. Si ADEME met à jour, mise à jour
backend + restart = propagation frontend sans redéploiement frontend.

Fix P0 #1-5 de l'audit QA Guardian SDK (2026-04-15, scope source-guards).
Le fix #6 (persistent DB pollution) a déjà été livré dans `routes/actions.py`
(helper `_resolve_co2e_kg`, commit bece37a7).
"""

from __future__ import annotations

from fastapi import APIRouter

from config.emission_factors import EMISSION_FACTORS

router = APIRouter(prefix="/api/config", tags=["Config"])


@router.get("/emission-factors")
def get_emission_factors() -> dict:
    """Retourne les facteurs d'émission CO₂e par vecteur énergétique.

    Source unique : `backend/config/emission_factors.py` (ADEME Base Empreinte V23.6).

    Response :
      {
        "factors": {
          "elec": {
            "kgco2e_per_kwh": <valeur ELEC depuis la source de vérité>,
            "source": "ADEME Base Empreinte V23.6 ...",
            "year": 2024
          },
          "gaz": { ... }
        },
        "source_version": "ADEME V23.6",
        "doctrine": "Les calculs côté frontend utilisent cette API comme source ..."
      }
    """
    return {
        "factors": {vector.lower(): entry for vector, entry in EMISSION_FACTORS.items()},
        "source_version": "ADEME Base Empreinte V23.6",
        "doctrine": (
            "Facteurs ADEME officiels. Jamais hardcoder côté frontend : "
            "fetcher cet endpoint au mount via EmissionFactorsContext. "
            "Pour persistence en DB : envoyer estimated_savings_kwh_year, "
            "le backend calcule via _resolve_co2e_kg (routes/actions.py)."
        ),
    }
