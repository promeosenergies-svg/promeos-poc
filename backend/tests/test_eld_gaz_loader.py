"""
PROMEOS — Sprint C-3 Phase 3.6 : Tests eld_gaz_loader.

Vérifie le SoT YAML `eld_gaz_referentiel.yaml` (21 ELD France) + service loader :
- Structure YAML valide + schéma cohérent
- Cache `@lru_cache(maxsize=1)` actif + reload_* fonctionnel
- Helpers typés : get_eld_by_code, is_grdf, is_eld_locale, list_eld_codes
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Structure YAML ──────────────────────────────────────────────────────────


def test_load_yaml_returns_dict_with_eld_key():
    from config.eld_gaz_loader import load_eld_gaz

    data = load_eld_gaz()
    assert isinstance(data, dict)
    assert "eld" in data
    assert isinstance(data["eld"], dict)


def test_yaml_has_at_least_15_eld():
    """Volumétrie cible Sprint C-3 Phase 3.6 ≥ 15 ELD (cible 21)."""
    from config.eld_gaz_loader import list_eld_codes

    codes = list_eld_codes()
    assert len(codes) >= 15, f"Trop peu d'ELD: {len(codes)} (attendu ≥15)"


def test_grdf_is_in_eld_list():
    """GRDF (national) est obligatoirement présent."""
    from config.eld_gaz_loader import list_eld_codes

    assert "GRDF" in list_eld_codes()


# ─── API publique ────────────────────────────────────────────────────────────


def test_get_eld_by_code_grdf_returns_dict():
    from config.eld_gaz_loader import get_eld_by_code

    grdf = get_eld_by_code("GRDF")
    assert grdf is not None
    assert grdf["code"] == "GRDF"
    assert grdf["type"] == "GRD_NATIONAL"
    assert "label" in grdf
    assert "perimetre" in grdf
    assert "site_web" in grdf


def test_get_eld_by_code_unknown_returns_none():
    from config.eld_gaz_loader import get_eld_by_code

    assert get_eld_by_code("UNKNOWN_ELD_XYZ") is None
    assert get_eld_by_code("") is None
    assert get_eld_by_code(None) is None


def test_get_eld_by_code_regaz_local_eld():
    from config.eld_gaz_loader import get_eld_by_code

    regaz = get_eld_by_code("REGAZ")
    assert regaz is not None
    assert regaz["type"] == "ELD_LOCALE"


# ─── Helpers typés ───────────────────────────────────────────────────────────


def test_is_grdf_returns_true_for_grdf_only():
    from config.eld_gaz_loader import is_grdf

    assert is_grdf("GRDF") is True
    assert is_grdf("REGAZ") is False
    assert is_grdf("ENEDIS") is False  # élec, hors périmètre
    assert is_grdf(None) is False
    assert is_grdf("") is False


def test_is_eld_locale_returns_true_for_regaz_false_for_grdf():
    from config.eld_gaz_loader import is_eld_locale

    assert is_eld_locale("REGAZ") is True
    assert is_eld_locale("GREENALP") is True
    assert is_eld_locale("GRDF") is False  # GRD_NATIONAL pas ELD_LOCALE
    assert is_eld_locale("UNKNOWN") is False
    assert is_eld_locale(None) is False


def test_is_known_eld_returns_correct():
    from config.eld_gaz_loader import is_known_eld

    assert is_known_eld("GRDF") is True
    assert is_known_eld("REGAZ") is True
    assert is_known_eld("ENEDIS") is False  # élec, hors périmètre ELD gaz
    assert is_known_eld(None) is False


def test_get_eld_count_by_type():
    from config.eld_gaz_loader import get_eld_count_by_type

    counts = get_eld_count_by_type()
    assert "GRD_NATIONAL" in counts
    assert "ELD_LOCALE" in counts
    assert counts["GRD_NATIONAL"] >= 1  # au moins GRDF
    assert counts["ELD_LOCALE"] >= 10  # au moins 10 ELD locales (cible 20)


# ─── Cache LRU ───────────────────────────────────────────────────────────────


def test_lru_cache_returns_same_dict_object():
    """2 appels successifs → même objet en mémoire (cache hit)."""
    from config.eld_gaz_loader import load_eld_gaz, reload_eld_gaz

    reload_eld_gaz()
    d1 = load_eld_gaz()
    d2 = load_eld_gaz()
    assert d1 is d2, "Cache LRU non actif"


def test_reload_clears_cache():
    """reload_eld_gaz() invalide cache → nouveau dict object."""
    from config.eld_gaz_loader import load_eld_gaz, reload_eld_gaz

    d1 = load_eld_gaz()
    d2 = reload_eld_gaz()
    assert d1 is not d2
