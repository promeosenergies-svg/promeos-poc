"""PROMEOS — Enedis R63 R6X load-curve JSON/CSV parser."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import io
import json
import unicodedata
from typing import Any


class R63ParseError(Exception):
    """Raised when payload structure is invalid for R63 ingestion."""


@dataclass
class ParsedR63Header:
    raw: dict[str, Any]


@dataclass
class ParsedR63Row:
    point_id: str
    periode_date_debut: str
    periode_date_fin: str
    etape_metier: str
    mode_calcul: str | None
    grandeur_metier: str
    grandeur_physique: str
    unite: str
    horodatage: str
    valeur: str | None
    nature_point: str
    pas: str
    type_correction: str | None = None
    indice_vraisemblance: str | None = None
    etat_complementaire: str | None = None


@dataclass
class ParsedR63File:
    header: ParsedR63Header
    source_format: str
    member_name: str
    rows: list[ParsedR63Row] = field(default_factory=list)

    @property
    def total_measures(self) -> int:
        return len(self.rows)


def parse_r63_payload(payload_bytes: bytes, source_format: str, member_name: str) -> ParsedR63File:
    fmt = source_format.upper()
    if fmt == "JSON":
        return _parse_json(payload_bytes, member_name)
    if fmt == "CSV":
        return _parse_csv(payload_bytes, member_name)
    raise R63ParseError(f"Unsupported R63 payload format: {source_format}")


def _parse_json(payload_bytes: bytes, member_name: str) -> ParsedR63File:
    try:
        payload = json.loads(payload_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R63ParseError(f"Invalid R63 JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise R63ParseError("R63 JSON root must be an object")
    header = payload.get("header")
    mesures = payload.get("mesures")
    if not isinstance(header, dict):
        raise R63ParseError("R63 JSON missing object header")
    if not isinstance(mesures, list):
        raise R63ParseError("R63 JSON missing mesures array")

    warnings = _json_schema_warnings(payload)
    header_raw: dict[str, Any] = dict(header)
    if warnings:
        header_raw["warnings"] = warnings

    rows: list[ParsedR63Row] = []
    for mesure_idx, mesure in enumerate(mesures):
        if not isinstance(mesure, dict):
            raise R63ParseError(f"R63 mesure #{mesure_idx + 1} must be an object")
        point_id = _required_str(mesure, "idPrm", f"mesures[{mesure_idx}]")
        etape_metier = _required_str(mesure, "etapeMetier", f"mesures[{mesure_idx}]")
        periode = mesure.get("periode")
        if not isinstance(periode, dict):
            raise R63ParseError(f"R63 mesures[{mesure_idx}].periode must be an object")
        date_debut = _required_str(periode, "dateDebut", f"mesures[{mesure_idx}].periode")
        date_fin = _required_str(periode, "dateFin", f"mesures[{mesure_idx}].periode")
        mode_calcul = _optional_str(mesure.get("modeCalcul"))
        grandeurs = mesure.get("grandeur")
        if not isinstance(grandeurs, list):
            raise R63ParseError(f"R63 mesures[{mesure_idx}].grandeur must be an array")

        for grandeur_idx, grandeur in enumerate(grandeurs):
            if not isinstance(grandeur, dict):
                raise R63ParseError(f"R63 grandeur #{grandeur_idx + 1} must be an object")
            path = f"mesures[{mesure_idx}].grandeur[{grandeur_idx}]"
            grandeur_metier = _required_str(grandeur, "grandeurMetier", path)
            grandeur_physique = _required_str(grandeur, "grandeurPhysique", path)
            unite = _required_str(grandeur, "unite", path)
            points = grandeur.get("points")
            if not isinstance(points, list):
                raise R63ParseError(f"R63 {path}.points must be an array")
            for point_idx, point in enumerate(points):
                if not isinstance(point, dict):
                    raise R63ParseError(f"R63 point #{point_idx + 1} must be an object")
                point_path = f"{path}.points[{point_idx}]"
                rows.append(
                    ParsedR63Row(
                        point_id=point_id,
                        periode_date_debut=date_debut,
                        periode_date_fin=date_fin,
                        etape_metier=etape_metier,
                        mode_calcul=mode_calcul,
                        grandeur_metier=grandeur_metier,
                        grandeur_physique=grandeur_physique,
                        unite=unite,
                        horodatage=_required_str(point, "d", point_path),
                        valeur=_optional_str(point.get("v")),
                        nature_point=_required_str(point, "n", point_path),
                        pas=_required_str(point, "p", point_path),
                        type_correction=_optional_str(point.get("tc")),
                        indice_vraisemblance=_optional_str(point.get("iv")),
                        etat_complementaire=_optional_str(point.get("ec")),
                    )
                )

    return ParsedR63File(header=ParsedR63Header(header_raw), source_format="JSON", member_name=member_name, rows=rows)


_CSV_REQUIRED = {
    "point_id": ("identifiant prm",),
    "periode_date_debut": ("date de debut",),
    "periode_date_fin": ("date de fin",),
    "grandeur_physique": ("grandeur physique",),
    "grandeur_metier": ("grandeur metier",),
    "etape_metier": ("etape metier",),
    "unite": ("unite",),
    "horodatage": ("horodate",),
    "valeur": ("valeur",),
    "nature_point": ("nature",),
    "pas": ("pas",),
}

_CSV_OPTIONAL = {
    "mode_calcul": ("mode calcul",),
    "type_correction": ("type correction", "tc"),
    "indice_vraisemblance": ("indice vraisemblance", "iv"),
    "etat_complementaire": ("etat complementaire", "ec"),
}


def _parse_csv(payload_bytes: bytes, member_name: str) -> ParsedR63File:
    try:
        text = payload_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise R63ParseError(f"Invalid R63 CSV encoding: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise R63ParseError("R63 CSV missing header row")
    normalized = {_normalize_header(name): name for name in reader.fieldnames if name is not None}
    mapping: dict[str, str] = {}
    for target_field, aliases in _CSV_REQUIRED.items():
        raw = _lookup_header(normalized, aliases)
        if raw is None:
            raise R63ParseError(f"R63 CSV missing mandatory header: {aliases[0]}")
        mapping[target_field] = raw
    for target_field, aliases in _CSV_OPTIONAL.items():
        raw = _lookup_header(normalized, aliases)
        if raw is not None:
            mapping[target_field] = raw

    rows: list[ParsedR63Row] = []
    for row_number, row in enumerate(reader, start=2):
        values = {target_field: _cell(row, raw_name) for target_field, raw_name in mapping.items()}
        for target_field in _CSV_REQUIRED:
            if not values.get(target_field):
                raise R63ParseError(f"R63 CSV row {row_number} missing mandatory value for {mapping[target_field]}")
        rows.append(
            ParsedR63Row(
                point_id=values["point_id"],
                periode_date_debut=values["periode_date_debut"],
                periode_date_fin=values["periode_date_fin"],
                etape_metier=values["etape_metier"],
                mode_calcul=values.get("mode_calcul"),
                grandeur_metier=values["grandeur_metier"],
                grandeur_physique=values["grandeur_physique"],
                unite=values["unite"],
                horodatage=values["horodatage"],
                valeur=values["valeur"],
                nature_point=values["nature_point"],
                pas=values["pas"],
                type_correction=values.get("type_correction"),
                indice_vraisemblance=values.get("indice_vraisemblance"),
                etat_complementaire=values.get("etat_complementaire"),
            )
        )

    return ParsedR63File(
        header=ParsedR63Header({"source": "csv", "headers": reader.fieldnames, "warnings": []}),
        source_format="CSV",
        member_name=member_name,
        rows=rows,
    )


def _required_str(obj: dict[str, Any], key: str, path: str) -> str:
    value = obj.get(key)
    if value is None or str(value).strip() == "":
        raise R63ParseError(f"R63 JSON missing mandatory {path}.{key}")
    return str(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _cell(row: dict[str, str | None], raw_name: str) -> str | None:
    value = row.get(raw_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_accents.strip().lower().replace("_", " ").split())


def _lookup_header(headers: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        raw = headers.get(_normalize_header(alias))
        if raw is not None:
            return raw
    return None


def _json_schema_warnings(payload: dict[str, Any]) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    _warn_unknown_keys(payload, {"header", "mesures"}, "$", warnings)
    header = payload.get("header")
    if isinstance(header, dict):
        _warn_unknown_keys(
            header,
            {
                "siDemandeur",
                "typeDestinataire",
                "idDestinataire",
                "codeFlux",
                "idDemande",
                "modePublication",
                "idCanalContact",
                "format",
                "publicationCrp",
            },
            "$.header",
            warnings,
        )
    for idx, mesure in enumerate(payload.get("mesures") if isinstance(payload.get("mesures"), list) else []):
        if not isinstance(mesure, dict):
            continue
        _warn_unknown_keys(
            mesure, {"idPrm", "etapeMetier", "periode", "modeCalcul", "grandeur"}, f"$.mesures[{idx}]", warnings
        )
    return warnings


def _warn_unknown_keys(obj: dict[str, Any], allowed: set[str], path: str, warnings: list[dict[str, str]]) -> None:
    for key in obj:
        if key not in allowed:
            warnings.append({"code": "unknown_json_field", "path": f"{path}.{key}"})
