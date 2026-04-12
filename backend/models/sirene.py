"""
PROMEOS - Modeles Referentiel Sirene
Brique isolee : stockage local des donnees INSEE Sirene (stock mensuel + delta).
Ne modifie AUCUNE table metier (Organisation, EntiteJuridique, Site, etc.).
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Index
from .base import Base, TimestampMixin


class SireneUniteLegale(Base, TimestampMixin):
    """Unite legale Sirene (identifiee par SIREN).

    Source : fichier stockUniteLegale INSEE (CSV mensuel).
    """

    __tablename__ = "sirene_unites_legales"

    id = Column(Integer, primary_key=True, index=True)

    # Identifiant unique INSEE
    siren = Column(String(9), unique=True, nullable=False, index=True)

    # Denomination
    denomination = Column(String(500), nullable=True)
    sigle = Column(String(100), nullable=True)
    nom_unite_legale = Column(String(200), nullable=True)
    prenom1 = Column(String(100), nullable=True)

    # Classification
    categorie_juridique = Column(String(10), nullable=True)
    activite_principale = Column(String(10), nullable=True, index=True)
    nomenclature_activite = Column(String(10), nullable=True)
    activite_principale_naf25 = Column(String(10), nullable=True)

    # Taille
    tranche_effectifs = Column(String(5), nullable=True)
    annee_effectifs = Column(String(4), nullable=True)
    categorie_entreprise = Column(String(5), nullable=True)

    # Statut
    etat_administratif = Column(String(1), nullable=False, default="A")
    statut_diffusion = Column(String(1), nullable=False, default="O")

    # Siege
    nic_siege = Column(String(5), nullable=True)

    # Flags
    economie_sociale_solidaire = Column(String(1), nullable=True)
    societe_mission = Column(String(1), nullable=True)
    caractere_employeur = Column(String(1), nullable=True)

    # Dates
    date_creation = Column(String(10), nullable=True)
    date_dernier_traitement = Column(String(19), nullable=True)

    # Snapshot et tracabilite
    snapshot_date = Column(DateTime, nullable=False, comment="Date du fichier stock source")
    payload_brut = Column(Text, nullable=True, comment="Ligne CSV brute JSON")

    __table_args__ = (
        Index("ix_sirene_ul_denomination", "denomination"),
        Index("ix_sirene_ul_etat", "etat_administratif"),
        Index("ix_sirene_ul_ddt", "date_dernier_traitement"),
        Index("ix_sirene_ul_snapshot", "snapshot_date"),
    )


class SireneEtablissement(Base, TimestampMixin):
    """Etablissement Sirene (identifie par SIRET).

    Source : fichier stockEtablissement INSEE (CSV mensuel).
    """

    __tablename__ = "sirene_etablissements"

    id = Column(Integer, primary_key=True, index=True)

    # Identifiants (index explicites dans __table_args__)
    siret = Column(String(14), unique=True, nullable=False, index=True)
    siren = Column(String(9), nullable=False)
    nic = Column(String(5), nullable=False)

    # Denomination
    enseigne = Column(String(500), nullable=True)
    denomination_usuelle = Column(String(500), nullable=True)

    # Classification
    activite_principale = Column(String(10), nullable=True, index=True)
    nomenclature_activite = Column(String(10), nullable=True)
    activite_principale_naf25 = Column(String(10), nullable=True)

    # Statut
    etat_administratif = Column(String(1), nullable=False, default="A")
    statut_diffusion = Column(String(1), nullable=False, default="O")
    etablissement_siege = Column(Boolean, nullable=True, default=False)

    # Adresse
    numero_voie = Column(String(10), nullable=True)
    type_voie = Column(String(10), nullable=True)
    libelle_voie = Column(String(200), nullable=True)
    complement_adresse = Column(String(200), nullable=True)
    code_postal = Column(String(5), nullable=True)
    libelle_commune = Column(String(200), nullable=True)
    code_commune = Column(String(5), nullable=True)

    # Effectifs
    tranche_effectifs = Column(String(5), nullable=True)
    annee_effectifs = Column(String(4), nullable=True)
    caractere_employeur = Column(String(1), nullable=True)

    # Dates
    date_creation = Column(String(10), nullable=True)
    date_dernier_traitement = Column(String(19), nullable=True)

    # Snapshot et tracabilite
    snapshot_date = Column(DateTime, nullable=False, comment="Date du fichier stock source")
    payload_brut = Column(Text, nullable=True, comment="Ligne CSV brute JSON")

    __table_args__ = (
        Index("ix_sirene_etab_siren", "siren"),
        Index("ix_sirene_etab_cp", "code_postal"),
        Index("ix_sirene_etab_commune", "libelle_commune"),
        Index("ix_sirene_etab_etat", "etat_administratif"),
        Index("ix_sirene_etab_ddt", "date_dernier_traitement"),
        Index("ix_sirene_etab_snapshot", "snapshot_date"),
    )


class SireneDoublon(Base, TimestampMixin):
    """Doublons SIREN (fichier stockDoublons INSEE).

    Un doublon = 2 SIREN designant la meme entite.
    """

    __tablename__ = "sirene_doublons"

    id = Column(Integer, primary_key=True, index=True)
    siren = Column(String(9), nullable=False, index=True)
    siren_doublon = Column(String(9), nullable=False, index=True)
    date_dernier_traitement = Column(String(19), nullable=True)
    snapshot_date = Column(DateTime, nullable=False)

    __table_args__ = (Index("ix_sirene_doublons_pair", "siren", "siren_doublon", unique=True),)


class SireneSyncRun(Base, TimestampMixin):
    """Journal d'import Sirene (full ou delta)."""

    __tablename__ = "sirene_sync_runs"

    id = Column(Integer, primary_key=True, index=True)

    # Type d'import
    sync_type = Column(String(20), nullable=False, comment="full / delta / doublons")
    source_file = Column(String(500), nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    # Compteurs
    lines_read = Column(Integer, default=0)
    lines_inserted = Column(Integer, default=0)
    lines_updated = Column(Integer, default=0)
    lines_rejected = Column(Integer, default=0)

    # Statut
    status = Column(String(20), nullable=False, default="running", comment="running / success / failed")
    error_message = Column(Text, nullable=True)
    correlation_id = Column(String(50), nullable=True, index=True)


class CustomerCreationTrace(Base, TimestampMixin):
    """Trace de creation client depuis Sirene.

    Chaque creation via le flow onboarding from-sirene est journalisee ici.
    """

    __tablename__ = "customer_creation_traces"

    id = Column(Integer, primary_key=True, index=True)

    # Source
    source_type = Column(String(20), nullable=False, default="sirene")
    source_siren = Column(String(9), nullable=True)
    source_sirets = Column(Text, nullable=True, comment="JSON array des SIRETs utilises")

    # Objets crees (IDs)
    organisation_id = Column(Integer, nullable=True)
    entite_juridique_id = Column(Integer, nullable=True)
    portefeuille_id = Column(Integer, nullable=True)
    site_ids = Column(Text, nullable=True, comment="JSON array des site IDs crees")

    # Utilisateur
    user_id = Column(Integer, nullable=True)
    user_email = Column(String(200), nullable=True)

    # Statut
    status = Column(String(20), nullable=False, default="success")
    warnings = Column(Text, nullable=True, comment="JSON array des warnings")
    correlation_id = Column(String(50), nullable=True, index=True)
