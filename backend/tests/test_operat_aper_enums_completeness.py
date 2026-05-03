"""
PROMEOS — Sprint C-1 Phase 3 : Tests complétude des 6 enums OPERAT/APER.

Vérifie que les 6 enums créés en matrice v1 §4.4.C/D contiennent exactement les
valeurs attendues (citées dans matrice + sources réglementaires officielles).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── OperatZoneClimatiqueEnum — 13 valeurs (8 métropole + 5 DOM) ───


def test_operat_zone_climatique_count():
    from models.enums import OperatZoneClimatiqueEnum

    assert len(list(OperatZoneClimatiqueEnum)) == 13


def test_operat_zone_climatique_metropole():
    from models.enums import OperatZoneClimatiqueEnum

    metropole = {"H1a", "H1b", "H1c", "H2a", "H2b", "H2c", "H2d", "H3"}
    actual = {
        z.value
        for z in OperatZoneClimatiqueEnum
        if z.value not in {"Guadeloupe", "Martinique", "Guyane", "Réunion", "Mayotte"}
    }
    assert actual == metropole


def test_operat_zone_climatique_dom():
    from models.enums import OperatZoneClimatiqueEnum

    dom = {"Guadeloupe", "Martinique", "Guyane", "Réunion", "Mayotte"}
    actual = {z.value for z in OperatZoneClimatiqueEnum if z.value in dom}
    assert actual == dom


def test_operat_zone_climatique_reunion_normalized():
    """⚠️ Annexe III écrit 'Réunion' (pas 'La Réunion').

    Annexe I peut différer. Normalisation requise dans OperatValeursAbsoluesService
    (Sprint C-1 Phase 4).
    """
    from models.enums import OperatZoneClimatiqueEnum

    assert OperatZoneClimatiqueEnum.REUNION.value == "Réunion"
    assert "La Réunion" not in {z.value for z in OperatZoneClimatiqueEnum}


# ─── OperatPalierAltitudeEnum — 5 paliers stricts ───


def test_operat_palier_altitude_count():
    from models.enums import OperatPalierAltitudeEnum

    assert len(list(OperatPalierAltitudeEnum)) == 5


def test_operat_palier_altitude_values():
    from models.enums import OperatPalierAltitudeEnum

    expected = {"alt_lt_400", "alt_400_800", "alt_800_1200", "alt_1200_1600", "alt_gte_1600"}
    actual = {p.value for p in OperatPalierAltitudeEnum}
    assert actual == expected


# ─── OperatUsagePrincipalEnum — 9 catégories ───


def test_operat_usage_principal_count():
    from models.enums import OperatUsagePrincipalEnum

    assert len(list(OperatUsagePrincipalEnum)) == 9


def test_operat_usage_principal_values():
    from models.enums import OperatUsagePrincipalEnum

    expected = {
        "BUREAUX",
        "COMMERCES",
        "ENSEIGNEMENT",
        "HOTELLERIE",
        "RESTAURATION",
        "SANTE",
        "SPORT_LOISIRS",
        "LOGISTIQUE",
        "MIXTE",
    }
    actual = {u.value for u in OperatUsagePrincipalEnum}
    assert actual == expected


# ─── OperatModulationMotifEnum — 4 motifs officiels art. 12 ───


def test_operat_modulation_motif_count():
    from models.enums import OperatModulationMotifEnum

    assert len(list(OperatModulationMotifEnum)) == 4


def test_operat_modulation_motif_values():
    from models.enums import OperatModulationMotifEnum

    expected = {
        "COUT_DISPROPORTIONNE",
        "CONSEQUENCES_NEGATIVES",
        "PATRIMOINE_INCOMPATIBILITE",
        "CHANGEMENT_ACTIVITE",
    }
    actual = {m.value for m in OperatModulationMotifEnum}
    assert actual == expected


# ─── AperCategorieTailleEnum — 2 valeurs ───


def test_aper_categorie_taille_count():
    from models.enums import AperCategorieTailleEnum

    assert len(list(AperCategorieTailleEnum)) == 2


def test_aper_categorie_taille_values():
    from models.enums import AperCategorieTailleEnum

    actual = {c.value for c in AperCategorieTailleEnum}
    assert actual == {"SMALL", "LARGE"}


# ─── AperExemptionMotifEnum — 4 motifs ───


def test_aper_exemption_motif_count():
    from models.enums import AperExemptionMotifEnum

    assert len(list(AperExemptionMotifEnum)) == 4


def test_aper_exemption_motif_values():
    from models.enums import AperExemptionMotifEnum

    expected = {
        "CONTRAINTES_TECHNIQUES",
        "CONTRAINTES_PATRIMONIALES",
        "CONTRAINTES_ECONOMIQUES",
        "CONTRAINTES_OPERATIONNELLES",
    }
    actual = {m.value for m in AperExemptionMotifEnum}
    assert actual == expected


# ─── Convention naming + str inheritance ───


def test_all_enums_inherit_str():
    """Tous les enums doivent hériter de str pour serialization JSON natif."""
    from models.enums import (
        AperCategorieTailleEnum,
        AperExemptionMotifEnum,
        OperatModulationMotifEnum,
        OperatPalierAltitudeEnum,
        OperatUsagePrincipalEnum,
        OperatZoneClimatiqueEnum,
    )

    for cls in [
        OperatZoneClimatiqueEnum,
        OperatPalierAltitudeEnum,
        OperatUsagePrincipalEnum,
        OperatModulationMotifEnum,
        AperCategorieTailleEnum,
        AperExemptionMotifEnum,
    ]:
        assert issubclass(cls, str), f"{cls.__name__} doit hériter de str"
