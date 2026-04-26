"""Pipeline tests for SF5 R63/R64/C68 raw ingestion."""

import io
import json
import zipfile

from data_ingestion.enedis.enums import FluxStatus
from data_ingestion.enedis.models import EnedisFluxFile, EnedisFluxMesureR6x
from data_ingestion.enedis.pipeline import ingest_file

from .conftest import TEST_IV, TEST_KEY, aes_encrypt


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
