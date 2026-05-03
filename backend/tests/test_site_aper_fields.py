"""
PROMEOS — Sprint C-1 Phase 3 : Tests présence champs APER sur Site.

Vérifie que les 5 champs APER (matrice v1 §4.4.D) sont présents dans le modèle
Site SQLAlchemy avec types corrects et stockage en colonne (pas hybrid_property).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import Boolean, Date, Float

from models.enums import AperCategorieTailleEnum, AperExemptionMotifEnum
from models.site import Site


APER_FIELDS_SPEC = [
    ("aper_assujetti", Boolean, True),
    ("aper_categorie_taille", "ENUM", True),
    ("aper_deadline", Date, True),
    ("parking_solar_pct_engaged", Float, True),
    ("aper_exemption_motif", "ENUM", True),
]


@pytest.mark.parametrize("name,expected_type,nullable", APER_FIELDS_SPEC)
def test_aper_field_present(name: str, expected_type, nullable: bool):
    """Chaque champ APER doit être présent dans Site avec type + nullabilité corrects."""
    assert name in Site.__table__.columns, f"Colonne {name} manquante sur Site"
    col = Site.__table__.columns[name]
    assert col.nullable is nullable, f"{name} : nullable attendu {nullable}, observé {col.nullable}"

    if expected_type == "ENUM":
        assert "Enum" in col.type.__class__.__name__ or "VARCHAR" in str(col.type)
    else:
        assert isinstance(col.type, expected_type)


def test_aper_assujetti_is_stored_column_not_property():
    """aper_assujetti doit être une vraie colonne Boolean stockée (pas hybrid_property).

    Décision archi (matrice v1 §4.4.D #37) : aper_assujetti est calculé par
    cascade_recompute (Phase 6) et stocké en colonne, pour permettre lookup
    rapide sans déclencher le calcul à chaque accès.
    """
    col = Site.__table__.columns["aper_assujetti"]
    assert isinstance(col.type, Boolean)


def test_aper_categorie_taille_uses_enum_class():
    """aper_categorie_taille doit utiliser AperCategorieTailleEnum."""
    col = Site.__table__.columns["aper_categorie_taille"]
    assert hasattr(col.type, "enum_class") and col.type.enum_class is AperCategorieTailleEnum


def test_aper_exemption_motif_uses_enum_class():
    """aper_exemption_motif doit utiliser AperExemptionMotifEnum."""
    col = Site.__table__.columns["aper_exemption_motif"]
    assert hasattr(col.type, "enum_class") and col.type.enum_class is AperExemptionMotifEnum


def test_aper_deadline_is_date_not_datetime():
    """aper_deadline doit être Date pure (pas DateTime — l'échéance est une date civile)."""
    col = Site.__table__.columns["aper_deadline"]
    assert isinstance(col.type, Date)


def test_aper_fields_total_count():
    """5 champs APER attendus (matrice v1 §4.4.D)."""
    aper_columns = [
        c.name for c in Site.__table__.columns if c.name.startswith("aper_") or c.name == "parking_solar_pct_engaged"
    ]
    # aper_assujetti, aper_categorie_taille, aper_deadline, aper_exemption_motif + parking_solar_pct_engaged
    assert len(aper_columns) == 5, f"5 champs APER attendus, observé {len(aper_columns)} : {aper_columns}"
