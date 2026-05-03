"""Historique bascules Site↔Portefeuille — Sprint C-2 Phase 2.

Source : matrice v1 §6.5 + audit Phase B R4 (temporalité).

Permet :
- Analyses rétrospectives (KPI portefeuille à date donnée)
- Audit trail des bascules (qui, quand, pourquoi)
- Cohérence avec audit_log_service Phase 1 (entry_id référencé dans audit log payload)

Convention temporelle :
- 1 entrée = 1 période d'appartenance Site à un Portefeuille
- valid_to = None → période courante (active)
- Bascule : valid_to ancien = valid_from nouveau (continuité temporelle)

⚠️ Invariant métier (enforced par site_portefeuille_service) :
- Bascule cross-EJ INTERDITE (un Site doit rester dans la même Entité Juridique).
- Cf. CrossEjTransferError dans services/site_portefeuille_service.py.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .base import Base, TimestampMixin


class SitePortefeuilleHistory(Base, TimestampMixin):
    """Historique des bascules Site↔Portefeuille avec valid_from/valid_to."""

    __tablename__ = "site_portefeuille_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(
        Integer,
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
        comment="Site qui appartient au portefeuille pendant la période",
    )
    portefeuille_id = Column(
        Integer,
        ForeignKey("portefeuilles.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Portefeuille auquel le site est rattaché",
    )

    # Temporalité
    valid_from = Column(
        DateTime,
        nullable=False,
        comment="Début de la période (inclusif)",
    )
    valid_to = Column(
        DateTime,
        nullable=True,
        comment="Fin de la période (inclusif). None = période courante (active)",
    )

    # Audit
    transferred_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        comment="Utilisateur ayant déclenché la bascule (None si système/cron)",
    )
    raison = Column(
        String(500),
        nullable=True,
        comment="Raison textuelle de la bascule (saisie utilisateur)",
    )
    metadata_json = Column(
        Text,
        nullable=True,
        comment="Payload contextuel optionnel (correlation_id, batch_id, etc.)",
    )

    __table_args__ = (
        Index("ix_sph_site_id_valid_from", "site_id", "valid_from"),
        Index("ix_sph_portefeuille_id_valid_from", "portefeuille_id", "valid_from"),
    )

    # Relations
    site = relationship("Site", foreign_keys=[site_id])
    portefeuille = relationship("Portefeuille", foreign_keys=[portefeuille_id])
    transferred_by = relationship("User", foreign_keys=[transferred_by_user_id])

    def __repr__(self):
        return (
            f"<SitePortefeuilleHistory site={self.site_id} pf={self.portefeuille_id} "
            f"valid_from={self.valid_from} valid_to={self.valid_to}>"
        )
