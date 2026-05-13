"""
PROMEOS - Modèle Organisation
Niveau groupe/client COMEX (ex: "Groupe HELIOS", "Ville de Lyon")
"""

import re

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, validates
from .base import Base, TimestampMixin, SoftDeleteMixin

# Phase D-3 Tier 2 VAL-2 — tva_intra format ^FR\d{11}$ (audit P1-AUDIT-D-018).
_TVA_INTRA_FR_PATTERN = re.compile(r"^FR\d{2}\d{9}$")


class Organisation(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, nullable=False)
    type_client = Column(String, nullable=True)  # "retail", "tertiaire", "industrie"
    logo_url = Column(String, nullable=True)
    siren = Column(String(9), nullable=True, comment="Numero SIREN")
    actif = Column(Boolean, default=True)
    is_demo = Column(Boolean, default=False, comment="Donnees de demonstration")

    # Phase D-1 hotfix — D-Audit-PARAM-Org-Champs-004 P1 :
    # 6 champs entreprise enrichie matrice v1 §4.1 (cible 16 champs, gap 6 manquants).
    # Anti-pattern : `type_client` partiel ≠ `secteur` cardinal entreprise.
    tva_intra = Column(
        String(20),
        nullable=True,
        comment="N° TVA intracommunautaire (FR + 11 chars) — matrice v1 §4.1",
    )
    code_naf_principal = Column(
        String(10),
        nullable=True,
        index=True,
        comment="Code NAF principal entreprise (ex: 6201Z) — matrice v1 §4.1",
    )
    pays = Column(
        String(2),
        nullable=True,
        default="FR",
        comment="Pays (ISO 3166-1 alpha-2, défaut FR) — matrice v1 §4.1",
    )
    secteur = Column(
        String(50),
        nullable=True,
        comment="Secteur d'activité (industrie/tertiaire_bureaux/tertiaire_commerce/etc.) — matrice v1 §4.1",
    )
    effectif_total = Column(
        Integer,
        nullable=True,
        comment="Effectif total entreprise (TPE<10/PME<50/PME<250/ETI<5000/GE) — matrice v1 §4.1",
    )
    chiffre_affaires_eur = Column(
        Float,
        nullable=True,
        comment="Chiffre d'affaires annuel EUR — matrice v1 §4.1 (segmentation Audit SMÉ)",
    )

    # Phase 3.7 P0 — Code énergie L233-1 critère SMÉ (b) : bilan total
    # ≥ 43 M€ + CA ≥ 50 M€ → audit obligatoire. Audit regulatory-expert
    # P3.5 a flagué le champ absent (SMEEvaluator faux NOT_APPLICABLE.PME).
    bilan_eur = Column(
        Float,
        nullable=True,
        comment="Bilan total EUR — Code énergie L233-1 critère SMÉ (b), Phase 3.7",
    )

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

    # ─── Phase D-3 Tier 2 DOC-1 + VAL-2 validators (audit P1-AUDIT-D-009 + -018) ───

    @validates("secteur")
    def _validate_secteur_strict(self, key: str, value: str | None):
        """DOC-1 : `secteur` réutilise `Typologie` Enum existant.

        Pattern Pilier 9 ADR-016 — String reste, validator runtime exige Enum value
        (TERTIAIRE_PRIVE/TERTIAIRE_PUBLIC/INDUSTRIE/COMMERCE_RETAIL/etc.).
        """
        if value is None or value == "":
            return value
        from .enums import Typologie

        valid = {v.value for v in Typologie}
        if value not in valid:
            raise ValueError(
                f"DOC-1 Phase D-3 Tier 2 violation : secteur={value!r} non canonique "
                f"(attendu un de {sorted(valid)} — Typologie)"
            )
        return value

    @validates("tva_intra")
    def _validate_tva_intra_format(self, key: str, value: str | None):
        """VAL-2 Phase D-3 Tier 2 : `tva_intra` format `^FR\\d{11}$` strict (P1-AUDIT-D-018).

        N° TVA intracommunautaire FR = `FR` + clé 2 chiffres + SIREN 9 chiffres = 13 chars total.
        """
        if value is None or value == "":
            return value
        if not _TVA_INTRA_FR_PATTERN.match(value):
            raise ValueError(
                f"VAL-2 Phase D-3 Tier 2 violation : tva_intra={value!r} format invalide "
                f"(attendu `^FR\\d{{11}}$` — 'FR' + clé 2 chiffres + SIREN 9 chiffres)"
            )
        return value

    # Relations (1-to-many)
    entites_juridiques = relationship(
        "EntiteJuridique",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
