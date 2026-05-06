"""
PROMEOS — Tests cardinaux Phase 7.6 Sprint C-7 — 3 pre-commit hooks systémiques (ADR-016 Pilier 5).

Anti-régression Phase D+ : empêche récidive 5/5 angles morts Phase C audit transversal Phase 5.7.

3 hooks couverts :
- check_alembic_no_drop : anti-DROP autogenerate (Pilier 5 ADR-016)
- check_sqlite_pragma_fk : anti-PRAGMA-OFF (Pilier 2 ADR-016, Phase 5.6 F1)
- check_math_consistency : anti-erreur-arithmétique (Pilier 1 ADR-016, Phase 5.6 F3)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / "scripts" / "pre_commit_hooks"

_HOOK_ALEMBIC = _HOOKS_DIR / "check_alembic_no_drop.py"
_HOOK_PRAGMA = _HOOKS_DIR / "check_sqlite_pragma_fk.py"
_HOOK_MATH = _HOOKS_DIR / "check_math_consistency.py"


def _run_hook(hook_path: Path, *files: Path) -> tuple[int, str, str]:
    """Exécute un hook avec liste fichiers, retourne (returncode, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(hook_path), *(str(f) for f in files)],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return proc.returncode, proc.stdout, proc.stderr


# ─── Hook 1 — anti-DROP Alembic ────────────────────────────────────────────


def test_phase76_anti_drop_alembic_blocks_op_drop_table_unauthorized(tmp_path):
    """Phase 7.6 cardinal : op.drop_table sans override → exit 1."""
    migration = tmp_path / "test_migration.py"
    migration.write_text('"""Test migration."""\ndef upgrade():\n    op.drop_table("legacy_orphan_table")\n')
    rc, _, stderr = _run_hook(_HOOK_ALEMBIC, migration)
    assert rc == 1
    assert "Anti-DROP Alembic" in stderr
    assert "drop_table" in stderr


def test_phase76_anti_drop_alembic_allows_with_authorized_comment(tmp_path):
    """Phase 7.6 : override `# ALEMBIC_DROP_AUTHORIZED:` autorise drop justifié."""
    migration = tmp_path / "test_migration.py"
    migration.write_text(
        '"""Test migration."""\n'
        "def upgrade():\n"
        "    # ALEMBIC_DROP_AUTHORIZED: legacy_orphan_table archivée Sprint X-Y, GDPR retention 5 ans\n"
        '    op.drop_table("legacy_orphan_table")\n'
    )
    rc, _, _ = _run_hook(_HOOK_ALEMBIC, migration)
    assert rc == 0


def test_phase76_anti_drop_alembic_blocks_drop_index_and_drop_constraint(tmp_path):
    """Phase 7.6 : drop_index + drop_constraint aussi bloqués (3 patterns)."""
    migration_idx = tmp_path / "mig_idx.py"
    migration_idx.write_text("def upgrade():\n    op.drop_index('ix_foo')\n")
    rc1, _, _ = _run_hook(_HOOK_ALEMBIC, migration_idx)
    assert rc1 == 1

    migration_constr = tmp_path / "mig_constr.py"
    migration_constr.write_text("def upgrade():\n    op.drop_constraint('uq_bar')\n")
    rc2, _, _ = _run_hook(_HOOK_ALEMBIC, migration_constr)
    assert rc2 == 1


def test_phase76_anti_drop_alembic_allows_drops_inside_downgrade_function(tmp_path):
    """Phase 7.6 : drops dans `def downgrade()` autorisés (reverse upgrade — Alembic standard).

    Anti-faux-positif cardinal : sans cette exception, hook bloque toutes migrations
    Alembic existantes Phase C (qui ont toutes des downgrade() avec drops légitimes).
    """
    migration = tmp_path / "test_migration.py"
    migration.write_text(
        '"""Test migration."""\n'
        "def upgrade():\n"
        '    op.create_table("foo", ...)\n'
        "\n"
        "def downgrade():\n"
        '    op.drop_table("foo")\n'  # legitimate reverse of upgrade
        '    op.drop_index("ix_foo_bar", "foo")\n'
        '    op.drop_constraint("uq_foo", "foo")\n'
    )
    rc, _, stderr = _run_hook(_HOOK_ALEMBIC, migration)
    assert rc == 0, f"drops dans downgrade() doivent être autorisés. stderr={stderr}"


def test_phase76_anti_drop_alembic_skips_original_autogenerate_backups(tmp_path):
    """Phase 7.6 : fichiers `.original-autogenerate` (backups audit) skipés."""
    backup = tmp_path / "test_migration.py.original-autogenerate"
    backup.write_text("def upgrade():\n    op.drop_table('orphan')\n")
    rc, _, _ = _run_hook(_HOOK_ALEMBIC, backup)
    assert rc == 0  # skip — backup audit


# ─── Hook 2 — anti-PRAGMA-OFF SQLite ────────────────────────────────────────


def test_phase76_anti_pragma_off_blocks_connection_without_pragma(tmp_path):
    """Phase 7.6 cardinal : connection.py sans PRAGMA foreign_keys=ON → exit 1."""
    conn = tmp_path / "connection.py"
    conn.write_text(
        '"""DB connection."""\n'
        "from sqlalchemy import create_engine\n"
        "engine = create_engine('sqlite:///foo.db')\n"
        "# PRAGMA foreign_keys=ON manquant — régression Phase 5.6 F1\n"
    )
    rc, _, stderr = _run_hook(_HOOK_PRAGMA, conn)
    assert rc == 1
    assert "Anti-PRAGMA-OFF" in stderr
    assert "PRAGMA foreign_keys=ON" in stderr


def test_phase76_anti_pragma_off_allows_with_event_listener_pragma_on(tmp_path):
    """Phase 7.6 : PRAGMA + event listener `connect` présents → exit 0."""
    conn = tmp_path / "connection.py"
    conn.write_text(
        "from sqlalchemy import event, create_engine\n"
        "engine = create_engine('sqlite:///foo.db')\n"
        "\n"
        '@event.listens_for(engine, "connect")\n'
        "def _enable_fk(dbapi_conn, conn_record):\n"
        "    cursor = dbapi_conn.cursor()\n"
        '    cursor.execute("PRAGMA foreign_keys=ON")\n'
        "    cursor.close()\n"
    )
    rc, _, _ = _run_hook(_HOOK_PRAGMA, conn)
    assert rc == 0


def test_phase76_anti_pragma_off_skips_other_files(tmp_path):
    """Phase 7.6 : hook ne traite QUE connection.py (autres fichiers ignorés)."""
    other = tmp_path / "models.py"
    other.write_text("# pas de PRAGMA ici, normal\n")
    rc, _, _ = _run_hook(_HOOK_PRAGMA, other)
    assert rc == 0  # skip — pas le fichier cible


# ─── Hook 3 — anti-erreur-arithmétique ──────────────────────────────────────


def test_phase76_anti_arithmetic_blocks_phase5_6_f3_error_3_15_x_1_2_div_8760_eq_0_43(tmp_path):
    """Phase 7.6 CARDINAL anti-régression : exact erreur Phase 5.6 F3 ×1000.

    Documenté faussement : 3.15 × 1.2 / 8760 = 0.43 (calcul réel = 0.000432)
    """
    yaml_file = tmp_path / "sources_reglementaires.yaml"
    yaml_file.write_text("# Faux historique Phase 4.2 : 3.15 × 1.2 / 8760 = 0.43 EUR/MWh\nCAPACITE: { rate: 0.43 }\n")
    rc, _, stderr = _run_hook(_HOOK_MATH, yaml_file)
    assert rc == 1
    assert "Anti-erreur-arithmetique" in stderr
    assert "Formule incoherente" in stderr or "incoherente" in stderr


def test_phase76_anti_arithmetic_allows_phase5_6_f3_correction_3150(tmp_path):
    """Phase 7.6 : correction Phase 5.6 F3 : 3150 × 1.2 / 8760 ≈ 0.4315 → OK."""
    yaml_file = tmp_path / "sources_reglementaires.yaml"
    yaml_file.write_text("# Correction Phase 5.6 F3 : 3150 × 1.2 / 8760 = 0.4315 EUR/MWh\nCAPACITE: { rate: 0.4315 }\n")
    rc, _, _ = _run_hook(_HOOK_MATH, yaml_file)
    assert rc == 0


def test_phase76_anti_arithmetic_tolerance_5pct_acceptable(tmp_path):
    """Phase 7.6 : arrondis ≤5% acceptables (10 × 3 / 6 = 4.95 OK car écart 1%)."""
    yaml_file = tmp_path / "sources.yaml"
    yaml_file.write_text("Formule arrondie : 10 * 3 / 6 = 4.95\n")
    rc, _, _ = _run_hook(_HOOK_MATH, yaml_file)
    assert rc == 0  # 5.0 vs 4.95 → écart 1% < tolerance 5%


def test_phase76_anti_arithmetic_supports_unicode_multiplication_sign(tmp_path):
    """Phase 7.6 : pattern doit matcher × (Unicode) ET * (ASCII)."""
    yaml_file = tmp_path / "sources.yaml"
    yaml_file.write_text("Formule × : 100 × 2 / 4 = 999\n")
    rc, _, stderr = _run_hook(_HOOK_MATH, yaml_file)
    assert rc == 1
    assert "incoherente" in stderr


def test_phase76_anti_arithmetic_supports_french_decimal_comma(tmp_path):
    """Phase 7.6 : virgule décimale FR (`3,15`) acceptée comme séparateur."""
    yaml_file = tmp_path / "sources.yaml"
    yaml_file.write_text("Formule FR : 3,15 * 1,2 / 8760 = 999\n")
    rc, _, _ = _run_hook(_HOOK_MATH, yaml_file)
    # 3.15 × 1.2 / 8760 ≈ 0.000432 ≠ 999 → violation détectée
    assert rc == 1


# ─── Source-guard infrastructure ────────────────────────────────────────────


def test_phase76_pre_commit_config_present_at_repo_root():
    """SG cardinal : `.pre-commit-config.yaml` greenfield créé Phase 7.6."""
    config = _REPO_ROOT / ".pre-commit-config.yaml"
    assert config.exists(), (
        "Phase 7.6 BLOQUANT : `.pre-commit-config.yaml` absent à la racine.\n"
        "Greenfield Phase 7.6 = création initiale doctrine ADR-016 Pilier 5."
    )
    content = config.read_text(encoding="utf-8")
    # 3 hooks cardinaux
    assert "anti-drop-alembic" in content
    assert "anti-pragma-foreign-keys-off" in content
    assert "anti-erreur-arithmetique" in content


def test_phase76_three_hooks_present_in_repo():
    """SG : 3 scripts hooks présents et exécutables."""
    for hook in (_HOOK_ALEMBIC, _HOOK_PRAGMA, _HOOK_MATH):
        assert hook.exists(), f"Hook manquant : {hook.name}"
        # Premier ligne shebang ou docstring
        content = hook.read_text(encoding="utf-8")
        assert content.startswith("#!") or content.startswith('"""')
