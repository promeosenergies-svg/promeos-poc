"""
PROMEOS — TaxProfile (Vague 1 data model).

Mapping point de livraison → régime fiscal pour accise élec/gaz.
Permet au moteur shadow billing d'appliquer le bon taux d'accise selon la
catégorie réglementaire (ménages, PME, haute puissance, réduit, exonéré).

Un DeliveryPoint peut avoir 0 ou 1 TaxProfile actif. L'absence = régime
par défaut (déduit du segment TURPE pour l'élec, NORMAL pour le gaz).
"""

from sqlalchemy import Boolean, Column, Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin
from .enums import AcciseCategoryElec, AcciseCategoryGaz


class TaxProfile(Base, TimestampMixin):
    """Profil fiscal d'un point de livraison."""

    __tablename__ = "tax_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    delivery_point_id = Column(
        Integer,
        ForeignKey("delivery_points.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Point de livraison rattaché",
    )

    # Catégories accise (nullable : l'une des deux selon energy_type du PDL)
    accise_category_elec = Column(
        Enum(AcciseCategoryElec),
        nullable=True,
        comment="Catégorie accise élec (si PDL élec)",
    )
    accise_category_gaz = Column(
        Enum(AcciseCategoryGaz),
        nullable=True,
        comment="Catégorie accise gaz (si PDL gaz)",
    )

    # Régime réduit / exonération : traçabilité et éligibilité
    regime_reduit = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="True si régime réduit/exonéré (électro-intensif, double usage...)",
    )
    attestation_ref = Column(
        String(200),
        nullable=True,
        comment="Référence attestation réglementaire (arrêté, n° dossier)",
    )
    eligibility_code = Column(
        String(50),
        nullable=True,
        comment="Code fiscal éligibilité (ex: CIBS art 266 quinquies)",
    )

    # Période de validité (utile si le régime change dans le temps)
    valid_from = Column(Date, nullable=True, comment="Début de validité du régime")
    valid_to = Column(Date, nullable=True, comment="Fin de validité (null = en cours)")

    # Métadonnées libres
    notes = Column(Text, nullable=True, comment="Commentaires libres")

    # Relation
    delivery_point = relationship(
        "DeliveryPoint",
        foreign_keys=[delivery_point_id],
        backref="tax_profiles",
    )

    def __repr__(self):
        cat = self.accise_category_elec or self.accise_category_gaz
        return f"<TaxProfile(pdl={self.delivery_point_id}, cat={cat})>"
