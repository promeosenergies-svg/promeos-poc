"""
PROMEOS - Modèle Bâtiment
Unité réglementaire (décret tertiaire, BACS)
"""

import re

from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from .base import Base, SoftDeleteMixin, TimestampMixin

# Phase D-4 Tier 3 — SIRET 14 chiffres
_SIRET_PATTERN = re.compile(r"^\d{14}$")


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

    # Phase D-4 Tier 1 — P0-MATV1-009 : categorie_operat_batiment cardinal A9
    # Source : matrice v1 §4.5#17 — contrainte agrégat A9 (Cabs faux pour Site MIXTE multi-bâtiments)
    # Audit : docs/audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §3 P0-MATV1-009.
    categorie_operat_batiment = Column(
        String(50),
        nullable=True,
        comment="Catégorie OPERAT bâtiment (héritée Site avec override possible) — matrice v1 §4.5#17 / contrainte A9",
    )

    # Phase D-4 Tier 2 — P1-MATV1-023 + 024 : DPE complet (énergie + climat) + usage bâtiment
    # Source : matrice v1 §4.5#9 + #14 — Décret 2020-1610 modifié 2024 (DPE double étiquette).
    # Audit : AUDIT_ECARTS_MATRICE_V1_2026_05_07.md §4 P1-MATV1-023/024.
    usage_batiment = Column(
        String(50),
        nullable=True,
        comment="Usage principal bâtiment (UsageBatimentEnum) — matrice v1 §4.5#9 / cardinal BACS classification",
    )
    dpe_emissions_kgco2_m2 = Column(
        Float,
        nullable=True,
        comment="Émissions DPE bâtiment (kgCO2e/m²/an) — double étiquette DPE Décret 2020-1610 — matrice v1 §4.5#14",
    )

    # Phase D-4 Tier 3 — 4 P1 polish matrice v1 §4.5#8/10/15/16
    siret_batiment = Column(String(14), nullable=True, comment="SIRET bâtiment — matrice v1 §4.5#8")
    etage_count = Column(Integer, nullable=True, comment="Nombre d'étages — matrice v1 §4.5#10")
    efa_operat_id = Column(
        String(50),
        nullable=True,
        comment="Identifiant EFA OPERAT bâtiment (cas multi-bâtiments multi-EFA) — matrice v1 §4.5#15",
    )
    parties_communes_pct = Column(
        Float,
        nullable=True,
        comment="Pourcentage parties communes (0-100) — matrice v1 §4.5#16",
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

    @validates("categorie_operat_batiment")
    def _validate_categorie_operat_batiment_strict(self, key: str, value: str | None):
        """P0-2 fix code-reviewer Phase D-4 Tier 1 : `categorie_operat_batiment` strict
        `OperatUsagePrincipalEnum` (9 catégories OPERAT macro).

        Pattern Pilier 9 ADR-016 — contrainte A9 cardinale (Cabs faux Site MIXTE).

        Phase D-4 Tier 2 P1-E : cross-FK contrat usage_batiment ↔ categorie_operat_batiment.
        Si usage_batiment ∈ {PARKING, TECHNIQUE} (hors OPERAT), categorie_operat_batiment NULL.
        """
        if value is None or value == "":
            return value
        from .enums import OperatUsagePrincipalEnum

        valid = {v.value for v in OperatUsagePrincipalEnum}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 1 P0-2 violation : categorie_operat_batiment={value!r} non canonique "
                f"(attendu {sorted(valid)} — OperatUsagePrincipalEnum 9 catégories macro)"
            )
        # P1-E cross-FK : si usage_batiment hors OPERAT, refuser categorie non-NULL
        if self.usage_batiment in {"PARKING", "TECHNIQUE"}:
            raise ValueError(
                f"Phase D-4 Tier 2 P1-E violation : categorie_operat_batiment={value!r} interdit "
                f"si usage_batiment={self.usage_batiment!r} (hors périmètre OPERAT)"
            )
        return value

    @validates("siret_batiment")
    def _validate_siret_batiment(self, key: str, value: str | None):
        """Phase D-4 Tier 3 : SIRET strict 14 chiffres (matrice v1 §4.5#8)."""
        if value is None or value == "":
            return value
        if not _SIRET_PATTERN.match(value):
            raise ValueError(
                f"Phase D-4 Tier 3 violation : siret_batiment={value!r} format invalide "
                f"(attendu 14 chiffres exactement)"
            )
        return value

    @validates("parties_communes_pct")
    def _validate_parties_communes_pct(self, key: str, value: float | None):
        """Phase D-4 Tier 3 : parties_communes_pct range [0.0, 100.0]."""
        if value is None:
            return value
        if not isinstance(value, (int, float)) or value < 0.0 or value > 100.0:
            raise ValueError(
                f"Phase D-4 Tier 3 violation : parties_communes_pct={value!r} hors range (attendu float 0.0-100.0)"
            )
        return value

    @validates("etage_count")
    def _validate_etage_count(self, key: str, value: int | None):
        """Phase D-4 Tier 3 : etage_count range plausible (-5 à 200)."""
        if value is None:
            return value
        if not isinstance(value, int) or value < -5 or value > 200:
            raise ValueError(
                f"Phase D-4 Tier 3 violation : etage_count={value!r} hors range "
                f"(attendu int -5 à 200 — sous-sols + tour)"
            )
        return value

    @validates("usage_batiment")
    def _validate_usage_batiment_strict(self, key: str, value: str | None):
        """P1-MATV1-023 Phase D-4 Tier 2 : `usage_batiment` strict `UsageBatimentEnum`.

        ⚠️ Contrat cardinal P1-E audit code-reviewer (consigne user 2026-05-08) :
        `UsageBatimentEnum` (11 valeurs) est plus large qu'`OperatUsagePrincipalEnum`
        (9 valeurs OPERAT). Si `usage_batiment` ∈ {PARKING, TECHNIQUE} (hors périmètre OPERAT),
        `categorie_operat_batiment` DOIT être NULL (validator cross-FK ci-dessous).
        """
        if value is None or value == "":
            return value
        from .enums import UsageBatimentEnum

        valid = {v.value for v in UsageBatimentEnum}
        if value not in valid:
            raise ValueError(
                f"Phase D-4 Tier 2 violation : usage_batiment={value!r} non canonique "
                f"(attendu {sorted(valid)} — UsageBatimentEnum)"
            )
        # P1-E cross-FK : PARKING/TECHNIQUE hors périmètre OPERAT → categorie_operat_batiment NULL
        if value in {"PARKING", "TECHNIQUE"} and self.categorie_operat_batiment is not None:
            raise ValueError(
                f"Phase D-4 Tier 2 P1-E violation : usage_batiment={value!r} (hors OPERAT) "
                f"incohérent avec categorie_operat_batiment={self.categorie_operat_batiment!r} "
                f"(attendu NULL pour PARKING/TECHNIQUE)"
            )
        return value

    # Relations
    site = relationship("Site", back_populates="batiments")
