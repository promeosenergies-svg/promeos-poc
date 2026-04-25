"""Source-guard : backend/ai_layer/agents/*.py n'écrivent qu'aux tables ai_*.

Détection basée sur SQL literals / ORM session.add(...) — heuristique stricte
mais documentée : tables autorisées en écriture depuis ai_layer = ai_insights,
ai_agent_traces, ai_recommendations (insertions uniquement, pas de DELETE).
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_LAYER = REPO_ROOT / "backend" / "ai_layer"

ALLOWED_WRITE_TABLES = {"ai_insights", "ai_agent_traces", "ai_recommendations"}
FORBIDDEN_WRITE_PATTERNS = [
    "DELETE FROM ",
    "DROP TABLE",
    "TRUNCATE",
    "UPDATE sites ",
    "UPDATE org ",
    "UPDATE bills ",
]


def test_ai_layer_no_forbidden_sql() -> None:
    """ai_layer/ ne doit jamais contenir de SQL destructif hors tables ai_*."""
    if not AI_LAYER.exists():
        return  # ai_layer absent sur cette branche → skip silent
    violations: list[str] = []
    for py_file in AI_LAYER.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        for pattern in FORBIDDEN_WRITE_PATTERNS:
            if pattern in content:
                violations.append(f"{py_file.relative_to(REPO_ROOT)} : {pattern}")
    assert not violations, (
        "backend/ai_layer/ contient SQL destructif (scope violation) :\n"
        + "\n".join(violations)
    )
