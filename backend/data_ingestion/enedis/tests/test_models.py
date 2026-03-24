"""Tests for Enedis flux staging models — schema and basic operations."""

import pytest
from sqlalchemy.exc import IntegrityError

from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxMesureR4x


# ---------------------------------------------------------------------------
# EnedisFluxFile
# ---------------------------------------------------------------------------


class TestEnedisFluxFile:
    def test_create_file_record(self, db):
        f = EnedisFluxFile(
            filename="ENEDIS_R4H_20260302.zip",
            file_hash="abc123" * 10 + "abcd",
            flux_type="R4H",
            status="parsed",
            measures_count=2016,
        )
        db.add(f)
        db.commit()

        result = db.query(EnedisFluxFile).first()
        assert result.filename == "ENEDIS_R4H_20260302.zip"
        assert result.flux_type == "R4H"
        assert result.status == "parsed"
        assert result.measures_count == 2016
        assert result.created_at is not None

    def test_file_hash_unique_constraint(self, db):
        f1 = EnedisFluxFile(filename="a.zip", file_hash="hash_dup", flux_type="R4H", status="parsed")
        f2 = EnedisFluxFile(filename="b.zip", file_hash="hash_dup", flux_type="R4H", status="parsed")
        db.add(f1)
        db.commit()
        db.add(f2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_different_hashes_allowed(self, db):
        f1 = EnedisFluxFile(filename="a.zip", file_hash="hash_1", flux_type="R4H", status="parsed")
        f2 = EnedisFluxFile(filename="b.zip", file_hash="hash_2", flux_type="R4H", status="parsed")
        db.add_all([f1, f2])
        db.commit()
        assert db.query(EnedisFluxFile).count() == 2

    def test_version_defaults_to_1(self, db):
        f = EnedisFluxFile(filename="a.zip", file_hash="h_ver", flux_type="R4H", status="parsed")
        db.add(f)
        db.commit()

        result = db.query(EnedisFluxFile).first()
        assert result.version == 1
        assert result.supersedes_file_id is None

    def test_version_chain_fk(self, db):
        f1 = EnedisFluxFile(filename="a.zip", file_hash="h1_chain", flux_type="R4H", status="parsed", version=1)
        db.add(f1)
        db.flush()

        f2 = EnedisFluxFile(
            filename="a.zip",
            file_hash="h2_chain",
            flux_type="R4H",
            status="needs_review",
            version=2,
            supersedes_file_id=f1.id,
        )
        db.add(f2)
        db.commit()

        result = db.query(EnedisFluxFile).filter_by(version=2).first()
        assert result.supersedes_file_id == f1.id
        assert result.status == "needs_review"

    def test_header_raw_json_roundtrip(self, db):
        f = EnedisFluxFile(filename="a.zip", file_hash="h1", flux_type="R4H", status="parsed")
        header = {"Identifiant_Flux": "R4x", "Frequence_Publication": "H"}
        f.set_header_raw(header)
        db.add(f)
        db.commit()

        result = db.query(EnedisFluxFile).first()
        assert result.get_header_raw() == header

    def test_header_raw_none_returns_none(self, db):
        f = EnedisFluxFile(filename="a.zip", file_hash="h1", flux_type="R4H", status="parsed")
        db.add(f)
        db.commit()

        result = db.query(EnedisFluxFile).first()
        assert result.get_header_raw() is None

    def test_queryable_header_fields(self, db):
        f = EnedisFluxFile(
            filename="a.zip",
            file_hash="h1",
            flux_type="R4H",
            status="parsed",
            frequence_publication="H",
            nature_courbe_demandee="Corrigee",
            identifiant_destinataire="23X--130624--EE1",
        )
        db.add(f)
        db.commit()

        result = db.query(EnedisFluxFile).filter_by(frequence_publication="H").first()
        assert result is not None
        assert result.nature_courbe_demandee == "Corrigee"


# ---------------------------------------------------------------------------
# EnedisFluxMesureR4x
# ---------------------------------------------------------------------------


class TestEnedisFluxMesureR4x:
    def _make_file(self, db, file_hash="h1"):
        f = EnedisFluxFile(filename="a.zip", file_hash=file_hash, flux_type="R4H", status="parsed")
        db.add(f)
        db.flush()
        return f

    def test_create_mesure(self, db):
        f = self._make_file(db)
        m = EnedisFluxMesureR4x(
            flux_file_id=f.id,
            flux_type="R4H",
            point_id="30000210411333",
            grandeur_physique="EA",
            grandeur_metier="CONS",
            unite_mesure="kW",
            granularite="5",
            horodatage_debut="2026-03-07T00:00:00+01:00",
            horodatage_fin="2026-03-07T23:59:59+01:00",
            horodatage="2026-03-07T00:00:00+01:00",
            valeur_point="398",
            statut_point="R",
        )
        db.add(m)
        db.commit()

        result = db.query(EnedisFluxMesureR4x).first()
        assert result.point_id == "30000210411333"
        assert result.valeur_point == "398"
        assert result.statut_point == "R"
        assert result.grandeur_physique == "EA"
        assert isinstance(result.valeur_point, str)

    def test_duplicate_mesures_allowed(self, db):
        """No unique constraint on mesures — raw archive allows duplicates."""
        f = self._make_file(db)
        m1 = EnedisFluxMesureR4x(
            flux_file_id=f.id,
            flux_type="R4H",
            point_id="30000210411333",
            horodatage="2026-03-07T00:00:00+01:00",
            valeur_point="398",
            statut_point="R",
        )
        m2 = EnedisFluxMesureR4x(
            flux_file_id=f.id,
            flux_type="R4H",
            point_id="30000210411333",
            horodatage="2026-03-07T00:00:00+01:00",
            valeur_point="405",
            statut_point="C",
        )
        db.add_all([m1, m2])
        db.commit()
        assert db.query(EnedisFluxMesureR4x).count() == 2

    def test_mesure_from_different_files_coexist(self, db):
        """Same PRM/timestamp from different files are both stored."""
        f1 = self._make_file(db, file_hash="h1")
        f2 = self._make_file(db, file_hash="h2")
        m1 = EnedisFluxMesureR4x(
            flux_file_id=f1.id,
            flux_type="R4H",
            point_id="30000210411333",
            horodatage="2026-03-07T00:00:00+01:00",
            valeur_point="398",
            statut_point="R",
        )
        m2 = EnedisFluxMesureR4x(
            flux_file_id=f2.id,
            flux_type="R4H",
            point_id="30000210411333",
            horodatage="2026-03-07T00:00:00+01:00",
            valeur_point="405",
            statut_point="C",
        )
        db.add_all([m1, m2])
        db.commit()
        assert db.query(EnedisFluxMesureR4x).count() == 2

    def test_null_valeur_point_allowed(self, db):
        f = self._make_file(db)
        m = EnedisFluxMesureR4x(
            flux_file_id=f.id,
            flux_type="R4H",
            point_id="30000210411333",
            horodatage="2026-03-07T00:00:00+01:00",
            valeur_point=None,
            statut_point=None,
        )
        db.add(m)
        db.commit()
        result = db.query(EnedisFluxMesureR4x).first()
        assert result.valeur_point is None
        assert result.statut_point is None

    def test_cascade_delete_with_file(self, db):
        f = self._make_file(db)
        m = EnedisFluxMesureR4x(
            flux_file_id=f.id,
            flux_type="R4H",
            point_id="30000210411333",
            horodatage="2026-03-07T00:00:00+01:00",
            valeur_point="100",
        )
        db.add(m)
        db.commit()
        assert db.query(EnedisFluxMesureR4x).count() == 1

        db.delete(f)
        db.commit()
        assert db.query(EnedisFluxMesureR4x).count() == 0

    def test_relationship_file_to_mesures(self, db):
        f = self._make_file(db)
        db.add_all(
            [
                EnedisFluxMesureR4x(
                    flux_file_id=f.id,
                    flux_type="R4H",
                    point_id="PRM1",
                    horodatage=f"2026-03-07T0{i}:00:00+01:00",
                    valeur_point=str(i * 100),
                )
                for i in range(3)
            ]
        )
        db.commit()

        db.refresh(f)
        assert len(f.mesures) == 3
