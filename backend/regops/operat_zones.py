"""
Resolveur de zone climatique OPERAT depuis code postal / code INSEE / departement.

Source : backend/config/operat_zones_climatiques.json (RT 2012 + arrete methode OPERAT 10/04/2020).
Confidence : 🟡 — verification croisee Legifrance manuelle recommandee P1
(WebFetch bloque lors de l'extraction 2026-05-03).

Usage typique dans le backend :
    from backend.regops.operat_zones import resolve_zone_from_postal_code

    zone = resolve_zone_from_postal_code("75001")  # -> "H1b"
    zone = resolve_zone_from_postal_code("13001")  # -> "H3"
    zone = resolve_zone_from_postal_code("97110")  # -> "Guadeloupe"

Cf. operat_annexe_i_sous_categories.json pour l'usage (CVCi par zone × palier altitude).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

ZoneOperat = Literal[
    "H1a", "H1b", "H1c", "H2a", "H2b", "H2c", "H2d", "H3", "Guadeloupe", "Martinique", "Guyane", "Reunion", "Mayotte"
]

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "operat_zones_climatiques.json"


@lru_cache(maxsize=1)
def _load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _build_dept_to_zone_index() -> dict[str, ZoneOperat]:
    """Construit un index departement (str) -> zone OPERAT.

    Couvre 96 metropole (codes 01-95 sans 20, plus 2A/2B) + 5 DOM (971-976 sauf 975).
    """
    cfg = _load_config()
    index: dict[str, ZoneOperat] = {}

    # Metropole : H1a-H3
    for zone_id, zone_data in cfg["zones"].items():
        for dept in zone_data["departements"]:
            if dept in index:
                raise ValueError(f"Doublon detecte : departement {dept} present dans {index[dept]} et {zone_id}")
            index[dept] = zone_id  # type: ignore[assignment]

    # DOM : 5 zones propres
    dom_to_code = {
        "Guadeloupe": "971",
        "Martinique": "972",
        "Guyane": "973",
        "Reunion": "974",
        "Mayotte": "976",
    }
    # On accepte les DOM via leur code 3-chiffres ET via leur nom de zone (utilise par operat_annexe_i)
    for dom_name, dom_data in cfg["dom"].items():
        code = dom_to_code.get(dom_name, dom_data["code_insee_departement"])
        # zone_operat dans le JSON utilise "Réunion" (avec accent) cf. operat_annexe_i
        index[code] = dom_data["zone_operat"]

    return index


def resolve_zone_from_departement(code_departement: str) -> ZoneOperat | None:
    """Resout la zone OPERAT depuis un code departement.

    Args:
        code_departement: Code 2 caracteres (01, 02, ..., 95, 2A, 2B) ou 3 caracteres
                          DOM (971, 972, 973, 974, 976).

    Returns:
        Zone OPERAT (str) ou None si departement inconnu / hors perimetre.
    """
    if not code_departement:
        return None
    code = code_departement.strip().upper()
    # Normalisation : "1" -> "01", "9" -> "09"
    if len(code) == 1 and code.isdigit():
        code = "0" + code
    return _build_dept_to_zone_index().get(code)


def resolve_zone_from_postal_code(code_postal: str) -> ZoneOperat | None:
    """Resout la zone OPERAT depuis un code postal francais.

    Args:
        code_postal: Code postal 5 chiffres (ex. "75001", "13001", "20000", "97110").

    Returns:
        Zone OPERAT (str) ou None si code postal invalide / hors perimetre.

    Notes:
        - Metropole : 2 premiers chiffres = departement (sauf Corse 20xxx)
        - Corse : 200-201xx -> 2A (Corse-du-Sud), 202xx -> 2B (Haute-Corse)
        - DOM : 97x ou 98x -> 3 premiers chiffres = code departement DOM
            (97100-97190 = Guadeloupe / 97200-97290 = Martinique / 97300-97390 = Guyane /
             97400-97490 = Reunion / 97600-97690 = Mayotte ;
             97500-97590 = Saint-Pierre-et-Miquelon = HORS PERIMETRE OPERAT — return None)
    """
    if not code_postal:
        return None
    cp = code_postal.strip()
    if len(cp) != 5 or not cp.isdigit():
        return None

    # DOM
    if cp.startswith("97"):
        prefix3 = cp[:3]
        if prefix3 == "975":  # Saint-Pierre-et-Miquelon = hors OPERAT
            return None
        if prefix3 == "977":  # Saint-Barthelemy = hors OPERAT (COM)
            return None
        if prefix3 == "978":  # Saint-Martin = hors OPERAT (COM)
            return None
        return resolve_zone_from_departement(prefix3)

    # Corse
    if cp.startswith("20"):
        suffix3 = int(cp[2:])  # 000-999
        # Convention : 20000-20199 (Corse-du-Sud, principal Ajaccio) + 20200-20999 (Haute-Corse)
        # Reference : codes postaux La Poste — dept 2A va jusqu'a ~20190, 2B demarre a 20200+
        if suffix3 < 200:
            return resolve_zone_from_departement("2A")
        return resolve_zone_from_departement("2B")

    # Metropole standard
    return resolve_zone_from_departement(cp[:2])


def resolve_zone_from_insee_commune(code_insee: str) -> ZoneOperat | None:
    """Resout la zone OPERAT depuis un code INSEE commune (5 caracteres).

    Args:
        code_insee: Code INSEE 5 caracteres (ex. "75056" Paris, "13201" Marseille,
                    "2A004" Ajaccio, "97101" Basse-Terre).

    Returns:
        Zone OPERAT (str) ou None.
    """
    if not code_insee:
        return None
    code = code_insee.strip().upper()
    if len(code) != 5:
        return None

    # DOM (3 chiffres en prefix)
    if code[:2] == "97":
        return resolve_zone_from_departement(code[:3])

    # Corse (alphanumerique)
    if code[:2] in ("2A", "2B"):
        return resolve_zone_from_departement(code[:2])

    # Metropole numerique
    return resolve_zone_from_departement(code[:2])


def list_departements_for_zone(zone: ZoneOperat) -> list[str]:
    """Liste les departements (ou codes DOM) d'une zone OPERAT donnee."""
    cfg = _load_config()
    if zone in cfg["zones"]:
        return list(cfg["zones"][zone]["departements"])
    # DOM
    for dom_name, dom_data in cfg["dom"].items():
        if dom_data["zone_operat"] == zone:
            return [dom_data["code_insee_departement"]]
    return []


def all_zones() -> list[ZoneOperat]:
    """Retourne la liste des 13 zones OPERAT (8 metropole + 5 DOM)."""
    cfg = _load_config()
    return list(cfg["zones"].keys()) + [d["zone_operat"] for d in cfg["dom"].values()]


def zone_metadata(zone: ZoneOperat) -> dict | None:
    """Retourne les metadonnees d'une zone (description, regions, etc.)."""
    cfg = _load_config()
    if zone in cfg["zones"]:
        return cfg["zones"][zone]
    for dom_name, dom_data in cfg["dom"].items():
        if dom_data["zone_operat"] == zone:
            return dom_data
    return None
