"""PROMEOS - Enedis R64 R6X index JSON/CSV parser."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
import io
import json
import unicodedata
from typing import Any


class R64ParseError(Exception):
    """Raised when payload structure is invalid for R64 ingestion."""


@dataclass
class ParsedR64Header:
    raw: dict[str, Any]


@dataclass
class ParsedR64Row:
    point_id: str
    periode_date_debut: str
    periode_date_fin: str
    etape_metier: str
    contexte_releve: str
    type_releve: str
    motif_releve: str | None
    grandeur_metier: str
    grandeur_physique: str
    unite: str
    horodatage: str
    valeur: str | None
    indice_vraisemblance: str | None = None
    code_grille: str | None = None
    id_calendrier: str | None = None
    libelle_calendrier: str | None = None
    libelle_grille: str | None = None
    id_classe_temporelle: str | None = None
    libelle_classe_temporelle: str | None = None
    code_cadran: str | None = None


@dataclass
class ParsedR64File:
    header: ParsedR64Header
    source_format: str
    member_name: str
    rows: list[ParsedR64Row] = field(default_factory=list)

    @property
    def total_measures(self) -> int:
        return len(self.rows)


def parse_r64_payload(payload_bytes: bytes, source_format: str, member_name: str) -> ParsedR64File:
    fmt = source_format.upper()
    if fmt == "JSON":
        return _parse_json(payload_bytes, member_name)
    if fmt == "CSV":
        return _parse_csv(payload_bytes, member_name)
    raise R64ParseError(f"Unsupported R64 payload format: {source_format}")


def _parse_json(payload_bytes: bytes, member_name: str) -> ParsedR64File:
    try:
        payload = json.loads(payload_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R64ParseError(f"Invalid R64 JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise R64ParseError("R64 JSON root must be an object")
    header = payload.get("header")
    mesures = payload.get("mesures")
    if not isinstance(header, dict):
        raise R64ParseError("R64 JSON missing object header")
    if not isinstance(mesures, list):
        raise R64ParseError("R64 JSON missing mesures array")

    warnings = _json_schema_warnings(payload)
    header_raw: dict[str, Any] = dict(header)
    if warnings:
        header_raw["warnings"] = warnings

    rows: list[ParsedR64Row] = []
    for mesure_idx, mesure in enumerate(mesures):
        if not isinstance(mesure, dict):
            raise R64ParseError(f"R64 mesure #{mesure_idx + 1} must be an object")
        point_id = _required_str(mesure, "idPrm", f"mesures[{mesure_idx}]")
        periode = mesure.get("periode")
        if not isinstance(periode, dict):
            raise R64ParseError(f"R64 mesures[{mesure_idx}].periode must be an object")
        date_debut = _required_str(periode, "dateDebut", f"mesures[{mesure_idx}].periode")
        date_fin = _required_str(periode, "dateFin", f"mesures[{mesure_idx}].periode")
        contextes = mesure.get("contexte")
        if not isinstance(contextes, list):
            raise R64ParseError(f"R64 mesures[{mesure_idx}].contexte must be an array")

        for contexte_idx, contexte in enumerate(contextes):
            if not isinstance(contexte, dict):
                raise R64ParseError(f"R64 contexte #{contexte_idx + 1} must be an object")
            contexte_path = f"mesures[{mesure_idx}].contexte[{contexte_idx}]"
            grandeurs = contexte.get("grandeur")
            if not isinstance(grandeurs, list):
                raise R64ParseError(f"R64 {contexte_path}.grandeur must be an array")
            for grandeur_idx, grandeur in enumerate(grandeurs):
                if not isinstance(grandeur, dict):
                    raise R64ParseError(f"R64 grandeur #{grandeur_idx + 1} must be an object")
                rows.extend(
                    _flatten_grandeur(
                        point_id=point_id,
                        date_debut=date_debut,
                        date_fin=date_fin,
                        etape_metier=_required_str(contexte, "etapeMetier", contexte_path),
                        contexte_releve=_required_str(contexte, "contexteReleve", contexte_path),
                        type_releve=_required_str(contexte, "typeReleve", contexte_path),
                        motif_releve=_optional_str(contexte.get("motifReleve")),
                        grandeur=grandeur,
                        path=f"{contexte_path}.grandeur[{grandeur_idx}]",
                    )
                )

    return ParsedR64File(header=ParsedR64Header(header_raw), source_format="JSON", member_name=member_name, rows=rows)


def _flatten_grandeur(
    *,
    point_id: str,
    date_debut: str,
    date_fin: str,
    etape_metier: str,
    contexte_releve: str,
    type_releve: str,
    motif_releve: str | None,
    grandeur: dict[str, Any],
    path: str,
) -> list[ParsedR64Row]:
    base = {
        "point_id": point_id,
        "periode_date_debut": date_debut,
        "periode_date_fin": date_fin,
        "etape_metier": etape_metier,
        "contexte_releve": contexte_releve,
        "type_releve": type_releve,
        "motif_releve": motif_releve,
        "grandeur_metier": _required_str(grandeur, "grandeurMetier", path),
        "grandeur_physique": _required_str(grandeur, "grandeurPhysique", path),
        "unite": _required_str(grandeur, "unite", path),
    }
    rows: list[ParsedR64Row] = []

    calendriers = grandeur.get("calendrier")
    if calendriers is not None:
        if not isinstance(calendriers, list):
            raise R64ParseError(f"R64 {path}.calendrier must be an array")
        for calendrier_idx, calendrier in enumerate(calendriers):
            if not isinstance(calendrier, dict):
                raise R64ParseError(f"R64 calendrier #{calendrier_idx + 1} must be an object")
            cal_path = f"{path}.calendrier[{calendrier_idx}]"
            classes = calendrier.get("classeTemporelle")
            if not isinstance(classes, list):
                raise R64ParseError(f"R64 {cal_path}.classeTemporelle must be an array")
            for classe_idx, classe in enumerate(classes):
                if not isinstance(classe, dict):
                    raise R64ParseError(f"R64 classeTemporelle #{classe_idx + 1} must be an object")
                classe_path = f"{cal_path}.classeTemporelle[{classe_idx}]"
                rows.extend(
                    _rows_from_values(
                        classe.get("valeur"),
                        classe_path,
                        base,
                        id_calendrier=_optional_str(calendrier.get("idCalendrier")),
                        libelle_calendrier=_optional_str(calendrier.get("libelleCalendrier")),
                        libelle_grille=_optional_str(calendrier.get("libelleGrille")),
                        id_classe_temporelle=_optional_str(classe.get("idClasseTemporelle")),
                        libelle_classe_temporelle=_optional_str(classe.get("libelleClasseTemporelle")),
                        code_cadran=_optional_str(classe.get("codeCadran")),
                    )
                )

    totalisateur = grandeur.get("cadranTotalisateur")
    if totalisateur is not None:
        if not isinstance(totalisateur, dict):
            raise R64ParseError(f"R64 {path}.cadranTotalisateur must be an object")
        rows.extend(
            _rows_from_values(
                totalisateur.get("valeur"),
                f"{path}.cadranTotalisateur",
                base,
                code_cadran=_required_str(totalisateur, "codeCadran", f"{path}.cadranTotalisateur"),
            )
        )

    if not rows:
        raise R64ParseError(f"R64 {path} has no reachable valeur[] leaf")
    return rows


def _rows_from_values(values: Any, path: str, base: dict[str, str | None], **context: str | None) -> list[ParsedR64Row]:
    if not isinstance(values, list):
        raise R64ParseError(f"R64 {path}.valeur must be an array")
    rows = []
    for value_idx, value in enumerate(values):
        if not isinstance(value, dict):
            raise R64ParseError(f"R64 valeur #{value_idx + 1} must be an object")
        value_path = f"{path}.valeur[{value_idx}]"
        rows.append(
            ParsedR64Row(
                **base,
                horodatage=_required_str(value, "d", value_path),
                valeur=_optional_str(value.get("v")),
                indice_vraisemblance=_optional_str(value.get("iv")),
                **context,
            )
        )
    return rows


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
}

_CSV_OPTIONAL = {
    "contexte_releve": ("contexte releve", "contexte de releve"),
    "type_releve": ("type releve", "type de releve"),
    "motif_releve": ("motif releve", "motif de releve"),
    "code_grille": ("code grille", "grille"),
    "id_calendrier": ("id calendrier", "identifiant calendrier"),
    "libelle_calendrier": ("libelle calendrier",),
    "libelle_grille": ("libelle grille",),
    "id_classe_temporelle": ("id classe temporelle", "identifiant classe temporelle"),
    "libelle_classe_temporelle": ("libelle classe temporelle",),
    "code_cadran": ("code cadran", "cadran"),
    "indice_vraisemblance": ("indice vraisemblance", "indice de vraisemblance", "iv"),
}


def _parse_csv(payload_bytes: bytes, member_name: str) -> ParsedR64File:
    try:
        text = payload_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise R64ParseError(f"Invalid R64 CSV encoding: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise R64ParseError("R64 CSV missing header row")
    normalized = {_normalize_header(name): name for name in reader.fieldnames if name is not None}
    mapping: dict[str, str] = {}
    for target_field, aliases in _CSV_REQUIRED.items():
        raw = _lookup_header(normalized, aliases)
        if raw is None:
            raise R64ParseError(f"R64 CSV missing mandatory header: {aliases[0]}")
        mapping[target_field] = raw
    for target_field, aliases in _CSV_OPTIONAL.items():
        raw = _lookup_header(normalized, aliases)
        if raw is not None:
            mapping[target_field] = raw

    rows: list[ParsedR64Row] = []
    for row_number, row in enumerate(reader, start=2):
        values = {target_field: _cell(row, raw_name) for target_field, raw_name in mapping.items()}
        for target_field in _CSV_REQUIRED:
            if not values.get(target_field):
                raise R64ParseError(f"R64 CSV row {row_number} missing mandatory value for {mapping[target_field]}")
        rows.append(
            ParsedR64Row(
                point_id=values["point_id"],
                periode_date_debut=values["periode_date_debut"],
                periode_date_fin=values["periode_date_fin"],
                etape_metier=values["etape_metier"],
                contexte_releve=values.get("contexte_releve") or "",
                type_releve=values.get("type_releve") or "",
                motif_releve=values.get("motif_releve"),
                grandeur_metier=values["grandeur_metier"],
                grandeur_physique=values["grandeur_physique"],
                unite=values["unite"],
                horodatage=values["horodatage"],
                valeur=values["valeur"],
                indice_vraisemblance=values.get("indice_vraisemblance"),
                code_grille=values.get("code_grille"),
                id_calendrier=values.get("id_calendrier"),
                libelle_calendrier=values.get("libelle_calendrier"),
                libelle_grille=values.get("libelle_grille"),
                id_classe_temporelle=values.get("id_classe_temporelle"),
                libelle_classe_temporelle=values.get("libelle_classe_temporelle"),
                code_cadran=values.get("code_cadran"),
            )
        )

    return ParsedR64File(
        header=ParsedR64Header({"source": "csv", "headers": reader.fieldnames, "warnings": []}),
        source_format="CSV",
        member_name=member_name,
        rows=rows,
    )


def _required_str(obj: dict[str, Any], key: str, path: str) -> str:
    value = obj.get(key)
    if value is None or str(value).strip() == "":
        raise R64ParseError(f"R64 JSON missing mandatory {path}.{key}")
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
    return warnings


def _warn_unknown_keys(obj: dict[str, Any], allowed: set[str], path: str, warnings: list[dict[str, str]]) -> None:
    for key in obj:
        if key not in allowed:
            warnings.append({"code": "unknown_json_field", "path": f"{path}.{key}"})
