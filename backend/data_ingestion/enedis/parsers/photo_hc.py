"""PROMEOS — Parser fichier PHOTO HC reprogrammation Enedis.

Parse les fichiers CSV PHOTO transmis par Enedis dans le cadre du chantier
de reprogrammation des heures creuses TURPE 7.

3 types de fichiers :
  - PHOTO M-6 : prévision de reprogrammation (date prévue, code HC cible)
  - PHOTO M-2 : confirmation de reprogrammation (date confirmée)
  - CR-M      : compte-rendu de téléopération (date effective, statut)

Format CSV Phase 1 (non saisonnalisé) :
  PRM;DATE_PREVUE;CODE_HC_ACTUEL;LIB_HC_ACTUEL;CODE_HC_CIBLE;LIB_HC_CIBLE;STATUT

Format CSV Phase 2 (saisonnalisé, colonnes dédoublées SH/SB) :
  PRM;DATE_PREVUE;CODE_HC_ACTUEL;LIB_HC_ACTUEL;
  CODE_HC_CIBLE_SH;LIB_HC_CIBLE_SH;CODE_HC_CIBLE_SB;LIB_HC_CIBLE_SB;STATUT

Encodage : UTF-8 avec BOM optionnel.
Séparateur : point-virgule (;).
Première ligne : en-tête.

Sources :
  - Enedis spécification PHOTO HC v2.1 (2026)
  - CRE délibération n°2025-78 + n°2026-33
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PhotoType(str, Enum):
    """Type de fichier PHOTO HC."""

    M6 = "M-6"  # Prévision (6 mois avant)
    M2 = "M-2"  # Confirmation (2 mois avant)
    CRM = "CR-M"  # Compte-rendu téléopération


class PhotoParseError(Exception):
    """Raised when CSV is structurally invalid for PHOTO HC format."""


@dataclass
class ParsedPhotoRow:
    """One PRM row from a PHOTO HC file."""

    prm: str  # PRM 14 chiffres
    date_prevue: Optional[str] = None  # YYYY-MM-DD
    date_effective: Optional[str] = None  # YYYY-MM-DD (CR-M uniquement)

    # HC actuel
    code_hc_actuel: Optional[str] = None
    libelle_hc_actuel: Optional[str] = None

    # HC cible — Phase 1 (non saisonnalisé)
    code_hc_cible: Optional[str] = None
    libelle_hc_cible: Optional[str] = None

    # HC cible — Phase 2 (saisonnalisé, dédoublé SH/SB)
    code_hc_cible_sh: Optional[str] = None  # Saison Haute (hiver)
    libelle_hc_cible_sh: Optional[str] = None
    code_hc_cible_sb: Optional[str] = None  # Saison Basse (été)
    libelle_hc_cible_sb: Optional[str] = None

    # Statut (CR-M)
    statut: Optional[str] = None  # TRAITE, ABANDON, EN_COURS

    @property
    def is_seasonal(self) -> bool:
        """True si le fichier contient des plages saisonnalisées."""
        return bool(self.code_hc_cible_sh or self.code_hc_cible_sb)


@dataclass
class ParsedPhotoFile:
    """Complete parse result for one PHOTO HC file."""

    photo_type: PhotoType
    headers: list[str]
    rows: list[ParsedPhotoRow] = field(default_factory=list)
    is_phase2: bool = False  # True si colonnes SH/SB détectées

    @property
    def total_prms(self) -> int:
        return len(self.rows)

    @property
    def prm_list(self) -> list[str]:
        return [r.prm for r in self.rows]


# ─── Mapping colonnes ──────────────────────────────────────────────────────

# Phase 1 headers (normalisés en minuscules)
_PHASE1_FIELDS = {
    "prm",
    "date_prevue",
    "code_hc_actuel",
    "lib_hc_actuel",
    "code_hc_cible",
    "lib_hc_cible",
    "statut",
}

# Phase 2 headers additionnels (saisonnalisé)
_PHASE2_FIELDS = {
    "code_hc_cible_sh",
    "lib_hc_cible_sh",
    "code_hc_cible_sb",
    "lib_hc_cible_sb",
}

# CR-M additionnel
_CRM_FIELDS = {"date_effective"}

# Mapping alias → champ canonique (gère les variantes Enedis)
_ALIASES = {
    "id_prm": "prm",
    "pdl": "prm",
    "date_reprog_prevue": "date_prevue",
    "date_reprog_effective": "date_effective",
    "hc_actuel": "code_hc_actuel",
    "hc_cible": "code_hc_cible",
    "libelle_hc_actuel": "lib_hc_actuel",
    "libelle_hc_cible": "lib_hc_cible",
    "hc_cible_hiver": "code_hc_cible_sh",
    "hc_cible_ete": "code_hc_cible_sb",
    "lib_hc_cible_hiver": "lib_hc_cible_sh",
    "lib_hc_cible_ete": "lib_hc_cible_sb",
    "resultat": "statut",
    "status": "statut",
}


def _normalize_header(raw: str) -> str:
    """Normalise un nom de colonne CSV."""
    h = raw.strip().lower().replace(" ", "_").replace("-", "_")
    return _ALIASES.get(h, h)


def _detect_photo_type(headers: list[str], filename: str = "") -> PhotoType:
    """Détecte le type de fichier PHOTO depuis les colonnes et le nom."""
    fname = filename.lower()
    has_effective = "date_effective" in headers
    if "cr" in fname or has_effective:
        return PhotoType.CRM
    if "m2" in fname or "m_2" in fname:
        return PhotoType.M2
    return PhotoType.M6


# ─── Parser principal ──────────────────────────────────────────────────────


def parse_photo_hc(
    csv_content: str | bytes,
    filename: str = "",
) -> ParsedPhotoFile:
    """Parse a PHOTO HC CSV file.

    Args:
        csv_content: CSV content (str or UTF-8 bytes).
        filename: Original filename (used for type detection).

    Returns:
        ParsedPhotoFile with all PRM rows.

    Raises:
        PhotoParseError: CSV structure invalid (missing PRM column, etc.)
    """
    if isinstance(csv_content, bytes):
        # Handle BOM
        csv_content = csv_content.decode("utf-8-sig")

    reader = csv.reader(io.StringIO(csv_content), delimiter=";")

    # Parse header
    try:
        raw_headers = next(reader)
    except StopIteration:
        raise PhotoParseError("Empty CSV file")

    headers = [_normalize_header(h) for h in raw_headers]

    if "prm" not in headers:
        raise PhotoParseError(f"Missing PRM column. Found headers: {raw_headers}")

    # Detect phase 2 (seasonal)
    is_phase2 = bool(set(headers) & _PHASE2_FIELDS)

    # Detect photo type
    photo_type = _detect_photo_type(headers, filename)

    # Build column index
    col_idx = {h: i for i, h in enumerate(headers)}

    def _get(row: list[str], field: str) -> Optional[str]:
        idx = col_idx.get(field)
        if idx is not None and idx < len(row):
            val = row[idx].strip()
            return val if val else None
        return None

    # Parse rows
    rows = []
    for line_num, row in enumerate(reader, start=2):
        if not row or all(c.strip() == "" for c in row):
            continue  # Skip empty lines

        prm = _get(row, "prm")
        if not prm:
            continue  # Skip rows without PRM

        # Validate PRM format (14 digits)
        prm_clean = prm.replace(" ", "")
        if not prm_clean.isdigit() or len(prm_clean) != 14:
            continue  # Skip invalid PRMs silently

        parsed = ParsedPhotoRow(
            prm=prm_clean,
            date_prevue=_get(row, "date_prevue"),
            date_effective=_get(row, "date_effective"),
            code_hc_actuel=_get(row, "code_hc_actuel"),
            libelle_hc_actuel=_get(row, "lib_hc_actuel"),
            code_hc_cible=_get(row, "code_hc_cible"),
            libelle_hc_cible=_get(row, "lib_hc_cible"),
            code_hc_cible_sh=_get(row, "code_hc_cible_sh"),
            libelle_hc_cible_sh=_get(row, "lib_hc_cible_sh"),
            code_hc_cible_sb=_get(row, "code_hc_cible_sb"),
            libelle_hc_cible_sb=_get(row, "lib_hc_cible_sb"),
            statut=_get(row, "statut"),
        )
        rows.append(parsed)

    return ParsedPhotoFile(
        photo_type=photo_type,
        headers=headers,
        rows=rows,
        is_phase2=is_phase2,
    )
