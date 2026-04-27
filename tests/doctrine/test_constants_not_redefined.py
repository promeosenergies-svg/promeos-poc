"""Vérifie que les valeurs inviolables n'apparaissent QUE dans constants.py.

Sprint P0 : 21 fichiers métier listés dans LEGACY_DEBT_ALLOWED conservent
temporairement des constantes hard-codées. Sprint P1 : migration progressive
vers `from backend.doctrine.constants import …` puis suppression de cette liste.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Valeurs sentinelles : si elles apparaissent ailleurs que constants.py et tests, alerte
SENTINELS = [
    (r"\b0\.052\b", "CO2_FACTOR_ELEC"),
    (r"\b0\.227\b", "CO2_FACTOR_GAS"),
    (r"\b0\.068\b", "PRICE_FALLBACK"),
    (r"\b7500\b", "DT_PENALTY"),
    (r"\b3750\b", "DT_PENALTY_AT_RISK"),
    (r"\b30\.85\b", "ACCISE_ELEC_T1"),
    (r"\b26\.58\b", "ACCISE_ELEC_T2"),
    (r"\b10\.73\b", "ACCISE_GAS"),
]

# Chemins toujours autorisés (SoT canonique + tests + docs + config YAML)
ALLOWED_PATHS = [
    "backend/doctrine/constants.py",
    "backend/doctrine/__init__.py",
    "tests/doctrine/",
    "backend/tests/",  # tests métier valident contre les valeurs SoT (oracles)
    "docs/",
    "backend/config/tarifs_reglementaires.yaml",
    "backend/venv/",  # dépendances tierces
]

# Dette legacy reconnue (sprint P0) — à migrer en P1 puis supprimer cette liste.
# Voir docs/doctrine/CHANGELOG.md → "Dette structurelle reconnue"
LEGACY_DEBT_ALLOWED = [
    "backend/config/default_prices.py",
    "backend/config/emission_factors.py",
    "backend/main.py",
    "backend/orchestration/agents/qa_guardian.py",
    "backend/orchestration/agents/regulatory.py",
    "backend/regops/rules/tertiaire_operat.py",
    "backend/routes/config_emission_factors.py",
    "backend/routes/config_price_references.py",
    "backend/routes/site_config.py",
    "backend/schemas/kpi_catalog.py",
    "backend/services/aper_service.py",
    "backend/services/benchmark_analysis.py",
    "backend/services/billing_engine/catalog.py",
    "backend/services/billing_engine/engine.py",
    "backend/services/billing_seed.py",
    "backend/services/billing_service.py",
    "backend/services/billing_shadow_v2.py",
    "backend/services/demo_seed/gen_notifications.py",
    "backend/services/demo_seed/packs.py",
    "backend/services/narrative/narrative_generator.py",
    "backend/services/usage_service.py",
]

ALL_ALLOWED = ALLOWED_PATHS + LEGACY_DEBT_ALLOWED


def is_allowed(path: Path) -> bool:
    rel = str(path.relative_to(REPO_ROOT))
    return any(allowed in rel for allowed in ALL_ALLOWED)


def test_sentinels_only_in_doctrine_or_legacy_debt():
    backend_dir = REPO_ROOT / "backend"
    violations: list[str] = []

    for py_file in backend_dir.rglob("*.py"):
        if is_allowed(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        for pattern, name in SENTINELS:
            if re.search(pattern, content):
                rel = py_file.relative_to(REPO_ROOT)
                violations.append(f"{rel}: contient {name} ({pattern})")

    assert not violations, (
        "NOUVELLES violations détectées (constantes inviolables redéfinies hors backend/doctrine/constants.py):\n"
        + "\n".join(violations)
        + "\n\nImporter depuis backend.doctrine.constants au lieu de hard-coder.\n"
        + "Si le fichier est legacy, l'ajouter à LEGACY_DEBT_ALLOWED avec ticket P1."
    )


def test_legacy_debt_list_is_documented():
    """Garantit que la dette est traçable dans le CHANGELOG."""
    changelog = (REPO_ROOT / "docs/doctrine/CHANGELOG.md").read_text(encoding="utf-8")
    assert "Dette structurelle reconnue" in changelog, (
        "Le CHANGELOG doctrine DOIT documenter la dette legacy. "
        "Voir docs/doctrine/CHANGELOG.md"
    )
