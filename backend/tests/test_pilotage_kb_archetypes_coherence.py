"""
PROMEOS - Tests coherence KB archetypes vs code canonique pilotage.

Previent la drift : tout archetype utilise par le code
(`services.pilotage.constants.ARCHETYPE_CALIBRATION_2024`) doit avoir un
fichier YAML KB correspondant dans `docs/kb/items/usages/ARCHETYPE-*.yaml`,
et reciproquement (modulo une whitelist de sous-archetypes d'enrichissement).

Source de calibrage : Barometre Flex 2026 RTE / Enedis / GIMELEC (avril 2026).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pilotage.constants import (  # noqa: E402
    ARCHETYPE_CALIBRATION_2024,
    NAF_PREFIX_TO_PILOTAGE_ARCHETYPE,
)


# Racine des YAML KB archetypes. On remonte depuis backend/tests -> repo root.
KB_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "kb" / "items" / "usages"

# Sous-archetypes enrichissements (pas dans CALIBRATION_2024 mais legitimes).
# Ces fichiers documentent des sous-cas plus precis sans etre des cles
# canoniques du scoring pilotage. Ils doivent rester whitelistes explicitement
# pour eviter tout ajout silencieux d'archetype hors perimetre Barometre 2026.
KB_SUBARCHETYPES_ALLOWED: frozenset[str] = frozenset(
    {
        "HOPITAL_STANDARD",  # sous-cas plus precis de SANTE (hopitaux multi-services)
        "RESTAURATION_SERVICE",  # sous-cas plus precis de HOTELLERIE (restaurants / services collectifs)
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_kb_archetype_codes() -> set[str]:
    """Liste les codes archetypes depuis les fichiers KB (ARCHETYPE-<CODE>.yaml)."""
    if not KB_DIR.exists():
        return set()
    codes: set[str] = set()
    for p in KB_DIR.glob("ARCHETYPE-*.yaml"):
        # "ARCHETYPE-BUREAU_STANDARD.yaml" -> "BUREAU_STANDARD"
        codes.add(p.stem.replace("ARCHETYPE-", ""))
    return codes


def _load_kb_archetype(code: str) -> dict:
    """Charge le YAML KB pour un archetype, assertion explicite si absent."""
    p = KB_DIR / f"ARCHETYPE-{code}.yaml"
    assert p.exists(), (
        f"YAML KB manquant : {p}. "
        f"Chaque archetype canonique doit avoir son fichier `docs/kb/items/usages/ARCHETYPE-<CODE>.yaml`."
    )
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert isinstance(data, dict), f"{code}: YAML racine n'est pas un dict"
    return data


def _normalize_naf_prefix(naf: str) -> str:
    """Normalise un code NAF YAML ('47.11' ou '4711') en prefixe 4 chars comme dans le mapping Python."""
    return str(naf).replace(".", "").replace(" ", "")[:4]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_tous_les_archetypes_code_ont_yaml_kb():
    """Chaque cle de ARCHETYPE_CALIBRATION_2024 doit avoir un YAML KB correspondant."""
    kb_codes = _list_kb_archetype_codes()
    missing = set(ARCHETYPE_CALIBRATION_2024.keys()) - kb_codes
    assert not missing, (
        f"Archetypes code sans YAML KB : {sorted(missing)}. "
        f"Creer `docs/kb/items/usages/ARCHETYPE-<CODE>.yaml` pour chacun."
    )


def test_tous_les_yaml_kb_sont_dans_code_canonique():
    """Chaque YAML KB doit correspondre a un archetype canonique ou etre explicitement whiteliste."""
    kb_codes = _list_kb_archetype_codes()
    canonical = set(ARCHETYPE_CALIBRATION_2024.keys())
    extras = kb_codes - canonical - KB_SUBARCHETYPES_ALLOWED
    assert not extras, (
        f"YAML KB orphelins (ni dans code canonique, ni dans whitelist sous-archetypes) : {sorted(extras)}. "
        f"Soit ajouter au code (services/pilotage/constants.py), soit whitelister dans KB_SUBARCHETYPES_ALLOWED."
    )


@pytest.mark.parametrize("code", sorted(ARCHETYPE_CALIBRATION_2024.keys()))
def test_yaml_kb_format_structurel(code):
    """Structure obligatoire du YAML KB : champs top-level, coherence id/filename/scope.archetype."""
    data = _load_kb_archetype(code)
    required_keys = (
        "id",
        "type",
        "domain",
        "title",
        "summary",
        "tags",
        "scope",
        "content_md",
        "sources",
        "provenance",
        "updated_at",
        "confidence",
        "status",
        "priority",
    )
    for key in required_keys:
        assert key in data, f"{code}: champ '{key}' manquant dans YAML KB"

    assert data["type"] == "knowledge", f"{code}: type doit etre 'knowledge'"
    assert data["domain"] == "usages", f"{code}: domain doit etre 'usages'"

    assert isinstance(data["scope"], dict), f"{code}: scope doit etre un dict"
    assert data["scope"].get("archetype") == code, (
        f"{code}: scope.archetype ({data['scope'].get('archetype')!r}) doit etre egal au suffixe du filename ({code!r})"
    )
    assert data["scope"].get("naf_codes"), f"{code}: scope.naf_codes vide ou absent"

    assert isinstance(data["tags"], dict), f"{code}: tags doit etre un dict"
    assert data["tags"].get("energy"), f"{code}: tags.energy vide ou absent"


@pytest.mark.parametrize("code", sorted(ARCHETYPE_CALIBRATION_2024.keys()))
def test_naf_codes_yaml_alignes_avec_code(code):
    """Au moins 1 code NAF du YAML doit avoir son equivalent dans NAF_PREFIX_TO_PILOTAGE_ARCHETYPE."""
    data = _load_kb_archetype(code)
    yaml_naf = {_normalize_naf_prefix(c) for c in data["scope"]["naf_codes"]}
    code_naf_for_archetype = {prefix for prefix, arch in NAF_PREFIX_TO_PILOTAGE_ARCHETYPE.items() if arch == code}
    shared = yaml_naf & code_naf_for_archetype
    assert shared, (
        f"{code}: aucun NAF partage entre YAML ({sorted(yaml_naf)}) "
        f"et code Python NAF_PREFIX_TO_PILOTAGE_ARCHETYPE ({sorted(code_naf_for_archetype)}). "
        f"Le YAML peut enrichir la liste Python mais au moins 1 code doit etre commun."
    )


@pytest.mark.parametrize("code", sorted(ARCHETYPE_CALIBRATION_2024.keys()))
def test_content_md_mentionne_barometre_flex_2026(code):
    """Le content_md doit citer 'Barometre Flex 2026' (source primaire calibrage)."""
    data = _load_kb_archetype(code)
    content = str(data.get("content_md", ""))
    # Tolere les deux orthographes (accentuee et non-accentuee).
    has_ref = ("Baromètre Flex 2026" in content) or ("Barometre Flex 2026" in content)
    assert has_ref, (
        f"{code}: content_md ne cite pas 'Barometre Flex 2026' (source primaire de calibrage). "
        f"Tout archetype canonique doit tracer la source officielle."
    )


@pytest.mark.parametrize("code", sorted(ARCHETYPE_CALIBRATION_2024.keys()))
def test_wording_doctrine_content_md(code):
    """Doctrine wording : pas d'usage 'NEBCO' standalone (brique technique, pas terme archetype)."""
    data = _load_kb_archetype(code)
    content = str(data.get("content_md", ""))
    # Check simple : le token "NEBCO" ne doit pas apparaitre nu dans la description
    # d'archetype (markdown rendu cote doc). Les marques "Flex Ready" et les
    # references "Barometre Flex 2026" restent autorisees (mentions explicites).
    # Si on veut parler de NEBCO, le faire dans les briques dediees, pas dans
    # les archetypes.
    assert "NEBCO" not in content, (
        f"{code}: content_md contient 'NEBCO' nu. "
        f"NEBCO est une brique technique, pas un terme d'archetype. "
        f"Utiliser 'flexibilite' ou 'effacement' dans le wording archetype."
    )
