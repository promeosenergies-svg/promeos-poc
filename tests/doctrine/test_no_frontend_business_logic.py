"""Vérifie qu'aucune logique métier critique n'est calculée côté frontend."""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Patterns interdits dans le frontend (signe de calcul métier)
FORBIDDEN_PATTERNS = [
    (r"\*\s*0\.052\b", "Calcul CO2 frontend"),
    (r"\*\s*0\.227\b", "Calcul CO2 gas frontend"),
    (r"\*\s*1\.9\b", "Calcul énergie primaire frontend"),
    (r"\*\s*0\.068\b", "Calcul prix fallback frontend"),
    (r"\*\s*7500\b", "Calcul pénalité DT frontend"),
]

FRONTEND_DIRS = ["frontend/src"]
ALLOWED_FILES = [".test.", ".spec.", "/tests/", "/__tests__/"]


def test_no_business_logic_in_frontend():
    violations: list[str] = []

    for fdir in FRONTEND_DIRS:
        d = REPO_ROOT / fdir
        if not d.exists():
            continue
        for ext in ("*.jsx", "*.tsx", "*.js", "*.ts"):
            for f in d.rglob(ext):
                if any(allowed in str(f) for allowed in ALLOWED_FILES):
                    continue
                try:
                    content = f.read_text(encoding="utf-8")
                except (UnicodeDecodeError, PermissionError):
                    continue
                for pattern, label in FORBIDDEN_PATTERNS:
                    if re.search(pattern, content):
                        rel = f.relative_to(REPO_ROOT)
                        violations.append(f"{rel}: {label} ({pattern})")

    assert not violations, (
        "Logique métier détectée dans le frontend (Doctrine §12.3):\n"
        + "\n".join(violations)
        + "\n\nMigrer vers un endpoint backend dédié."
    )
