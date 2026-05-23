"""PROMEOS — Source guard backend : Site.is_demo NOT NULL (P0 audit Sprint F).

Phase 3.4-bis Correctif #4 — figer l'invariant introduit par la migration
`p34bisisd` (Site.is_demo NOT NULL DEFAULT FALSE).

Risque adressé : si un site existe avec `is_demo=NULL` en DB, le filtre F.4
`Site.is_demo == Organisation.is_demo` (`services.scope_utils.
sites_for_org_query`) le filtre OUT silencieusement (NULL == False = NULL
en SQL). Combiné aux 13 callsites cockpit + 4 helpers factorisés Correctif #3,
un site NULL = site invisible côté API → cockpit vide pour 1er pilote client réel.

Cette source-guard pytest échoue le build CI si :
  1. La colonne `Site.is_demo` redevient nullable (régression model/migration).
  2. Un site existe en DB avec `is_demo=NULL` (vérif runtime DB).

À NE PAS supprimer sans relire l'audit Sprint F CS verdict.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from sqlalchemy import inspect, text

from database import SessionLocal, engine
from models.site import Site


# P0-D hygiène 2026-05-23 — skip runtime DB checks si la table `sites` n'existe
# pas (cas CI fresh sans seed). Les checks structurels (model SQLAlchemy + colonne
# nullable=False) restent actifs car ils n'ont pas besoin d'une DB peuplée.
_DB_HAS_SITES_TABLE = inspect(engine).has_table("sites")
_SKIP_REASON_FRESH_DB = (
    "Table `sites` absente — DB fresh (CI sans seed). "
    "Test runtime DB skippé ; les checks structurels model/schéma restent actifs."
)


def test_site_isdemo_column_not_nullable():
    """Site.is_demo doit avoir nullable=False au niveau model SQLAlchemy."""
    assert Site.__table__.c.is_demo.nullable is False, (
        "Régression P0 audit Sprint F : Site.is_demo redevenu nullable. "
        "Cf migration `p34bisisd` + commentaire model. La fuite `is_demo IS NULL` "
        "rend les sites invisibles via le filtre F.4 sites_for_org_query."
    )


def test_site_isdemo_column_has_server_default_false():
    """Site.is_demo doit avoir un server_default '0' (FALSE) pour les INSERT direct SQL."""
    col = Site.__table__.c.is_demo
    assert col.server_default is not None, (
        "Site.is_demo manque server_default — risque que les INSERT direct SQL laissent NULL malgré le default Python."
    )


@pytest.mark.skipif(not _DB_HAS_SITES_TABLE, reason=_SKIP_REASON_FRESH_DB)
def test_site_isdemo_db_no_null_rows():
    """Aucune ligne sites en DB ne doit avoir is_demo IS NULL.

    Si ce test échoue : migration non appliquée OU un INSERT a contourné la
    contrainte (BD corrompue). Action immédiate : `alembic upgrade head`
    + audit des inserts récents.
    """
    db = SessionLocal()
    try:
        count_null = db.execute(text("SELECT COUNT(*) FROM sites WHERE is_demo IS NULL")).scalar()
        assert count_null == 0, (
            f"P0 audit Sprint F : {count_null} site(s) en DB avec is_demo IS NULL. "
            f"Ces sites sont filtrés OUT silencieusement par le filtre F.4. "
            f"Action : `alembic upgrade head` pour appliquer p34bisisd (backfill)."
        )
    finally:
        db.close()


@pytest.mark.skipif(not _DB_HAS_SITES_TABLE, reason=_SKIP_REASON_FRESH_DB)
def test_site_isdemo_db_column_not_nullable():
    """La colonne `sites.is_demo` doit être déclarée NOT NULL au niveau DB.

    Vérifie l'introspection SQLAlchemy directe sur le schéma effectif
    (vs le model Python qui pourrait diverger de la DB en cas de migration
    manquée).
    """
    inspector = inspect(engine)
    cols = {c["name"]: c for c in inspector.get_columns("sites")}
    assert "is_demo" in cols, "Colonne sites.is_demo absente — model désynchronisé."
    assert cols["is_demo"]["nullable"] is False, (
        "P0 audit Sprint F : sites.is_demo nullable=True en DB malgré migration "
        "`p34bisisd`. Lancer `alembic upgrade head` pour rétablir la contrainte."
    )
