"""Unit tests for Enedis SGE decryption and classification.

All tests use synthetic AES-encrypted data — no real Enedis keys required.
"""

import pytest

from data_ingestion.enedis.decrypt import (
    DecryptError,
    MissingKeyError,
    classify_flux,
    decrypt_file,
    load_keys_from_env,
    SKIP_FLUX_TYPES,
)
from data_ingestion.enedis.enums import FluxType

from .conftest import SAMPLE_XML, TEST_IV, TEST_KEY


# ========================================================================
# classify_flux
# ========================================================================


class TestClassifyFlux:
    @pytest.mark.parametrize(
        "filename, expected",
        [
            ("ENEDIS_23X--130624--EE1_R4H_CDC_20260302.zip", FluxType.R4H),
            ("ENEDIS_23X--130624--EE1_R4M_CDC_20251203.zip", FluxType.R4M),
            ("ENEDIS_23X--130624--EE1_R4Q_CDC_20230519.zip", FluxType.R4Q),
            ("ENEDIS_R171_C_00000099895595_GRDF_23X.zip", FluxType.R171),
            ("ERDF_R50_23X--130624--EE1_GRD-F121.zip", FluxType.R50),
            ("ERDF_R151_23X--130624--EE1_GRD-F121.zip", FluxType.R151),
            ("ENEDIS_R172_30000550403414_192431565.zip", FluxType.R172),
            ("ENEDIS_X14_GRD-F121_00072.zip", FluxType.X14),
            ("Enedis_SGE_HDM_A08693PL.csv", FluxType.HDM),
            ("some_random_file.zip", FluxType.UNKNOWN),
        ],
    )
    def test_classify(self, filename, expected):
        assert classify_flux(filename) == expected

    def test_skip_types_are_not_decryptable(self):
        """R172, X14, HDM, UNKNOWN should be in SKIP_FLUX_TYPES."""
        assert FluxType.R172 in SKIP_FLUX_TYPES
        assert FluxType.X14 in SKIP_FLUX_TYPES
        assert FluxType.HDM in SKIP_FLUX_TYPES
        assert FluxType.UNKNOWN in SKIP_FLUX_TYPES
        for ft in (FluxType.R4H, FluxType.R4M, FluxType.R4Q, FluxType.R171, FluxType.R50, FluxType.R151):
            assert ft not in SKIP_FLUX_TYPES


# ========================================================================
# decrypt_file
# ========================================================================


class TestDecryptFile:
    def test_zip_wrapped(self, encrypted_zip_file, test_keys):
        """Standard case: AES(ZIP(XML)) -> XML bytes."""
        result = decrypt_file(encrypted_zip_file, test_keys)
        assert result == SAMPLE_XML

    def test_direct_xml(self, encrypted_direct_xml_file, test_keys):
        """Edge case: AES(XML) without ZIP wrapper."""
        result = decrypt_file(encrypted_direct_xml_file, test_keys)
        assert result == SAMPLE_XML

    def test_corrupt_file(self, corrupt_file, test_keys):
        """Random bytes -> DecryptError."""
        with pytest.raises(DecryptError, match="none of the"):
            decrypt_file(corrupt_file, test_keys)

    def test_empty_file(self, empty_file, test_keys):
        """Empty file -> DecryptError."""
        with pytest.raises(DecryptError, match="empty"):
            decrypt_file(empty_file, test_keys)

    def test_file_not_found(self, tmp_path, test_keys):
        """Nonexistent path -> FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            decrypt_file(tmp_path / "nonexistent.zip", test_keys)

    def test_wrong_key(self, encrypted_zip_file):
        """Valid encrypted data, wrong key -> DecryptError."""
        wrong_key = bytes.fromhex("ffffffffffffffffffffffffffffffff")
        wrong_iv = bytes.fromhex("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        with pytest.raises(DecryptError, match="none of the"):
            decrypt_file(encrypted_zip_file, [(wrong_key, wrong_iv)])

    def test_multiple_keys_first_fails(self, encrypted_zip_file):
        """First key wrong, second key correct -> success."""
        wrong_key = bytes.fromhex("ffffffffffffffffffffffffffffffff")
        wrong_iv = bytes.fromhex("eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
        keys = [(wrong_key, wrong_iv), (TEST_KEY, TEST_IV)]
        result = decrypt_file(encrypted_zip_file, keys)
        assert result == SAMPLE_XML

    def test_archive_writes_xml(self, encrypted_zip_file, test_keys, tmp_path):
        """With archive_dir set, decrypted XML is written to disk."""
        archive_dir = tmp_path / "archive"
        decrypt_file(encrypted_zip_file, test_keys, archive_dir=archive_dir)

        expected_path = archive_dir / (encrypted_zip_file.stem + ".xml")
        assert expected_path.exists()
        assert expected_path.read_bytes() == SAMPLE_XML

    def test_no_archive_by_default(self, encrypted_zip_file, test_keys, tmp_path):
        """Without archive_dir, no files are written."""
        archive_dir = tmp_path / "archive"
        decrypt_file(encrypted_zip_file, test_keys)
        assert not archive_dir.exists()


# ========================================================================
# load_keys_from_env
# ========================================================================


class TestLoadKeysFromEnv:
    def test_loads_keys(self, monkeypatch):
        """Reads KEY_1/IV_1 from environment."""
        monkeypatch.setenv("KEY_1", "00112233445566778899aabbccddeeff")
        monkeypatch.setenv("IV_1", "aabbccddeeff00112233445566778899")
        monkeypatch.delenv("KEY_2", raising=False)
        monkeypatch.delenv("IV_2", raising=False)

        keys = load_keys_from_env()
        assert len(keys) == 1
        assert keys[0] == (TEST_KEY, TEST_IV)

    def test_loads_multiple_keys(self, monkeypatch):
        """Reads KEY_1/IV_1 and KEY_2/IV_2."""
        monkeypatch.setenv("KEY_1", "00112233445566778899aabbccddeeff")
        monkeypatch.setenv("IV_1", "aabbccddeeff00112233445566778899")
        monkeypatch.setenv("KEY_2", "ffeeddccbbaa99887766554433221100")
        monkeypatch.setenv("IV_2", "99887766554433221100ffeeddccbbaa")
        monkeypatch.delenv("KEY_3", raising=False)
        monkeypatch.delenv("IV_3", raising=False)

        keys = load_keys_from_env()
        assert len(keys) == 2

    def test_missing_keys_raises(self, monkeypatch):
        """No KEY_1/IV_1 in env -> MissingKeyError."""
        monkeypatch.delenv("KEY_1", raising=False)
        monkeypatch.delenv("IV_1", raising=False)

        with pytest.raises(MissingKeyError, match="No decryption keys"):
            load_keys_from_env()

    def test_invalid_hex_raises(self, monkeypatch):
        """Non-hex value -> MissingKeyError."""
        monkeypatch.setenv("KEY_1", "not_valid_hex")
        monkeypatch.setenv("IV_1", "aabbccddeeff00112233445566778899")

        with pytest.raises(MissingKeyError, match="not valid hex"):
            load_keys_from_env()

    def test_partial_pair_key_without_iv(self, monkeypatch):
        """KEY_1 set but IV_1 missing -> MissingKeyError."""
        monkeypatch.setenv("KEY_1", "00112233445566778899aabbccddeeff")
        monkeypatch.delenv("IV_1", raising=False)

        with pytest.raises(MissingKeyError, match="IV_1"):
            load_keys_from_env()

    def test_partial_pair_iv_without_key(self, monkeypatch):
        """IV_1 set but KEY_1 missing -> MissingKeyError."""
        monkeypatch.delenv("KEY_1", raising=False)
        monkeypatch.setenv("IV_1", "aabbccddeeff00112233445566778899")

        with pytest.raises(MissingKeyError, match="KEY_1"):
            load_keys_from_env()
