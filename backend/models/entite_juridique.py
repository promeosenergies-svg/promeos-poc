"""
PROMEOS - Modèle Entité Juridique
SIREN/SIRET - qui signe les contrats / qui paye
"""

import re

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, validates
from .base import Base, TimestampMixin, SoftDeleteMixin

# Phase D-4 Tier 3 — SIRET strict 14 chiffres (cohérent batiment.py + patrimoine.py).
_SIRET_PATTERN = re.compile(r"^\d{14}$")
# URL HTTP/HTTPS — normalisation silencieuse "https://" si schema absent.
_URL_PATTERN = re.compile(r"^https?://[^\s]+$")


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

    # Phase D-4 Tier 3 — 7 P1 polish matrice v1 §4.2#13-15 + 19-22
    telephone = Column(String(30), nullable=True, comment="Téléphone — matrice v1 §4.2#13")
    email_contact = Column(String(255), nullable=True, comment="Email contact — matrice v1 §4.2#14")
    site_web = Column(String(500), nullable=True, comment="Site web (HTTPS) — matrice v1 §4.2#15")
    type_societe = Column(String(50), nullable=True, comment="Type société (SA/SAS/SARL/...) — matrice v1 §4.2#19")
    date_creation_societe = Column(Date, nullable=True, comment="Date création société — matrice v1 §4.2#20")
    capital_social_eur = Column(Float, nullable=True, comment="Capital social EUR — matrice v1 §4.2#21")
    representant_legal_nom = Column(String(255), nullable=True, comment="Représentant légal — matrice v1 §4.2#22")

    @validates("siret")
    def _validate_siret_strict(self, key: str, value: str | None):
        """P1-2 fix code-reviewer Phase D-4 Tier 3 : EJ.siret strict 14 chiffres.

        Cohérent Batiment.siret_batiment validator (asymétrie corrigée).
        """
        if value is None or value == "":
            return value
        if not _SIRET_PATTERN.match(value):
            raise ValueError(
                f"Phase D-4 Tier 3 violation : EJ.siret={value!r} format invalide (attendu 14 chiffres exactement)"
            )
        # Cohérence cardinale : SIREN(siret[0:9]) doit matcher EJ.siren si défini
        if self.siren and value[:9] != self.siren:
            raise ValueError(
                f"Phase D-4 Tier 3 violation : EJ.siret={value!r} préfixe 9 chiffres "
                f"incohérent avec siren={self.siren!r}"
            )
        return value

    @validates("email_contact")
    def _validate_email_contact(self, key: str, value: str | None):
        """P1-3 fix Phase D-4 Tier 3 + Tier 4 audit P1 : email_contact via PII SoT named export.

        Délégué à `services.security.pii_sanitizer.EMAIL_RFC5322_PATTERN` (named export
        anti-couplage index positionnel — Phase D-4 Tier 4 fix code-reviewer).
        Pattern Pilier 13 ADR-016 (SoT cross-services centralisé — pas de duplication).
        """
        if value is None or value == "":
            return value
        from services.security.pii_sanitizer import EMAIL_RFC5322_PATTERN

        # Le pattern PII utilise \b...\b (matchage substring) — pour validator strict,
        # on vérifie que le pattern couvre toute la string (start/end) via fullmatch.
        if EMAIL_RFC5322_PATTERN.fullmatch(value) is None:
            raise ValueError(
                f"Phase D-4 Tier 3 violation : email_contact={value!r} format invalide "
                f"(attendu RFC 5322 simplifié — voir pii_sanitizer.py SoT)"
            )
        return value

    @validates("site_web")
    def _validate_site_web(self, key: str, value: str | None):
        """P1-4 fix code-reviewer Phase D-4 Tier 3 : site_web normalisation silencieuse HTTPS.

        Si l'utilisateur saisit "www.exemple.fr" (UX courante), normalise en "https://www.exemple.fr".
        """
        if value is None or value == "":
            return value
        # Normalisation silencieuse : préfixer https:// si schema absent
        if not value.startswith(("http://", "https://")):
            value = f"https://{value}"
        if not _URL_PATTERN.match(value):
            raise ValueError(
                f"Phase D-4 Tier 3 violation : site_web={value!r} format invalide "
                f"(attendu URL valide avec ou sans http(s)://)"
            )
        return value

    # Relations
    organisation = relationship("Organisation", back_populates="entites_juridiques")
    portefeuilles = relationship(
        "Portefeuille",
        back_populates="entite_juridique",
        cascade="all, delete-orphan",
    )
