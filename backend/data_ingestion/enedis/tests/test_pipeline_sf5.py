"""Pipeline tests for SF5 R63/R64/C68 raw ingestion."""

import io
import json
import zipfile

from data_ingestion.enedis.enums import FluxStatus
from data_ingestion.enedis.config import MAX_RETRIES
from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxItcC68, EnedisFluxMesureR6x
from data_ingestion.enedis.pipeline import ingest_directory, ingest_file

from .conftest import TEST_IV, TEST_KEY, aes_encrypt, make_encrypted_zip


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            zf.writestr(name, payload)
    return buf.getvalue()


def _r63_json() -> bytes:
    return json.dumps(
        {
            "header": {
                "siDemandeur": "SGE",
                "typeDestinataire": "SI",
                "idDestinataire": "GRD-F001",
                "codeFlux": "R63",
                "idDemande": "M053Q0D3",
                "modePublication": "P",
                "idCanalContact": "WEB",
                "format": "JSON",
            },
            "mesures": [
                {
                    "idPrm": "30000000000001",
                    "etapeMetier": "MESURE",
                    "periode": {"dateDebut": "2026-01-01", "dateFin": "2026-01-02"},
                    "modeCalcul": "BRUT",
                    "grandeur": [
                        {
                            "grandeurMetier": "CONS",
                            "grandeurPhysique": "EA",
                            "unite": "Wh",
                            "points": [
                                {"d": "2026-01-01T00:00:00+01:00", "v": "10", "p": "PT5M", "n": "R"},
                                {"d": "2026-01-01T00:05:00+01:00", "v": "11", "p": "PT5M", "n": "R"},
                            ],
                        }
                    ],
                }
            ],
        }
    ).encode()


def _r63_csv() -> bytes:
    return (
        "Identifiant PRM;Date de debut;Date de fin;Grandeur physique;Grandeur metier;Etape metier;Unite;"
        "Horodate;Valeur;Nature;Pas\n"
        "30000000000001;2026-01-01;2026-01-02;EA;CONS;MESURE;Wh;2026-01-01T00:00:00+01:00;10;R;PT5M\n"
    ).encode()


def _r64_json() -> bytes:
    return json.dumps(
        {
            "header": {
                "siDemandeur": "SGE",
                "typeDestinataire": "SI",
                "idDestinataire": "GRD-F001",
                "codeFlux": "R64",
                "idDemande": "M06IFF1Z",
                "modePublication": "P",
                "idCanalContact": "WEB",
                "format": "JSON",
            },
            "mesures": [
                {
                    "idPrm": "30000000000001",
                    "periode": {"dateDebut": "2026-01-01", "dateFin": "2026-01-02"},
                    "contexte": [
                        {
                            "etapeMetier": "RELEVE",
                            "contexteReleve": "NORMAL",
                            "typeReleve": "INDEX",
                            "motifReleve": "PERIODIQUE",
                            "grandeur": [
                                {
                                    "grandeurMetier": "CONS",
                                    "grandeurPhysique": "EA",
                                    "unite": "Wh",
                                    "calendrier": [
                                        {
                                            "idCalendrier": "CAL1",
                                            "libelleCalendrier": "Calendrier",
                                            "libelleGrille": "Grille",
                                            "classeTemporelle": [
                                                {
                                                    "idClasseTemporelle": "HP",
                                                    "libelleClasseTemporelle": "Heures pleines",
                                                    "codeCadran": "01",
                                                    "valeur": [{"d": "2026-01-01T00:00:00+01:00", "v": 100, "iv": 0}],
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ],
        }
    ).encode()


def _r64_csv() -> bytes:
    return (
        "Identifiant PRM;Date de debut;Date de fin;Grandeur physique;Grandeur metier;Etape metier;Unite;"
        "Horodate;Valeur;Contexte releve;Type releve;Motif releve;Code grille;Id calendrier;"
        "Libelle calendrier;Libelle grille;Id classe temporelle;Libelle classe temporelle;Code cadran;iv\n"
        "30000000000001;2026-01-01;2026-01-02;EA;CONS;RELEVE;Wh;2026-01-01T00:00:00+01:00;"
        "100;NORMAL;INDEX;PERIODIQUE;GRD;CAL1;Calendrier;Grille;HP;Heures pleines;01;0\n"
    ).encode()


def _c68_json(point_id: str = "30000000000001") -> bytes:
    return json.dumps(
        [
            {
                "idPrm": point_id,
                "siret": "12345678900011",
                "siren": "123456789",
                "domaineTension": "BT",
                "situationsContractuelles": [{"dateDebut": "2025-01-01", "segment": "C5", "etatContractuel": "ACTIF"}],
                "puissanceSouscrite": {"valeur": "36", "unite": "kVA"},
            }
        ]
    ).encode()


def _c68_csv(point_id: str = "30000000000001", *, v12: bool = False) -> bytes:
    if v12:
        return (
            "PRM;Segment;SIRET;SIREN;Refus de pose Linky;Date refus de pose Linky;Borne Fixe;Type Injection\n"
            f"{point_id};C5;12345678900011;123456789;NON;;OUI;SURPLUS\n"
        ).encode()
    return (
        "PRM;Segment;Etat contractuel;SIRET;SIREN;Domaine Tension;Puissance Souscrite Valeur;"
        "Puissance Souscrite Unite\n"
        f"{point_id};C5;ACTIF;12345678900011;123456789;BT;36;kVA\n"
    ).encode()


def _c68_primary(entries: dict[str, bytes]) -> bytes:
    return _zip_bytes(entries)


def test_ingest_r63_direct_json_zip_without_keys(db, tmp_path):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: _r63_json()}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.PARSED
    file_row = db.query(EnedisFluxFile).one()
    assert file_row.flux_type == "R63"
    assert file_row.payload_format == "JSON"
    assert file_row.id_demande == "M053Q0D3"
    assert file_row.measures_count == 2
    header_raw = file_row.get_header_raw()
    assert header_raw["filename_metadata"]["num_sequence"] == "00001"
    assert header_raw["archive_manifest"]["payload_member_name"] == member
    rows = db.query(EnedisFluxMesureR6x).order_by(EnedisFluxMesureR6x.horodatage).all()
    assert [row.valeur for row in rows] == ["10", "11"]


def test_ingest_r63_direct_csv_zip(db, tmp_path):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.csv"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: _r63_csv()}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.PARSED
    file_row = db.query(EnedisFluxFile).one()
    assert file_row.payload_format == "CSV"
    assert file_row.measures_count == 1
    assert db.query(EnedisFluxMesureR6x).one().source_format == "CSV"


def test_ingest_r63_aes_wrapped_zip(db, tmp_path, test_keys):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json"
    path = tmp_path / outer
    path.write_bytes(aes_encrypt(_zip_bytes({member: _r63_json()}), TEST_KEY, TEST_IV))

    status = ingest_file(path, db, keys=test_keys)

    assert status == FluxStatus.PARSED
    assert db.query(EnedisFluxMesureR6x).count() == 2


def test_ingest_r63_payload_filename_mismatch_records_error_and_rolls_back(db, tmp_path):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00002_20230918161101.json"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: _r63_json()}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.ERROR
    assert db.query(EnedisFluxFile).one().status == FluxStatus.ERROR
    assert db.query(EnedisFluxMesureR6x).count() == 0


def test_ingest_r63_malformed_csv_records_error_and_rolls_back(db, tmp_path):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.csv"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: b"Identifiant PRM;Date de debut\n30000000000001;2026-01-01\n"}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.ERROR
    assert db.query(EnedisFluxMesureR6x).count() == 0


def test_ingest_r64_direct_json_zip_without_keys(db, tmp_path):
    outer = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip"
    member = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.json"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: _r64_json()}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.PARSED
    file_row = db.query(EnedisFluxFile).one()
    assert file_row.flux_type == "R64"
    assert file_row.payload_format == "JSON"
    assert file_row.measures_count == 1
    row = db.query(EnedisFluxMesureR6x).one()
    assert row.id_calendrier == "CAL1"
    assert row.code_cadran == "01"
    assert row.valeur == "100"


def test_ingest_r64_direct_csv_zip(db, tmp_path):
    outer = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip"
    member = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.csv"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: _r64_csv()}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.PARSED
    assert db.query(EnedisFluxFile).one().payload_format == "CSV"
    assert db.query(EnedisFluxMesureR6x).one().source_format == "CSV"


def test_ingest_r64_aes_wrapped_zip(db, tmp_path, test_keys):
    outer = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip"
    member = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.json"
    path = tmp_path / outer
    path.write_bytes(aes_encrypt(_zip_bytes({member: _r64_json()}), TEST_KEY, TEST_IV))

    status = ingest_file(path, db, keys=test_keys)

    assert status == FluxStatus.PARSED
    assert db.query(EnedisFluxMesureR6x).count() == 1


def test_ingest_r64_payload_filename_mismatch_records_error_and_rolls_back(db, tmp_path):
    outer = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip"
    member = "ENEDIS_R64_P_INDEX_M06IFF1Z_00002_20240627165441.json"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: _r64_json()}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.ERROR
    assert db.query(EnedisFluxMesureR6x).count() == 0


def test_ingest_c68_json_primary_zip(db, tmp_path):
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    member = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.json"
    path = tmp_path / primary
    path.write_bytes(_c68_primary({secondary: _zip_bytes({member: _c68_json()})}))

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.PARSED
    file_row = db.query(EnedisFluxFile).one()
    assert file_row.flux_type == "C68"
    assert file_row.payload_format == "JSON"
    assert file_row.measures_count == 1
    assert file_row.archive_members_count == 1
    header_raw = file_row.get_header_raw()
    assert header_raw["archive_manifest"]["secondary_archives"][0]["payload_member_name"] == member
    row = db.query(EnedisFluxItcC68).one()
    assert row.point_id == "30000000000001"
    assert row.segment == "C5"
    assert row.siret == "12345678900011"
    assert row.puissance_souscrite_valeur == "36"


def test_ingest_c68_csv_legacy_and_v12_layouts(db, tmp_path):
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary_1 = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    secondary_2 = "ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.zip"
    path = tmp_path / primary
    path.write_bytes(
        _c68_primary(
            {
                secondary_1: _zip_bytes({"ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.csv": _c68_csv()}),
                secondary_2: _zip_bytes(
                    {"ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.csv": _c68_csv("30000000000002", v12=True)}
                ),
            }
        )
    )

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.PARSED
    assert db.query(EnedisFluxFile).one().measures_count == 2
    rows = db.query(EnedisFluxItcC68).order_by(EnedisFluxItcC68.point_id).all()
    assert rows[0].puissance_souscrite_valeur == "36"
    assert rows[1].borne_fixe == "OUI"
    assert rows[1].refus_pose_linky == "NON"


def test_ingest_c68_aes_wrapped_primary_zip(db, tmp_path, test_keys):
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    member = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.json"
    path = tmp_path / primary
    path.write_bytes(aes_encrypt(_c68_primary({secondary: _zip_bytes({member: _c68_json()})}), TEST_KEY, TEST_IV))

    status = ingest_file(path, db, keys=test_keys)

    assert status == FluxStatus.PARSED
    assert db.query(EnedisFluxItcC68).count() == 1


def test_ingest_c68_bad_second_secondary_rolls_back_whole_file(db, tmp_path):
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary_1 = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    secondary_2 = "ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.zip"
    path = tmp_path / primary
    path.write_bytes(
        _c68_primary(
            {
                secondary_1: _zip_bytes({"ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.json": _c68_json()}),
                secondary_2: _zip_bytes({"ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.json": b"[{}]"}),
            }
        )
    )

    status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.ERROR
    assert db.query(EnedisFluxItcC68).count() == 0


def test_ingest_directory_mixed_legacy_sf5_skipped_and_corrupt(db, tmp_path, test_keys):
    legacy_xml = b"""\
<?xml version="1.0" encoding="UTF-8"?>
<Courbe>
  <Entete><Identifiant_Flux>R4x</Identifiant_Flux><Frequence_Publication>H</Frequence_Publication></Entete>
  <Corps>
    <Identifiant_PRM>30000000000001</Identifiant_PRM>
    <Donnees_Courbe>
      <Donnees_Point_Mesure Horodatage="2026-01-01T00:00:00+01:00" Valeur_Point="1" Statut_Point="R"/>
    </Donnees_Courbe>
  </Corps>
</Courbe>"""
    (tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260101.zip").write_bytes(
        make_encrypted_zip(legacy_xml, "legacy.xml", TEST_KEY, TEST_IV)
    )
    r63_outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    (tmp_path / r63_outer).write_bytes(_zip_bytes({"ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json": _r63_json()}))
    c68_outer = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    (tmp_path / c68_outer).write_bytes(
        _c68_primary(
            {
                "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip": _zip_bytes(
                    {"ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.json": _c68_json()}
                )
            }
        )
    )
    (tmp_path / "ENEDIS_R63A_R_CDC_M01ABCDE_GRD-F345_00001_20230918161101.zip").write_bytes(b"known skipped")
    (tmp_path / "ENEDIS_C68_P_ITC_BAD_00001_20231219094139.zip").write_bytes(b"not a zip")

    counters = ingest_directory(tmp_path, db, test_keys, recursive=False)

    assert counters["parsed"] == 3
    assert counters["skipped"] == 1
    assert counters["error"] == 1
    assert db.query(EnedisFluxFile).count() == 5
    assert db.query(EnedisFluxMesureR6x).count() == 2
    assert db.query(EnedisFluxItcC68).count() == 1


def test_ingest_directory_dry_run_classifies_sf5_without_keys_or_db_mutation(db, tmp_path):
    (tmp_path / "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip").write_bytes(b"not inspected")
    (tmp_path / "ENEDIS_R63A_R_CDC_M01ABCDE_GRD-F345_00001_20230918161101.zip").write_bytes(b"not inspected")

    counters = ingest_directory(tmp_path, db, keys=[], recursive=False, dry_run=True)

    assert counters["received"] == 2
    assert db.query(EnedisFluxFile).count() == 0


def test_sf5_direct_file_idempotence(db, tmp_path):
    outer = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    member = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.json"
    path = tmp_path / outer
    path.write_bytes(_c68_primary({secondary: _zip_bytes({member: _c68_json()})}))

    assert ingest_file(path, db, keys=[]) == FluxStatus.PARSED
    assert ingest_file(path, db, keys=[]) == FluxStatus.PARSED
    assert db.query(EnedisFluxFile).count() == 1
    assert db.query(EnedisFluxItcC68).count() == 1


def test_sf5_same_filename_different_hash_is_republication(db, tmp_path):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({"ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json": _r63_json()}))

    assert ingest_file(path, db, keys=[]) == FluxStatus.PARSED
    path.write_bytes(_zip_bytes({"ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.csv": _r63_csv()}))

    assert ingest_file(path, db, keys=[]) == FluxStatus.NEEDS_REVIEW
    files = db.query(EnedisFluxFile).order_by(EnedisFluxFile.version).all()
    assert [file.version for file in files] == [1, 2]
    assert files[1].supersedes_file_id == files[0].id
    assert db.query(EnedisFluxMesureR6x).count() == 3


def test_sf5_retry_after_parse_error_archives_error_history(db, tmp_path):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.csv"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: b"Identifiant PRM;Date de debut\n30000000000001;2026-01-01\n"}))

    assert ingest_file(path, db, keys=[]) == FluxStatus.ERROR
    assert ingest_file(path, db, keys=[]) == FluxStatus.ERROR
    file_row = db.query(EnedisFluxFile).one()
    assert file_row.status == FluxStatus.ERROR
    assert len(file_row.errors) == 1


def test_sf5_permanent_failure_after_max_retries(db, tmp_path):
    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.csv"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: b"Identifiant PRM;Date de debut\n30000000000001;2026-01-01\n"}))

    for _ in range(MAX_RETRIES + 2):
        status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.PERMANENTLY_FAILED
    assert db.query(EnedisFluxFile).one().status == FluxStatus.PERMANENTLY_FAILED


def test_sf5_storage_error_rolls_back_rows(db, tmp_path):
    from unittest.mock import patch

    from sqlalchemy import Insert

    outer = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json"
    path = tmp_path / outer
    path.write_bytes(_zip_bytes({member: _r63_json()}))
    original_execute = db.execute

    def execute_that_fails_on_insert(stmt, *args, **kwargs):
        if isinstance(stmt, Insert):
            raise Exception("disk full")
        return original_execute(stmt, *args, **kwargs)

    with patch.object(db, "execute", side_effect=execute_that_fails_on_insert):
        status = ingest_file(path, db, keys=[])

    assert status == FluxStatus.ERROR
    assert "disk full" in db.query(EnedisFluxFile).one().error_message
    assert db.query(EnedisFluxMesureR6x).count() == 0
