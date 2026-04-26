"""Tests for SF5 ZIP container validation."""

import io
import zipfile

import pytest

from data_ingestion.enedis.containers import ContainerError, extract_c68_payloads, extract_r6x_payload


def _zip_bytes(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, payload in entries.items():
            zf.writestr(name, payload)
    return buf.getvalue()


def test_r63_direct_zip_single_json_member():
    name = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    member = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json"
    archive = _zip_bytes({member: b"[]"})

    payload = extract_r6x_payload(name, archive)

    assert payload.payload_format == "JSON"
    assert payload.member_name == member
    assert payload.outer_metadata.id_demande == "M053Q0D3"
    assert payload.archive_members_count == 1


def test_r64_direct_zip_single_csv_member_case_insensitive_extension():
    name = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip"
    member = "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.CSV"
    archive = _zip_bytes({member: b"a;b\n1;2\n"})

    payload = extract_r6x_payload(name, archive)

    assert payload.payload_format == "CSV"
    assert payload.payload_bytes == b"a;b\n1;2\n"


def test_r6x_extra_non_directory_member_is_fatal():
    name = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    archive = _zip_bytes(
        {
            "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json": b"[]",
            ".DS_Store": b"sidecar",
        }
    )

    with pytest.raises(ContainerError, match="exactly one"):
        extract_r6x_payload(name, archive)


def test_r6x_payload_filename_mismatch_is_fatal():
    name = "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    archive = _zip_bytes({"ENEDIS_R63_P_CdC_M053Q0D3_00002_20230918161101.json": b"[]"})

    with pytest.raises(ContainerError, match="num_sequence"):
        extract_r6x_payload(name, archive)


def test_c68_primary_with_one_secondary_json_payload():
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    payload_name = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.json"
    primary_zip = _zip_bytes({secondary: _zip_bytes({payload_name: b"[]"})})

    archive = extract_c68_payloads(primary, primary_zip)

    assert archive.archive_members_count == 1
    assert archive.payloads[0].payload_format == "JSON"
    assert archive.payloads[0].secondary_archive_name == secondary


def test_c68_multi_secondary_contiguous_sequences_and_primary_timestamp_can_differ():
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary_1 = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    secondary_2 = "ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.zip"
    primary_zip = _zip_bytes(
        {
            secondary_1: _zip_bytes({"ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.csv": b"PRM\n1\n"}),
            secondary_2: _zip_bytes({"ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.csv": b"PRM\n2\n"}),
        }
    )

    archive = extract_c68_payloads(primary, primary_zip)

    assert [p.secondary_metadata.num_sequence for p in archive.payloads] == ["00001", "00002"]
    assert {p.payload_format for p in archive.payloads} == {"CSV"}


def test_c68_sidecar_in_primary_is_fatal():
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    primary_zip = _zip_bytes({"__MACOSX/._payload.zip": b"sidecar"})

    with pytest.raises(ContainerError, match="sidecar|nested"):
        extract_c68_payloads(primary, primary_zip)


def test_c68_invalid_secondary_zip_is_fatal():
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    primary_zip = _zip_bytes({secondary: b"not a zip"})

    with pytest.raises(ContainerError, match="invalid ZIP"):
        extract_c68_payloads(primary, primary_zip)


def test_c68_mixed_payload_formats_are_fatal():
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    primary_zip = _zip_bytes(
        {
            "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip": _zip_bytes(
                {"ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.json": b"[]"}
            ),
            "ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.zip": _zip_bytes(
                {"ENEDIS_C68_P_ITC_M05J6FUB_00002_20231219094141.csv": b"PRM\n1\n"}
            ),
        }
    )

    with pytest.raises(ContainerError, match="mixed"):
        extract_c68_payloads(primary, primary_zip)


def test_c68_secondary_payload_timestamp_mismatch_is_fatal():
    primary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    secondary = "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094140.zip"
    primary_zip = _zip_bytes({secondary: _zip_bytes({"ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094199.json": b"[]"})})

    with pytest.raises(ContainerError, match="publication_horodatage"):
        extract_c68_payloads(primary, primary_zip)
