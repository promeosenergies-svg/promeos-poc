"""
Tests structurels du mapping departement -> zone climatique OPERAT.

Cf. backend/config/operat_zones_climatiques.json
Cf. backend/regops/operat_zones.py

Confidence : 🟡 — verification croisee Legifrance manuelle recommandee P1.
Ces tests valident la STRUCTURE (couverture, doublons, format) pas la justesse
canonique des affectations zone par zone (qui necessite verification arrete
26/10/2010 NOR DEVU1026270A annexe III).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from regops.operat_zones import (
    all_zones,
    list_departements_for_zone,
    resolve_zone_from_departement,
    resolve_zone_from_insee_commune,
    resolve_zone_from_postal_code,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "operat_zones_climatiques.json"


@pytest.fixture(scope="module")
def cfg():
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# Tests de couverture exhaustive (96 metropole + 5 DOM = 101)
# ============================================================


def test_metropole_couvre_96_departements(cfg):
    """Tous les departements 01-95 (sans 20) + 2A + 2B doivent etre couverts."""
    all_metro = []
    for zone_data in cfg["zones"].values():
        all_metro.extend(zone_data["departements"])
    assert len(all_metro) == 96, f"Attendu 96 departements metro, trouve {len(all_metro)}"

    # Liste attendue : 01-95 sans 20, plus 2A et 2B
    expected = [f"{i:02d}" for i in range(1, 96) if i != 20] + ["2A", "2B"]
    assert sorted(all_metro) == sorted(expected), (
        f"Departements manquants : {set(expected) - set(all_metro)} ; en trop : {set(all_metro) - set(expected)}"
    )


def test_aucun_doublon_metropole(cfg):
    all_metro = []
    for zone_data in cfg["zones"].values():
        all_metro.extend(zone_data["departements"])
    assert len(all_metro) == len(set(all_metro)), "Doublons detectes dans le mapping metropole"


def test_dom_couvre_5_zones(cfg):
    assert len(cfg["dom"]) == 5
    expected_codes = {"971", "972", "973", "974", "976"}
    actual_codes = {d["code_insee_departement"] for d in cfg["dom"].values()}
    assert actual_codes == expected_codes


def test_zones_count_dans_chaque_zone_correspond_a_la_liste(cfg):
    """Chaque entree zone doit avoir count == len(departements)."""
    for zone_id, zone_data in cfg["zones"].items():
        assert zone_data["count"] == len(zone_data["departements"]), (
            f"{zone_id}: count={zone_data['count']} mais len(departements)={len(zone_data['departements'])}"
        )


def test_totaux_correspondent(cfg):
    assert cfg["totaux"]["metropole"] == 96
    assert cfg["totaux"]["dom"] == 5
    assert cfg["totaux"]["total"] == 101


# ============================================================
# Tests resolveur depuis departement
# ============================================================


@pytest.mark.parametrize(
    "dept,expected_zone",
    [
        # H1a — Bassin parisien + Hauts-de-France + Normandie + Aisne
        ("75", "H1a"),  # Paris
        ("92", "H1a"),  # Hauts-de-Seine (utilise station Paris-Montsouris)
        ("59", "H1a"),  # Nord
        ("02", "H1a"),  # Aisne
        ("14", "H1a"),  # Calvados
        # H1b — Grand Est + Bourgogne nord + Loiret
        ("57", "H1b"),  # Moselle (vs consensus RT 2012 H1a)
        ("67", "H1b"),  # Bas-Rhin (vs consensus RT 2012 H1a)
        ("88", "H1b"),  # Vosges
        ("51", "H1b"),  # Marne
        ("45", "H1b"),  # Loiret (vs consensus RT 2012 H2b)
        ("89", "H1b"),  # Yonne
        # H1c — Auvergne + Alpes Nord + Limousin sud + 05 Hautes-Alpes
        ("21", "H1c"),  # Côte-d'Or
        ("69", "H1c"),  # Rhône
        ("74", "H1c"),  # Haute-Savoie
        ("87", "H1c"),  # Haute-Vienne (vs consensus RT 2012 H2c)
        ("19", "H1c"),  # Corrèze (vs consensus RT 2012 H2d)
        ("23", "H1c"),  # Creuse (vs consensus RT 2012 H2c)
        ("05", "H1c"),  # Hautes-Alpes (vs consensus RT 2012 H2d)
        # H2a — Bretagne + Manche
        ("29", "H2a"),  # Finistère
        ("35", "H2a"),  # Ille-et-Vilaine
        ("50", "H2a"),  # Manche
        # H2b — Pays de la Loire + Centre + Mayenne
        ("44", "H2b"),  # Loire-Atlantique
        ("85", "H2b"),  # Vendée
        ("53", "H2b"),  # Mayenne (vs consensus RT 2012 H2a)
        # H2c — Sud-Ouest + Pyrénées
        ("33", "H2c"),  # Gironde
        ("64", "H2c"),  # Pyrénées-Atlantiques
        # H2d — Vallée Rhône + Provence intérieure (réduit à 5 dépts)
        ("26", "H2d"),  # Drôme
        ("84", "H2d"),  # Vaucluse (vs consensus RT 2012 H3)
        ("48", "H2d"),  # Lozère
        # H3 — Méditerranée + Corse
        ("13", "H3"),  # Bouches-du-Rhône
        ("06", "H3"),  # Alpes-Maritimes
        ("2A", "H3"),  # Corse-du-Sud
        ("2B", "H3"),  # Haute-Corse
        # DOM
        ("971", "Guadeloupe"),
        ("972", "Martinique"),
        ("973", "Guyane"),
        ("974", "La Réunion"),
        ("976", "Mayotte"),
    ],
)
def test_resolve_zone_from_departement_cas_canoniques(dept, expected_zone):
    assert resolve_zone_from_departement(dept) == expected_zone


def test_resolve_zone_from_departement_normalisation_un_chiffre():
    """'1' doit etre normalise en '01' -> H1c (Ain)."""
    assert resolve_zone_from_departement("1") == "H1c"
    assert resolve_zone_from_departement("01") == "H1c"


def test_resolve_zone_from_departement_inconnu():
    assert resolve_zone_from_departement("99") is None
    assert resolve_zone_from_departement("") is None
    assert resolve_zone_from_departement("ZZ") is None


# ============================================================
# Tests resolveur depuis code postal
# ============================================================


@pytest.mark.parametrize(
    "cp,expected_zone",
    [
        # Metropole standard
        ("75001", "H1a"),  # Paris 1er (annexe III: H1a)
        ("75116", "H1a"),  # Paris 16e
        ("13001", "H3"),  # Marseille
        ("69001", "H1c"),  # Lyon 1er
        ("31000", "H2c"),  # Toulouse (annexe III: H2c, vs consensus RT 2012 H2d)
        ("44000", "H2b"),  # Nantes
        ("33000", "H2c"),  # Bordeaux
        ("59000", "H1a"),  # Lille (annexe III: H1a, vs consensus H1b)
        ("57000", "H1b"),  # Metz (annexe III: H1b, vs consensus H1a)
        ("06000", "H3"),  # Nice
        # Corse
        ("20000", "H3"),  # Ajaccio (2A)
        ("20100", "H3"),  # Sartene (2A)
        ("20200", "H3"),  # Bastia (2B)
        ("20600", "H3"),  # Bastia rive sud (2B)
        # DOM
        ("97110", "Guadeloupe"),
        ("97200", "Martinique"),
        ("97300", "Guyane"),
        ("97400", "La Réunion"),
        ("97600", "Mayotte"),
    ],
)
def test_resolve_zone_from_postal_code_cas_canoniques(cp, expected_zone):
    assert resolve_zone_from_postal_code(cp) == expected_zone


def test_resolve_zone_from_postal_code_invalide():
    assert resolve_zone_from_postal_code("") is None
    assert resolve_zone_from_postal_code("ABCDE") is None
    assert resolve_zone_from_postal_code("123") is None
    assert resolve_zone_from_postal_code("123456") is None


def test_resolve_zone_from_postal_code_hors_operat():
    # Saint-Pierre-et-Miquelon (975xx) est COM, hors decret tertiaire
    assert resolve_zone_from_postal_code("97500") is None
    # Saint-Barthelemy / Saint-Martin (977/978) idem
    assert resolve_zone_from_postal_code("97700") is None
    assert resolve_zone_from_postal_code("97800") is None


# ============================================================
# Tests resolveur depuis code INSEE commune
# ============================================================


@pytest.mark.parametrize(
    "insee,expected_zone",
    [
        ("75056", "H1a"),  # Paris (annexe III: H1a)
        ("13055", "H3"),  # Marseille
        ("69123", "H1c"),  # Lyon
        ("2A004", "H3"),  # Ajaccio (Corse-du-Sud)
        ("2B033", "H3"),  # Bastia (Haute-Corse)
        ("97101", "Guadeloupe"),  # Basse-Terre
        ("97411", "La Réunion"),  # Saint-Denis La Reunion
    ],
)
def test_resolve_zone_from_insee_commune(insee, expected_zone):
    assert resolve_zone_from_insee_commune(insee) == expected_zone


# ============================================================
# Tests fonctions utilitaires
# ============================================================


def test_all_zones_retourne_13_zones():
    zones = all_zones()
    assert len(zones) == 13
    assert "H1a" in zones
    assert "H3" in zones
    assert "Guadeloupe" in zones
    assert "Mayotte" in zones


def test_list_departements_for_zone_h1a():
    depts = list_departements_for_zone("H1a")
    # Annexe III authentifiée : H1a = 18 dépts (Bassin parisien + Hauts-de-France + Normandie + Aisne)
    assert len(depts) == 18
    assert "75" in depts  # Paris
    assert "59" in depts  # Nord
    assert "02" in depts  # Aisne
    assert "57" not in depts  # Moselle est en H1b (pas H1a comme dans consensus RT 2012)
    assert "67" not in depts  # Bas-Rhin est en H1b


def test_list_departements_for_zone_dom():
    depts = list_departements_for_zone("Guadeloupe")
    assert depts == ["971"]


# ============================================================
# Coherence avec annexe I OPERAT (zones geographiques attendues)
# ============================================================


def test_zones_metropole_correspondent_annexe_i():
    """Les 8 zones metro (H1a-H3) du mapping doivent etre celles utilisees
    dans operat_annexe_i_sous_categories.json. Tolerance accents+article DOM
    (annexe I parser PyMuPDF normalise -> Reunion sans article ; annexe III
    Legifrance utilise La Reunion avec article officiel)."""
    zones_dans_mapping = {_strip_accents(z) for z in all_zones()}
    expected_metro = {"H1a", "H1b", "H1c", "H2a", "H2b", "H2c", "H2d", "H3"}
    # Pour DOM, accepter les variantes "La Reunion" et "Reunion"
    expected_dom_normalized = {
        _strip_accents(z) for z in ("Guadeloupe", "Martinique", "Guyane", "La Réunion", "Mayotte")
    }
    assert expected_metro.issubset(zones_dans_mapping)
    # Verifier qu'au moins 4/5 DOM matchent (Reunion/La Reunion possible variation)
    matches = expected_dom_normalized & zones_dans_mapping
    assert len(matches) >= 4, f"Expected >=4 DOM matches, got {matches}"


def _strip_accents(s: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def test_zones_alignees_avec_annexe_i_json():
    """Verifie que les zones de operat_annexe_i_sous_categories.json sont coherentes
    avec les zones du mapping departement. Tolere les variations de nommage DOM
    (annexe I extraite par PyMuPDF utilise 'Reunion' sans article ; annexe III
    Legifrance utilise 'La Reunion' avec article)."""
    annexe_i_path = Path(__file__).resolve().parent.parent / "config" / "operat_annexe_i_sous_categories.json"
    with annexe_i_path.open(encoding="utf-8") as f:
        annexe_i = json.load(f)

    # Normaliser les deux : lower + strip accents + ignorer 'la ' prefixe pour Reunion
    def normalize_zone(z):
        s = _strip_accents(z).lower().strip()
        if s.startswith("la "):
            s = s[3:]
        return s

    zones_annexe_i = {normalize_zone(z) for z in annexe_i["zones_order"]}
    zones_mapping = {normalize_zone(z) for z in all_zones()}

    assert zones_annexe_i == zones_mapping, (
        f"Desalignement zones : annexe_i={zones_annexe_i} vs mapping={zones_mapping}"
    )
