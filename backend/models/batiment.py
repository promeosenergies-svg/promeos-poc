"""
PROMEOS - Modèle Bâtiment
Unité réglementaire (décret tertiaire, BACS)
"""

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from .base import Base, SoftDeleteMixin, TimestampMixin


class Batiment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "batiments"
    # Sprint D1-B C50 matrice v1 §8.3 : nom bâtiment unique par site (anti-doublon
    # de saisie manuelle parc multi-bâtiments).
    __table_args__ = (UniqueConstraint("site_id", "nom", name="uq_batiment_nom_per_site"),)

    id = Column(Integer, primary_key=True, index=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False, index=True)
    nom = Column(String, nullable=False)
    surface_m2 = Column(Float, nullable=False)
    annee_construction = Column(Integer, nullable=True)
    cvc_power_kw = Column(Float, nullable=True, comment="Puissance CVC nominale (kW)")

    # Phase D-0 hotfix — D-Audit-PARAM-Bati-Champs-Manquants-001 P0 :
    # 5 champs cardinaux matrice v1 §4.5 ajoutés (RNB V9.0 + DPE A-G + rénovation lourde).
    # Cohérent L2 + L4 limites Section 11 audit (Phase 8.4 audit deep).

    rnb_id = Column(
        String(20),
        nullable=True,
        index=True,
        comment="Référentiel National Bâtiments V9.0 (matrice v1 §4.5 — obligatoire OPERAT 2026)",
    )
    dpe_class = Column(
        String(1),
        nullable=True,
        comment="Classe DPE A-G (matrice v1 §4.5 — Décret n° 2020-1610 modifié 2024)",
    )
    dpe_score_kwhep_m2_an = Column(
        Float,
        nullable=True,
        comment="Score DPE en énergie primaire (kWhep/m²/an) — différenciateur intensité énergétique",
    )
    dpe_date_validite = Column(
        Date,
        nullable=True,
        comment="Date validité DPE (10 ans depuis émission) — alerte renouvellement",
    )
    annee_renovation_lourde = Column(
        Integer,
        nullable=True,
        comment="Année rénovation lourde (matrice v1 §4.5) — base ajustée OPERAT post-rénovation",
    )

    # ─── Phase D-3 Tier 2 DOC-1 — String→Enum validator (P1-AUDIT-D-011) ───

    @validates("dpe_class")
    def _validate_dpe_class_strict(self, key: str, value: str | None):
        """DOC-1 Phase D-3 Tier 2 : `dpe_class` réutilise `DpeClasseEnergie` Enum existant.

        Valeurs canoniques : A/B/C/D/E/F/G + VIERGE.
        Pattern Pilier 9 ADR-016.
        """
        if value is None or value == "":
            return value
        from .enums import DpeClasseEnergie

        valid = {v.value for v in DpeClasseEnergie}
        if value not in valid:
            raise ValueError(
                f"DOC-1 Phase D-3 Tier 2 violation : dpe_class={value!r} non canonique "
                f"(attendu {sorted(valid)} — DpeClasseEnergie)"
            )
        return value

    # Relations
    site = relationship("Site", back_populates="batiments")
