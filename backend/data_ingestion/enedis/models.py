"""PROMEOS — Enedis SGE raw archive models.

Raw archive layer: store every byte Enedis sends, without transformation.

Tables:
  enedis_flux_file         — one row per ingested file (registry + raw header)
  enedis_flux_mesure_r4x   — one row per Donnees_Point_Mesure R4x CDC (fully denormalized)
  enedis_flux_mesure_r171  — one row per mesureDatee R171 index C2-C4
  enedis_flux_mesure_r50   — one row per PDC R50 courbe de charge C5
  enedis_flux_mesure_r151  — one row per valeur R151 index+puissance max C5

Design decisions:
  - Uses the dedicated FluxDataBase so raw Enedis tables live in flux_data.db
    instead of the main PROMEOS product database.
  - No unique constraint on mesure rows: Enedis may republish corrections for the
    same PRM/timestamp. Both versions are archived; deduplication is deferred to a
    future promotion/normalization layer.
  - File-level idempotence: file_hash (SHA256 of ciphertext) prevents
    re-processing the exact same physical file.
  - Republication detection: if a new file shares the filename of an already-parsed
    file (but has a different hash), it is ingested as a versioned republication
    (version 2+, supersedes_file_id → previous file) with status needs_review.
    Both original and republication data are preserved for data manager analysis.
  - All values stored as raw strings from the XML (no float conversion, no UTC
    normalization) to guarantee zero data loss or transformation.
"""

import json

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from data_ingestion.enedis.base import FluxDataBase
from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus
from models.base import TimestampMixin

Base = FluxDataBase


class EnedisFluxFile(Base, TimestampMixin):
    """Registry of ingested Enedis flux files."""

    __tablename__ = "enedis_flux_file"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, comment="Nom du fichier .zip original")
    file_hash = Column(String(64), nullable=False, unique=True, comment="SHA256 du fichier chiffré")
    flux_type = Column(String(10), nullable=False, comment="R4H, R4M, R4Q, etc.")
    status = Column(String(20), nullable=False, default=FluxStatus.RECEIVED, comment="received/parsed/error/skipped")
    error_message = Column(Text, nullable=True, comment="Message d'erreur si status=error")
    measures_count = Column(Integer, nullable=True, default=0, comment="Nombre de mesures extraites")

    # Republication versioning
    version = Column(Integer, nullable=False, default=1, comment="Version du fichier (1=original, 2+=republication)")
    supersedes_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK vers le fichier précédent que cette version remplace",
    )

    # Header fields — dedicated columns for queryable fields
    frequence_publication = Column(String(5), nullable=True, comment="H/M/Q — Frequence_Publication")
    nature_courbe_demandee = Column(String(20), nullable=True, comment="Brute/Corrigee")
    identifiant_destinataire = Column(String(100), nullable=True, comment="Code destinataire du flux")
    code_flux = Column(String(20), nullable=True, comment="Code flux source du nom de fichier")
    type_donnee = Column(String(20), nullable=True, comment="Type de donnee du nom de fichier")
    id_demande = Column(String(20), nullable=True, comment="Identifiant de demande M023")
    mode_publication = Column(String(5), nullable=True, comment="Mode de publication du nom de fichier")
    payload_format = Column(String(10), nullable=True, comment="Format payload parse: XML/JSON/CSV")
    num_sequence = Column(String(10), nullable=True, comment="Numero de sequence brut du nom de fichier")
    siren_publication = Column(String(20), nullable=True, comment="SIREN de publication R6X guide-style")
    code_contrat_publication = Column(String(50), nullable=True, comment="Code contrat/publication R6X")
    publication_horodatage = Column(String(20), nullable=True, comment="Horodatage publication AAAAMMJJHHMMSS")
    archive_members_count = Column(Integer, nullable=True, comment="Nombre de membres non-dossier ouverts au niveau 1")

    # Full raw header as JSON for complete fidelity
    header_raw = Column(Text, nullable=True, comment="Entete XML complet en JSON")

    mesures_r4x = relationship("EnedisFluxMesureR4x", back_populates="flux_file", cascade="all, delete-orphan")
    mesures_r171 = relationship("EnedisFluxMesureR171", back_populates="flux_file", cascade="all, delete-orphan")
    mesures_r50 = relationship("EnedisFluxMesureR50", back_populates="flux_file", cascade="all, delete-orphan")
    mesures_r151 = relationship("EnedisFluxMesureR151", back_populates="flux_file", cascade="all, delete-orphan")
    mesures_r6x = relationship("EnedisFluxMesureR6x", back_populates="flux_file", cascade="all, delete-orphan")
    itc_c68 = relationship("EnedisFluxItcC68", back_populates="flux_file", cascade="all, delete-orphan")
    errors = relationship(
        "EnedisFluxFileError",
        back_populates="flux_file",
        order_by="EnedisFluxFileError.created_at",
        cascade="all, delete-orphan",
    )

    def set_header_raw(self, header_dict: dict) -> None:
        self.header_raw = json.dumps(header_dict, ensure_ascii=False)

    def get_header_raw(self) -> dict | None:
        if self.header_raw:
            return json.loads(self.header_raw)
        return None

    def __repr__(self) -> str:
        return f"<EnedisFluxFile {self.filename} [{self.flux_type}] {self.status}>"


class EnedisFluxMesureR4x(Base, TimestampMixin):
    """Raw measurement point from an Enedis R4x CDC flux.

    Fully denormalized: each row carries its Donnees_Courbe context
    (PRM, grandeur_physique, unite, etc.) for standalone queries.

    No unique constraint — Enedis may republish corrections. Both
    original and corrected values are archived. Deduplication is
    deferred to a future promotion layer.
    """

    __tablename__ = "enedis_flux_mesure_r4x"
    __table_args__ = (
        # Performance indexes (not unique — raw archive)
        Index("ix_enedis_mesure_r4x_point_horodatage", "point_id", "horodatage"),
        Index("ix_enedis_mesure_r4x_flux_file", "flux_file_id"),
        Index("ix_enedis_mesure_r4x_flux_type", "flux_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flux_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK vers enedis_flux_file",
    )
    flux_type = Column(String(10), nullable=False, comment="R4H/R4M/R4Q — dénormalisé pour les requêtes")

    # Corps — PRM
    point_id = Column(String(14), nullable=False, comment="Identifiant_PRM (14 chiffres)")

    # Donnees_Courbe context — denormalized onto each row
    grandeur_physique = Column(String(10), nullable=True, comment="EA/ERI/ERC/E — brut XML")
    grandeur_metier = Column(String(10), nullable=True, comment="CONS/PROD — brut XML")
    unite_mesure = Column(String(10), nullable=True, comment="kW/kWr/V — brut XML")
    granularite = Column(String(10), nullable=True, comment="Pas en minutes — brut XML")
    horodatage_debut = Column(String(50), nullable=True, comment="Début période du bloc Donnees_Courbe")
    horodatage_fin = Column(String(50), nullable=True, comment="Fin période du bloc Donnees_Courbe")

    # Donnees_Point_Mesure — the actual measurement
    horodatage = Column(String(50), nullable=False, comment="Horodatage du point — brut ISO8601")
    valeur_point = Column(String(20), nullable=True, comment="Valeur brute — string, pas float")
    statut_point = Column(String(2), nullable=True, comment="R/H/P/S/T/F/G/E/C/K/D — brut XML")

    flux_file = relationship("EnedisFluxFile", back_populates="mesures_r4x")

    def __repr__(self) -> str:
        return f"<EnedisFluxMesureR4x {self.point_id} {self.horodatage} {self.valeur_point}>"


class EnedisFluxMesureR171(Base, TimestampMixin):
    """Raw measurement row from an Enedis R171 index flux (C2-C4).

    Granularity: 1 row per mesureDatee (= 1 row per serie in observed data, but
    the official XSD allows 1..* mesures per serie).
    No unique constraint — raw archive, deduplication deferred.
    """

    __tablename__ = "enedis_flux_mesure_r171"
    __table_args__ = (
        Index("ix_enedis_mesure_r171_point_date_fin", "point_id", "date_fin"),
        Index("ix_enedis_mesure_r171_flux_file", "flux_file_id"),
        Index("ix_enedis_mesure_r171_flux_type", "flux_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flux_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK vers enedis_flux_file",
    )
    flux_type = Column(String(10), nullable=False, comment="R171 — dénormalisé pour les requêtes")

    # Serie context
    point_id = Column(String(14), nullable=False, comment="prmId (14 chiffres)")
    type_mesure = Column(
        String(10),
        nullable=False,
        comment="Type brut XML (observe: INDEX, annexe officielle: IDX)",
    )
    grandeur_metier = Column(String(10), nullable=True, comment="CONS — brut XML")
    grandeur_physique = Column(
        String(10),
        nullable=True,
        comment="EA/PMA/ERC/ERI/ER/TF/DD/DE/DQ — brut XML",
    )
    type_calendrier = Column(String(5), nullable=True, comment="D/F — brut XML")
    code_classe_temporelle = Column(String(10), nullable=True, comment="HCE/HCH/HPE/HPH/P — brut XML")
    libelle_classe_temporelle = Column(String(100), nullable=True, comment="Libellé humain — brut XML")
    unite = Column(String(10), nullable=True, comment="Wh/W/VArh/VA/s — brut XML")

    # Mesure
    date_fin = Column(String(50), nullable=False, comment="dateFin — brut ISO8601, horodatage de releve")
    valeur = Column(String(20), nullable=True, comment="Valeur brute — string, pas float")

    flux_file = relationship("EnedisFluxFile", back_populates="mesures_r171")

    def __repr__(self) -> str:
        return f"<EnedisFluxMesureR171 {self.point_id} {self.date_fin} {self.valeur}>"


class EnedisFluxMesureR50(Base, TimestampMixin):
    """Raw measurement row from an Enedis R50 courbe de charge flux (C5).

    Granularity: 1 row per PDC (point de courbe, pas de 30 min).
    No unique constraint — raw archive, deduplication deferred.
    """

    __tablename__ = "enedis_flux_mesure_r50"
    __table_args__ = (
        Index("ix_enedis_mesure_r50_point_horodatage", "point_id", "horodatage"),
        Index("ix_enedis_mesure_r50_flux_file", "flux_file_id"),
        Index("ix_enedis_mesure_r50_flux_type", "flux_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flux_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK vers enedis_flux_file",
    )
    flux_type = Column(String(10), nullable=False, comment="R50 — dénormalisé pour les requêtes")

    # PRM + releve context
    point_id = Column(String(14), nullable=False, comment="Id_PRM (14 chiffres)")
    date_releve = Column(String(20), nullable=False, comment="Date_Releve — brut XML")
    id_affaire = Column(String(20), nullable=True, comment="Id_Affaire — brut XML")

    # PDC (point de courbe)
    horodatage = Column(String(50), nullable=False, comment="Horodatage du PDC — brut ISO8601+TZ")
    valeur = Column(String(20), nullable=True, comment="Valeur brute — absent si pas de mesure")
    indice_vraisemblance = Column(String(5), nullable=True, comment="0/1 — brut XML")

    flux_file = relationship("EnedisFluxFile", back_populates="mesures_r50")

    def __repr__(self) -> str:
        return f"<EnedisFluxMesureR50 {self.point_id} {self.horodatage} {self.valeur}>"


class EnedisFluxMesureR151(Base, TimestampMixin):
    """Raw measurement row from an Enedis R151 index + puissance max flux (C5).

    Granularity: 1 row per valeur (index par classe temporelle OU puissance max).
    type_donnee distinguishes: CT_DIST (grille distributeur), CT (fournisseur), PMAX.
    No unique constraint — raw archive, deduplication deferred.
    """

    __tablename__ = "enedis_flux_mesure_r151"
    __table_args__ = (
        Index("ix_enedis_mesure_r151_point_date_releve", "point_id", "date_releve"),
        Index("ix_enedis_mesure_r151_flux_file", "flux_file_id"),
        Index("ix_enedis_mesure_r151_flux_type", "flux_type"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flux_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK vers enedis_flux_file",
    )
    flux_type = Column(String(10), nullable=False, comment="R151 — dénormalisé pour les requêtes")

    # PRM + releve context
    point_id = Column(String(14), nullable=False, comment="Id_PRM (14 chiffres)")
    date_releve = Column(String(20), nullable=False, comment="Date_Releve — brut XML")
    id_calendrier_fournisseur = Column(String(20), nullable=True, comment="Id_Calendrier_Fournisseur — brut XML")
    libelle_calendrier_fournisseur = Column(String(100), nullable=True, comment="Brut XML")
    id_calendrier_distributeur = Column(String(20), nullable=True, comment="Id_Calendrier_Distributeur — brut XML")
    libelle_calendrier_distributeur = Column(String(150), nullable=True, comment="Brut XML")
    id_affaire = Column(String(20), nullable=True, comment="Id_Affaire — brut XML")

    # Donnee (index ou puissance max)
    type_donnee = Column(String(10), nullable=False, comment="CT_DIST/CT/PMAX — dérivé de la structure XML")
    id_classe_temporelle = Column(String(10), nullable=True, comment="HCB/HCH/HPB/HPH/HC/HP — NULL pour PMAX")
    libelle_classe_temporelle = Column(String(100), nullable=True, comment="NULL pour PMAX — brut XML")
    rang_cadran = Column(String(5), nullable=True, comment="NULL pour PMAX — brut XML")
    valeur = Column(String(20), nullable=True, comment="Index Wh ou puissance VA — brut string")
    indice_vraisemblance = Column(String(5), nullable=True, comment="0-15 — NULL pour PMAX — brut XML")

    flux_file = relationship("EnedisFluxFile", back_populates="mesures_r151")

    def __repr__(self) -> str:
        return f"<EnedisFluxMesureR151 {self.point_id} {self.date_releve} {self.valeur}>"


class EnedisFluxMesureR6x(Base, TimestampMixin):
    """Raw atomic R63/R64 measurement or index value.

    Values remain raw strings. There is deliberately no unique constraint:
    republications and corrections are archived side by side.
    """

    __tablename__ = "enedis_flux_mesure_r6x"
    __table_args__ = (
        Index("ix_enedis_mesure_r6x_point_horodatage", "point_id", "horodatage"),
        Index("ix_enedis_mesure_r6x_flux_file", "flux_file_id"),
        Index("ix_enedis_mesure_r6x_flux_type", "flux_type"),
        Index("ix_enedis_mesure_r6x_point_flux_gp", "point_id", "flux_type", "grandeur_physique"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flux_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK vers enedis_flux_file",
    )
    flux_type = Column(String(10), nullable=False, comment="R63/R64")
    source_format = Column(String(10), nullable=False, comment="JSON/CSV")
    archive_member_name = Column(String(255), nullable=False, comment="Nom du payload dans l'archive")
    point_id = Column(String(14), nullable=False, comment="Identifiant PRM")
    periode_date_debut = Column(String(50), nullable=True, comment="Debut de periode brut")
    periode_date_fin = Column(String(50), nullable=True, comment="Fin de periode brut")
    etape_metier = Column(String(20), nullable=True, comment="Etape metier brute")
    mode_calcul = Column(String(20), nullable=True, comment="Mode calcul R63")
    contexte_releve = Column(String(20), nullable=True, comment="Contexte releve R64")
    type_releve = Column(String(20), nullable=True, comment="Type releve R64")
    motif_releve = Column(String(20), nullable=True, comment="Motif releve R64")
    grandeur_metier = Column(String(20), nullable=True, comment="Grandeur metier brute")
    grandeur_physique = Column(String(20), nullable=True, comment="Grandeur physique brute")
    unite = Column(String(20), nullable=True, comment="Unite brute")
    horodatage = Column(String(50), nullable=False, comment="Horodatage brut de la valeur")
    pas = Column(String(20), nullable=True, comment="Pas R63 brut")
    nature_point = Column(String(10), nullable=True, comment="Nature point R63")
    type_correction = Column(String(10), nullable=True, comment="Type correction R63")
    valeur = Column(String(30), nullable=True, comment="Valeur brute")
    indice_vraisemblance = Column(String(10), nullable=True, comment="Indice vraisemblance brut")
    etat_complementaire = Column(String(10), nullable=True, comment="Etat complementaire R63")
    code_grille = Column(String(20), nullable=True, comment="Code grille R64")
    id_calendrier = Column(String(30), nullable=True, comment="Identifiant calendrier R64")
    libelle_calendrier = Column(String(100), nullable=True, comment="Libelle calendrier R64")
    libelle_grille = Column(String(100), nullable=True, comment="Libelle grille R64")
    id_classe_temporelle = Column(String(30), nullable=True, comment="Identifiant classe temporelle R64")
    libelle_classe_temporelle = Column(String(100), nullable=True, comment="Libelle classe temporelle R64")
    code_cadran = Column(String(30), nullable=True, comment="Code cadran R64")

    flux_file = relationship("EnedisFluxFile", back_populates="mesures_r6x")

    def __repr__(self) -> str:
        return f"<EnedisFluxMesureR6x {self.flux_type} {self.point_id} {self.horodatage} {self.valeur}>"


class EnedisFluxItcC68(Base, TimestampMixin):
    """Raw C68 technical and contractual PRM snapshot."""

    __tablename__ = "enedis_flux_itc_c68"
    __table_args__ = (
        Index("ix_enedis_itc_c68_point", "point_id"),
        Index("ix_enedis_itc_c68_flux_file", "flux_file_id"),
        Index("ix_enedis_itc_c68_point_flux_file", "point_id", "flux_file_id"),
        Index("ix_enedis_itc_c68_siret", "siret"),
        Index("ix_enedis_itc_c68_siren", "siren"),
    )

    id = Column(Integer, primary_key=True, index=True)
    flux_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK vers enedis_flux_file",
    )
    source_format = Column(String(10), nullable=False, comment="JSON/CSV")
    secondary_archive_name = Column(String(255), nullable=True, comment="Archive secondaire C68")
    payload_member_name = Column(String(255), nullable=False, comment="Payload JSON/CSV")
    point_id = Column(String(14), nullable=False, comment="Identifiant PRM")
    payload_raw = Column(Text, nullable=False, comment="Payload complet par PRM serialize en JSON")
    contractual_situation_count = Column(Integer, nullable=True, comment="Nombre de situations contractuelles")
    date_debut_situation_contractuelle = Column(String(30), nullable=True, comment="Date debut situation retenue")
    segment = Column(String(20), nullable=True, comment="Segment brut")
    etat_contractuel = Column(String(20), nullable=True, comment="Etat contractuel brut")
    formule_tarifaire_acheminement = Column(String(50), nullable=True, comment="FTA brute")
    code_tarif_acheminement = Column(String(30), nullable=True, comment="Code tarif acheminement brut")
    siret = Column(String(20), nullable=True, comment="SIRET extrait")
    siren = Column(String(20), nullable=True, comment="SIREN extrait")
    domaine_tension = Column(String(20), nullable=True, comment="Domaine tension brut")
    tension_livraison = Column(String(30), nullable=True, comment="Tension livraison brute")
    type_comptage = Column(String(30), nullable=True, comment="Type comptage brut")
    mode_releve = Column(String(30), nullable=True, comment="Mode releve brut")
    media_comptage = Column(String(30), nullable=True, comment="Media comptage brut")
    periodicite_releve = Column(String(30), nullable=True, comment="Periodicite releve brute")
    puissance_souscrite_valeur = Column(String(50), nullable=True, comment="Puissance souscrite valeur brute")
    puissance_souscrite_unite = Column(String(20), nullable=True, comment="Puissance souscrite unite")
    puissance_limite_soutirage_valeur = Column(String(50), nullable=True, comment="Puissance limite soutirage")
    puissance_limite_soutirage_unite = Column(String(20), nullable=True, comment="Unite puissance limite soutirage")
    puissance_raccordement_soutirage_valeur = Column(String(50), nullable=True, comment="Puissance raccord soutirage")
    puissance_raccordement_soutirage_unite = Column(
        String(20), nullable=True, comment="Unite puissance raccord soutirage"
    )
    puissance_raccordement_injection_valeur = Column(String(50), nullable=True, comment="Puissance raccord injection")
    puissance_raccordement_injection_unite = Column(
        String(20), nullable=True, comment="Unite puissance raccord injection"
    )
    borne_fixe = Column(String(10), nullable=True, comment="Borne fixe brute")
    refus_pose_linky = Column(String(10), nullable=True, comment="Refus pose Linky brut")
    date_refus_pose_linky = Column(String(30), nullable=True, comment="Date refus pose Linky brute")

    flux_file = relationship("EnedisFluxFile", back_populates="itc_c68")

    def __repr__(self) -> str:
        return f"<EnedisFluxItcC68 {self.point_id} file={self.flux_file_id}>"


class EnedisFluxFileError(Base, TimestampMixin):
    """Archived error entry for an Enedis flux file.

    Each row represents one failed processing attempt. The number of
    errors for a file gives the retry count (no dedicated column needed).
    """

    __tablename__ = "enedis_flux_file_error"
    __table_args__ = (Index("ix_enedis_flux_file_error_flux_file", "flux_file_id"),)

    id = Column(Integer, primary_key=True, index=True)
    flux_file_id = Column(
        Integer,
        ForeignKey("enedis_flux_file.id", ondelete="CASCADE"),
        nullable=False,
        comment="FK vers enedis_flux_file",
    )
    error_message = Column(Text, nullable=False, comment="Message d'erreur de la tentative")

    flux_file = relationship("EnedisFluxFile", back_populates="errors")

    def __repr__(self) -> str:
        return f"<EnedisFluxFileError file={self.flux_file_id} msg={self.error_message[:50]}>"


class IngestionRun(Base, TimestampMixin):
    """Tracks a single execution of the ingestion pipeline.

    Counters are updated incrementally (per-file) so that a crash
    mid-run still reflects the work actually completed.
    """

    __tablename__ = "enedis_ingestion_run"
    __table_args__ = (
        Index(
            "ix_ingestion_run_single_running",
            "status",
            unique=True,
            sqlite_where=Column("status") == "running",  # DDL literal — must match IngestionRunStatus.RUNNING.value
            postgresql_where=Column("status") == "running",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False, comment="Debut du run")
    finished_at = Column(DateTime, nullable=True, comment="Fin du run (null si en cours)")
    directory = Column(String(500), nullable=False, comment="Repertoire source scanne")
    recursive = Column(Boolean, nullable=False, default=True, comment="Scan recursif")
    dry_run = Column(Boolean, nullable=False, default=False, comment="Mode dry-run (pas de mutation)")
    status = Column(
        String(20),
        nullable=False,
        default=IngestionRunStatus.RUNNING,
        comment="running / completed / failed",
    )
    triggered_by = Column(String(10), nullable=False, comment="cli / api")

    # Counters — incremental updates
    files_received = Column(Integer, default=0, comment="Fichiers nouveaux a traiter")
    files_parsed = Column(Integer, default=0, comment="Fichiers parses avec succes")
    files_skipped = Column(Integer, default=0, comment="Fichiers flux hors scope (R172, X14, HDM)")
    files_error = Column(Integer, default=0, comment="Fichiers en erreur")
    files_needs_review = Column(Integer, default=0, comment="Fichiers en attente de review (republication)")
    files_already_processed = Column(Integer, default=0, comment="Fichiers deja traites (PARSED/SKIPPED)")
    files_retried = Column(Integer, default=0, comment="Fichiers ERROR retentes dans ce run")
    files_max_retries = Column(Integer, default=0, comment="Fichiers PERMANENTLY_FAILED (nouveau + existant)")

    # Run-level error
    error_message = Column(Text, nullable=True, comment="Erreur ayant interrompu le run")

    def __repr__(self) -> str:
        return f"<IngestionRun #{self.id} {self.status} triggered_by={self.triggered_by}>"


ENEDIS_RAW_TABLES = (
    "enedis_flux_file",
    "enedis_flux_mesure_r4x",
    "enedis_flux_mesure_r171",
    "enedis_flux_mesure_r50",
    "enedis_flux_mesure_r151",
    "enedis_flux_mesure_r6x",
    "enedis_flux_itc_c68",
    "enedis_flux_file_error",
    "enedis_ingestion_run",
)
