"""
PROMEOS S3 (2026-05-28) — Modèles « Groupe de structures » pour la
mutualisation des résultats au sens de l'Article 14 de l'arrêté du
10 avril 2020 modifié, en application de l'Article L.174-1 + R.174-31
du Code de la construction et de l'habitation.

Cross-check Légifrance livré :
docs/audits/crosscheck_legifrance_mutualisation_art14_2026_05_28.md

5 invariants juridiques verrouillés au niveau modèle :

I1.  « groupe de structures » est l'entité canonique (Art. 14 §1 al.1).
I2.  Validation du représentant légal par EFA obligatoire avant export
     opposable (Art. 14 §1 al.2 — solidarité).
I3.  Une EFA active ne peut appartenir qu'à un seul groupe actif
     (Art. 14 §1 al.3 — règle d'unicité).
I4.  Les économies redistribuées ne peuvent l'être qu'une seule fois
     (Art. 14 §1 al.4 + §III).
I5.  Données à exporter = Table 1B Annexe IV (Art. 14 §1 al.1, renvoi).

Aucun calcul métier ici : pure structure de persistance.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text as sa_text

from .base import Base, TimestampMixin, SoftDeleteMixin


# ── Valeurs canoniques (whitelist stricte) ─────────────────────────────

# I1 — lifecycle d'un groupe de structures (canonique S3).
GROUPE_STATUSES = ("draft", "pending_validation", "validated", "archived")

# I2 — état de validation du représentant légal pour chaque EFA membre.
RL_STATUSES = ("pending", "validated", "rejected")


class GroupeStructures(Base, TimestampMixin, SoftDeleteMixin):
    """Groupe de structures au sens de l'Article 14 §1 al.1 de l'arrêté
    du 10 avril 2020 modifié.

    Un groupe rassemble plusieurs EFA (entités fonctionnelles assujetties)
    appartenant à la même organisation pour mutualiser les résultats au
    contrôle décennal. PROMEOS anticipe la constitution du groupe en
    amont du module OPERAT « Mutualisation des résultats à l'échelle
    d'un patrimoine » (déploiement progressif ADEME, cf. cross-check
    Phase 0).
    """

    __tablename__ = "tertiaire_groupe_structures"

    id = Column(Integer, primary_key=True, index=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id"),
        nullable=False,
        index=True,
        comment="Org scope (cardinal — IS1 même hors V4)",
    )
    nom = Column(String(200), nullable=False, comment="Libellé FR métier du groupe")
    description = Column(Text, nullable=True, comment="Note libre (objectif patrimonial, périmètre...)")
    status = Column(
        String(30),
        nullable=False,
        default="draft",
        server_default="draft",
        comment="Lifecycle : draft / pending_validation / validated / archived",
    )
    created_by = Column(
        String(200),
        nullable=True,
        comment="Email/identifiant utilisateur créateur (snapshot, pas FK)",
    )

    # Relations
    membres = relationship(
        "GroupeStructuresMembre",
        back_populates="groupe",
        cascade="all, delete-orphan",
    )
    ledger_entries = relationship(
        "MutualisationLedger",
        back_populates="groupe",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending_validation', 'validated', 'archived')",
            name="chk_groupe_status",
        ),
        # Lookup index : groupes actifs par org (cas le + fréquent UI).
        Index(
            "idx_groupe_org_active",
            "organisation_id",
            "status",
            sqlite_where=sa_text("deleted_at IS NULL AND status != 'archived'"),
            postgresql_where=sa_text("deleted_at IS NULL AND status != 'archived'"),
        ),
    )


class GroupeStructuresMembre(Base, TimestampMixin):
    """Association EFA ⇄ groupe de structures + état validation RL.

    Invariants enforced :
      - I3 : `UniqueConstraint(efa_id) WHERE deleted_at IS NULL AND
        groupe.status != 'archived'` (au plus 1 groupe actif par EFA).
      - I2 : champ `representant_legal_status` strict whitelist + audit
        trail (date + validator + note).

    `site_id` est dénormalisé pour faciliter les exports Table 1B sans
    avoir à re-joindre `tertiaire_efa.site_id` à chaque requête.
    """

    __tablename__ = "tertiaire_groupe_structures_membre"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer,
        ForeignKey("tertiaire_groupe_structures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    efa_id = Column(
        Integer,
        ForeignKey("tertiaire_efa.id"),
        nullable=False,
        index=True,
    )
    site_id = Column(
        Integer,
        ForeignKey("sites.id"),
        nullable=True,
        index=True,
        comment="Dénormalisation pour Table 1B (peut être NULL si EFA non rattachée)",
    )

    # I2 — état de validation du représentant légal pour CETTE EFA.
    # Une validation = acceptation explicite du principe de solidarité
    # patrimoniale au sens Art. 14 §1 al.2.
    representant_legal_status = Column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="pending / validated / rejected",
    )
    representant_legal_validated_at = Column(
        DateTime,
        nullable=True,
        comment="Horodatage de la validation RL (NULL tant que pending/rejected)",
    )
    validator_user_id = Column(
        String(200),
        nullable=True,
        comment="Email/identifiant du validateur RL (snapshot, pas FK)",
    )
    validation_note = Column(
        Text,
        nullable=True,
        comment="Motif validation/rejet (RL OK, refus pour cause X, etc.)",
    )

    # Soft-delete pour préserver l'historique en cas de retrait d'une
    # EFA du groupe (audit trail mutualisation).
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Relations
    groupe = relationship("GroupeStructures", back_populates="membres")

    __table_args__ = (
        CheckConstraint(
            "representant_legal_status IN ('pending', 'validated', 'rejected')",
            name="chk_membre_rl_status",
        ),
        # I3 cardinale : une EFA active ne peut être présente que dans
        # une seule appartenance non-deleted. La règle « groupe non archivé »
        # est portée applicativement (le service refuse la création si le
        # groupe cible est archivé) — l'index DB n'a pas accès au status
        # du groupe parent.
        Index(
            "uq_membre_efa_active",
            "efa_id",
            unique=True,
            sqlite_where=sa_text("deleted_at IS NULL"),
            postgresql_where=sa_text("deleted_at IS NULL"),
        ),
        UniqueConstraint("group_id", "efa_id", name="uq_membre_group_efa"),
    )


class MutualisationLedger(Base, TimestampMixin):
    """Journal d'audit des redistributions d'économies (I4 — Art. 14
    §1 al.4 + §III).

    Une ligne par mouvement de redistribution. La somme par EFA source
    ne peut excéder le surplus disponible (vérifié par service). La
    règle « une économie ne peut être redistribuée qu'une fois » est
    matérialisée par le fait qu'une même EFA source ne peut apparaître
    en `donneuse_efa_id` qu'au plus une fois par jalon (`jalon_annee`).
    """

    __tablename__ = "tertiaire_mutualisation_ledger"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(
        Integer,
        ForeignKey("tertiaire_groupe_structures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    jalon_annee = Column(
        Integer,
        nullable=False,
        comment="Année du jalon réglementaire (2030, 2040, 2050)",
    )
    donneuse_efa_id = Column(
        Integer,
        ForeignKey("tertiaire_efa.id"),
        nullable=False,
        index=True,
    )
    kwh_redistribues = Column(
        Float,
        nullable=False,
        comment="Volume d'énergie redistribué (kWh, positif)",
    )
    note = Column(Text, nullable=True)

    # Relations
    groupe = relationship("GroupeStructures", back_populates="ledger_entries")

    __table_args__ = (
        CheckConstraint("kwh_redistribues >= 0", name="chk_ledger_kwh_positive"),
        # I4 — une EFA donneuse ne peut redistribuer qu'une fois par jalon.
        UniqueConstraint("group_id", "donneuse_efa_id", "jalon_annee", name="uq_ledger_donneuse_jalon"),
    )
