"""Domain enum — doctrine v0.3 §3 + L7 §3.7.

D5 PRAGMATIQUE EXTENSIBILITÉ : pas de CHECK constraint DB sur la colonne
`action_center_items.domain` (VARCHAR(30) libre). L'enum Python documente
les 7 valeurs canoniques actuelles ; validation Pydantic souple côté service
permet l'ajout de nouveaux modules Mois 6+ sans migration DDL.

Cohérence R6 plancher P1 conformité (doctrine v0.3 §5.6) : si
`domain ∈ {conformite, facturation}` ET `regulatory_rule_id IS NOT NULL`
→ bracket plancher P1 forcé par PriorityScoringService.
"""

from enum import Enum


class Domain(str, Enum):
    """7 valeurs canoniques (extensible Mois 6+ sans migration DDL — D5)."""

    CONFORMITE = "conformite"  # DT, BACS, APER, Audit SMÉ
    FACTURATION = "facturation"  # Bill Intelligence (R01-R20)
    MAINTENANCE = "maintenance"
    OPTIMISATION = "optimisation"  # Économies, EMS
    PURCHASE = "purchase"  # Achat énergie
    FLEXIBILITE = "flexibilite"  # NEBCO/AOFD
    DATA_QUALITY = "data_quality"  # PHOTO D020, Sirene

    @classmethod
    def values(cls) -> list[str]:
        return [d.value for d in cls]

    @classmethod
    def is_compliance_floor_eligible(cls, domain: str) -> bool:
        """R6 plancher P1 conformité (doctrine v0.3 §5.6) — domains éligibles."""
        return domain in (cls.CONFORMITE.value, cls.FACTURATION.value)
