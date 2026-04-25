"""
PROMEOS Capacity — Revenue Estimation

Estime les revenus potentiels d'un actif ou portefeuille au mécanisme de
capacité RTE 2026+, basé sur enchères PL-4 / PL-1.

Source prix : KB CAPACITE-ELIGIBILITE-ACTIFS. 2025 ~30 k€/MW/an, fourchette
attendue 2026+ : 20-50 k€/MW/an.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class EnchereType(str, Enum):
    """Types d'enchères du mécanisme centralisé."""

    PL4 = "pl_4"
    PL1 = "pl_1"


PRIX_MOYEN_MW_AN: dict[EnchereType, tuple[float, float, float]] = {
    EnchereType.PL4: (25_000, 35_000, 45_000),
    EnchereType.PL1: (20_000, 30_000, 50_000),
}


@dataclass
class CapacityRevenueEstimate:
    """Estimation revenus capacité sur 1 an (1 période PP1)."""

    puissance_certifiable_mw: float
    enchere_type: EnchereType
    revenu_min_eur: float
    revenu_moyen_eur: float
    revenu_max_eur: float
    confidence: str = "medium"
    kb_item_ids: list[str] = field(
        default_factory=lambda: ["CAPACITE-MECANISME-RTE-2026", "CAPACITE-ELIGIBILITE-ACTIFS"]
    )


def estimate_capacity_revenue(
    puissance_certifiable_kw: float,
    enchere_type: EnchereType = EnchereType.PL1,
    retention_agregateur_pct: float = 15.0,
) -> CapacityRevenueEstimate:
    """Estime les revenus capacité nets après commission agrégateur."""
    puissance_mw = puissance_certifiable_kw / 1000.0
    prix_min, prix_moyen, prix_max = PRIX_MOYEN_MW_AN[enchere_type]

    retention = retention_agregateur_pct / 100.0
    revenu_net_min = puissance_mw * prix_min * (1 - retention)
    revenu_net_moyen = puissance_mw * prix_moyen * (1 - retention)
    revenu_net_max = puissance_mw * prix_max * (1 - retention)

    confidence = "medium" if enchere_type == EnchereType.PL1 else "low"

    return CapacityRevenueEstimate(
        puissance_certifiable_mw=round(puissance_mw, 2),
        enchere_type=enchere_type,
        revenu_min_eur=round(revenu_net_min, 0),
        revenu_moyen_eur=round(revenu_net_moyen, 0),
        revenu_max_eur=round(revenu_net_max, 0),
        confidence=confidence,
    )
