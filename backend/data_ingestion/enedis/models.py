"""PROMEOS — Enedis SGE flux staging models.

Raw archive layer: store every byte Enedis sends, without transformation.

Tables:
  enedis_flux_file         — one row per ingested file (registry + raw header)
  enedis_flux_mesure_r4x   — one row per Donnees_Point_Mesure R4x CDC (fully denormalized)
  enedis_flux_mesure_r171  — one row per mesureDatee R171 index C2-C4
  enedis_flux_mesure_r50   — one row per PDC R50 courbe de charge C5
  enedis_flux_mesure_r151  — one row per valeur R151 index+puissance max C5

Design decisions:
  - Uses the shared Base (models.base.Base) so tables are created in promeos.db
    alongside all other PROMEOS models. Production may later migrate to a
    specialized time-series DB.
  - No unique constraint on mesure rows: Enedis may republish corrections for the
    same PRM/timestamp. Both versions are archived; deduplication is deferred to a
    future staging/normalization layer.
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

from data_ingestion.enedis.enums import FluxStatus, IngestionRunStatus
from models.base import Base, TimestampMixin


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

    # Full raw header as JSON for complete fidelity
    header_raw = Column(Text, nullable=True, comment="Entete XML complet en JSON")

    mesures_r4x = relationship("EnedisFluxMesureR4x", back_populates="flux_file", cascade="all, delete-orphan")
    mesures_r171 = relationship("EnedisFluxMesureR171", back_populates="flux_file", cascade="all, delete-orphan")
    mesures_r50 = relationship("EnedisFluxMesureR50", back_populates="flux_file", cascade="all, delete-orphan")
    mesures_r151 = relationship("EnedisFluxMesureR151", back_populates="flux_file", cascade="all, delete-orphan")
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
    deferred to a future staging layer.
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

    Granularity: 1 row per mesureDatee (= 1 row per serie in observed data).
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
    type_mesure = Column(String(10), nullable=False, comment="INDEX — brut XML")
    grandeur_metier = Column(String(10), nullable=True, comment="CONS — brut XML")
    grandeur_physique = Column(String(10), nullable=True, comment="DD/DQ/EA/ERC/ERI/PMA/TF — brut XML")
    type_calendrier = Column(String(5), nullable=True, comment="D — brut XML")
    code_classe_temporelle = Column(String(10), nullable=True, comment="HCE/HCH/HPE/HPH/P — brut XML")
    libelle_classe_temporelle = Column(String(100), nullable=True, comment="Libellé humain — brut XML")
    unite = Column(String(10), nullable=True, comment="Wh/VArh/VA/s — brut XML")

    # Mesure
    date_fin = Column(String(50), nullable=False, comment="dateFin — brut ISO8601")
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


class EnedisFluxFileError(Base, TimestampMixin):
    """Archived error entry for an Enedis flux file.

    Each row represents one failed processing attempt. The number of
    errors for a file gives the retry count (no dedicated column needed).
    """

    __tablename__ = "enedis_flux_file_error"
    __table_args__ = (
        Index("ix_enedis_flux_file_error_flux_file", "flux_file_id"),
    )

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
        String(20), nullable=False, default=IngestionRunStatus.RUNNING,
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
