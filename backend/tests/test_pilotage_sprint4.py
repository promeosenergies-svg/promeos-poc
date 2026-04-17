"""
PROMEOS - Tests Sprint 4 polish pilotage.

Couvre :
    1. NAF resolver : archetype_from_naf sur les 8 segments
    2. resolve_pilotage_archetype cascade (override > NAF > signaux > fallback)
    3. detect_archetype : heuristique hotellerie biaisee RETIREE
    4. Memo portefeuille_scoring : 1 lookup par archetype distinct (pas 2xN)
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from services.pilotage.constants import archetype_from_naf
from services.pilotage.portefeuille_scoring import (
    _estimate_gain_annuel_eur,
    compute_portefeuille_scoring,
)
from services.pilotage.usage_detector import (
    detect_archetype,
    resolve_pilotage_archetype,
)


# ---------------------------------------------------------------------------
# Test 1 : mapping NAF -> 8 archetypes pilotage
# ---------------------------------------------------------------------------
def test_archetype_from_naf_8_segments():
    """Les 8 archetypes canoniques sont tous couverts par au moins un prefix NAF."""
    # Echantillon couvrant les 8 segments
    cas = [
        ("6820Z", "BUREAU_STANDARD"),
        ("47.11F", "COMMERCE_ALIMENTAIRE"),  # grande surface alimentaire
        ("4771Z", "COMMERCE_SPECIALISE"),
        ("1013B", "LOGISTIQUE_FRIGO"),
        ("8520Z", "ENSEIGNEMENT"),
        ("8610Z", "SANTE"),
        ("5510Z", "HOTELLERIE"),
        ("2511Z", "INDUSTRIE_LEGERE"),
    ]
    for naf, expected in cas:
        assert archetype_from_naf(naf) == expected, f"{naf} should map to {expected}"


def test_archetype_from_naf_unknown_returns_none():
    """NAF non couvert -> None (le caller decide du fallback)."""
    assert archetype_from_naf("9999Z") is None
    assert archetype_from_naf("") is None
    assert archetype_from_naf(None) is None


def test_archetype_from_naf_format_flexible():
    """Formats DD.DDC et DDDDC tous deux supportes."""
    assert archetype_from_naf("47.11F") == "COMMERCE_ALIMENTAIRE"
    assert archetype_from_naf("4711F") == "COMMERCE_ALIMENTAIRE"
    assert archetype_from_naf("47 11 F") == "COMMERCE_ALIMENTAIRE"


# ---------------------------------------------------------------------------
# Test 2 : resolve_pilotage_archetype cascade
# ---------------------------------------------------------------------------
def test_resolve_cascade_override_archetype_code():
    """Priorite 1 : site.archetype_code direct bat tout le reste."""
    site = MagicMock(archetype_code="SANTE", naf_code="5510Z", id=1, nom="test")
    db = MagicMock()
    assert resolve_pilotage_archetype(site, db) == "SANTE"


def test_resolve_cascade_naf_when_no_archetype_code():
    """Priorite 2 : NAF mappe si pas d'archetype direct."""
    site = MagicMock(archetype_code=None, naf_code="8610Z", id=1, nom="CHU", portefeuille_id=None)
    db = MagicMock()
    with patch("utils.naf_resolver.resolve_naf_code", return_value="8610Z"):
        assert resolve_pilotage_archetype(site, db) == "SANTE"


def test_resolve_cascade_signals_when_no_naf():
    """Priorite 3 : signaux conso quand ni archetype ni NAF."""
    site = MagicMock(archetype_code=None, naf_code=None, id=1, nom="inconnu", portefeuille_id=None)
    db = MagicMock()
    with patch("utils.naf_resolver.resolve_naf_code", return_value=None):
        result = resolve_pilotage_archetype(site, db, signals={"continu_24_7": True, "talon_froid": True})
        assert result == "LOGISTIQUE_FRIGO"


def test_resolve_cascade_fallback_bureau_standard():
    """Priorite 4 : BUREAU_STANDARD + warning si rien ne matche."""
    site = MagicMock(archetype_code=None, naf_code=None, id=1, nom="no-info", portefeuille_id=None)
    db = MagicMock()
    with patch("utils.naf_resolver.resolve_naf_code", return_value=None):
        assert resolve_pilotage_archetype(site, db) == "BUREAU_STANDARD"


# ---------------------------------------------------------------------------
# Test 3 : heuristique HOTELLERIE biaisee RETIREE
# ---------------------------------------------------------------------------
def test_detect_archetype_plus_de_biais_hotellerie_24_7():
    """
    Avant Sprint 4 : `continu_24_7=True` sans `talon_froid` -> HOTELLERIE.
    Apres Sprint 4 : fallback BUREAU_STANDARD (biais retire, NAF prime).
    """
    result = detect_archetype(continu_24_7=True, talon_froid=False)
    assert result != "HOTELLERIE", "Le biais hotellerie doit etre retire -- utiliser NAF ou archetype_code explicite"
    assert result == "BUREAU_STANDARD"


def test_detect_archetype_signaux_forts_conserves():
    """Signaux robustes conserves : froid 24/7, talon froid, plages horaires."""
    assert detect_archetype(continu_24_7=True, talon_froid=True) == "LOGISTIQUE_FRIGO"
    assert detect_archetype(talon_froid=True) == "COMMERCE_ALIMENTAIRE"
    assert detect_archetype(horaires_ouverture=(8, 18)) == "ENSEIGNEMENT"
    assert detect_archetype(horaires_ouverture=(10, 20)) == "COMMERCE_SPECIALISE"
    assert detect_archetype(horaires_ouverture=(6, 19)) == "INDUSTRIE_LEGERE"


# ---------------------------------------------------------------------------
# Test 4 : memo portefeuille_scoring (perf)
# ---------------------------------------------------------------------------
def test_memo_portefeuille_scoring_reduit_lookups():
    """
    10 sites BUREAU_STANDARD -> 1 seul lookup YAML (pas 10).
    Verifie que `params_memo` est rempli apres 1er site du meme archetype.
    """
    with patch("services.pilotage.portefeuille_scoring.get_pilotage_param") as mock_param:
        # Fake response ParameterStore
        mock_param.return_value = MagicMock(value=900.0)
        sites = [
            {
                "site_id": f"site-{i}",
                "archetype_code": "BUREAU_STANDARD",
                "puissance_pilotable_kw": 100.0,
            }
            for i in range(10)
        ]
        compute_portefeuille_scoring(sites)
        # 10 sites BUREAU_STANDARD -> 2 lookups (HEURES + SPREAD) au total,
        # pas 2*10=20. Le memo evite les redondances.
        assert mock_param.call_count == 2, f"Memo defaillant : {mock_param.call_count} appels au lieu de 2"


def test_memo_portefeuille_scoring_archetypes_distincts():
    """3 archetypes distincts x N sites -> 3*2=6 lookups (pas 2*N)."""
    with patch("services.pilotage.portefeuille_scoring.get_pilotage_param") as mock_param:
        mock_param.return_value = MagicMock(value=900.0)
        sites = [
            {"site_id": "a1", "archetype_code": "BUREAU_STANDARD", "puissance_pilotable_kw": 100.0},
            {"site_id": "a2", "archetype_code": "BUREAU_STANDARD", "puissance_pilotable_kw": 50.0},
            {"site_id": "b1", "archetype_code": "SANTE", "puissance_pilotable_kw": 200.0},
            {"site_id": "c1", "archetype_code": "LOGISTIQUE_FRIGO", "puissance_pilotable_kw": 80.0},
            {"site_id": "c2", "archetype_code": "LOGISTIQUE_FRIGO", "puissance_pilotable_kw": 40.0},
        ]
        compute_portefeuille_scoring(sites)
        # 3 archetypes distincts * 2 params (HEURES + SPREAD) = 6 lookups
        assert mock_param.call_count == 6, f"Memo defaillant : {mock_param.call_count} appels au lieu de 6"


def test_estimate_gain_sans_memo_comportement_historique():
    """Sans memo passe, comportement historique preserve (appel YAML a chaque fois)."""
    with patch("services.pilotage.portefeuille_scoring.get_pilotage_param") as mock_param:
        mock_param.return_value = MagicMock(value=900.0)
        _estimate_gain_annuel_eur("BUREAU_STANDARD", 100.0)
        _estimate_gain_annuel_eur("BUREAU_STANDARD", 100.0)
        # Sans memo : 2 sites * 2 params = 4 appels
        assert mock_param.call_count == 4


def test_estimate_gain_zero_puissance_pas_de_lookup():
    """Shortcut : puissance <= 0 -> return 0 sans aucun lookup."""
    with patch("services.pilotage.portefeuille_scoring.get_pilotage_param") as mock_param:
        result = _estimate_gain_annuel_eur("BUREAU_STANDARD", 0.0)
        assert result == 0.0
        assert mock_param.call_count == 0
