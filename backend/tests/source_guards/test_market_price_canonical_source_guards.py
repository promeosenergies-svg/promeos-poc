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


class TestMarketPriceCanonicalP2_3:
    """Sprint Énergie P2.3 (2026-05-30) — durcissement migration MarketPrice.

    Couverture renforcée :
    - aucun fichier `backend/services/energy_orchestration/*` n'importe
      `MarketPrice` (vérifie le SoT orchestration énergie).
    - `market_data_service.py` n'importe pas MarketPrice si présent.
    - `billing_service.py` n'importe pas MarketPrice.
    - le modèle legacy porte le marquage DEPRECATED P2.3 explicite.
    """

    def test_energy_orchestration_no_market_price_import(self):
        """Aucun import MarketPrice dans backend/services/energy_orchestration/.

        Le SoT canonique pour la brique Énergie est MktPrice (cf. P1.S2d).
        """
        orchestration_dir = BACKEND / "services" / "energy_orchestration"
        assert orchestration_dir.exists(), (
            "backend/services/energy_orchestration/ introuvable — répertoire SoT brique Énergie manquant."
        )
        for py_file in sorted(orchestration_dir.rglob("*.py")):
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            content = py_file.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_IMPORT_PATTERNS:
                # Skip if just a comment mentioning the name (no import)
                for match in pattern.finditer(content):
                    line_no = content[: match.start()].count("\n") + 1
                    line = content.split("\n")[line_no - 1]
                    if line.strip().startswith("#"):
                        continue
                    pytest.fail(
                        f"🔴 P2.3 — Import legacy MarketPrice dans SoT Énergie : "
                        f"{rel}:{line_no} → « {match.group(0)[:80]} ». "
                        f"Utiliser MktPrice depuis models.market_models."
                    )

    def test_billing_service_no_market_price_import(self):
        """billing_service.py n'importe pas le modèle legacy MarketPrice.

        Vérifié P2.3 : billing_service utilise MktPrice canonique pour
        le calcul prix référence (priority 2 du resolve_reference_price).
        """
        billing = BACKEND / "services" / "billing_service.py"
        if not billing.exists():
            return
        content = billing.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_IMPORT_PATTERNS:
            for match in pattern.finditer(content):
                line_no = content[: match.start()].count("\n") + 1
                line = content.split("\n")[line_no - 1]
                if line.strip().startswith("#"):
                    continue
                pytest.fail(
                    f"🔴 P2.3 — billing_service.py importe MarketPrice legacy "
                    f"ligne {line_no} : « {match.group(0)[:80]} ». "
                    f"Utiliser MktPrice canonique."
                )

    def test_market_data_service_uses_canonical_if_exists(self):
        """Si market_data_service existe, il utilise MktPrice (pas legacy)."""
        candidates = [
            BACKEND / "services" / "market_data_service.py",
            BACKEND / "services" / "market_data" / "service.py",
        ]
        for path in candidates:
            if not path.exists():
                continue
            content = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_IMPORT_PATTERNS:
                for match in pattern.finditer(content):
                    line_no = content[: match.start()].count("\n") + 1
                    line = content.split("\n")[line_no - 1]
                    if line.strip().startswith("#"):
                        continue
                    rel = path.relative_to(REPO_ROOT).as_posix()
                    pytest.fail(f"🔴 P2.3 — {rel}:{line_no} importe MarketPrice legacy. Utiliser MktPrice canonique.")

    def test_legacy_model_has_p2_3_deprecation_marker(self):
        """Le modèle legacy porte le marquage DEPRECATED P2.3 renforcé."""
        legacy_model = BACKEND / "models" / "market_price.py"
        if not legacy_model.exists():
            return
        content = legacy_model.read_text(encoding="utf-8")
        # Marqueur P2.3 explicite
        assert "P2.3" in content, (
            "models/market_price.py manque le marqueur Sprint P2.3 dans la "
            "doctrine DEPRECATED. Ajouter référence sprint pour traçabilité."
        )
        # Lien vers source-guard
        assert "test_market_price_canonical_source_guards" in content, (
            "models/market_price.py doit référencer le nom du source-guard qui interdit ses imports applicatifs."
        )

    def test_models_init_marks_legacy_import_as_compat(self):
        """models/__init__.py marque l'import legacy comme compat-only."""
        init = BACKEND / "models" / "__init__.py"
        content = init.read_text(encoding="utf-8")
        # Doit avoir un commentaire DEPRECATED + un noqa: F401
        # (l'import est nécessaire pour SQLAlchemy mais non utilisé directement)
        idx = content.find("from .market_price import MarketPrice")
        assert idx > -1, "Import MarketPrice attendu dans models/__init__.py."
        # Le commentaire DEPRECATED P2.3 doit précéder l'import
        preceding = content[max(0, idx - 600) : idx]
        assert "DEPRECATED" in preceding.upper(), (
            "models/__init__.py — l'import MarketPrice doit être précédé d'un commentaire DEPRECATED explicite."
        )
        # noqa: F401 nécessaire car l'import sert pour ORM seulement
        line_after = content[idx : idx + 200]
        assert "noqa" in line_after or "legacy" in line_after.lower(), (
            "models/__init__.py — l'import MarketPrice doit porter `noqa: F401` "
            "(import compat ORM, jamais utilisé directement) ou mention `legacy`."
        )

    def test_p2_3_doc_references_canonical_fields(self):
        """La doctrine in-file mentionne les champs canoniques attendus."""
        legacy_model = BACKEND / "models" / "market_price.py"
        if not legacy_model.exists():
            return
        content = legacy_model.read_text(encoding="utf-8")
        # Au moins 2 champs canoniques cités
        canonical_fields = [
            "market_type",
            "zone",
            "delivery_start",
            "price_eur_mwh",
        ]
        found = sum(1 for f in canonical_fields if f in content)
        assert found >= 3, (
            f"La doctrine de market_price.py doit citer les champs canoniques "
            f"MktPrice attendus (au moins 3 sur {canonical_fields}). "
            f"Actuellement : {found}."
        )
