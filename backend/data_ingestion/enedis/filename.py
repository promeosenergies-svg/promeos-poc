"""Filename parsing for Enedis R6X/M023 and C68 publications."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from data_ingestion.enedis.enums import FluxType


SF5_SUPPORTED_FLUX_TYPES = frozenset({FluxType.R63, FluxType.R64, FluxType.C68})
SF5_KNOWN_SKIPPED_FLUX_TYPES = frozenset(
    {
        FluxType.R63A,
        FluxType.R63B,
        FluxType.R64A,
        FluxType.R64B,
        FluxType.R65,
        FluxType.R66,
        FluxType.R66B,
        FluxType.R67,
        FluxType.CR_M023,
    }
)
SF5_KNOWN_FLUX_TYPES = SF5_SUPPORTED_FLUX_TYPES | SF5_KNOWN_SKIPPED_FLUX_TYPES

_NORMALIZED_CODE_TO_FLUX_TYPE = {
    "R63": FluxType.R63,
    "R64": FluxType.R64,
    "C68": FluxType.C68,
    "R63A": FluxType.R63A,
    "R63B": FluxType.R63B,
    "R64A": FluxType.R64A,
    "R64B": FluxType.R64B,
    "R65": FluxType.R65,
    "R66": FluxType.R66,
    "R66B": FluxType.R66B,
    "R67": FluxType.R67,
    "CR_M023": FluxType.CR_M023,
}


class FilenameParseError(ValueError):
    """Structured filename error for recognized SF5-adjacent families."""

    def __init__(self, filename: str, code_flux: str | None, message: str):
        self.filename = filename
        self.code_flux = code_flux
        self.message = message
        super().__init__(f"{filename}: {message}")


@dataclass(frozen=True)
class EnedisFilenameMetadata:
    """Parsed Enedis publication filename metadata, preserving raw values."""

    original_name: str
    extension: str
    code_flux: str
    flux_type: FluxType
    mode_publication: str
    type_donnee: str
    id_demande: str
    num_sequence: str
    publication_horodatage: str
    siren_publication: str | None = None
    code_contrat_publication: str | None = None

    @property
    def is_rec_shape(self) -> bool:
        return self.siren_publication is not None or self.code_contrat_publication is not None


def normalize_code_flux(raw_code: str) -> str:
    """Normalize technical code matching while preserving raw metadata elsewhere."""
    cleaned = re.sub(r"[^A-Z0-9]+", "_", raw_code.strip().upper()).strip("_")
    if cleaned == "CRM023":
        return "CR_M023"
    return cleaned


def flux_type_from_code(raw_code: str) -> FluxType | None:
    return _NORMALIZED_CODE_TO_FLUX_TYPE.get(normalize_code_flux(raw_code))


def classify_sf5_filename(filename: str) -> FluxType | None:
    """Return an SF5 flux type only when a filename code segment explicitly matches."""
    name = Path(filename).name
    stem = name[: -len(Path(name).suffix)] if Path(name).suffix else name
    parts = stem.split("_")

    candidates: list[str] = []
    if len(parts) >= 2 and parts[0].upper() == "ENEDIS":
        candidates.append(parts[1])
    if parts:
        candidates.append(parts[0])

    for candidate in candidates:
        flux_type = flux_type_from_code(candidate)
        if flux_type is not None:
            return flux_type
    return None


def parse_enedis_filename(filename: str) -> EnedisFilenameMetadata:
    """Parse M023 six-token or R6X-REC seven-token Enedis publication names."""
    name = Path(filename).name
    suffix = Path(name).suffix
    extension = suffix[1:] if suffix else ""
    stem = name[: -len(suffix)] if suffix else name
    parts = stem.split("_")

    if len(parts) < 2 or parts[0].upper() != "ENEDIS":
        flux_type = classify_sf5_filename(name)
        raise FilenameParseError(name, flux_type.value if flux_type else None, "expected ENEDIS-prefixed filename")

    raw_code = parts[1]
    flux_type = flux_type_from_code(raw_code)
    if flux_type is None:
        raise FilenameParseError(name, raw_code, "unknown Enedis SF5 code segment")

    if len(parts) == 7:
        _, code_flux, mode_publication, type_donnee, id_demande, num_sequence, horodate = parts
        return EnedisFilenameMetadata(
            original_name=name,
            extension=extension,
            code_flux=code_flux,
            flux_type=flux_type,
            mode_publication=mode_publication,
            type_donnee=type_donnee,
            id_demande=id_demande,
            num_sequence=num_sequence,
            publication_horodatage=horodate,
        )

    if len(parts) == 8:
        _, code_flux, mode_publication, type_donnee, id_demande, extra_id, num_sequence, horodate = parts
        is_siren = bool(re.fullmatch(r"\d{9}", extra_id))
        return EnedisFilenameMetadata(
            original_name=name,
            extension=extension,
            code_flux=code_flux,
            flux_type=flux_type,
            mode_publication=mode_publication,
            type_donnee=type_donnee,
            id_demande=id_demande,
            num_sequence=num_sequence,
            publication_horodatage=horodate,
            siren_publication=extra_id if is_siren else None,
            code_contrat_publication=None if is_siren else extra_id,
        )

    raise FilenameParseError(
        name,
        raw_code,
        "expected ENEDIS_<code>_<mode>_<type>_<idDemande>_<sequence>_<horodate> or REC seven-token shape",
    )
