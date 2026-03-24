"""Tests for Enedis flux staging models — schema and basic operations."""

import pytest
from sqlalchemy.exc import IntegrityError

from data_ingestion.enedis.models import (
    EnedisFluxFile,
    EnedisFluxMesureR4x,
    EnedisFluxMesureR171,
    EnedisFluxMesureR50,
    EnedisFluxMesureR151,
)


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
        assert len(f.mesures_r4x) == 3


# ---------------------------------------------------------------------------
# EnedisFluxMesureR171
# ---------------------------------------------------------------------------


class TestEnedisFluxMesureR171:
    def _make_file(self, db, file_hash="h_r171"):
        f = EnedisFluxFile(filename="ENEDIS_R171.zip", file_hash=file_hash, flux_type="R171", status="parsed")
        db.add(f)
        db.flush()
        return f

    def test_create_mesure(self, db):
        f = self._make_file(db)
        m = EnedisFluxMesureR171(
            flux_file_id=f.id,
            flux_type="R171",
            point_id="30000550506121",
            type_mesure="INDEX",
            grandeur_metier="CONS",
            grandeur_physique="EA",
            type_calendrier="D",
            code_classe_temporelle="HPH",
            libelle_classe_temporelle="Heures Pleines Hiver",
            unite="Wh",
            date_fin="2026-03-01T00:51:11",
            valeur="1320",
        )
        db.add(m)
        db.commit()

        result = db.query(EnedisFluxMesureR171).first()
        assert result.point_id == "30000550506121"
        assert result.type_mesure == "INDEX"
        assert result.valeur == "1320"
        assert isinstance(result.valeur, str)

    def test_cascade_delete(self, db):
        f = self._make_file(db)
        db.add(
            EnedisFluxMesureR171(
                flux_file_id=f.id,
                flux_type="R171",
                point_id="30000550506121",
                type_mesure="INDEX",
                date_fin="2026-03-01T00:51:11",
                valeur="1320",
            )
        )
        db.commit()
        assert db.query(EnedisFluxMesureR171).count() == 1

        db.delete(f)
        db.commit()
        assert db.query(EnedisFluxMesureR171).count() == 0

    def test_duplicate_mesures_allowed(self, db):
        f = self._make_file(db)
        for val in ("1320", "1325"):
            db.add(
                EnedisFluxMesureR171(
                    flux_file_id=f.id,
                    flux_type="R171",
                    point_id="30000550506121",
                    type_mesure="INDEX",
                    date_fin="2026-03-01T00:51:11",
                    valeur=val,
                )
            )
        db.commit()
        assert db.query(EnedisFluxMesureR171).count() == 2

    def test_nullable_fields(self, db):
        f = self._make_file(db)
        m = EnedisFluxMesureR171(
            flux_file_id=f.id,
            flux_type="R171",
            point_id="30000550506121",
            type_mesure="INDEX",
            date_fin="2026-03-01T00:51:11",
            valeur=None,
            grandeur_metier=None,
            grandeur_physique=None,
        )
        db.add(m)
        db.commit()
        result = db.query(EnedisFluxMesureR171).first()
        assert result.valeur is None
        assert result.grandeur_metier is None

    def test_relationship_file_to_mesures_r171(self, db):
        f = self._make_file(db)
        db.add_all(
            [
                EnedisFluxMesureR171(
                    flux_file_id=f.id,
                    flux_type="R171",
                    point_id="30000550506121",
                    type_mesure="INDEX",
                    date_fin=f"2026-03-0{i + 1}T00:00:00",
                    valeur=str(i * 100),
                )
                for i in range(3)
            ]
        )
        db.commit()
        db.refresh(f)
        assert len(f.mesures_r171) == 3


# ---------------------------------------------------------------------------
# EnedisFluxMesureR50
# ---------------------------------------------------------------------------


class TestEnedisFluxMesureR50:
    def _make_file(self, db, file_hash="h_r50"):
        f = EnedisFluxFile(filename="ERDF_R50.zip", file_hash=file_hash, flux_type="R50", status="parsed")
        db.add(f)
        db.flush()
        return f

    def test_create_mesure(self, db):
        f = self._make_file(db)
        m = EnedisFluxMesureR50(
            flux_file_id=f.id,
            flux_type="R50",
            point_id="01445441288824",
            date_releve="2023-01-02",
            id_affaire="M041AWXF",
            horodatage="2023-01-02T16:30:00+01:00",
            valeur="20710",
            indice_vraisemblance="0",
        )
        db.add(m)
        db.commit()

        result = db.query(EnedisFluxMesureR50).first()
        assert result.point_id == "01445441288824"
        assert result.horodatage == "2023-01-02T16:30:00+01:00"
        assert result.valeur == "20710"
        assert isinstance(result.valeur, str)

    def test_cascade_delete(self, db):
        f = self._make_file(db)
        db.add(
            EnedisFluxMesureR50(
                flux_file_id=f.id,
                flux_type="R50",
                point_id="01445441288824",
                date_releve="2023-01-02",
                horodatage="2023-01-02T16:30:00+01:00",
                valeur="20710",
            )
        )
        db.commit()
        assert db.query(EnedisFluxMesureR50).count() == 1

        db.delete(f)
        db.commit()
        assert db.query(EnedisFluxMesureR50).count() == 0

    def test_null_valeur_allowed(self, db):
        """PDC without V/IV — empty time slot."""
        f = self._make_file(db)
        m = EnedisFluxMesureR50(
            flux_file_id=f.id,
            flux_type="R50",
            point_id="01445441288824",
            date_releve="2023-01-02",
            horodatage="2023-01-02T16:30:00+01:00",
            valeur=None,
            indice_vraisemblance=None,
        )
        db.add(m)
        db.commit()
        result = db.query(EnedisFluxMesureR50).first()
        assert result.valeur is None
        assert result.indice_vraisemblance is None

    def test_duplicate_mesures_allowed(self, db):
        f = self._make_file(db)
        for val in ("20710", "20715"):
            db.add(
                EnedisFluxMesureR50(
                    flux_file_id=f.id,
                    flux_type="R50",
                    point_id="01445441288824",
                    date_releve="2023-01-02",
                    horodatage="2023-01-02T16:30:00+01:00",
                    valeur=val,
                )
            )
        db.commit()
        assert db.query(EnedisFluxMesureR50).count() == 2

    def test_relationship_file_to_mesures_r50(self, db):
        f = self._make_file(db)
        db.add_all(
            [
                EnedisFluxMesureR50(
                    flux_file_id=f.id,
                    flux_type="R50",
                    point_id="01445441288824",
                    date_releve="2023-01-02",
                    horodatage=f"2023-01-02T{i:02d}:30:00+01:00",
                    valeur=str(i * 100),
                )
                for i in range(3)
            ]
        )
        db.commit()
        db.refresh(f)
        assert len(f.mesures_r50) == 3


# ---------------------------------------------------------------------------
# EnedisFluxMesureR151
# ---------------------------------------------------------------------------


class TestEnedisFluxMesureR151:
    def _make_file(self, db, file_hash="h_r151"):
        f = EnedisFluxFile(filename="ERDF_R151.zip", file_hash=file_hash, flux_type="R151", status="parsed")
        db.add(f)
        db.flush()
        return f

    def test_create_mesure_ct_dist(self, db):
        f = self._make_file(db)
        m = EnedisFluxMesureR151(
            flux_file_id=f.id,
            flux_type="R151",
            point_id="17745151915440",
            date_releve="2024-12-17",
            id_calendrier_fournisseur="FC020831",
            libelle_calendrier_fournisseur="Heures Pleines/Creuses",
            id_calendrier_distributeur="DI000003",
            libelle_calendrier_distributeur="Avec differenciation temporelle",
            id_affaire="M07E7D2I",
            type_donnee="CT_DIST",
            id_classe_temporelle="HCB",
            libelle_classe_temporelle="Heures Creuses Saison Basse",
            rang_cadran="1",
            valeur="83044953",
            indice_vraisemblance="0",
        )
        db.add(m)
        db.commit()

        result = db.query(EnedisFluxMesureR151).first()
        assert result.point_id == "17745151915440"
        assert result.type_donnee == "CT_DIST"
        assert result.valeur == "83044953"
        assert isinstance(result.valeur, str)

    def test_create_mesure_pmax(self, db):
        """PMAX rows have NULL classe/rang/indice fields."""
        f = self._make_file(db)
        m = EnedisFluxMesureR151(
            flux_file_id=f.id,
            flux_type="R151",
            point_id="17745151915440",
            date_releve="2024-12-17",
            type_donnee="PMAX",
            valeur="7452",
            id_classe_temporelle=None,
            libelle_classe_temporelle=None,
            rang_cadran=None,
            indice_vraisemblance=None,
        )
        db.add(m)
        db.commit()

        result = db.query(EnedisFluxMesureR151).first()
        assert result.type_donnee == "PMAX"
        assert result.id_classe_temporelle is None
        assert result.rang_cadran is None
        assert result.indice_vraisemblance is None

    def test_cascade_delete(self, db):
        f = self._make_file(db)
        db.add(
            EnedisFluxMesureR151(
                flux_file_id=f.id,
                flux_type="R151",
                point_id="17745151915440",
                date_releve="2024-12-17",
                type_donnee="CT_DIST",
                valeur="83044953",
            )
        )
        db.commit()
        assert db.query(EnedisFluxMesureR151).count() == 1

        db.delete(f)
        db.commit()
        assert db.query(EnedisFluxMesureR151).count() == 0

    def test_duplicate_mesures_allowed(self, db):
        f = self._make_file(db)
        for val in ("83044953", "83044960"):
            db.add(
                EnedisFluxMesureR151(
                    flux_file_id=f.id,
                    flux_type="R151",
                    point_id="17745151915440",
                    date_releve="2024-12-17",
                    type_donnee="CT_DIST",
                    valeur=val,
                )
            )
        db.commit()
        assert db.query(EnedisFluxMesureR151).count() == 2

    def test_relationship_file_to_mesures_r151(self, db):
        f = self._make_file(db)
        db.add_all(
            [
                EnedisFluxMesureR151(
                    flux_file_id=f.id,
                    flux_type="R151",
                    point_id="17745151915440",
                    date_releve="2024-12-17",
                    type_donnee=td,
                    valeur=str(i * 1000),
                )
                for i, td in enumerate(["CT_DIST", "CT", "PMAX"])
            ]
        )
        db.commit()
        db.refresh(f)
        assert len(f.mesures_r151) == 3
