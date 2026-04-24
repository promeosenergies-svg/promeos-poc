"""Source-guard : CLAUDE.md racine mentionne les 11 agents et < 120L."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

ELEVEN_AGENTS = [
    "architect-helios",
    "implementer",
    "code-reviewer",
    "test-engineer",
    "qa-guardian",
    "regulatory-expert",
    "bill-intelligence",
    "ems-expert",
    "data-connector",
    "security-auditor",
    "prompt-architect",
]


def test_claude_md_exists() -> None:
    assert CLAUDE_MD.exists(), f"CLAUDE.md racine absent : {CLAUDE_MD}"


def test_claude_md_under_120_lines() -> None:
    n = len(CLAUDE_MD.read_text(encoding="utf-8").splitlines())
    assert n <= 120, f"CLAUDE.md = {n} lignes (plafond 120)"


@pytest.mark.parametrize("agent", ELEVEN_AGENTS)
def test_claude_md_mentions_agent(agent: str) -> None:
    content = CLAUDE_MD.read_text(encoding="utf-8")
    assert agent in content, f"CLAUDE.md ne mentionne pas `{agent}`"
