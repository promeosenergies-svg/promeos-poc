"""Source-guard cross-stack PROMEOS Sol — chantier α (Vague C ét11bis).

Vérifie que les mappings/types partagés entre `backend/services/event_bus/types.py`
(Python) et `frontend/src/domain/events/eventTypes.js` (JS) restent
synchronisés mécaniquement. Drift silencieux = bug runtime garanti.

Audit Architecture P0 ét11bis : « SEVERITY_TO_CARD_TYPE risque P0 dès qu'un
détecteur émet une nouvelle severity ». Résolu ici par parsing croisé.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_TYPES = REPO_ROOT / "backend" / "services" / "event_bus" / "types.py"
FRONTEND_TYPES = REPO_ROOT / "frontend" / "src" / "domain" / "events" / "eventTypes.js"


# ── Helpers parsing ──────────────────────────────────────────────────


def _parse_python_dict(content: str, var_name: str) -> dict[str, str]:
    """Extrait un `dict[str, str]` Python (ex: SEVERITY_TO_CARD_TYPE)."""
    pattern = rf"{var_name}.*?=\s*\{{(.*?)\}}"
    match = re.search(pattern, content, re.DOTALL)
    if match is None:
        return {}
    body = match.group(1)
    pairs = re.findall(r"\"(\w+)\"\s*:\s*\"(\w+)\"", body)
    return dict(pairs)


def _parse_js_object(content: str, var_name: str) -> dict[str, str]:
    """Extrait `Object.freeze({...})` JS (ex: SEVERITY_TO_CARD_TYPE)."""
    pattern = rf"{var_name}\s*=\s*Object\.freeze\(\{{(.*?)\}}\)"
    match = re.search(pattern, content, re.DOTALL)
    if match is None:
        return {}
    body = match.group(1)
    pairs = re.findall(r"(\w+)\s*:\s*'(\w+)'", body)
    return dict(pairs)


def _parse_python_literal_list(content: str, type_alias: str) -> list[str]:
    """Extrait `Foo = Literal[...]` Python (ex: EventType, EventSeverity)."""
    pattern = rf"{type_alias}\s*=\s*Literal\[(.*?)\]"
    match = re.search(pattern, content, re.DOTALL)
    if match is None:
        return []
    body = match.group(1)
    # Capture chaque "literal_value" en ignorant les commentaires
    values = re.findall(r"\"([^\"]+)\"", body)
    return values


def _parse_js_object_freeze_array(content: str, var_name: str) -> list[str]:
    """Extrait `export const FOO = Object.freeze([...])` JS."""
    pattern = rf"{var_name}\s*=\s*Object\.freeze\(\[(.*?)\]\)"
    match = re.search(pattern, content, re.DOTALL)
    if match is None:
        return []
    body = match.group(1)
    values = re.findall(r"'([^']+)'", body)
    return values


# ── Tests synchronisation ────────────────────────────────────────────


@pytest.fixture
def backend_content():
    return BACKEND_TYPES.read_text(encoding="utf-8")


@pytest.fixture
def frontend_content():
    return FRONTEND_TYPES.read_text(encoding="utf-8")


def test_severity_to_card_type_in_sync(backend_content, frontend_content):
    """SEVERITY_TO_CARD_TYPE doit être identique côté backend et frontend."""
    backend_map = _parse_python_dict(backend_content, "SEVERITY_TO_CARD_TYPE")
    frontend_map = _parse_js_object(frontend_content, "SEVERITY_TO_CARD_TYPE")
    assert backend_map, "SEVERITY_TO_CARD_TYPE introuvable dans types.py"
    assert frontend_map, "SEVERITY_TO_CARD_TYPE introuvable dans eventTypes.js"
    assert backend_map == frontend_map, (
        f"Drift cross-stack détecté !\n"
        f"  backend: {backend_map}\n"
        f"  frontend: {frontend_map}\n"
        "Mettre à jour le mirror frontend/src/domain/events/eventTypes.js."
    )


def test_event_types_in_sync(backend_content, frontend_content):
    """Les 9 event_types doctrine §10 doivent être identiques côté Python+JS."""
    backend_types = set(_parse_python_literal_list(backend_content, "EventType"))
    frontend_types = set(_parse_js_object_freeze_array(frontend_content, "EVENT_TYPES"))
    assert backend_types, "EventType introuvable dans types.py"
    assert frontend_types, "EVENT_TYPES introuvable dans eventTypes.js"
    assert backend_types == frontend_types, (
        f"Drift event_types !\n  backend: {sorted(backend_types)}\n  frontend: {sorted(frontend_types)}"
    )


def test_event_severities_in_sync(backend_content, frontend_content):
    """4 severities doctrine §10 identiques cross-stack."""
    backend_sev = set(_parse_python_literal_list(backend_content, "EventSeverity"))
    frontend_sev = set(_parse_js_object_freeze_array(frontend_content, "EVENT_SEVERITIES"))
    assert backend_sev == frontend_sev


def test_event_units_in_sync(backend_content, frontend_content):
    """8 unités doctrine §10 identiques cross-stack."""
    backend_units = set(_parse_python_literal_list(backend_content, "EventUnit"))
    frontend_units = set(_parse_js_object_freeze_array(frontend_content, "EVENT_UNITS"))
    assert backend_units == frontend_units


def test_event_periods_in_sync(backend_content, frontend_content):
    """6 périodes doctrine §10 identiques cross-stack."""
    backend_periods = set(_parse_python_literal_list(backend_content, "EventPeriod"))
    frontend_periods = set(_parse_js_object_freeze_array(frontend_content, "EVENT_PERIODS"))
    assert backend_periods == frontend_periods


def test_event_source_systems_in_sync(backend_content, frontend_content):
    """9 systèmes source doctrine §10 identiques cross-stack."""
    backend_sys = set(_parse_python_literal_list(backend_content, "EventSourceSystem"))
    frontend_sys = set(_parse_js_object_freeze_array(frontend_content, "EVENT_SOURCE_SYSTEMS"))
    assert backend_sys == frontend_sys


def test_event_confidences_in_sync(backend_content, frontend_content):
    """3 niveaux confidence doctrine §7.1+§10 identiques cross-stack."""
    backend_conf = set(_parse_python_literal_list(backend_content, "EventConfidence"))
    frontend_conf = set(_parse_js_object_freeze_array(frontend_content, "EVENT_CONFIDENCES"))
    assert backend_conf == frontend_conf


def test_event_owner_roles_in_sync(backend_content, frontend_content):
    """5 owner roles doctrine §10 identiques cross-stack."""
    backend_roles = set(_parse_python_literal_list(backend_content, "EventOwnerRole"))
    frontend_roles = set(_parse_js_object_freeze_array(frontend_content, "EVENT_OWNER_ROLES"))
    assert backend_roles == frontend_roles
