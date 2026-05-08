"""
PROMEOS - Modèle Portefeuille
Regroupement décisionnel (ex: "Retail IDF", "Région Sud")
"""

import re

from sqlalchemy import JSON, Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship, validates

from .base import Base, SoftDeleteMixin, TimestampMixin

# Phase D-4 Tier 3 — couleur UI hex strict (#RRGGBB ou #RGB).
_HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class Portefeuille(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "portefeuilles"

    id = Column(Integer, primary_key=True, index=True)
    entite_juridique_id = Column(Integer, ForeignKey("entites_juridiques.id"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Phase D-4 Tier 3 — 6 P1 polish matrice v1 §4.3#6-11
    # Audit : AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §4 P1-MATV1-017+018 + §4.3 polish.
    responsable_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Responsable portefeuille (FK User) — matrice v1 §4.3#6",
    )
    actif = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="Portefeuille actif (cohérent SoftDeleteMixin + not_deleted) — matrice v1 §4.3#9",
    )
    couleur_ui = Column(String(7), nullable=True, comment="Couleur UI hex #RRGGBB — matrice v1 §4.3#7")
    tags = Column(JSON, nullable=True, comment="Tags JSON libres (UX filtrage) — matrice v1 §4.3#8")
    code_interne = Column(String(50), nullable=True, index=True, comment="Code interne — matrice v1 §4.3#10")
    notes = Column(Text, nullable=True, comment="Notes libres — matrice v1 §4.3#11")

    @validates("couleur_ui")
    def _validate_couleur_ui_hex(self, key: str, value: str | None):
        """Phase D-4 Tier 3 : couleur_ui format hex strict (#RRGGBB ou #RGB)."""
        if value is None or value == "":
            return value
        if not _HEX_COLOR_PATTERN.match(value):
            raise ValueError(
                f"Phase D-4 Tier 3 violation : couleur_ui={value!r} format invalide (attendu #RRGGBB ou #RGB hex)"
            )
        return value

    # Relations
    entite_juridique = relationship("EntiteJuridique", back_populates="portefeuilles")
    responsable = relationship("User", foreign_keys=[responsable_id])
    sites = relationship("Site", back_populates="portefeuille", cascade="all, delete-orphan")
