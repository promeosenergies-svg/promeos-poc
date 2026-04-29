"""
PROMEOS — Modèle EurAmount typé (Décision A §0.D)

Tout montant € exposé doit être traçable :
  - CALCULATED_REGULATORY : article réglementaire cité (DT/BACS/OPERAT/TURPE…)
  - CALCULATED_CONTRACTUAL : lié à un EnergyContract

PAS de "modeled" ni "estimated" — les valeurs non-traçables réglementairement
ou contractuellement DOIVENT être exprimées en énergie (MWh/an), jamais en €.

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §0.D + §2.B Phase 1.1
"""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)

from .base import Base


class EurAmountCategory(str, PyEnum):
    """Doctrine décision A : 2 catégories canoniques uniquement.

    PAS de "modeled" ni "estimated" — toute valeur sans traçabilité
    réglementaire ou contractuelle DOIT être exprimée en énergie (MWh/an).
    """

    CALCULATED_REGULATORY = "calculated_regulatory"
    CALCULATED_CONTRACTUAL = "calculated_contractual"


class EurAmount(Base):
    """Montant € typé avec traçabilité obligatoire.

    Chaque entrée référence soit un article réglementaire (BACS, DT, OPERAT…)
    soit un contrat d'énergie. La contrainte DB enforce cette règle au niveau
    persistance — aucune insertion ne peut contourner la traçabilité.
    """

    __tablename__ = "eur_amounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value_eur = Column(Float, nullable=False, comment="Montant en € HT")
    category = Column(
        Enum(
            EurAmountCategory,
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        comment="Catégorie canonique (regulatory/contractual). values_callable "
        "force le stockage des values minuscules pour aligner avec le CHECK.",
    )
    regulatory_article = Column(
        String(255),
        nullable=True,
        comment="Article réglementaire source (ex: 'Décret 2019-771 art. 9')",
    )
    contract_id = Column(
        Integer,
        ForeignKey("energy_contracts.id"),
        nullable=True,
        comment="Contrat d'énergie source (EnergyContract.id)",
    )
    formula_text = Column(
        String(500),
        nullable=False,
        comment="Formule de calcul lisible (ex: '3 sites × 7500 + 1 site × 3750')",
    )
    computed_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Horodatage du calcul",
    )

    __table_args__ = (
        CheckConstraint(
            "(category = 'calculated_regulatory' AND regulatory_article IS NOT NULL) OR "
            "(category = 'calculated_contractual' AND contract_id IS NOT NULL)",
            name="eur_amount_traceability_check",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<EurAmount id={self.id} value={self.value_eur}€ category={self.category} computed_at={self.computed_at}>"
        )
