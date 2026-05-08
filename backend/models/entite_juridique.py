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

    # Phase D-4 Tier 2 — 6 P1 doctrine cardinaux matrice v1 §4.2#9-17 :
    # adresse siège (Sirène round-trip + scoring conformité géo) + co-déclencheurs Audit SMÉ.
    # Audit : AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §4 P1-MATV1-011→016.
    #
    # ⚠️ SoT cardinal contrat sémantique Org vs EJ (P1-D fix code-reviewer audit milieu-étape) :
    # - `Organisation.chiffre_affaires_eur` + `Organisation.pays` = niveau **groupe consolidé**
    #   (cas Holding/Mère pour reporting CSRD ESRS E1).
    # - `EntiteJuridique.chiffre_affaires_eur` + `EntiteJuridique.pays` = niveau **entité signataire
    #   contrats** (cas filiale juridique distincte). **SoT pour Audit SMÉ** (Loi DDADUE 2025-391
    #   art. 8 — appliqué par EJ qui paye les factures, pas par groupe consolidé).
    # Cf. compliance_score_service.py qui DOIT lire EJ.* pour calcul assujettissement.
    adresse_siege = Column(String(500), nullable=True, comment="Adresse siège — matrice v1 §4.2#9")
    code_postal_siege = Column(String(5), nullable=True, comment="Code postal siège — matrice v1 §4.2#10")
    commune_siege = Column(String(100), nullable=True, comment="Commune siège — matrice v1 §4.2#11")
    pays = Column(String(2), nullable=True, default="FR", comment="Pays ISO 3166-1 alpha-2 — matrice v1 §4.2#12")
    effectif_etp = Column(
        Integer,
        nullable=True,
        comment="Effectif ETP entreprise — co-déclencheur Audit SMÉ matrice v1 §4.2#16",
    )
    chiffre_affaires_eur = Column(
        Float,
        nullable=True,
        comment="CA annuel EUR — co-déclencheur Audit SMÉ matrice v1 §4.2#17 (Sirène)",
    )

    # Relations
    organisation = relationship("Organisation", back_populates="entites_juridiques")
    portefeuilles = relationship(
        "Portefeuille",
        back_populates="entite_juridique",
        cascade="all, delete-orphan",
    )
