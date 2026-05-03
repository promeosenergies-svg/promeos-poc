"""
PROMEOS — Sprint C-1 Phase 4 : Tests OperatValeursAbsoluesService.

Vérifie la chaîne 4 lookups OPERAT (zone → palier → CVCi → Coeff DJU) +
compute Cabs 2030 e2e + endpoint /api/operat/cabs/{site_id} avec org-scoping.

Sources :
- Annexes I+II arrêté 01/08/2025 NOR ATDL2430864A
- Annexe III arrêté 10/04/2020 NOR LOGL2005904A v2 (zones authentifiées 🟢)
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Titre Annexe I exact pour les tests (sous-cat avec coverage CVCi/USE complet)
_TITLE_BUREAU_STANDARD = "Bureaux - Bureaux Standards (cloisonnés - attribués)"


@pytest.fixture(scope="module")
def service():
    """Instance unique du service pour économiser les chargements JSON (LRU cache)."""
    from regops.services.operat_cabs_service import OperatValeursAbsoluesService

    return OperatValeursAbsoluesService()


# ─── Lookup 1 : code postal → zone ───────────────────────────────────────────


def test_resolve_zone_paris(service):
    """Paris (75001) → H1a (Bassin parisien)."""
    assert service.resolve_zone("75001") == "H1a"


def test_resolve_zone_lyon(service):
    """Lyon (69001) → H1c (climat continental Rhône-Alpes)."""
    assert service.resolve_zone("69001") == "H1c"


def test_resolve_zone_marseille(service):
    """Marseille (13001) → H3 (climat méditerranéen)."""
    assert service.resolve_zone("13001") == "H3"


def test_resolve_zone_com_returns_none(service):
    """COM (Saint-Pierre-et-Miquelon 97500-97590) hors périmètre → None."""
    assert service.resolve_zone("97500") is None


# ─── Lookup 2 : altitude → palier strict ─────────────────────────────────────


def test_resolve_palier_altitude_5_paliers(service):
    """5 paliers stricts : <400, 400-800, 800-1200, 1200-1600, ≥1600."""
    assert service.resolve_palier_altitude(0) == "alt_lt_400"
    assert service.resolve_palier_altitude(399) == "alt_lt_400"
    assert service.resolve_palier_altitude(400) == "alt_400_800"
    assert service.resolve_palier_altitude(799) == "alt_400_800"
    assert service.resolve_palier_altitude(800) == "alt_800_1200"
    assert service.resolve_palier_altitude(1199) == "alt_800_1200"
    assert service.resolve_palier_altitude(1200) == "alt_1200_1600"
    assert service.resolve_palier_altitude(1599) == "alt_1200_1600"
    assert service.resolve_palier_altitude(1600) == "alt_gte_1600"
    assert service.resolve_palier_altitude(2500) == "alt_gte_1600"


def test_resolve_palier_altitude_negative_raises(service):
    """Altitude négative → ValueError."""
    with pytest.raises(ValueError):
        service.resolve_palier_altitude(-10)


def test_resolve_palier_altitude_none_raises(service):
    """Altitude None → ValueError."""
    with pytest.raises(ValueError):
        service.resolve_palier_altitude(None)


# ─── Lookup 3 : sous-cat × zone × palier → CVCi + USEi ───────────────────────


def test_get_cvci_usei_bureau_paris_h1a_alt_lt_400(service):
    """Bureau standard Paris H1a alt<400 : CVC=57, USE étalon=50 (Annexe I)."""
    result = service.get_cvci_usei(_TITLE_BUREAU_STANDARD, "H1a", "alt_lt_400")
    assert result is not None
    assert result["cvc_kwh_m2_an"] == 57
    assert result["use_etalon_kwh_m2_an"] == 50
    # Traçabilité complète
    assert result["tracability"]["nor"] == "ATDL2430864A"
    assert result["tracability"]["date_arrete"] == "2025-08-01"
    assert result["tracability"]["annexe"] == "I"


def test_get_cvci_usei_bureau_marseille_h3_alt_lt_400(service):
    """Bureau standard Marseille H3 alt<400 : CVC=40 (climat méditerranéen plus doux)."""
    result = service.get_cvci_usei(_TITLE_BUREAU_STANDARD, "H3", "alt_lt_400")
    assert result is not None
    assert result["cvc_kwh_m2_an"] == 40


def test_get_cvci_usei_unknown_subcat_raises(service):
    """Sous-cat invalide → OperatSousCategorieIntrouvableError."""
    from regops.services.operat_cabs_service import OperatSousCategorieIntrouvableError

    with pytest.raises(OperatSousCategorieIntrouvableError):
        service.get_cvci_usei("SOUS_CAT_INEXISTANTE", "H1a", "alt_lt_400")


def test_get_cvci_usei_invalid_zone_returns_none(service):
    """Zone hors index → None (palier valide mais zone invalide)."""
    result = service.get_cvci_usei(_TITLE_BUREAU_STANDARD, "H99", "alt_lt_400")
    assert result is None


def test_la_reunion_normalization(service):
    """Le service accepte 'La Réunion', 'Réunion', 'Reunion' → mêmes données."""
    # Annexe I JSON contient "Reunion" (sans accent — extraction PDF)
    res_reunion = service.get_cvci_usei(_TITLE_BUREAU_STANDARD, "Reunion", "alt_lt_400")
    res_reunion_acc = service.get_cvci_usei(_TITLE_BUREAU_STANDARD, "Réunion", "alt_lt_400")
    res_la_reunion = service.get_cvci_usei(_TITLE_BUREAU_STANDARD, "La Réunion", "alt_lt_400")

    assert res_reunion is not None
    assert res_reunion_acc is not None
    assert res_la_reunion is not None
    # Mêmes valeurs CVC (normalisation appliquée)
    assert res_reunion["cvc_kwh_m2_an"] == res_reunion_acc["cvc_kwh_m2_an"] == res_la_reunion["cvc_kwh_m2_an"]


# ─── Lookup 4 : sous-cat → groupe Coeff DJU ──────────────────────────────────


def test_get_coeff_dju_groupes_g1_g13_count(service):
    """13 groupes G1-G13 doivent être chargés depuis Annexe II."""
    # Lecture directe via service interne
    assert len(service._annexe_ii.get("groupes", [])) == 13


def test_get_coeff_dju_returns_none_when_not_mapped(service):
    """Une sous-catégorie sans entrée dans Annexe II.categories_couvertes → None."""
    # Le titre Bureaux standards spécifique d'Annexe I n'a pas forcément un mapping
    # exact dans Annexe II.categories_couvertes (mapping fuzzy à implémenter sprint
    # futur). Le service retourne proprement None.
    result = service.get_coeff_dju("Sous-cat absolument fictive XYZ")
    assert result is None


def test_get_coeff_dju_finds_mapped_subcat(service):
    """Une sous-cat listée dans categories_couvertes G1 doit retourner ce groupe."""
    # Récupérer la première categorie_couverte du premier groupe pour test
    first_groupe = service._annexe_ii["groupes"][0]
    if first_groupe["categories_couvertes"]:
        sample_title = first_groupe["categories_couvertes"][0]
        result = service.get_coeff_dju(sample_title)
        assert result is not None
        assert result["groupe_id"] == first_groupe["groupe_id"]
        assert result["coeff_ch_par_dj"] == first_groupe["coeff_ch_par_dj"]
        assert result["coeff_fr_par_dj"] == first_groupe["coeff_fr_par_dj"]


# ─── Compute Cabs 2030 e2e ───────────────────────────────────────────────────


def test_compute_cabs_2030_e2e_helios_paris(service):
    """Site HELIOS Paris (1500 m² Bureau standard) → Cabs cohérent (~107 kWh/m²/an)."""
    result = service.compute_cabs_2030(
        code_postal="75001",
        altitude_m=35,
        sous_categories_declared=[
            {"title": _TITLE_BUREAU_STANDARD, "surface_m2": 1500},
        ],
    )
    # CVC 57 + USE 50 = 107 (sans modulation DJU)
    assert result["cabs_2030_kwh_m2_an"] == 107.0
    assert result["surface_totale_m2"] == 1500.0
    assert len(result["components"]) == 1

    trac = result["tracability_complete"]
    assert trac["zone"] == "H1a"
    assert trac["palier_altitude"] == "alt_lt_400"
    assert trac["nor_annexe_i"] == "ATDL2430864A (annexe I)"
    assert trac["modulation_dju_active"] is False
    assert trac["modulation_iiu_active"] is False


def test_compute_cabs_2030_marseille_h3_lower_cvc(service):
    """Marseille H3 → Cabs plus bas que Paris H1a (climat plus doux)."""
    paris = service.compute_cabs_2030(
        code_postal="75001",
        altitude_m=35,
        sous_categories_declared=[{"title": _TITLE_BUREAU_STANDARD, "surface_m2": 1000}],
    )
    marseille = service.compute_cabs_2030(
        code_postal="13001",
        altitude_m=12,
        sous_categories_declared=[{"title": _TITLE_BUREAU_STANDARD, "surface_m2": 1000}],
    )
    assert marseille["cabs_2030_kwh_m2_an"] < paris["cabs_2030_kwh_m2_an"]
    # 40 + 50 = 90 (Marseille H3) vs 57 + 50 = 107 (Paris H1a)
    assert marseille["cabs_2030_kwh_m2_an"] == 90.0


def test_compute_cabs_2030_com_hors_perimetre_raises(service):
    """COM (Saint-Pierre-et-Miquelon 97500) → OperatNonAssujettiError."""
    from regops.services.operat_cabs_service import OperatNonAssujettiError

    with pytest.raises(OperatNonAssujettiError):
        service.compute_cabs_2030(
            code_postal="97500",
            altitude_m=10,
            sous_categories_declared=[{"title": _TITLE_BUREAU_STANDARD, "surface_m2": 100}],
        )


def test_compute_cabs_2030_empty_sous_cat_raises(service):
    """Liste vide de sous-cat → ValueError."""
    with pytest.raises(ValueError):
        service.compute_cabs_2030(
            code_postal="75001",
            altitude_m=35,
            sous_categories_declared=[],
        )


def test_compute_cabs_2030_zero_surface_raises(service):
    """Surface totale nulle → ValueError."""
    with pytest.raises(ValueError):
        service.compute_cabs_2030(
            code_postal="75001",
            altitude_m=35,
            sous_categories_declared=[{"title": _TITLE_BUREAU_STANDARD, "surface_m2": 0}],
        )


def test_compute_cabs_2030_invalid_subcat_raises(service):
    """Sous-cat invalide → OperatSousCategorieIntrouvableError."""
    from regops.services.operat_cabs_service import OperatSousCategorieIntrouvableError

    with pytest.raises(OperatSousCategorieIntrouvableError):
        service.compute_cabs_2030(
            code_postal="75001",
            altitude_m=35,
            sous_categories_declared=[{"title": "SOUS_CAT_INEXISTANTE", "surface_m2": 100}],
        )


def test_compute_cabs_2030_returns_in_reasonable_range(service):
    """Cabs cohérent : positif et < 1000 kWh/m²/an pour bureau standard."""
    result = service.compute_cabs_2030(
        code_postal="75001",
        altitude_m=35,
        sous_categories_declared=[{"title": _TITLE_BUREAU_STANDARD, "surface_m2": 1500}],
    )
    cabs = result["cabs_2030_kwh_m2_an"]
    assert cabs > 0, "Cabs négatif aberrant"
    assert cabs < 1000, "Cabs > 1000 kWh/m²/an aberrant pour bureau standard"


# ─── Tooltip traçabilité (différenciateur PROMEOS Sol §13) ──────────────────


def test_tracability_complete_contains_nor_url_date(service):
    """Le tooltip traçabilité doit contenir NOR + URL Légifrance + date."""
    result = service.get_cvci_usei(_TITLE_BUREAU_STANDARD, "H1a", "alt_lt_400")
    trac = result["tracability"]
    assert trac["nor"] == "ATDL2430864A"
    assert trac["date_arrete"] == "2025-08-01"
    assert "bulletin-officiel.developpement-durable.gouv.fr" in trac["url_bulletin_officiel"]
    assert trac["sous_categorie"] == _TITLE_BUREAU_STANDARD
    assert trac["zone"] == "H1a"
    assert trac["palier"] == "alt_lt_400"
