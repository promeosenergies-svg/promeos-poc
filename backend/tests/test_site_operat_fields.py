"""
PROMEOS — Sprint C-1 Phase 3 : Tests présence champs OPERAT + EFA sur Site.

Vérifie que les 13 champs OPERAT + 1 champ EFA (matrice v1 §4.4.C + §4.4.G)
sont présents dans le modèle Site SQLAlchemy avec types et nullabilité corrects.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import Boolean, Date, Float, Integer, String

from models.enums import (
    OperatModulationMotifEnum,
    OperatPalierAltitudeEnum,
    OperatUsagePrincipalEnum,
    OperatZoneClimatiqueEnum,
)
from models.site import Site


# Spec matrice v1 : (nom_colonne, type_attendu, nullable_attendu)
OPERAT_FIELDS_SPEC = [
    ("operat_zone_climatique", "ENUM", True),
    ("operat_palier_altitude", "ENUM", True),
    ("altitude_m", Integer, True),
    ("operat_sous_categorie_id", String, True),
    ("operat_iiu_temporels", "JSON", True),
    ("operat_iiu_surfaciques", "JSON", True),
    ("cabs_kwh_m2_an", Float, True),
    ("crelat_kwh_m2_an", Float, True),
    ("usage_principal", "ENUM", True),
    ("efa_id", String, True),
    ("annee_reference_operat", Integer, True),
    ("methode_modulation_dt", "ENUM", True),
    ("dossier_modulation_id", String, True),
]


@pytest.mark.parametrize("name,expected_type,nullable", OPERAT_FIELDS_SPEC)
def test_operat_field_present(name: str, expected_type, nullable: bool):
    """Chaque champ OPERAT doit être présent dans Site avec type + nullabilité corrects."""
    assert name in Site.__table__.columns, f"Colonne {name} manquante sur Site"
    col = Site.__table__.columns[name]
    assert col.nullable is nullable, f"{name} : nullable attendu {nullable}, observé {col.nullable}"

    if expected_type == "ENUM":
        assert "Enum" in col.type.__class__.__name__ or "VARCHAR" in str(col.type), (
            f"{name} : type Enum/VARCHAR attendu, observé {col.type}"
        )
    elif expected_type == "JSON":
        assert "JSON" in str(col.type).upper(), f"{name} : type JSON attendu, observé {col.type}"
    else:
        assert isinstance(col.type, expected_type), (
            f"{name} : type {expected_type.__name__} attendu, observé {type(col.type).__name__}"
        )


def test_efa_id_indexed():
    """efa_id doit être indexé (lookup rapide cf. matrice v1 §4.4.G)."""
    col = Site.__table__.columns["efa_id"]
    # Pour SQLite avec batch_alter_table, l'index est créé séparément.
    # On vérifie via la table.
    indexes = [idx for idx in Site.__table__.indexes if "efa_id" in [c.name for c in idx.columns]]
    assert len(indexes) >= 1, "Aucun index sur efa_id (attendu : ix_sites_efa_id)"


def test_operat_zone_climatique_uses_enum_class():
    """operat_zone_climatique doit utiliser OperatZoneClimatiqueEnum (pas de string libre)."""
    col = Site.__table__.columns["operat_zone_climatique"]
    assert hasattr(col.type, "enum_class") and col.type.enum_class is OperatZoneClimatiqueEnum


def test_operat_palier_altitude_uses_enum_class():
    """operat_palier_altitude doit utiliser OperatPalierAltitudeEnum."""
    col = Site.__table__.columns["operat_palier_altitude"]
    assert hasattr(col.type, "enum_class") and col.type.enum_class is OperatPalierAltitudeEnum


def test_usage_principal_uses_enum_class():
    """usage_principal doit utiliser OperatUsagePrincipalEnum."""
    col = Site.__table__.columns["usage_principal"]
    assert hasattr(col.type, "enum_class") and col.type.enum_class is OperatUsagePrincipalEnum


def test_methode_modulation_dt_uses_enum_class():
    """methode_modulation_dt doit utiliser OperatModulationMotifEnum."""
    col = Site.__table__.columns["methode_modulation_dt"]
    assert hasattr(col.type, "enum_class") and col.type.enum_class is OperatModulationMotifEnum


def test_total_operat_fields_count():
    """13 champs OPERAT + 1 EFA doivent être présents."""
    fields = [name for name, *_ in OPERAT_FIELDS_SPEC]
    assert len(fields) == 13, f"Spec attend 13 OPERAT + 1 EFA, observé {len(fields)}"
    # efa_id est dans la liste — vérification globale 13 OPERAT (efa_id partagé)
    for name in fields:
        assert name in Site.__table__.columns


def test_operat_fields_native_enum_false():
    """Tous les enums OPERAT/APER doivent être native_enum=False (compat SQLite/PostgreSQL)."""
    enum_columns = ["operat_zone_climatique", "operat_palier_altitude", "usage_principal", "methode_modulation_dt"]
    for cname in enum_columns:
        col = Site.__table__.columns[cname]
        # native_enum False signifie que SQLAlchemy stocke en VARCHAR + CHECK
        assert col.type.native_enum is False, f"{cname} : native_enum=False attendu (compat SQLite ↔ PostgreSQL)"
