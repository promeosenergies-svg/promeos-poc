"""PROMEOS — Enedis SGE flux decryption and classification.

Encryption: AES-128-CBC with PKCS7 padding.
Observed post-decrypt in the current POC dataset: ZIP archive containing one XML
file. Official Enedis R4x v2.0.3 documentation allows one or more XML files per
archive; the current implementation still extracts the first ZIP member only.
Three key/IV pairs (KEY_1/IV_1 .. KEY_3/IV_3) are tried sequentially.
No deterministic mapping between key and flux type exists
(e.g. R4Q files may use KEY_2 or KEY_3 depending on the file).

Discovery performed 2026-03-22 on 91 in-scope files — 100% success rate.
"""

import io
import os
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import padding as crypto_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from data_ingestion.enedis.enums import FluxType
from data_ingestion.enedis.filename import SF5_KNOWN_SKIPPED_FLUX_TYPES, classify_sf5_filename


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class DecryptError(Exception):
    """Decryption failed: bad key, corrupt data, or result is not valid XML."""


class MissingKeyError(Exception):
    """No decryption keys found in environment variables."""


# ---------------------------------------------------------------------------
# Flux types that should NOT be decrypted
# ---------------------------------------------------------------------------

SKIP_FLUX_TYPES = (
    frozenset({FluxType.R172, FluxType.X14, FluxType.HDM, FluxType.UNKNOWN}) | SF5_KNOWN_SKIPPED_FLUX_TYPES
)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


_CLASSIFY_RULES: tuple[tuple[str, FluxType], ...] = (
    ("_R4H_CDC_", FluxType.R4H),
    ("_R4M_CDC_", FluxType.R4M),
    ("_R4Q_CDC_", FluxType.R4Q),
    ("_R171_", FluxType.R171),
    ("_R50_", FluxType.R50),
    ("_R151_", FluxType.R151),
    ("_R172_", FluxType.R172),
    ("_X14_", FluxType.X14),
    ("_HDM_", FluxType.HDM),
)


def classify_flux(filename: str) -> FluxType:
    """Identify flux type from filename pattern.

    >>> classify_flux("ENEDIS_23X--130624--EE1_R4H_CDC_20260302.zip")
    <FluxType.R4H: 'R4H'>
    >>> classify_flux("ERDF_R50_23X--130624--EE1_GRD-F121.zip")
    <FluxType.R50: 'R50'>
    """
    sf5_type = classify_sf5_filename(filename)
    if sf5_type is not None:
        return sf5_type

    upper_filename = filename.upper()
    for pattern, flux_type in _CLASSIFY_RULES:
        if pattern in upper_filename:
            return flux_type
    return FluxType.UNKNOWN


# ---------------------------------------------------------------------------
# Key management
# ---------------------------------------------------------------------------


def load_keys_from_env() -> list[tuple[bytes, bytes]]:
    """Load AES key/IV pairs from KEY_1/IV_1 .. KEY_N/IV_N env vars.

    Values must be hex-encoded (32 hex chars = 16 bytes for AES-128).
    Raises MissingKeyError if no valid pairs found.
    """
    pairs = []
    for i in range(1, 10):
        key_hex = os.environ.get(f"KEY_{i}")
        iv_hex = os.environ.get(f"IV_{i}")
        if key_hex and not iv_hex:
            raise MissingKeyError(f"KEY_{i} is set but IV_{i} is missing")
        if iv_hex and not key_hex:
            raise MissingKeyError(f"IV_{i} is set but KEY_{i} is missing")
        if not key_hex and not iv_hex:
            continue
        try:
            pairs.append((bytes.fromhex(key_hex.strip()), bytes.fromhex(iv_hex.strip())))
        except ValueError as exc:
            raise MissingKeyError(f"KEY_{i}/IV_{i} is not valid hex: {exc}") from exc
    if not pairs:
        raise MissingKeyError("No decryption keys found. Set KEY_1/IV_1 .. KEY_N/IV_N env vars (hex-encoded).")
    return pairs


# ---------------------------------------------------------------------------
# Low-level crypto helpers
# ---------------------------------------------------------------------------


def _aes_cbc_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes | None:
    """AES-128-CBC + PKCS7 unpad. Returns None on any failure."""
    try:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = crypto_padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()
    except Exception:
        return None


def _extract_xml_from_zip(data: bytes) -> bytes:
    """Extract the first file from an in-memory ZIP archive."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        if not names:
            raise DecryptError("ZIP archive is empty — no files inside")
        return zf.read(names[0])


# ---------------------------------------------------------------------------
# Main decrypt function
# ---------------------------------------------------------------------------


def decrypt_file(
    file_path: Path,
    keys: list[tuple[bytes, bytes]],
    archive_dir: Path | None = None,
) -> bytes:
    """Decrypt an Enedis SGE encrypted file and return XML content.

    Tries each (key, iv) pair until one produces valid XML.
    Post-decrypt content may be a ZIP (extracted automatically) or direct XML.

    Args:
        file_path: Path to the encrypted file (.zip extension, raw AES ciphertext).
        keys: List of (key, iv) byte tuples to try.
        archive_dir: Optional directory to write the decrypted XML for audit.

    Returns:
        Decrypted XML as bytes.

    Raises:
        FileNotFoundError: file_path does not exist.
        DecryptError: no key produced valid XML.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ciphertext = file_path.read_bytes()
    if not ciphertext:
        raise DecryptError(f"File is empty: {file_path.name}")

    for key, iv in keys:
        plaintext = _aes_cbc_decrypt(ciphertext, key, iv)
        if plaintext is None:
            continue

        # Post-decrypt: ZIP containing XML, or direct XML
        try:
            if plaintext[:4] == b"PK\x03\x04":
                xml_bytes = _extract_xml_from_zip(plaintext)
            elif plaintext.lstrip()[:1] == b"<":
                xml_bytes = plaintext
            else:
                continue
        except Exception:
            continue

        # Validate: must be parseable XML
        try:
            ET.fromstring(xml_bytes)
        except ET.ParseError:
            continue

        # Optional archiving
        if archive_dir is not None:
            archive_dir.mkdir(parents=True, exist_ok=True)
            safe_stem = Path(file_path.name).stem
            archive_name = safe_stem + ".xml"
            resolved = (archive_dir / archive_name).resolve()
            if not str(resolved).startswith(str(archive_dir.resolve())):
                raise DecryptError(f"Archive path escape attempt: {archive_name}")
            resolved.write_bytes(xml_bytes)

        return xml_bytes

    raise DecryptError(f"Decryption failed for {file_path.name}: none of the {len(keys)} key(s) produced valid XML")
