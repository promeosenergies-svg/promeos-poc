"""Fixtures for Enedis SGE decrypt tests.

Provides synthetic AES-encrypted test data (no real Enedis keys needed).
"""

import io
import os
import sys
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import padding as crypto_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from dotenv import load_dotenv

# Ensure backend/ is on sys.path (same defensive pattern as existing tests)
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
)

# Load .env for integration tests (KEY_1/IV_1 etc.)
load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# ---------------------------------------------------------------------------
# Test key (NOT a real Enedis key)
# ---------------------------------------------------------------------------

TEST_KEY = bytes.fromhex("00112233445566778899aabbccddeeff")
TEST_IV = bytes.fromhex("aabbccddeeff00112233445566778899")

SAMPLE_XML = (
    b'<?xml version="1.0" encoding="UTF-8"?>'
    b"<Courbe><Entete>"
    b"<Identifiant_Flux>R4x</Identifiant_Flux>"
    b"<Frequence_Publication>H</Frequence_Publication>"
    b"</Entete></Courbe>"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def aes_encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """AES-128-CBC encrypt with PKCS7 padding."""
    padder = crypto_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def make_encrypted_zip(xml_content: bytes, inner_filename: str, key: bytes, iv: bytes) -> bytes:
    """Create AES ciphertext whose plaintext is a ZIP containing one XML file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_filename, xml_content)
    return aes_encrypt(buf.getvalue(), key, iv)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_keys():
    """Single (key, iv) test pair as a list."""
    return [(TEST_KEY, TEST_IV)]


@pytest.fixture
def encrypted_zip_file(tmp_path):
    """Encrypted file: AES(ZIP(XML)). Mimics real Enedis files."""
    ciphertext = make_encrypted_zip(SAMPLE_XML, "test_r4h.xml", TEST_KEY, TEST_IV)
    path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_20260101.zip"
    path.write_bytes(ciphertext)
    return path


@pytest.fixture
def encrypted_direct_xml_file(tmp_path):
    """Encrypted file: AES(XML) — no ZIP wrapper."""
    ciphertext = aes_encrypt(SAMPLE_XML, TEST_KEY, TEST_IV)
    path = tmp_path / "ENEDIS_23X--TEST_R4M_CDC_20260101.zip"
    path.write_bytes(ciphertext)
    return path


@pytest.fixture
def corrupt_file(tmp_path):
    """File with random bytes (not valid AES ciphertext)."""
    path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_CORRUPT.zip"
    path.write_bytes(os.urandom(256))
    return path


@pytest.fixture
def empty_file(tmp_path):
    """Empty file (0 bytes)."""
    path = tmp_path / "ENEDIS_23X--TEST_R4H_CDC_EMPTY.zip"
    path.write_bytes(b"")
    return path
