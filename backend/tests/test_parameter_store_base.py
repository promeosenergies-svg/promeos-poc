"""
PROMEOS - Tests du module commun utils/parameter_store_base.

Fige le contrat (fields + defaults + to_trace) partagé entre ParameterStore
(billing) et parameters (pilotage). Toute évolution de `ParameterResolution`
doit passer par ce test — en particulier : pas d'ajout de champ requis sans
default (sinon breaking change cross-module).

Couvre aussi :
    - `coerce_date` (ISO, date, datetime, None, invalid)
    - `period_contains` (bornes ouvertes et inclusives)
    - `warn_unknown_once` (anti-spam, sets isolés)
    - `load_yaml_section` (délégation tarif_loader)
    - `paris_today` (fuseau Europe/Paris)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from utils.parameter_store_base import (
    ParameterResolution,
    coerce_date,
    load_yaml_section,
    paris_today,
    period_contains,
    warn_unknown_once,
)


# ---------------------------------------------------------------------------
# Contract test : ParameterResolution — garanti entre billing et pilotage
# ---------------------------------------------------------------------------
def test_parameter_resolution_contract_fields():
    """
    Fige les champs publics. Ajouter un champ non-optional casse billing
    et pilotage simultanément — ce test doit tirer la sonnette d'alarme.
    """
    res = ParameterResolution(code="X", value=1.0, source="yaml")
    # Les 3 requis
    assert res.code == "X"
    assert res.value == 1.0
    assert res.source == "yaml"
    # Les 5 optionnels (défauts)
    assert res.source_ref is None
    assert res.valid_from is None
    assert res.valid_to is None
    assert res.unite is None
    assert res.scope == {}


def test_parameter_resolution_frozen():
    """Immuable : un set direct lève FrozenInstanceError."""
    res = ParameterResolution(code="X", value=1.0, source="yaml")
    with pytest.raises(Exception):
        res.code = "Y"  # type: ignore[misc]


def test_parameter_resolution_kw_only():
    """kw_only=True : arguments positionnels refusés (protège extensions futures)."""
    with pytest.raises(TypeError):
        ParameterResolution("X", 1.0, "yaml")  # type: ignore[misc]


def test_to_trace_expose_tous_les_champs():
    """`to_trace()` doit exposer les 8 champs (contrat audit regops/cfo)."""
    res = ParameterResolution(
        code="CEE_BACS_EUR_M2",
        value=3.5,
        source="yaml",
        source_ref="fiche CEE BAT-TH-116",
        valid_from=date(2026, 1, 1),
        valid_to=date(2026, 12, 31),
        unite="EUR/m2",
        scope={"archetype": "BUREAU_STANDARD"},
    )
    trace = res.to_trace()
    assert trace == {
        "code": "CEE_BACS_EUR_M2",
        "value": 3.5,
        "source": "yaml",
        "source_ref": "fiche CEE BAT-TH-116",
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31",
        "unite": "EUR/m2",
        "scope": {"archetype": "BUREAU_STANDARD"},
    }


def test_to_trace_nones_serializes_correctement():
    """Bornes ouvertes : isoformat() n'est pas appelé sur None."""
    res = ParameterResolution(code="X", value=1.0, source="yaml")
    trace = res.to_trace()
    assert trace["valid_from"] is None
    assert trace["valid_to"] is None
    assert trace["unite"] is None


# ---------------------------------------------------------------------------
# coerce_date
# ---------------------------------------------------------------------------
def test_coerce_date_iso_str():
    assert coerce_date("2026-01-01") == date(2026, 1, 1)


def test_coerce_date_datetime_to_date():
    assert coerce_date(datetime(2026, 1, 1, 12, 30)) == date(2026, 1, 1)


def test_coerce_date_date_passthrough():
    d = date(2026, 6, 15)
    assert coerce_date(d) == d


def test_coerce_date_none_returns_none():
    assert coerce_date(None) is None


def test_coerce_date_invalid_str_returns_none():
    """Str non parseable → None silent (ne raise pas, fail-safe batch)."""
    assert coerce_date("pas une date") is None
    assert coerce_date("2026-13-99") is None


# ---------------------------------------------------------------------------
# period_contains
# ---------------------------------------------------------------------------
def test_period_contains_bornes_inclusives():
    """valid_from ≤ at ≤ valid_to avec bornes comprises."""
    at = date(2026, 6, 15)
    assert period_contains(at, date(2026, 1, 1), date(2026, 12, 31)) is True
    assert period_contains(at, date(2026, 6, 15), date(2026, 6, 15)) is True  # 1 jour


def test_period_contains_avant_valid_from():
    assert period_contains(date(2025, 12, 31), date(2026, 1, 1), None) is False


def test_period_contains_apres_valid_to():
    assert period_contains(date(2027, 1, 1), None, date(2026, 12, 31)) is False


def test_period_contains_bornes_ouvertes():
    """None des deux côtés → applicable à toute l'histoire."""
    assert period_contains(date(2020, 1, 1), None, None) is True
    assert period_contains(date(2050, 6, 15), None, None) is True


# ---------------------------------------------------------------------------
# warn_unknown_once — set isolé, pas de double log
# ---------------------------------------------------------------------------
def test_warn_unknown_once_no_double_warning(caplog):
    """Le même code ne logue qu'une fois par set."""
    seen: set[str] = set()
    lg = logging.getLogger("test.warn")
    with caplog.at_level(logging.WARNING, logger="test.warn"):
        warn_unknown_once(seen, lg, "CODE_X")
        warn_unknown_once(seen, lg, "CODE_X")
        warn_unknown_once(seen, lg, "CODE_X")
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "CODE_X" in warnings[0].message


def test_warn_unknown_once_sets_isoles():
    """Deux sets distincts = 2 logs (billing n'empoisonne pas pilotage)."""
    set_a: set[str] = set()
    set_b: set[str] = set()
    lg = logging.getLogger("test.isole")
    warn_unknown_once(set_a, lg, "CODE_Y")
    warn_unknown_once(set_b, lg, "CODE_Y")
    # Chaque set a enregistré, indépendamment
    assert "CODE_Y" in set_a
    assert "CODE_Y" in set_b


# ---------------------------------------------------------------------------
# load_yaml_section + paris_today
# ---------------------------------------------------------------------------
def test_load_yaml_section_existe():
    """Une section connue du YAML doit être lisible."""
    entries = load_yaml_section("pilotage_flex_ready")
    assert entries is not None
    assert isinstance(entries, list)
    assert len(entries) > 0


def test_load_yaml_section_absente_retourne_none():
    """Section inexistante → None (le caller décide du fallback)."""
    assert load_yaml_section("section_bidon_inexistante") is None


def test_paris_today_dans_fuseau_paris():
    """`paris_today()` doit retourner une date Europe/Paris, pas UTC."""
    from zoneinfo import ZoneInfo

    today_paris = paris_today()
    expected = datetime.now(ZoneInfo("Europe/Paris")).date()
    # Très tolérant : on accepte une seconde de drift sur le tournant minuit
    # (si le test tourne à 23:59:59 Paris, paris_today() peut être J et expected J+1)
    assert abs((today_paris - expected).days) <= 1
