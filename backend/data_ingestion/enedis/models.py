"""PROMEOS — Enedis SGE flux staging models.

Raw archive layer: store every byte Enedis sends, without transformation.

Tables:
  enedis_flux_file   — one row per ingested file (registry + raw header)
  enedis_flux_mesure_r4x — one row per Donnees_Point_Mesure (fully denormalized)

Design decisions:
  - Uses the shared Base (models.base.Base) so tables are created in promeos.db
    alongside all other PROMEOS models. Production may later migrate to a
    specialized time-series DB.
  - No unique constraint on mesure rows: Enedis may republish corrections for the
    same PRM/timestamp. Both versions are archived; deduplication is deferred to a
    future staging/normalization layer.
  - File-level idempotence only: file_hash (SHA256 of ciphertext) prevents
    re-processing the exact same physical file.
  - All values stored as raw strings from the XML (no float conversion, no UTC
    normalization) to guarantee zero data loss or transformation.
"""

import json

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from models.base import Base, TimestampMixin


class EnedisFluxFile(Base, TimestampMixin):
    """Registry of ingested Enedis flux files."""

    __tablename__ = "enedis_flux_file"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, comment="Nom du fichier .zip original")
    file_hash = Column(String(64), nullable=False, unique=True, comment="SHA256 du fichier chiffré")
    flux_type = Column(String(10), nullable=False, comment="R4H, R4M, R4Q, etc.")
    status = Column(String(20), nullable=False, default="received", comment="received/parsed/error/skipped")
    error_message = Column(Text, nullable=True, comment="Message d'erreur si status=error")
    measures_count = Column(Integer, nullable=True, default=0, comment="Nombre de mesures extraites")

    # Header fields — dedicated columns for queryable fields
    frequence_publication = Column(String(5), nullable=True, comment="H/M/Q — Frequence_Publication")
    nature_courbe_demandee = Column(String(20), nullable=True, comment="Brute/Corrigee")
    identifiant_destinataire = Column(String(100), nullable=True, comment="Code destinataire du flux")

    # Full raw header as JSON for complete fidelity
    header_raw = Column(Text, nullable=True, comment="Entete XML complet en JSON")

    mesures = relationship("EnedisFluxMesureR4x", back_populates="flux_file", cascade="all, delete-orphan")

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

    flux_file = relationship("EnedisFluxFile", back_populates="mesures")

    def __repr__(self) -> str:
        return f"<EnedisFluxMesureR4x {self.point_id} {self.horodatage} {self.valeur_point}>"
