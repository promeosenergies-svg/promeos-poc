"""ZIP container validation for SF5 Enedis publications."""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import PurePosixPath
import zipfile

from data_ingestion.enedis.enums import FluxType
from data_ingestion.enedis.filename import EnedisFilenameMetadata, FilenameParseError, parse_enedis_filename


class ContainerError(Exception):
    """Invalid SF5 archive structure or filename coherence."""


@dataclass(frozen=True)
class R6xPayload:
    payload_bytes: bytes
    payload_format: str
    member_name: str
    outer_metadata: EnedisFilenameMetadata
    payload_metadata: EnedisFilenameMetadata
    archive_members_count: int


@dataclass(frozen=True)
class C68Payload:
    payload_bytes: bytes
    payload_format: str
    secondary_archive_name: str
    payload_member_name: str
    secondary_metadata: EnedisFilenameMetadata
    payload_metadata: EnedisFilenameMetadata


@dataclass(frozen=True)
class C68Archive:
    primary_metadata: EnedisFilenameMetadata
    payloads: list[C68Payload]
    archive_members_count: int


def extract_r6x_payload(outer_filename: str, zip_bytes: bytes) -> R6xPayload:
    """Validate an R63/R64 archive and return its single JSON/CSV payload."""
    outer_meta = _parse_named(outer_filename)
    if outer_meta.flux_type not in {FluxType.R63, FluxType.R64}:
        raise ContainerError(f"{outer_filename}: expected R63 or R64 archive")

    with _open_zip(zip_bytes, outer_filename) as zf:
        members = _non_directory_members(zf)
        if len(members) != 1:
            raise ContainerError(f"{outer_filename}: expected exactly one payload member, found {len(members)}")
        member = members[0]
        _reject_nested_or_sidecar(member)
        payload_meta = _parse_named(member)
        if payload_meta.flux_type != outer_meta.flux_type:
            raise ContainerError(f"{outer_filename}: payload flux type does not match outer archive")
        _assert_same_request_metadata(outer_meta, payload_meta, compare_timestamp=True, compare_sequence=True)
        payload_bytes = zf.read(member)

    payload_format = detect_payload_format(member, payload_bytes)
    if payload_format not in {"JSON", "CSV"}:
        raise ContainerError(f"{outer_filename}: unsupported payload format for {member}")

    return R6xPayload(
        payload_bytes=payload_bytes,
        payload_format=payload_format,
        member_name=member,
        outer_metadata=outer_meta,
        payload_metadata=payload_meta,
        archive_members_count=len(members),
    )


def extract_c68_payloads(primary_filename: str, zip_bytes: bytes) -> C68Archive:
    """Validate a C68 primary archive and return coherent secondary payloads."""
    primary_meta = _parse_named(primary_filename)
    if primary_meta.flux_type != FluxType.C68:
        raise ContainerError(f"{primary_filename}: expected C68 primary archive")
    if primary_meta.num_sequence != "00001":
        raise ContainerError(f"{primary_filename}: C68 primary sequence must be 00001")

    payloads: list[C68Payload] = []
    with _open_zip(zip_bytes, primary_filename) as primary_zf:
        secondary_members = _non_directory_members(primary_zf)
        if not (1 <= len(secondary_members) <= 10):
            raise ContainerError(
                f"{primary_filename}: expected 1..10 secondary archives, found {len(secondary_members)}"
            )

        for secondary_name in secondary_members:
            _reject_nested_or_sidecar(secondary_name)
            secondary_meta = _parse_named(secondary_name)
            if secondary_meta.flux_type != FluxType.C68:
                raise ContainerError(f"{primary_filename}: unexpected first-level member {secondary_name}")
            _assert_same_request_metadata(primary_meta, secondary_meta, compare_timestamp=False, compare_sequence=False)

            secondary_bytes = primary_zf.read(secondary_name)
            with _open_zip(secondary_bytes, secondary_name) as secondary_zf:
                payload_members = _non_directory_members(secondary_zf)
                if len(payload_members) != 1:
                    raise ContainerError(
                        f"{secondary_name}: expected exactly one payload member, found {len(payload_members)}"
                    )
                payload_name = payload_members[0]
                _reject_nested_or_sidecar(payload_name)
                payload_meta = _parse_named(payload_name)
                if payload_meta.flux_type != FluxType.C68:
                    raise ContainerError(f"{secondary_name}: payload flux type does not match C68")
                _assert_same_request_metadata(
                    secondary_meta,
                    payload_meta,
                    compare_timestamp=True,
                    compare_sequence=True,
                )
                payload_bytes = secondary_zf.read(payload_name)
                payloads.append(
                    C68Payload(
                        payload_bytes=payload_bytes,
                        payload_format=detect_payload_format(payload_name, payload_bytes),
                        secondary_archive_name=secondary_name,
                        payload_member_name=payload_name,
                        secondary_metadata=secondary_meta,
                        payload_metadata=payload_meta,
                    )
                )

    formats = {payload.payload_format for payload in payloads}
    if not formats <= {"JSON", "CSV"}:
        raise ContainerError(f"{primary_filename}: unsupported C68 payload format")
    if len(formats) > 1:
        raise ContainerError(f"{primary_filename}: mixed C68 payload formats are not supported")

    sequences = sorted(_c68_secondary_sequence_number(primary_filename, payload) for payload in payloads)
    expected = list(range(1, len(payloads) + 1))
    if sequences != expected:
        raise ContainerError(f"{primary_filename}: C68 secondary sequences must be contiguous 00001..N")

    return C68Archive(primary_metadata=primary_meta, payloads=payloads, archive_members_count=len(payloads))


def _c68_secondary_sequence_number(primary_filename: str, payload: C68Payload) -> int:
    sequence = payload.secondary_metadata.num_sequence
    try:
        return int(sequence)
    except ValueError as exc:
        raise ContainerError(
            f"{primary_filename}: C68 secondary sequence must be numeric for "
            f"{payload.secondary_archive_name}: {sequence}"
        ) from exc


def detect_payload_format(member_name: str, payload_bytes: bytes) -> str:
    suffix = PurePosixPath(member_name).suffix.lower()
    if suffix == ".json":
        return "JSON"
    if suffix == ".csv":
        return "CSV"

    first = payload_bytes.lstrip()[:1]
    if first in {b"{", b"["}:
        return "JSON"
    return "CSV"


def _open_zip(zip_bytes: bytes, label: str) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise ContainerError(f"{label}: invalid ZIP archive") from exc


def _non_directory_members(zf: zipfile.ZipFile) -> list[str]:
    return [info.filename for info in zf.infolist() if not info.is_dir()]


def _reject_nested_or_sidecar(member_name: str) -> None:
    path = PurePosixPath(member_name)
    if len(path.parts) != 1:
        raise ContainerError(f"unexpected nested or sidecar member: {member_name}")
    if path.name in {".DS_Store"} or path.name.startswith("._") or path.name.startswith("__MACOSX"):
        raise ContainerError(f"unexpected sidecar member: {member_name}")
    if path.suffix.lower() not in {".zip", ".json", ".csv"}:
        raise ContainerError(f"unexpected archive member: {member_name}")


def _parse_named(name: str) -> EnedisFilenameMetadata:
    try:
        return parse_enedis_filename(name)
    except FilenameParseError as exc:
        raise ContainerError(str(exc)) from exc


def _assert_same_request_metadata(
    expected: EnedisFilenameMetadata,
    actual: EnedisFilenameMetadata,
    *,
    compare_timestamp: bool,
    compare_sequence: bool,
) -> None:
    fields = ["flux_type", "mode_publication", "type_donnee", "id_demande"]
    if compare_sequence:
        fields.append("num_sequence")
    if compare_timestamp:
        fields.append("publication_horodatage")

    for field in fields:
        if getattr(expected, field) != getattr(actual, field):
            raise ContainerError(f"filename metadata mismatch on {field}")
