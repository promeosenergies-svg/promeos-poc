"""
PROMEOS - Modèle Entité Juridique
SIREN/SIRET - qui signe les contrats / qui paye
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin, SoftDeleteMixin


class EntiteJuridique(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "entites_juridiques"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    siren = Column(String(9), unique=True, nullable=False)
    siret = Column(String(14), nullable=True)
    naf_code = Column(String(10), nullable=True, comment="Code NAF principal (ex: 47.11F)")
    region_code = Column(String(3), nullable=True, comment="Code region")
    insee_code = Column(String(5), nullable=True, comment="Code INSEE siege")

    # Phase D-4 Tier 1 — P0-MATV1-001 : déclencheur Audit SMÉ deadline 11/10/2026
    # Source : Loi DDADUE 2025-391 + Décret 2024-1304 — seuils 2.75 / 23.6 GWh.
    # Audit cardinal : docs/audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §3 P0-MATV1-001.
    consommation_annuelle_moyenne_3y_gwh = Column(
        Float,
        nullable=True,
        comment="Consommation annuelle moyenne 3 ans (GWh) — déclencheur Audit SMÉ matrice v1 §4.2#18",
    )

    # Relations
    organisation = relationship("Organisation", back_populates="entites_juridiques")
    portefeuilles = relationship(
        "Portefeuille",
        back_populates="entite_juridique",
        cascade="all, delete-orphan",
    )
