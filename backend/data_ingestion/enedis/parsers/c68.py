"""PROMEOS - Enedis C68 technical/contractual JSON/CSV parser."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
import io
import json
import unicodedata
from typing import Any


class C68ParseError(Exception):
    """Raised when payload structure is invalid for C68 ingestion."""


@dataclass
class ParsedC68Row:
    point_id: str
    payload_raw: str
    contractual_situation_count: int | None = None
    date_debut_situation_contractuelle: str | None = None
    segment: str | None = None
    etat_contractuel: str | None = None
    formule_tarifaire_acheminement: str | None = None
    code_tarif_acheminement: str | None = None
    siret: str | None = None
    siren: str | None = None
    domaine_tension: str | None = None
    tension_livraison: str | None = None
    type_comptage: str | None = None
    mode_releve: str | None = None
    media_comptage: str | None = None
    periodicite_releve: str | None = None
    puissance_souscrite_valeur: str | None = None
    puissance_souscrite_unite: str | None = None
    puissance_limite_soutirage_valeur: str | None = None
    puissance_limite_soutirage_unite: str | None = None
    puissance_raccordement_soutirage_valeur: str | None = None
    puissance_raccordement_soutirage_unite: str | None = None
    puissance_raccordement_injection_valeur: str | None = None
    puissance_raccordement_injection_unite: str | None = None
    type_injection: str | None = None
    borne_fixe: str | None = None
    refus_pose_linky: str | None = None
    date_refus_pose_linky: str | None = None
    warnings: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ParsedC68Payload:
    source_format: str
    member_name: str
    rows: list[ParsedC68Row]
    warnings: list[dict[str, str]] = field(default_factory=list)

    @property
    def total_prms(self) -> int:
        return len(self.rows)


def parse_c68_payload(payload_bytes: bytes, source_format: str, member_name: str) -> ParsedC68Payload:
    fmt = source_format.upper()
    if fmt == "JSON":
        return _parse_json(payload_bytes, member_name)
    if fmt == "CSV":
        return _parse_csv(payload_bytes, member_name)
    raise C68ParseError(f"Unsupported C68 payload format: {source_format}")


def _parse_json(payload_bytes: bytes, member_name: str) -> ParsedC68Payload:
    try:
        payload = json.loads(payload_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise C68ParseError(f"Invalid C68 JSON: {exc}") from exc

    if not isinstance(payload, list):
        raise C68ParseError("C68 JSON root must be an array")

    rows: list[ParsedC68Row] = []
    warnings: list[dict[str, str]] = []
    for index, prm_obj in enumerate(payload):
        if not isinstance(prm_obj, dict):
            raise C68ParseError(f"C68 JSON item #{index + 1} must be an object")
        point_id = _first_str(prm_obj, "idPrm", "PRM")
        if not point_id:
            raise C68ParseError(f"C68 JSON item #{index + 1} missing idPrm")
        row_warnings = _json_object_warnings(prm_obj, index)
        row = ParsedC68Row(
            point_id=point_id,
            payload_raw=json.dumps(prm_obj, ensure_ascii=False, sort_keys=True),
            contractual_situation_count=_contractual_situation_count(prm_obj),
            **_extract_json_columns(prm_obj, row_warnings),
            warnings=row_warnings,
        )
        rows.append(row)
        warnings.extend(row_warnings)

    return ParsedC68Payload(source_format="JSON", member_name=member_name, rows=rows, warnings=warnings)


def _parse_csv(payload_bytes: bytes, member_name: str) -> ParsedC68Payload:
    try:
        text = payload_bytes.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise C68ParseError(f"Invalid C68 CSV encoding: {exc}") from exc

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    if not reader.fieldnames:
        raise C68ParseError("C68 CSV missing header row")
    normalized_headers = {_normalize_header(name): name for name in reader.fieldnames if name is not None}
    prm_header = normalized_headers.get("prm")
    if prm_header is None:
        raise C68ParseError("C68 CSV missing mandatory header: PRM")

    rows: list[ParsedC68Row] = []
    warnings: list[dict[str, str]] = []
    unknown_headers = sorted(set(reader.fieldnames) - set(_CSV_ALLOWED_RAW_HEADERS))
    if unknown_headers:
        warnings.append({"code": "unknown_csv_columns", "columns": ",".join(unknown_headers)})

    for row_number, csv_row in enumerate(reader, start=2):
        point_id = _csv_cell(csv_row, prm_header)
        if not point_id:
            raise C68ParseError(f"C68 CSV row {row_number} missing mandatory PRM")
        payload_raw = json.dumps(dict(csv_row), ensure_ascii=False, sort_keys=True)
        rows.append(
            ParsedC68Row(
                point_id=point_id,
                payload_raw=payload_raw,
                **_extract_csv_columns(csv_row, normalized_headers),
            )
        )

    return ParsedC68Payload(source_format="CSV", member_name=member_name, rows=rows, warnings=warnings)


def _extract_json_columns(prm_obj: dict[str, Any], warnings: list[dict[str, str]]) -> dict[str, str | None]:
    selected = _select_latest_contractual_situation(prm_obj.get("situationsContractuelles"), warnings)
    contractual_ambiguous = any(warning.get("code") == "ambiguous_contractual_situation" for warning in warnings)
    columns = {
        "date_debut_situation_contractuelle": _optional_str(selected.get("dateDebut")) if selected else None,
        "segment": None
        if contractual_ambiguous
        else _optional_str((selected or {}).get("segment") or _find_value(prm_obj, "segment")),
        "etat_contractuel": None
        if contractual_ambiguous
        else _optional_str((selected or {}).get("etatContractuel") or _find_value(prm_obj, "etatContractuel")),
        "formule_tarifaire_acheminement": _optional_str(
            (selected or {}).get("formuleTarifaireAcheminement") or _find_value(prm_obj, "formuleTarifaireAcheminement")
        )
        if not contractual_ambiguous
        else None,
        "code_tarif_acheminement": _optional_str(
            (selected or {}).get("codeTarifAcheminement") or _find_value(prm_obj, "codeTarifAcheminement")
        )
        if not contractual_ambiguous
        else None,
        "siret": _optional_str(_find_value(prm_obj, "siret")),
        "siren": _optional_str(_find_value(prm_obj, "siren")),
        "domaine_tension": _optional_str(_find_value(prm_obj, "domaineTension")),
        "tension_livraison": _optional_str(_find_value(prm_obj, "tensionLivraison")),
        "type_comptage": _optional_str(_find_value(prm_obj, "typeComptage")),
        "mode_releve": _optional_str(_find_value(prm_obj, "modeReleve")),
        "media_comptage": _optional_str(_find_value(prm_obj, "mediaComptage")),
        "periodicite_releve": _optional_str(_find_value(prm_obj, "periodiciteReleve")),
        "type_injection": None
        if contractual_ambiguous
        else _optional_str((selected or {}).get("typeInjection") or prm_obj.get("typeInjection")),
        "borne_fixe": _optional_str(_find_value(prm_obj, "borneFixe")),
        "refus_pose_linky": _optional_str(_find_value(prm_obj, "refusPoseLinky")),
        "date_refus_pose_linky": _optional_str(_find_value(prm_obj, "dateRefusPoseLinky")),
    }
    columns.update(_extract_power_json(prm_obj, "puissanceSouscrite", "puissance_souscrite"))
    columns.update(_extract_power_json(prm_obj, "puissanceLimiteSoutirage", "puissance_limite_soutirage"))
    columns.update(_extract_power_json(prm_obj, "puissanceRaccordementSoutirage", "puissance_raccordement_soutirage"))
    columns.update(_extract_power_json(prm_obj, "puissanceRaccordementInjection", "puissance_raccordement_injection"))
    return columns


def _extract_csv_columns(csv_row: dict[str, str | None], headers: dict[str, str]) -> dict[str, str | None]:
    def h(*aliases: str) -> str | None:
        for alias in aliases:
            raw = headers.get(_normalize_header(alias))
            if raw is not None:
                return _csv_cell(csv_row, raw)
        return None

    return {
        "date_debut_situation_contractuelle": h(
            "Date debut situation contractuelle", "Date de debut situation contractuelle"
        ),
        "segment": h("Segment"),
        "etat_contractuel": h("Etat contractuel"),
        "formule_tarifaire_acheminement": h("Formule Tarifaire Acheminement", "Formule tarifaire acheminement"),
        "code_tarif_acheminement": h("Code Tarif Acheminement", "Code tarif acheminement"),
        "siret": h("SIRET"),
        "siren": h("SIREN"),
        "domaine_tension": h("Domaine Tension", "Domaine tension"),
        "tension_livraison": h("Tension Livraison", "Tension livraison"),
        "type_comptage": h("Type Comptage", "Type comptage"),
        "mode_releve": h("Mode Releve", "Mode releve", "Mode relève"),
        "media_comptage": h("Media Comptage", "Media comptage"),
        "periodicite_releve": h("Periodicite Releve", "Periodicite releve", "Périodicité relève"),
        "puissance_souscrite_valeur": h(
            "Puissance Souscrite Valeur", "Puissance souscrite valeur", "Puissance souscrite"
        ),
        "puissance_souscrite_unite": h("Puissance Souscrite Unite", "Puissance souscrite unite"),
        "puissance_limite_soutirage_valeur": h("Puissance Limite Soutirage Valeur"),
        "puissance_limite_soutirage_unite": h("Puissance Limite Soutirage Unite"),
        "puissance_raccordement_soutirage_valeur": h("Puissance Raccordement Soutirage Valeur"),
        "puissance_raccordement_soutirage_unite": h("Puissance Raccordement Soutirage Unite"),
        "puissance_raccordement_injection_valeur": h("Puissance Raccordement Injection Valeur"),
        "puissance_raccordement_injection_unite": h("Puissance Raccordement Injection Unite"),
        "type_injection": h("Type Injection"),
        "borne_fixe": h("Borne Fixe"),
        "refus_pose_linky": h("Refus de pose Linky"),
        "date_refus_pose_linky": h("Date refus de pose Linky"),
    }


def _select_latest_contractual_situation(value: Any, warnings: list[dict[str, str]]) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        warnings.append({"code": "ambiguous_contractual_situation", "reason": "situationsContractuelles_not_array"})
        return None
    dated: list[tuple[date, dict[str, Any]]] = []
    for item in value:
        if not isinstance(item, dict):
            warnings.append({"code": "ambiguous_contractual_situation", "reason": "item_not_object"})
            return None
        raw_date = item.get("dateDebut")
        if not isinstance(raw_date, str):
            warnings.append({"code": "ambiguous_contractual_situation", "reason": "missing_dateDebut"})
            return None
        try:
            dated.append((date.fromisoformat(raw_date[:10]), item))
        except ValueError:
            warnings.append({"code": "ambiguous_contractual_situation", "reason": "invalid_dateDebut"})
            return None
    if not dated:
        return None
    max_date = max(item[0] for item in dated)
    latest = [item for item_date, item in dated if item_date == max_date]
    if len(latest) != 1:
        warnings.append({"code": "ambiguous_contractual_situation", "reason": "tied_latest_dateDebut"})
        return None
    return latest[0]


def _contractual_situation_count(prm_obj: dict[str, Any]) -> int | None:
    value = prm_obj.get("situationsContractuelles")
    return len(value) if isinstance(value, list) else None


def _extract_power_json(prm_obj: dict[str, Any], source_key: str, target_prefix: str) -> dict[str, str | None]:
    value = _find_value(prm_obj, source_key)
    if isinstance(value, dict):
        return {
            f"{target_prefix}_valeur": _optional_str(value.get("valeur")),
            f"{target_prefix}_unite": _optional_str(value.get("unite")),
        }
    return {f"{target_prefix}_valeur": _optional_str(value), f"{target_prefix}_unite": None}


def _find_value(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _find_value(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_value(value, key)
            if found is not None:
                return found
    return None


def _first_str(obj: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = obj.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _csv_cell(row: dict[str, str | None], raw_name: str) -> str | None:
    value = row.get(raw_name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_header(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(without_accents.strip().lower().replace("_", " ").split())


_JSON_ALLOWED_TOP_LEVEL = {
    "idPrm",
    "donneesGenerales",
    "situationsContractuelles",
    "rattachements",
    "installationsProduction",
    "optionsContractuelles",
    "siret",
    "siren",
    "domaineTension",
    "tensionLivraison",
    "typeComptage",
    "modeReleve",
    "mediaComptage",
    "periodiciteReleve",
    "puissanceSouscrite",
    "puissanceLimiteSoutirage",
    "puissanceRaccordementSoutirage",
    "puissanceRaccordementInjection",
    "typeInjection",
    "borneFixe",
    "refusPoseLinky",
    "dateRefusPoseLinky",
}

_CSV_ALLOWED_RAW_HEADERS = {
    "PRM",
    "Segment",
    "Etat contractuel",
    "Formule Tarifaire Acheminement",
    "Code Tarif Acheminement",
    "SIRET",
    "SIREN",
    "Domaine Tension",
    "Tension Livraison",
    "Type Comptage",
    "Mode Releve",
    "Media Comptage",
    "Periodicite Releve",
    "Puissance Souscrite Valeur",
    "Puissance Souscrite Unite",
    "Puissance Limite Soutirage Valeur",
    "Puissance Limite Soutirage Unite",
    "Puissance Raccordement Soutirage Valeur",
    "Puissance Raccordement Soutirage Unite",
    "Puissance Raccordement Injection Valeur",
    "Puissance Raccordement Injection Unite",
    "Type Injection",
    "Refus de pose Linky",
    "Date refus de pose Linky",
    "Borne Fixe",
}


def _json_object_warnings(prm_obj: dict[str, Any], index: int) -> list[dict[str, str]]:
    warnings = []
    for key in prm_obj:
        if key not in _JSON_ALLOWED_TOP_LEVEL:
            warnings.append({"code": "unknown_json_field", "path": f"$[{index}].{key}"})
    return warnings
