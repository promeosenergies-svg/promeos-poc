"""Transport resolution for direct or AES-wrapped Enedis payloads."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from data_ingestion.enedis.decrypt import DecryptError, MissingKeyError, aes_unwrap_bytes

PayloadKind = str
KeyLoader = Callable[[], list[tuple[bytes, bytes]]]


class TransportError(Exception):
    """Could not resolve raw file bytes to the expected payload/container."""


@dataclass(frozen=True)
class ResolvedPayload:
    payload_bytes: bytes
    transport: str
    payload_kind: PayloadKind
    key_index: int | None = None


def resolve_payload(
    file_path: Path,
    expected_payload_kind: PayloadKind,
    keys: list[tuple[bytes, bytes]] | None = None,
    key_loader: KeyLoader | None = None,
) -> ResolvedPayload:
    """Resolve a direct XML/ZIP payload or AES-wrapped payload in memory."""
    if not file_path.exists():
        raise FileNotFoundError(f"Flux file not found: {file_path}")

    raw_bytes = file_path.read_bytes()
    if _matches_payload_kind(raw_bytes, expected_payload_kind):
        return ResolvedPayload(raw_bytes, "direct", expected_payload_kind)

    loaded_keys = keys
    if loaded_keys is None and key_loader is not None:
        try:
            loaded_keys = key_loader()
        except MissingKeyError as exc:
            raise TransportError(f"{file_path.name} requires AES unwrap but no keys are available: {exc}") from exc

    if not loaded_keys:
        raise TransportError(
            f"{file_path.name} is not a direct {expected_payload_kind.upper()} payload and no keys are available"
        )

    try:
        plaintext, key_index = aes_unwrap_bytes(raw_bytes, loaded_keys)
    except DecryptError as exc:
        raise TransportError(str(exc)) from exc

    if not _matches_payload_kind(plaintext, expected_payload_kind):
        raise TransportError(f"AES unwrap did not produce a valid {expected_payload_kind.upper()} payload")

    return ResolvedPayload(plaintext, "aes", expected_payload_kind, key_index=key_index)


def _matches_payload_kind(payload: bytes, expected_payload_kind: PayloadKind) -> bool:
    kind = expected_payload_kind.lower()
    if kind == "zip":
        return zipfile.is_zipfile(_BytesPath(payload))
    if kind == "xml":
        try:
            ET.fromstring(payload)
        except ET.ParseError:
            return False
        return True
    raise ValueError(f"Unsupported payload kind: {expected_payload_kind}")


class _BytesPath:
    """Tiny seekable adapter for zipfile.is_zipfile without copying to disk."""

    def __init__(self, data: bytes):
        import io

        self._bio = io.BytesIO(data)

    def read(self, *args):
        return self._bio.read(*args)

    def seek(self, *args):
        return self._bio.seek(*args)

    def tell(self):
        return self._bio.tell()
