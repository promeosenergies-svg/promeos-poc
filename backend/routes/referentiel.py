"""
PROMEOS — Référentiel Tarifs Route (Step 18)
GET /api/referentiel/tarifs — tarifs réglementaires en vigueur (public, no auth).
"""

from fastapi import APIRouter

from config.tarif_loader import get_tarif_summary

router = APIRouter(prefix="/api/referentiel", tags=["Référentiel"])


@router.get("/tarifs")
def get_tarifs():
    """Tarifs réglementaires énergie France B2B (TURPE, accises, CTA, TVA)."""
    return get_tarif_summary()
