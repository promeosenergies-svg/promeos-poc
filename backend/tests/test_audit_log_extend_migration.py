"""
PROMEOS — Sprint C-2 Phase 1.2 : Tests statiques migration f415992b3d25.

Vérifie :
- 6 add_column dans upgrade()
- 6 drop_column dans downgrade() symétrique
- 2 create_index dans upgrade()
- Pas de drop_table en code actif (anti-régression cleanup pattern)
- Revision IDs corrects (f415992b3d25 revises c8f1246522f9)
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
_MIGRATION_PATH = _BACKEND_ROOT / "alembic" / "versions" / "f415992b3d25_audit_log_extend_for_patrimoine_cascade.py"


NEW_COLUMNS = [
    "correlation_id",
    "org_id",
    "field_modified",
    "old_value",
    "new_value",
    "user_agent",
]


@pytest.fixture(scope="module")
def migration_source() -> str:
    if not _MIGRATION_PATH.exists():
        pytest.fail(f"Migration manquante : {_MIGRATION_PATH}")
    return _MIGRATION_PATH.read_text(encoding="utf-8")


def _extract_function_source(source: str, func_name: str) -> str:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return ast.get_source_segment(source, node) or ""
    return ""


def test_migration_file_exists():
    assert _MIGRATION_PATH.is_file()


def test_migration_revision_ids(migration_source):
    """f415992b3d25 revises c8f1246522f9 (Phase 3 Sprint C-1 HEAD précédent)."""
    assert re.search(r'revision:\s*str\s*=\s*["\']f415992b3d25["\']', migration_source)
    assert re.search(r'down_revision[^=]*=\s*["\']c8f1246522f9["\']', migration_source)


def test_migration_upgrade_adds_6_columns(migration_source):
    """upgrade() ajoute exactement 6 colonnes."""
    upgrade_src = _extract_function_source(migration_source, "upgrade")
    add_count = upgrade_src.count("add_column(")
    assert add_count == 6, f"upgrade() : {add_count} add_column trouvés (attendu 6)"

    for col in NEW_COLUMNS:
        pattern = re.compile(rf'["\']{re.escape(col)}["\']')
        assert pattern.search(upgrade_src), f"add_column manquant pour {col}"


def test_migration_upgrade_creates_2_indexes(migration_source):
    """upgrade() crée 2 index : correlation_id + (org_id, resource_type, created_at)."""
    upgrade_src = _extract_function_source(migration_source, "upgrade")
    idx_count = upgrade_src.count("create_index(")
    assert idx_count == 2, f"upgrade() : {idx_count} create_index (attendu 2)"
    assert "ix_audit_correlation_id" in upgrade_src
    assert "ix_audit_org_id_resource_type_created" in upgrade_src


def test_migration_downgrade_drops_6_columns(migration_source):
    """downgrade() drop exactement 6 colonnes (symétrique upgrade)."""
    downgrade_src = _extract_function_source(migration_source, "downgrade")
    drop_count = downgrade_src.count("drop_column(")
    assert drop_count == 6

    for col in NEW_COLUMNS:
        pattern = re.compile(rf'drop_column\(["\']{re.escape(col)}["\']\)')
        assert pattern.search(downgrade_src), f"drop_column manquant pour {col}"


def test_migration_downgrade_drops_2_indexes(migration_source):
    """downgrade() drop les 2 index avant les colonnes."""
    downgrade_src = _extract_function_source(migration_source, "downgrade")
    assert downgrade_src.count("drop_index(") == 2


def test_migration_no_destructive_drop_table(migration_source):
    """Aucun drop_table ou create_table en code actif (anti-régression Phase 3 cleanup pattern).

    Tolère uniquement les mentions en docstring (qui expliquent le nettoyage des
    drops Enedis legacy).
    """
    sanitized = re.sub(r'"""[\s\S]*?"""', "", migration_source)
    sanitized = re.sub(r"'''[\s\S]*?'''", "", sanitized)
    sanitized = "\n".join(line.split("#", 1)[0] for line in sanitized.splitlines())
    assert "drop_table(" not in sanitized
    assert "create_table(" not in sanitized


def test_migration_uses_batch_alter_table_audit_logs(migration_source):
    """Migration utilise batch_alter_table('audit_logs') (compat SQLite)."""
    assert re.search(r'batch_alter_table\(["\']audit_logs["\']', migration_source)


def test_migration_documents_legacy_cleanup(migration_source):
    """Docstring mentionne le nettoyage des drops Enedis legacy."""
    assert "Enedis" in migration_source or "legacy" in migration_source.lower()
