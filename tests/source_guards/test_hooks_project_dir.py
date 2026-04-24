"""Source-guard : hooks .claude/settings.json et tools/hooks/ utilisent $CLAUDE_PROJECT_DIR.

Leçon Phase 4 (2026-04-24) : un chemin relatif dans hooks settings.json crée
un deadlock silencieux quand le cwd Claude Code devient un sous-dossier.
Toute commande hook doit référencer $CLAUDE_PROJECT_DIR pour la robustesse.
"""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = REPO_ROOT / ".claude" / "settings.json"
HOOKS_DIR = REPO_ROOT / "tools" / "hooks"


def test_settings_json_exists_and_valid() -> None:
    assert SETTINGS.exists(), f".claude/settings.json absent : {SETTINGS}"
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    assert "hooks" in data, "settings.json sans section `hooks`"


def test_hook_commands_use_project_dir_env() -> None:
    """Toute command `python3 tools/hooks/...` doit passer par $CLAUDE_PROJECT_DIR."""
    data = json.loads(SETTINGS.read_text(encoding="utf-8"))
    offenders: list[str] = []
    for event_type, blocks in data.get("hooks", {}).items():
        for block in blocks:
            for h in block.get("hooks", []):
                cmd = h.get("command", "")
                if "tools/hooks/" in cmd and "$CLAUDE_PROJECT_DIR" not in cmd:
                    offenders.append(f"{event_type}: {cmd}")
    assert not offenders, (
        "Commands hooks sans $CLAUDE_PROJECT_DIR (deadlock risque) :\n"
        + "\n".join(offenders)
    )


def test_hook_scripts_avoid_relative_open() -> None:
    """Scripts Python hooks ne doivent pas utiliser open('./...') ou Path('./...') relatif."""
    if not HOOKS_DIR.exists():
        pytest.skip("tools/hooks absent")
    forbidden = ('open("./', "open('./", 'Path("./', "Path('./")
    offenders: list[str] = []
    for py in HOOKS_DIR.glob("*.py"):
        content = py.read_text(encoding="utf-8")
        if any(f in content for f in forbidden):
            offenders.append(py.name)
    assert not offenders, f"Scripts hooks avec chemins relatifs : {offenders}"
