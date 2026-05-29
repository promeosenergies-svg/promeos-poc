"""
PROMEOS — Source-guard : modèle canonique MktPrice vs legacy MarketPrice.

Sprint Énergie P0.S1a (2026-05-29, brief P2.3).

Contexte :
- `MarketPrice` (table `market_prices`, fichier `models/market_price.py`)
  est DEPRECATED. Le commentaire docstring du fichier le confirme.
- `MktPrice` (table `mkt_prices`, fichier `models/market_models.py`) est la
  source-of-truth canonique pour tous les prix marché (spot, forward, etc.).
- Une migration progressive est en cours (cf. fix/market-data-cleanup).
- La table legacy sera droppée dans une migration Alembic future.

Ce guard empêche tout NOUVEAU import de `MarketPrice` (legacy) dans le code
applicatif (services, routes, api/). Seuls les fichiers listés en WHITELIST
peuvent encore référencer le modèle legacy — typiquement :
- le modèle lui-même (`models/market_price.py`)
- les seeds qui peuplent encore la table legacy en démo
- les scripts de migration explicite legacy → canonical

À chaque nettoyage d'un consommateur legacy, retirer l'entrée WHITELIST
correspondante. Quand WHITELIST = ∅ + table droppée Alembic = on peut
supprimer ce guard et le modèle MarketPrice.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND = REPO_ROOT / "backend"


# Whitelist explicite — fichiers autorisés à référencer MarketPrice legacy.
# Toute entrée DOIT documenter pourquoi + plan de cleanup.
LEGACY_MARKET_PRICE_WHITELIST: dict[str, str] = {
    # Le modèle lui-même — sera supprimé après DROP TABLE Alembic.
    "backend/models/market_price.py": (
        "Modèle deprecated lui-même (DEPRECATED docstring explicite). "
        "À supprimer après migration Alembic DROP TABLE market_prices "
        "(cf. P2.2 plan refonte audit 2026-05-29)."
    ),
    # Tests qui valident la coexistence legacy/canonical.
    "backend/tests/source_guards/test_market_price_canonical_source_guards.py": (
        "Ce guard lui-même référence le nom pour le détecter."
    ),
    # Seeds qui peuplent encore la table legacy (cf. commentaire models/market_price.py).
    # À retirer après migration seed_data.py vers mkt_prices.
    "backend/services/demo_seed/gen_market_prices.py": (
        "Seed démo legacy. À migrer vers mkt_prices avant DROP TABLE Alembic "
        "(cf. commentaire models/market_models.py:14 TODO migration tracking)."
    ),
}


# Pattern d'import (couvre les variantes courantes).
FORBIDDEN_IMPORT_PATTERNS = [
    re.compile(r"from\s+models\.market_price\s+import\s+", re.MULTILINE),
    re.compile(r"from\s+models\s+import\s+[^#\n]*\bMarketPrice\b", re.MULTILINE),
    re.compile(r"import\s+models\.market_price\b", re.MULTILINE),
    # Référence directe sans import explicite (rare mais possible).
    re.compile(r"\bmodels\.market_price\.MarketPrice\b"),
    re.compile(r"\bMarketPrice\s*\("),  # instanciation directe
]


def _scan_for_legacy_imports() -> list[tuple[str, int, str]]:
    """Cherche tous les imports/usages MarketPrice legacy hors whitelist."""
    violations: list[tuple[str, int, str]] = []
    targets: list[Path] = []
    for sub in ("services", "routes", "api", "app"):
        d = BACKEND / sub
        if d.exists():
            targets.extend(d.rglob("*.py"))
    # Inclure aussi quelques racines : main.py, jobs/
    for extra in ("main.py", "jobs"):
        p = BACKEND / extra
        if p.is_file():
            targets.append(p)
        elif p.is_dir():
            targets.extend(p.rglob("*.py"))

    for py_file in sorted(set(targets)):
        rel = py_file.relative_to(REPO_ROOT).as_posix()
        if rel in LEGACY_MARKET_PRICE_WHITELIST:
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for pattern in FORBIDDEN_IMPORT_PATTERNS:
            for match in pattern.finditer(content):
                line_no = content[: match.start()].count("\n") + 1
                snippet = match.group(0)[:100]
                violations.append((rel, line_no, snippet))
    return violations


class TestMarketPriceCanonical:
    """Garde-fous modèle canonique MktPrice (mkt_prices)."""

    def test_no_new_imports_of_legacy_market_price(self):
        """Aucun nouvel import du modèle legacy MarketPrice (hors whitelist).

        Doctrine : utiliser `MktPrice` depuis `models/market_models.py`
        pour tout nouveau code (spot, forward, etc.).
        """
        violations = _scan_for_legacy_imports()
        if violations:
            msg = (
                "\n\n🔴 Import du modèle legacy `MarketPrice` détecté "
                "(modèle DEPRECATED, utiliser `MktPrice` canonique).\n\n"
                + "\n".join(f"  {rel}:{line} → « {snippet} »" for rel, line, snippet in violations)
                + "\n\nMigration : `from models.market_models import MktPrice` "
                "+ adapter les requêtes (cf. fix/market-data-cleanup PRs).\n"
                + "Si dérogation nécessaire (script migration, etc.) : "
                "ajouter à LEGACY_MARKET_PRICE_WHITELIST avec justification.\n"
            )
            pytest.fail(msg)

    def test_canonical_mkt_price_model_exists(self):
        """Sanity check : le modèle canonique MktPrice existe bien."""
        market_models = BACKEND / "models" / "market_models.py"
        assert market_models.exists(), (
            f"models/market_models.py introuvable — modèle canonique MktPrice "
            f"manquant ! Le guard est inutile sans modèle canonique."
        )
        content = market_models.read_text(encoding="utf-8")
        assert "MktPrice" in content or "mkt_prices" in content, (
            "models/market_models.py n'expose ni `MktPrice` ni `mkt_prices` — "
            "le modèle canonique a peut-être été renommé. Mettre à jour ce guard."
        )

    def test_legacy_model_is_marked_deprecated(self):
        """Le modèle legacy doit porter une mention DEPRECATED claire."""
        legacy_model = BACKEND / "models" / "market_price.py"
        if not legacy_model.exists():
            # Modèle déjà supprimé : le guard devient inutile (succès trivial).
            return
        content = legacy_model.read_text(encoding="utf-8")
        assert re.search(r"deprecated", content, re.IGNORECASE), (
            "backend/models/market_price.py ne porte pas de mention 'DEPRECATED'. "
            "Ajouter une docstring explicite pour empêcher tout réemploi."
        )

    def test_whitelist_entries_have_justification(self):
        """Toute entrée whitelist doit avoir une justification non vide."""
        for path, reason in LEGACY_MARKET_PRICE_WHITELIST.items():
            assert reason and reason.strip(), f"WHITELIST entry '{path}' has empty justification."
