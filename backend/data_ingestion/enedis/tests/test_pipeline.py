"""Tests for the Enedis R4x CDC ingestion pipeline."""

import os

import pytest

from data_ingestion.enedis.enums import FluxStatus
from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxMesure
from data_ingestion.enedis.pipeline import ingest_file

from .conftest import TEST_IV, TEST_KEY, make_encrypted_zip


# ---------------------------------------------------------------------------
# Synthetic R4x XML fixtures
# ---------------------------------------------------------------------------

R4H_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<Courbe>
  <Entete>
    <Identifiant_Flux>R4x</Identifiant_Flux>
    <Libelle_Flux>Flux de courbes de charge R4x</Libelle_Flux>
    <Identifiant_Emetteur>ENEDIS</Identifiant_Emetteur>
    <Identifiant_Destinataire>23X--130624--EE1</Identifiant_Destinataire>
    <Date_Creation>2026-03-16T15:36:43+01:00</Date_Creation>
    <Frequence_Publication>H</Frequence_Publication>
    <Reference_Demande>189465931</Reference_Demande>
    <Nature_De_Courbe_Demandee>Corrigee</Nature_De_Courbe_Demandee>
  </Entete>
  <Corps>
    <Identifiant_PRM>30000210411333</Identifiant_PRM>
    <Donnees_Courbe>
      <Horodatage_Debut>2026-03-07T00:00:00+01:00</Horodatage_Debut>
      <Horodatage_Fin>2026-03-07T23:59:59+01:00</Horodatage_Fin>
      <Granularite>5</Granularite>
      <Unite_Mesure>kW</Unite_Mesure>
      <Grandeur_Metier>CONS</Grandeur_Metier>
      <Grandeur_Physique>EA</Grandeur_Physique>
      <Donnees_Point_Mesure Horodatage="2026-03-07T00:00:00+01:00" Valeur_Point="398" Statut_Point="R"/>
      <Donnees_Point_Mesure Horodatage="2026-03-07T00:05:00+01:00" Valeur_Point="383" Statut_Point="R"/>
      <Donnees_Point_Mesure Horodatage="2026-03-07T00:10:00+01:00" Valeur_Point="386" Statut_Point="E"/>
    </Donnees_Courbe>
  </Corps>
</Courbe>"""

R4Q_DUAL_XML = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<Courbe>
  <Entete>
    <Identifiant_Flux>R4x</Identifiant_Flux>
    <Libelle_Flux>Flux de courbes de charge R4x</Libelle_Flux>
    <Identifiant_Emetteur>ENEDIS</Identifiant_Emetteur>
    <Identifiant_Destinataire>23X--130624--EE1</Identifiant_Destinataire>
    <Date_Creation>2026-03-21T10:00:00+01:00</Date_Creation>
    <Frequence_Publication>Q</Frequence_Publication>
    <Reference_Demande>999999</Reference_Demande>
    <Nature_De_Courbe_Demandee>Brute</Nature_De_Courbe_Demandee>
  </Entete>
  <Corps>
    <Identifiant_PRM>30002541030720</Identifiant_PRM>
    <Donnees_Courbe>
      <Horodatage_Debut>2026-03-20T00:00:00+01:00</Horodatage_Debut>
      <Horodatage_Fin>2026-03-20T23:59:59+01:00</Horodatage_Fin>
      <Granularite>5</Granularite>
      <Unite_Mesure>kW</Unite_Mesure>
      <Grandeur_Metier>CONS</Grandeur_Metier>
      <Grandeur_Physique>EA</Grandeur_Physique>
      <Donnees_Point_Mesure Horodatage="2026-03-20T00:00:00+01:00" Valeur_Point="100" Statut_Point="R"/>
      <Donnees_Point_Mesure Horodatage="2026-03-20T00:05:00+01:00" Valeur_Point="101" Statut_Point="R"/>
    </Donnees_Courbe>
    <Donnees_Courbe>
      <Horodatage_Debut>2026-03-20T00:00:00+01:00</Horodatage_Debut>
      <Horodatage_Fin>2026-03-20T23:59:59+01:00</Horodatage_Fin>
      <Granularite>5</Granularite>
      <Unite_Mesure>kWr</Unite_Mesure>
      <Grandeur_Metier>CONS</Grandeur_Metier>
      <Grandeur_Physique>ERI</Grandeur_Physique>
      <Donnees_Point_Mesure Horodatage="2026-03-20T00:00:00+01:00" Valeur_Point="50" Statut_Point="R"/>
      <Donnees_Point_Mesure Horodatage="2026-03-20T00:05:00+01:00" Valeur_Point="51" Statut_Point="R"/>
    </Donnees_Courbe>
  </Corps>
</Courbe>"""


# ---------------------------------------------------------------------------
# File fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def r4h_encrypted_file(tmp_path):
    """Encrypted R4H file with 3 measurement points."""
    ciphertext = make_encrypted_zip(R4H_XML, "test_r4h.xml", TEST_KEY, TEST_IV)
    path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260302.zip"
    path.write_bytes(ciphertext)
    return path


@pytest.fixture
def r4q_dual_encrypted_file(tmp_path):
    """Encrypted R4Q file with 2 Donnees_Courbe blocks (EA + ERI)."""
    ciphertext = make_encrypted_zip(R4Q_DUAL_XML, "test_r4q.xml", TEST_KEY, TEST_IV)
    path = tmp_path / "ENEDIS_23X--TEST_R4Q_CDC_20260321.zip"
    path.write_bytes(ciphertext)
    return path


@pytest.fixture
def corrupt_encrypted_file(tmp_path):
    """File with random bytes — decryption will fail."""
    path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_CORRUPT.zip"
    path.write_bytes(os.urandom(256))
    return path


@pytest.fixture
def r172_file(tmp_path):
    """File classified as R172 — should be skipped."""
    path = tmp_path / "ENEDIS_23X--TEST_R172_20260302.zip"
    path.write_bytes(os.urandom(64))
    return path


# ---------------------------------------------------------------------------
# Tests — Full pipeline
# ---------------------------------------------------------------------------


class TestIngestFilePipeline:
    def test_ingest_r4h_success(self, db, r4h_encrypted_file, test_keys):
        status = ingest_file(r4h_encrypted_file, db, test_keys)
        assert status == FluxStatus.PARSED

        # File record
        files = db.query(EnedisFluxFile).all()
        assert len(files) == 1
        f = files[0]
        assert f.flux_type == "R4H"
        assert f.status == FluxStatus.PARSED
        assert f.measures_count == 3
        assert f.frequence_publication == "H"
        assert f.nature_courbe_demandee == "Corrigee"
        assert f.identifiant_destinataire == "23X--130624--EE1"
        assert f.get_header_raw() is not None
        assert f.get_header_raw()["Reference_Demande"] == "189465931"

        # Mesures
        mesures = db.query(EnedisFluxMesure).all()
        assert len(mesures) == 3
        m0 = mesures[0]
        assert m0.point_id == "30000210411333"
        assert m0.flux_type == "R4H"
        assert m0.grandeur_physique == "EA"
        assert m0.grandeur_metier == "CONS"
        assert m0.unite_mesure == "kW"
        assert m0.granularite == "5"
        assert m0.horodatage == "2026-03-07T00:00:00+01:00"
        assert m0.valeur_point == "398"
        assert m0.statut_point == "R"

    def test_ingest_r4q_dual_courbes(self, db, r4q_dual_encrypted_file, test_keys):
        status = ingest_file(r4q_dual_encrypted_file, db, test_keys)
        assert status == FluxStatus.PARSED

        f = db.query(EnedisFluxFile).first()
        assert f.measures_count == 4  # 2 EA + 2 ERI

        mesures = db.query(EnedisFluxMesure).all()
        assert len(mesures) == 4
        gp_values = {m.grandeur_physique for m in mesures}
        assert gp_values == {"EA", "ERI"}


# ---------------------------------------------------------------------------
# Tests — Idempotence
# ---------------------------------------------------------------------------


class TestIngestIdempotence:
    def test_same_file_twice_is_noop(self, db, r4h_encrypted_file, test_keys):
        status1 = ingest_file(r4h_encrypted_file, db, test_keys)
        status2 = ingest_file(r4h_encrypted_file, db, test_keys)

        assert status1 == FluxStatus.PARSED
        assert status2 == FluxStatus.PARSED  # returns PARSED (already done)
        assert db.query(EnedisFluxFile).count() == 1
        assert db.query(EnedisFluxMesure).count() == 3  # not duplicated

    def test_skipped_file_twice_is_noop(self, db, r172_file, test_keys):
        """Re-submitting a SKIPPED file should not raise IntegrityError."""
        status1 = ingest_file(r172_file, db, test_keys)
        status2 = ingest_file(r172_file, db, test_keys)

        assert status1 == FluxStatus.SKIPPED
        assert status2 == FluxStatus.SKIPPED
        assert db.query(EnedisFluxFile).count() == 1

    def test_different_files_same_data_both_stored(self, db, tmp_path, test_keys):
        """Two different files (different hash) with same measures → both archived."""
        ct1 = make_encrypted_zip(R4H_XML, "inner1.xml", TEST_KEY, TEST_IV)
        ct2 = make_encrypted_zip(R4H_XML, "inner2.xml", TEST_KEY, TEST_IV)
        f1 = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260302a.zip"
        f2 = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260302b.zip"
        f1.write_bytes(ct1)
        f2.write_bytes(ct2)

        ingest_file(f1, db, test_keys)
        ingest_file(f2, db, test_keys)

        assert db.query(EnedisFluxFile).count() == 2
        assert db.query(EnedisFluxMesure).count() == 6  # 3 + 3, both stored

    def test_retry_after_error(self, db, tmp_path, test_keys):
        """A file that previously failed can be retried."""
        from data_ingestion.enedis.pipeline import _hash_file

        ct = make_encrypted_zip(R4H_XML, "inner.xml", TEST_KEY, TEST_IV)
        real_file = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_RETRY.zip"
        real_file.write_bytes(ct)
        real_hash = _hash_file(real_file)

        # Simulate a previous error record with the same hash
        error_file = EnedisFluxFile(
            filename="retry.zip",
            file_hash=real_hash,
            flux_type="R4H",
            status=FluxStatus.ERROR,
            error_message="bad key",
        )
        db.add(error_file)
        db.commit()

        status = ingest_file(real_file, db, test_keys)
        assert status == FluxStatus.PARSED
        assert db.query(EnedisFluxFile).count() == 1
        assert db.query(EnedisFluxFile).first().status == FluxStatus.PARSED


# ---------------------------------------------------------------------------
# Tests — Error handling
# ---------------------------------------------------------------------------


class TestIngestErrors:
    def test_corrupt_file_returns_error(self, db, corrupt_encrypted_file, test_keys):
        status = ingest_file(corrupt_encrypted_file, db, test_keys)
        assert status == FluxStatus.ERROR

        f = db.query(EnedisFluxFile).first()
        assert f.status == FluxStatus.ERROR
        assert f.error_message is not None
        assert f.measures_count == 0

    def test_r172_file_returns_skipped(self, db, r172_file, test_keys):
        status = ingest_file(r172_file, db, test_keys)
        assert status == FluxStatus.SKIPPED

        f = db.query(EnedisFluxFile).first()
        assert f.status == FluxStatus.SKIPPED

    def test_file_not_found_raises(self, db, tmp_path, test_keys):
        from pathlib import Path

        with pytest.raises(FileNotFoundError):
            ingest_file(Path("/nonexistent/file.zip"), db, test_keys)

    def test_zero_mesures_is_parsed_not_error(self, db, tmp_path, test_keys):
        """Valid XML with 0 points → status=parsed, measures_count=0."""
        xml = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<Courbe>
  <Entete>
    <Identifiant_Flux>R4x</Identifiant_Flux>
    <Frequence_Publication>H</Frequence_Publication>
  </Entete>
  <Corps>
    <Identifiant_PRM>30000210411333</Identifiant_PRM>
  </Corps>
</Courbe>"""
        ct = make_encrypted_zip(xml, "empty.xml", TEST_KEY, TEST_IV)
        path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_EMPTY.zip"
        path.write_bytes(ct)

        status = ingest_file(path, db, test_keys)
        assert status == FluxStatus.PARSED

        f = db.query(EnedisFluxFile).first()
        assert f.status == FluxStatus.PARSED
        assert f.measures_count == 0
