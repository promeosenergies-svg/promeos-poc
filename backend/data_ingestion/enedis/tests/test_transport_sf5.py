"""Tests for SF5 transport resolution."""

import io
import zipfile

import pytest

from data_ingestion.enedis.transport import TransportError, resolve_payload

from .conftest import SAMPLE_XML, TEST_IV, TEST_KEY, aes_encrypt, make_encrypted_zip


def _zip_bytes(member_name: str, payload: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(member_name, payload)
    return buf.getvalue()


def test_direct_zip_resolves_without_loading_keys(tmp_path):
    path = tmp_path / "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    zip_payload = _zip_bytes("ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.json", b"[]")
    path.write_bytes(zip_payload)

    def fail_loader():
        raise AssertionError("keys should not be loaded for direct ZIP")

    resolved = resolve_payload(path, "zip", key_loader=fail_loader)

    assert resolved.payload_bytes == zip_payload
    assert resolved.transport == "direct"
    assert resolved.key_index is None


def test_aes_wrapped_zip_resolves_in_memory(tmp_path):
    zip_payload = _zip_bytes("ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.csv", b"a;b\n1;2\n")
    path = tmp_path / "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip"
    path.write_bytes(aes_encrypt(zip_payload, TEST_KEY, TEST_IV))

    resolved = resolve_payload(path, "zip", keys=[(TEST_KEY, TEST_IV)])

    assert resolved.payload_bytes == zip_payload
    assert resolved.transport == "aes"
    assert resolved.key_index == 1


def test_aes_wrapped_c68_primary_zip_resolves_in_memory(tmp_path):
    secondary = _zip_bytes("ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.json", b"[]")
    primary = _zip_bytes("ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip", secondary)
    path = tmp_path / "ENEDIS_C68_P_ITC_M05J6FUB_00001_20231219094139.zip"
    path.write_bytes(aes_encrypt(primary, TEST_KEY, TEST_IV))

    resolved = resolve_payload(path, "zip", keys=[(TEST_KEY, TEST_IV)])

    assert resolved.payload_bytes == primary
    assert resolved.transport == "aes"


def test_missing_keys_only_fails_payload_that_needs_unwrap(tmp_path):
    direct = tmp_path / "ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip"
    direct.write_bytes(_zip_bytes("payload.json", b"[]"))
    encrypted = tmp_path / "ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip"
    encrypted.write_bytes(aes_encrypt(_zip_bytes("payload.csv", b"a;b\n"), TEST_KEY, TEST_IV))

    assert resolve_payload(direct, "zip").transport == "direct"
    with pytest.raises(TransportError, match="no keys"):
        resolve_payload(encrypted, "zip")


def test_legacy_xml_can_still_resolve_after_aes_zip_xml_unwrap(tmp_path, test_keys):
    path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260101.zip"
    path.write_bytes(make_encrypted_zip(SAMPLE_XML, "payload.xml", TEST_KEY, TEST_IV))

    # The new resolver returns decrypted ZIP bytes. Existing decrypt_file keeps
    # its XML extraction/validation behavior, covered in test_decrypt.py.
    resolved = resolve_payload(path, "zip", keys=test_keys)
    assert resolved.transport == "aes"
    assert zipfile.is_zipfile(io.BytesIO(resolved.payload_bytes))


def test_invalid_non_zip_with_wrong_key_reports_transport_error(tmp_path):
    path = tmp_path / "bad.zip"
    path.write_bytes(b"not a zip and not aes")

    wrong_key = bytes.fromhex("ffffffffffffffffffffffffffffffff")
    wrong_iv = bytes.fromhex("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
    with pytest.raises(TransportError, match="none of the"):
        resolve_payload(path, "zip", keys=[(wrong_key, wrong_iv)])
