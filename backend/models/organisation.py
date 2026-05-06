"""
PROMEOS - Modèle Organisation
Niveau groupe/client COMEX (ex: "Groupe HELIOS", "Ville de Lyon")
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin


class Organisation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    type_client = Column(String, nullable=True)  # "retail", "tertiaire", "industrie"
    logo_url = Column(String, nullable=True)
    siren = Column(String(9), nullable=True, comment="Numero SIREN")
    actif = Column(Boolean, default=True)
    is_demo = Column(Boolean, default=False, comment="Donnees de demonstration")

    # ─── Sprint C-4 Phase 4.4 — Consentement RGPD (ADR-007) ──────────────────
    # Pré-requis cardinal Phase 4.5 cascade vivante org → DPs.
    # Court-circuit ELD locales préservé : cascade GRDF cible UNIQUEMENT
    # delivery_points.grd_code='GRDF' (pas Régaz/GreenAlp/R-GDS/etc.).
    consentement_dataconnect_global = Column(
        Boolean,
        nullable=True,
        comment="Consentement DataConnect (Enedis) global org-level (ADR-007 Sprint C-4)",
    )
    consentement_dataconnect_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp dernier changement consentement DataConnect (RGPD audit trail)",
    )
    consentement_grdf_global = Column(
        Boolean,
        nullable=True,
        comment="Consentement GRDF ADICT global org-level (court-circuit ELD locales préservé)",
    )
    consentement_grdf_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp dernier changement consentement GRDF (RGPD audit trail)",
    )

    # ─── Sprint C-5 Phase 5.3 — Audit RGPD étendu (ADR-007 ext) ──────────────
    # ondelete=SET NULL : suppression user RGPD-droit oubli préserve l'historique
    # de consentement (la trace persiste, la référence personnelle disparaît).
    consentement_dataconnect_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ayant donné le consentement DataConnect (RGPD audit, NULL si user supprimé)",
    )
    consentement_dataconnect_cgu_version = Column(
        String(20),
        nullable=True,
        comment="Version CGU au moment du consentement DataConnect (ex: '1.0', '2.1.0')",
    )
    consentement_grdf_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User ayant donné le consentement GRDF (RGPD audit, NULL si user supprimé)",
    )
    consentement_grdf_cgu_version = Column(
        String(20),
        nullable=True,
        comment="Version CGU au moment du consentement GRDF",
    )

    # Relations (1-to-many)
    entites_juridiques = relationship(
        "EntiteJuridique",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
