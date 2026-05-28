"""Source-guard : aucun nom de concurrent dans les strings rendus à
l'utilisateur PROMEOS (FE + BE).

Doctrine : `feedback_promeos_zero_concurrent_ui` (mémoire 2026-05-28).
Incident : `DISCLAIMER_MUTUALISATION` exposait « Source : Advizeo 2026 »
dans le bandeau /conformite — corrigé 2026-05-28.

Périmètre :
- Strings Python rendus via API (services qui populent des response models,
  messages d'erreur HTTPException, narrative_generator output).
- Strings FE (jsx/tsx) qui ne sont pas dans un docstring/commentaire.

Hors périmètre (autorisé) :
- Commentaires Python `#` et docstrings `\"\"\"...\"\"\"` (différenciation
  interne, briefs, ADRs).
- KB drafts (`docs/kb/drafts/`) : artefacts de recherche, jamais rendus.
- Source-guards eux-mêmes (qui doivent citer les concurrents pour les
  filtrer).
"""

import re
from pathlib import Path

import pytest

# Liste des concurrents à proscrire dans tout texte rendu à l'utilisateur.
COMPETITOR_NAMES: list[str] = [
    "Advizeo",
    "Deepki",
    "Metron",
    "Metroscope",
    "Citron",
    "Energisme",
    "Trinergy",
    "Spacewell",
    "HelloWatt",
    "Wattics",
]

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent

# Fichiers BE susceptibles d'exposer un STRING utilisateur :
# - services/* (response messages, disclaimers, narrative)
# - routes/* (HTTPException.detail messages)
# - schemas/* (Field descriptions exposées via /docs)
USER_FACING_BACKEND_GLOBS: list[str] = [
    "services/**/*.py",
    "routes/**/*.py",
    "schemas/**/*.py",
]

# Frontend : tout fichier prod (hors tests + node_modules + __tests__).
USER_FACING_FRONTEND_GLOB = "src/**/*"

# Allowlist : fichiers où la mention est explicitement souhaitée (ce
# source-guard inclus, doc de stratégie compétitive interne, etc.).
ALLOWED_PATHS = {
    # Ce fichier de test lui-même.
    "backend/tests/source_guards/test_no_competitor_in_user_facing_strings.py",
    # Tests qui pinçaient l'absence de différenciation interne.
    "backend/tests/source_guards/test_regulatory_rates_internal_doctrine_filter_source_guards.py",
}


def _strip_python_comments_and_docstrings(src: str) -> str:
    """Supprime commentaires et docstrings d'un source Python.

    Approche conservative : on retire les blocs `\"\"\"..\"\"\"` et `'''..'''`
    (greedy multi-ligne) puis les commentaires `# ...` jusqu'à fin de
    ligne. Ce qui reste = strings inline + code. C'est suffisant pour le
    grep `Advizeo` qui ne survivra que dans un STRING littéral exposé.
    """
    # Triple-quoted strings (docstrings + multi-line strings).
    # On les retire AUSSI quand elles sont des strings d'instance (ex
    # un `"""...""" + var`) car la doctrine interne PROMEOS ne renvoie
    # JAMAIS de message utilisateur depuis une triple-quoted string —
    # tous les messages exposés sont des f-strings ou strings simples
    # `"..."`. Faux positifs ici sont acceptables (la règle est stricte).
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    src = re.sub(r"'''[\s\S]*?'''", "", src)
    # Commentaires de ligne.
    src = re.sub(r"#[^\n]*", "", src)
    return src


def _strip_jsx_comments(src: str) -> str:
    """Supprime commentaires JSX/JS (/* */ et //)."""
    src = re.sub(r"/\*[\s\S]*?\*/", "", src)
    src = re.sub(r"//[^\n]*", "", src)
    return src


@pytest.mark.parametrize("competitor", COMPETITOR_NAMES)
def test_no_competitor_in_backend_user_facing_strings(competitor: str) -> None:
    """Chaque concurrent listé NE DOIT PAS apparaître dans un string
    rendu par les services/routes/schemas BE PROMEOS.

    Ne checke QUE le code "vivant" — commentaires + docstrings retirés
    avant grep (différenciation interne autorisée).
    """
    violations: list[str] = []
    for glob in USER_FACING_BACKEND_GLOBS:
        for path in BACKEND_ROOT.glob(glob):
            rel = path.relative_to(PROJECT_ROOT).as_posix()
            if rel in ALLOWED_PATHS:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            stripped = _strip_python_comments_and_docstrings(text)
            if competitor.lower() in stripped.lower():
                violations.append(rel)
    assert not violations, (
        f"Concurrent « {competitor} » trouvé dans des strings vivants BE : "
        f"{violations}. Doctrine : zéro concurrent dans l'UI "
        f"(cf. feedback_promeos_zero_concurrent_ui)."
    )


@pytest.mark.parametrize("competitor", COMPETITOR_NAMES)
def test_no_competitor_in_frontend_rendered_strings(competitor: str) -> None:
    """Chaque concurrent listé NE DOIT PAS apparaître dans du code FE
    rendu (hors commentaires)."""
    frontend_root = PROJECT_ROOT / "frontend"
    violations: list[str] = []
    for path in frontend_root.glob(USER_FACING_FRONTEND_GLOB):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".js", ".jsx", ".ts", ".tsx"}:
            continue
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        if "/__tests__/" in rel or "/tests/" in rel:
            continue
        if rel in ALLOWED_PATHS:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        stripped = _strip_jsx_comments(text)
        if competitor.lower() in stripped.lower():
            violations.append(rel)
    assert not violations, (
        f"Concurrent « {competitor} » trouvé dans du code FE rendu : "
        f"{violations}. Doctrine : zéro concurrent dans l'UI."
    )
