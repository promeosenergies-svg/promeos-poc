"""Source-guard : skills .claude/skills/*/SKILL.md ont SoT + last_verified + anti-patterns."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# Skills créées en Phase 3A — doctrine frontmatter enrichi
PHASE_3A_SKILLS = [
    "emission_factors",
    "regops_constants",
    "regulatory_calendar",
    "helios_architecture",
]


@pytest.mark.parametrize("skill_name", PHASE_3A_SKILLS)
def test_skill_file_exists(skill_name: str) -> None:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    assert path.exists(), f"Skill manquante : {path}"


@pytest.mark.parametrize("skill_name", PHASE_3A_SKILLS)
def test_skill_has_source_of_truth(skill_name: str) -> None:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    assert "\nsource_of_truth:" in content or content.startswith("source_of_truth:"), (
        f"{skill_name} : frontmatter source_of_truth manquant"
    )


@pytest.mark.parametrize("skill_name", PHASE_3A_SKILLS)
def test_skill_has_last_verified(skill_name: str) -> None:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    assert "\nlast_verified:" in content, f"{skill_name} : last_verified manquant"


@pytest.mark.parametrize("skill_name", PHASE_3A_SKILLS)
def test_skill_has_antipatterns_section(skill_name: str) -> None:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    content = path.read_text(encoding="utf-8")
    assert "Anti-patterns" in content, f"{skill_name} : section Anti-patterns manquante"


@pytest.mark.parametrize("skill_name", PHASE_3A_SKILLS)
def test_skill_under_200_lines(skill_name: str) -> None:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    n = len(path.read_text(encoding="utf-8").splitlines())
    assert n <= 200, f"{skill_name} : {n} lignes (plafond 200)"
