"""
PROMEOS — Sprint C-1 Phase 3 : Tests statiques migration Alembic.

Vérifie la cohérence du fichier de migration `c8f1246522f9` :
  - 18 add_column dans upgrade()
  - 18 drop_column dans downgrade()
  - Symétrie forward/backward (mêmes noms de colonne)
  - Pas de drop_table en code actif (anti-régression nettoyage Phase 3)
  - Index ix_sites_efa_id présent

Note : la preuve fonctionnelle (forward + backward + re-forward sur SQLite)
a été faite manuellement Sprint C-1 Phase 3 étapes 1-10 (cf. logs
/tmp/phase3_*.log). Ce fichier valide statiquement la cohérence du code de
migration sans dépendre de la DB de dev (qui est mutée par conftest.py
_ensure_seeded module-scoped autouse → empêche un test exécutif fiable).

Ref : matrice v1 §4.4.C/D/G + audit Phase B R6 (cascade recompute Phase 6).
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_MIGRATION_PATH = _BACKEND_ROOT / "alembic" / "versions" / "c8f1246522f9_site_operat_aper_efa_fields_18cols.py"


# Liste des 18 colonnes attendues
NEW_COLUMNS = [
    "operat_zone_climatique",
    "operat_palier_altitude",
    "altitude_m",
    "operat_sous_categorie_id",
    "operat_iiu_temporels",
    "operat_iiu_surfaciques",
    "cabs_kwh_m2_an",
    "crelat_kwh_m2_an",
    "usage_principal",
    "efa_id",
    "annee_reference_operat",
    "methode_modulation_dt",
    "dossier_modulation_id",
    "aper_assujetti",
    "aper_categorie_taille",
    "aper_deadline",
    "parking_solar_pct_engaged",
    "aper_exemption_motif",
]


@pytest.fixture(scope="module")
def migration_source() -> str:
    """Lit le fichier de migration une fois par module."""
    if not _MIGRATION_PATH.exists():
        pytest.fail(f"Migration manquante : {_MIGRATION_PATH}")
    return _MIGRATION_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def migration_ast(migration_source: str) -> ast.Module:
    """Parse l'AST du fichier de migration."""
    return ast.parse(migration_source)


def _extract_function_body_source(source: str, func_name: str) -> str:
    """Extrait le source code d'une fonction par son nom."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.get_source_segment(source, node) or ""
    return ""


def test_migration_file_exists():
    """Le fichier de migration doit exister à l'emplacement attendu."""
    assert _MIGRATION_PATH.is_file(), f"Migration manquante : {_MIGRATION_PATH}"


def test_migration_revision_ids(migration_source: str):
    """Revision IDs corrects : c8f1246522f9 revises 2f83c6bebc57."""
    assert re.search(r'revision:\s*str\s*=\s*["\']c8f1246522f9["\']', migration_source)
    assert re.search(r'down_revision[^=]*=\s*["\']2f83c6bebc57["\']', migration_source)


def test_migration_upgrade_adds_18_columns(migration_source: str):
    """upgrade() doit contenir 18 add_column avec les noms attendus."""
    upgrade_src = _extract_function_body_source(migration_source, "upgrade")
    add_count = upgrade_src.count("add_column(")
    assert add_count == 18, f"upgrade() : {add_count} add_column trouvés (attendu 18)"

    for col_name in NEW_COLUMNS:
        # Cherche soit "col_name" soit 'col_name' dans le source
        pattern = re.compile(rf'["\']{re.escape(col_name)}["\']')
        assert pattern.search(upgrade_src), f"add_column manquant pour {col_name}"


def test_migration_downgrade_drops_18_columns(migration_source: str):
    """downgrade() doit contenir 18 drop_column avec les noms attendus."""
    downgrade_src = _extract_function_body_source(migration_source, "downgrade")
    drop_count = downgrade_src.count("drop_column(")
    assert drop_count == 18, f"downgrade() : {drop_count} drop_column trouvés (attendu 18)"

    for col_name in NEW_COLUMNS:
        pattern = re.compile(rf'drop_column\(["\']{re.escape(col_name)}["\']\)')
        assert pattern.search(downgrade_src), f"drop_column manquant pour {col_name}"


def test_migration_no_destructive_drop_table(migration_source: str):
    """Aucun drop_table ou create_table en code actif (anti-régression Phase 3 cleanup).

    Tolère uniquement les mentions en docstring (qui expliquent l'historique
    du nettoyage des 17 tables Enedis legacy droppées par autogenerate).
    """
    # Retirer les docstrings pour ne scanner que le code actif
    sanitized = re.sub(r'"""[\s\S]*?"""', "", migration_source)
    sanitized = re.sub(r"'''[\s\S]*?'''", "", sanitized)
    # Retirer les commentaires de ligne
    sanitized = "\n".join(line.split("#", 1)[0] for line in sanitized.splitlines())

    # Aucun appel actif drop_table / create_table
    assert "drop_table(" not in sanitized, (
        "drop_table( détecté en code actif — anti-régression Phase 3 cleanup. "
        "La migration ne doit toucher qu'à la table sites."
    )
    assert "create_table(" not in sanitized, (
        "create_table( détecté en code actif — la migration n'est censée qu'ajouter "
        "des colonnes à sites, pas créer de tables."
    )


def test_migration_creates_efa_id_index(migration_source: str):
    """upgrade() doit créer l'index ix_sites_efa_id."""
    upgrade_src = _extract_function_body_source(migration_source, "upgrade")
    assert "create_index" in upgrade_src and "efa_id" in upgrade_src, "Index ix_sites_efa_id non créé dans upgrade()"


def test_migration_drops_efa_id_index_in_downgrade(migration_source: str):
    """downgrade() doit drop l'index ix_sites_efa_id."""
    downgrade_src = _extract_function_body_source(migration_source, "downgrade")
    assert "drop_index" in downgrade_src and "efa_id" in downgrade_src, (
        "drop_index ix_sites_efa_id manquant dans downgrade()"
    )


def test_migration_uses_batch_alter_table(migration_source: str):
    """Migration utilise batch_alter_table('sites') (compat SQLite ALTER multiple).

    Référence : SQLAlchemy / Alembic best practice pour SQLite qui ne supporte
    pas ALTER TABLE multiple natif → batch reconstruit la table.
    """
    assert "batch_alter_table" in migration_source
    assert re.search(r'batch_alter_table\(["\']sites["\']', migration_source)


def test_migration_enums_use_native_enum_false(migration_source: str):
    """Tous les sa.Enum() de la migration doivent avoir native_enum=False.

    Compat SQLite (CHECK constraint) ↔ PostgreSQL (type ENUM natif) sans cassure.
    """
    enum_blocks = re.findall(r"sa\.Enum\([^)]*\)", migration_source, flags=re.DOTALL)
    assert enum_blocks, "Aucun sa.Enum trouvé dans la migration"
    for block in enum_blocks:
        assert "native_enum=False" in block, f"sa.Enum sans native_enum=False détecté : {block[:80]}..."


def test_migration_documents_cleanup_history(migration_source: str):
    """Docstring doit mentionner le nettoyage des 17 tables Enedis legacy.

    Anti-régression : si quelqu'un re-génère la migration via autogenerate
    sans nettoyer, le commentaire doit le rappeler.
    """
    assert "Enedis" in migration_source or "legacy" in migration_source.lower(), (
        "Docstring migration doit mentionner le nettoyage des tables legacy "
        "(traçabilité du retrait manuel des 17 drop_table autogenerate)."
    )
