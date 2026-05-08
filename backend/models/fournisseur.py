"""
PROMEOS — Modèle Fournisseur (Phase F1, ADR-F-01).

Normalisation de l'entité Fournisseur en remplacement de la chaîne libre
`EnergyContract.supplier_name`. Pattern hybride catalogue partagé + override
tenant (ADR-F-01 Option C) :

- `organisation_id IS NULL` → fournisseur **canonique global** (Promeos master,
  lecture seule pour tenants — EDF, Engie, TotalEnergies, ...)
- `organisation_id NOT NULL` → fournisseur **privé** d'une organisation
  (ex: ELD régionale, négociation custom)

Validators stricts (cohérent ADR-D-04 EJ pattern) :
- SIREN 9 chiffres exactement
- TVA intra FR + 11 chiffres (FR\\d{11})
- Email RFC5322 via PII SoT centralisé (`pii_sanitizer.EMAIL_RFC5322_PATTERN`)
- Site web normalisation HTTPS silencieuse

Bridge eIDAS Compliance+ Vision v1.3 : `signataire_email` pour Universign/Yousign.
"""

from __future__ import annotations

import re

from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship, validates

from .base import Base, TimestampMixin
from .enums import TypeFournitureEnum

# ─── Patterns validators (cohérents ADR-D-04 EJ) ──────────────────────────────
_SIREN_PATTERN = re.compile(r"^\d{9}$")
_TVA_FR_PATTERN = re.compile(r"^FR\d{11}$")
_URL_PATTERN = re.compile(r"^https?://[^\s]+$")


class Fournisseur(Base, TimestampMixin):
    """Fournisseur d'énergie (canonique global ou privé organisation).

    Pattern hybride ADR-F-01 Option C : `organisation_id` nullable distingue
    catalogue Promeos master (NULL) vs catalogue privé tenant (NOT NULL).
    """

    __tablename__ = "fournisseurs"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=True,
        index=True,
        comment=(
            "NULL = catalogue canonique Promeos (lecture seule tenants). "
            "NOT NULL = fournisseur privé d'une organisation."
        ),
    )

    # ── Identité juridique ────────────────────────────────────────────────────
    nom = Column(String(200), nullable=False, comment="Raison sociale")
    siren = Column(String(9), nullable=True, index=True, comment="SIREN 9 chiffres")
    tva_intra = Column(String(13), nullable=True, comment="FR + 11 chiffres (FR\\d{11})")
    naf_code = Column(String(10), nullable=True, comment="Code NAF principal (via resolve_naf_code)")

    # ── Type fourniture (Enum strict pattern ADR-D-05) ───────────────────────
    type_fourniture = Column(
        Enum(TypeFournitureEnum),
        nullable=False,
        comment="ELEC / GAZ / MULTI — type énergie fournie",
    )

    # ── Contact + Web ─────────────────────────────────────────────────────────
    contact_email = Column(String(320), nullable=True, comment="Email RFC5322 (via PII SoT)")
    contact_telephone = Column(String(30), nullable=True)
    site_web = Column(String(500), nullable=True, comment="URL site web (HTTPS normalisé)")
    cgv_url = Column(String(500), nullable=True, comment="URL conditions générales de vente")

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    actif = Column(Boolean, nullable=False, default=True, index=True)

    # ── Bridge eIDAS Compliance+ (Vision v1.3) ────────────────────────────────
    signataire_nom = Column(String(200), nullable=True, comment="Nom signataire contractuel")
    signataire_email = Column(
        String(320),
        nullable=True,
        comment="Email signataire — bridge Universign/Yousign Advanced",
    )

    # ── Contraintes & index ───────────────────────────────────────────────────
    __table_args__ = (
        # Unicité SIREN privé même org (PostgreSQL nominal — SQLite traite NULL distinctement)
        UniqueConstraint("siren", "organisation_id", name="uq_fournisseur_siren_org"),
        # Partial unique index canoniques : SIREN unique parmi organisation_id IS NULL
        # SQLite + PostgreSQL supportent les partial indexes — couvre le cas SQLite NULL distinct
        Index(
            "uq_fournisseur_canonique_siren",
            "siren",
            unique=True,
            sqlite_where=text("organisation_id IS NULL"),
            postgresql_where=text("organisation_id IS NULL"),
        ),
        Index("ix_fournisseur_org_actif", "organisation_id", "actif"),
    )

    # ── Relations ─────────────────────────────────────────────────────────────
    organisation = relationship("Organisation", foreign_keys=[organisation_id])
    energy_contracts = relationship(
        "EnergyContract",
        back_populates="fournisseur",
        foreign_keys="EnergyContract.fournisseur_id",
    )

    # ── Validators stricts (cohérents ADR-D-04 EJ pattern) ───────────────────

    @validates("siren")
    def _validate_siren(self, key: str, value: str | None):
        """SIREN 9 chiffres exactement (cohérent EJ.siren)."""
        if value is None or value == "":
            return value
        # Normalisation : strip espaces et tirets
        value = re.sub(r"[\s\-]", "", value)
        if not _SIREN_PATTERN.match(value):
            raise ValueError(
                f"Phase F1 violation : Fournisseur.siren={value!r} format invalide (attendu 9 chiffres exactement)"
            )
        return value

    @validates("tva_intra")
    def _validate_tva_intra(self, key: str, value: str | None):
        """TVA intracommunautaire FR + 11 chiffres (cohérent EJ pattern)."""
        if value is None or value == "":
            return value
        value = value.upper().replace(" ", "")
        if not _TVA_FR_PATTERN.match(value):
            raise ValueError(
                f"Phase F1 violation : Fournisseur.tva_intra={value!r} format invalide "
                f"(attendu FR + 11 chiffres exactement)"
            )
        return value

    @validates("contact_email", "signataire_email")
    def _validate_email_rfc5322(self, key: str, value: str | None):
        """Email RFC5322 via PII SoT centralisé (named export anti-couplage).

        Pattern Pilier 13 ADR-016 : SoT cross-services centralisé,
        cohérent EJ.email_contact validator (Phase D-4 Tier 4).
        """
        if value is None or value == "":
            return value
        from services.security.pii_sanitizer import EMAIL_RFC5322_PATTERN

        if EMAIL_RFC5322_PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"Phase F1 violation : Fournisseur.{key}={value!r} format invalide "
                f"(attendu RFC 5322 simplifié — voir pii_sanitizer.py SoT)"
            )
        return value

    @validates("site_web", "cgv_url")
    def _validate_url(self, key: str, value: str | None):
        """URL HTTPS normalisée silencieuse (cohérent EJ.site_web pattern)."""
        if value is None or value == "":
            return value
        # Normalisation silencieuse : préfixer https:// si schema absent
        if not value.startswith(("http://", "https://")):
            value = f"https://{value}"
        if not _URL_PATTERN.match(value):
            raise ValueError(
                f"Phase F1 violation : Fournisseur.{key}={value!r} format invalide "
                f"(attendu URL valide avec ou sans http(s)://)"
            )
        return value

    def is_canonique(self) -> bool:
        """True si le fournisseur est canonique global (organisation_id NULL)."""
        return self.organisation_id is None

    def __repr__(self) -> str:
        scope = "canonique" if self.is_canonique() else f"org={self.organisation_id}"
        return f"<Fournisseur id={self.id} nom={self.nom!r} type={self.type_fourniture} {scope}>"
