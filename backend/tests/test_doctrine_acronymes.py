"""Source-guard : YAML acronymes_doctrine couvre les acronymes critiques
de la doctrine v1.1 §6.3.

Sprint Grammaire v1 Phase 1.1 (2026-05-09).
"""

from pathlib import Path

import yaml

YAML_PATH = Path(__file__).resolve().parents[1] / "config" / "acronymes_doctrine.yaml"

# Acronymes critiques obligatoires (doctrine §6.3 anti-pattern "acronymes bruts")
CRITICAL_ACRONYMS = [
    "TURPE",
    "DT",
    "BACS",
    "APER",
    "OPERAT",
    "ARENH",
    "VNU",
    "CSPE",
    "CTA",
    "CEE",
    "NEBCO",
    "RTE",
    "CRE",
    "ADEME",
]

# Champs requis sur chaque entrée acronyme
REQUIRED_FIELDS = ["short", "long", "narrative", "source", "doctrine_ref"]


def _load() -> dict:
    with open(YAML_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_yaml_loadable():
    """Le YAML doit être parsable et contenir les clés de structure minimales."""
    data = _load()
    assert "acronymes" in data, "Clé 'acronymes' manquante dans le YAML"
    assert isinstance(data["acronymes"], dict), "'acronymes' doit être un dict"
    assert "version" in data, "Clé 'version' manquante — versionning requis"
    assert "description" in data, "Clé 'description' manquante"


def test_version_format():
    """La version doit respecter le format YYYY.MM.N."""
    data = _load()
    version = data["version"]
    assert isinstance(version, str), "version doit être une string"
    parts = version.split(".")
    assert len(parts) == 3, f"Format version attendu YYYY.MM.N — obtenu : {version}"


def test_critical_acronyms_present():
    """Chaque acronyme critique doctrine §6.3 doit être dans le dictionnaire."""
    data = _load()
    keys = data["acronymes"].keys()
    missing = [acr for acr in CRITICAL_ACRONYMS if acr not in keys]
    assert not missing, f"Acronymes critiques manquants — viole doctrine §6.3 : {missing}"


def test_each_entry_has_required_fields():
    """Chaque entrée acronyme doit avoir tous les champs obligatoires."""
    data = _load()
    errors = []
    for key, entry in data["acronymes"].items():
        if not isinstance(entry, dict):
            errors.append(f"'{key}': l'entrée doit être un dict, obtenu {type(entry)}")
            continue
        for field in REQUIRED_FIELDS:
            if field not in entry:
                errors.append(f"'{key}' : champ '{field}' manquant")
    assert not errors, "Entrées incomplètes :\n" + "\n".join(errors)


def test_no_empty_narrative():
    """Le champ 'narrative' ne doit pas être vide (c'est lui qui remplace l'acronyme en titre)."""
    data = _load()
    errors = []
    for key, entry in data["acronymes"].items():
        if isinstance(entry, dict):
            narrative = entry.get("narrative", "")
            if not narrative or not narrative.strip():
                errors.append(f"'{key}' : narrative vide")
    assert not errors, "Narratives vides détectées :\n" + "\n".join(errors)


def test_no_empty_source():
    """Le champ 'source' doit être traçable (non vide)."""
    data = _load()
    errors = []
    for key, entry in data["acronymes"].items():
        if isinstance(entry, dict):
            source = entry.get("source", "")
            if not source or not source.strip():
                errors.append(f"'{key}' : source vide — traçabilité requise")
    assert not errors, "Sources vides détectées :\n" + "\n".join(errors)


def test_minimum_acronym_count():
    """Le dictionnaire doit contenir au minimum 40 acronymes (convergence 3 sources)."""
    data = _load()
    count = len(data["acronymes"])
    assert count >= 40, (
        f"Dictionnaire trop petit : {count} acronymes — minimum 40 requis "
        f"(convergence acronyms.py + acronyms.js + glossary.js)"
    )


def test_doctrine_ref_format():
    """Le champ doctrine_ref doit référencer la doctrine v1.1 §6.3."""
    data = _load()
    errors = []
    for key, entry in data["acronymes"].items():
        if isinstance(entry, dict):
            ref = entry.get("doctrine_ref", "")
            if "doctrine_sol_v1_1" not in ref:
                errors.append(f"'{key}' : doctrine_ref '{ref}' ne référence pas doctrine_sol_v1_1")
    assert not errors, "doctrine_ref incorrects :\n" + "\n".join(errors)
