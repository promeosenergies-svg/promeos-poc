"""Vérifie que les supports d'imprégnation existent."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_doctrine_source_file_exists():
    assert (REPO_ROOT / "docs/doctrine/doctrine_promeos_sol_v1_1.md").exists()


def test_claude_md_has_cardinal_rules():
    p = REPO_ROOT / "CLAUDE.md"
    assert p.exists(), "CLAUDE.md doit exister à la racine"
    content = p.read_text(encoding="utf-8")
    assert "Doctrine cardinale" in content
    # Présence des 10 règles via mots-clés
    for keyword in ["Tout est lié", "Non-sachants", "KPI magique",
                    "Constantes inviolables", "Statuts data", "logique métier",
                    "Cohérence transverse", "Erreurs API", "Org-scoping"]:
        assert keyword in content, f"CLAUDE.md manque: {keyword}"


def test_skill_promeos_doctrine_exists():
    skill = REPO_ROOT / ".claude/skills/promeos-doctrine/SKILL.md"
    assert skill.exists()
    refs = REPO_ROOT / ".claude/skills/promeos-doctrine/references"
    assert refs.is_dir()
    expected = ["doctrine_complete.md", "principes.md", "anti_patterns.md",
                "checklist_qa.md", "kpi_doctrine.md"]
    for ref in expected:
        assert (refs / ref).exists(), f"Reference manquante: {ref}"


def test_agents_doctrine_header_exists():
    h = REPO_ROOT / "agents/_doctrine_header.md"
    assert h.exists(), "Header doctrinal agents manquant"
    content = h.read_text(encoding="utf-8")
    assert "Contrat doctrinal PROMEOS Sol v1.1" in content
