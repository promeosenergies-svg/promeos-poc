"""
PROMEOS — Routes Config : price references (fallback shadow billing).

GET /api/config/price-references

Expose la section `prix_reference` du YAML tarifs_reglementaires au frontend
pour éviter le hardcode `EUR_FACTOR = 0.068` dans les composants
(findings P1 audit QA Guardian SDK 2026-04-15).

⚠️ Ce n'est PAS une grille tarifaire réglementaire. C'est un **fallback**
non-réglementaire (prix spot moyen interne PROMEOS) utilisé pour estimer
un coût quand aucun contrat n'est attaché. Le flag `is_regulatory: false`
dans la réponse doit être respecté par le frontend (éviter de l'afficher
comme une "source officielle").

Pattern cohérent avec `config_emission_factors.py` (même structure).
"""

from __future__ import annotations

from fastapi import APIRouter

from config.tarif_loader import load_tarifs

router = APIRouter(prefix="/api/config", tags=["Config"])


@router.get("/price-references")
def get_price_references() -> dict:
    """Retourne les prix de référence (fallback shadow billing).

    Response :
      {
        "elec_eur_kwh": 0.068,
        "gaz_eur_kwh": 0.045,
        "source": "PROMEOS POC fallback (EPEX Spot 30j moyen, 2024-2025)",
        "valid_from": "2024-01-01",
        "is_regulatory": false,
        "doctrine": "Fallback non-réglementaire, ne pas afficher comme source officielle."
      }
    """
    tarifs = load_tarifs()
    pr = tarifs.get("prix_reference", {}) or {}
    return {
        "elec_eur_kwh": pr.get("elec_eur_kwh"),
        "gaz_eur_kwh": pr.get("gaz_eur_kwh"),
        "source": pr.get("source"),
        "valid_from": pr.get("valid_from"),
        "is_regulatory": bool(pr.get("is_regulatory", False)),
        "doctrine": (
            "Fallback non-réglementaire PROMEOS (prix spot moyen). "
            "À utiliser uniquement pour l'affichage de coûts estimés quand "
            "aucun contrat n'est attaché. Pour les calculs shadow billing "
            "réels, privilégier les contrats réels (EnergyContract) ou "
            "ParameterStore (tarifs versionnés)."
        ),
    }
