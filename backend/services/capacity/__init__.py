"""
PROMEOS Capacity Module — P1 Nov 2026

Éligibilité et scoring pour le mécanisme de capacité centralisé RTE
(en vigueur 1er novembre 2026). Enchères PL-4 + PL-1.

Références KB : CAPACITE-MECANISME-RTE-2026, CAPACITE-ELIGIBILITE-ACTIFS.
"""

from .eligibility import (
    EligibilityScore,
    FlexAssetType,
    FlexibleAsset,
    compute_asset_eligibility,
    compute_portfolio_eligibility,
)
from .revenue import CapacityRevenueEstimate, EnchereType, estimate_capacity_revenue

__all__ = [
    "CapacityRevenueEstimate",
    "EligibilityScore",
    "EnchereType",
    "FlexAssetType",
    "FlexibleAsset",
    "compute_asset_eligibility",
    "compute_portfolio_eligibility",
    "estimate_capacity_revenue",
]
