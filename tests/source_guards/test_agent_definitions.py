"""Source-guard : structure .claude/agents/*.md (YAML valide, <150L, tools scope)."""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

READ_ONLY_AGENTS = {"code-reviewer", "qa-guardian", "security-auditor"}
FORBIDDEN_WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


@pytest.fixture(scope="module")
def agent_files() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*.md"))


def test_agents_dir_exists(agent_files: list[Path]) -> None:
    assert agent_files, f"Aucun agent dans {AGENTS_DIR}"


def test_agents_frontmatter_valid(agent_files: list[Path]) -> None:
    for path in agent_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert lines and lines[0] == "---", f"Frontmatter invalide : {path.name}"
        assert "---" in lines[1:10], f"Frontmatter non fermé : {path.name}"


def test_agents_under_150_lines(agent_files: list[Path]) -> None:
    oversized = [p.name for p in agent_files
                 if len(p.read_text(encoding="utf-8").splitlines()) > 150]
    assert not oversized, f"Agents >150L : {oversized}"


def test_readonly_agents_have_no_write_tools(agent_files: list[Path]) -> None:
    for path in agent_files:
        name = path.stem
        if name not in READ_ONLY_AGENTS:
            continue
        content = path.read_text(encoding="utf-8")
        tools_line = next(
            (line for line in content.splitlines() if line.startswith("tools:")),
            "",
        )
        for forbidden in FORBIDDEN_WRITE_TOOLS:
            assert forbidden not in tools_line, (
                f"Agent read-only '{name}' contient tool interdit '{forbidden}' : "
                f"{tools_line}"
            )


def test_agents_have_delegations_section(agent_files: list[Path]) -> None:
    missing = [
        p.name for p in agent_files
        if not re.search(r"^# Délégations sortantes", p.read_text(encoding="utf-8"), re.M)
    ]
    assert not missing, f"Section 'Délégations sortantes' manquante : {missing}"
