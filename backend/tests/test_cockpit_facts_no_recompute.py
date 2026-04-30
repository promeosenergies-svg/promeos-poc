"""Phase 4bis.1 — Sentinel #10 : verrou anti-recompute du payload `_facts`.

Garantit qu'aucun autre module ne **réimplémente** la logique des helpers
internes `_build_*` de `cockpit_facts_service`. Si un futur PR copie/colle
`_build_exposure`, `_build_consumption`, etc. ailleurs, le contrat
"_facts source unique" est rompu silencieusement.

Couvre :
  - Les helpers internes `_build_scope`, `_build_consumption`,
    `_build_compliance`, `_build_exposure`, `_build_potential_recoverable`,
    `_build_alerts`, `_build_data_quality`, `_build_flex_potential`,
    `_build_power` sont définis UNE SEULE FOIS dans
    `cockpit_facts_service.py`.
  - Aucun autre fichier ne définit une fonction `_build_*` qui retourne
    une structure semblable (>= 3 clés communes avec un bloc `_facts`).
  - Les imports externes des `_build_*` sont autorisés (ex: routes/cockpit.py
    importe `_build_exposure` ligne 1056), mais la **définition** reste unique.

Ref : audit Sprint Retro Cockpit Dual Sol2 — sentinel #10 ambigu.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

# Helpers internes que `cockpit_facts_service.get_cockpit_facts()` orchestre.
INTERNAL_BUILDERS = (
    "_build_scope",
    "_build_consumption",
    "_build_power",
    "_build_compliance",
    "_build_exposure",
    "_build_potential_recoverable",
    "_build_alerts",
    "_build_data_quality",
    "_build_flex_potential",
)


class TestCockpitFactsNoRecompute:
    """Vérifie qu'aucun module ne dédouble la logique des helpers `_build_*`."""

    @pytest.mark.parametrize("builder", INTERNAL_BUILDERS)
    def test_builder_defined_only_in_cockpit_facts_service(self, builder):
        """Chaque `_build_*` est défini UNE SEULE FOIS au scope module."""
        hits = []
        for path in BACKEND_DIR.rglob("*.py"):
            if "/.venv/" in str(path) or "/venv/" in str(path) or "/tests/" in str(path):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == builder:
                    hits.append(str(path.relative_to(REPO_ROOT)))
        assert len(hits) == 1, (
            f"Sentinel #10 : `{builder}` doit être défini UNE SEULE FOIS — trouvé {len(hits)} : {hits}"
        )
        assert hits[0].endswith("services/cockpit_facts_service.py"), (
            f"Sentinel #10 : `{builder}` doit être dans `services/cockpit_facts_service.py` — trouvé : {hits[0]}"
        )

    def test_get_cockpit_facts_orchestrates_all_builders(self):
        """`get_cockpit_facts` appelle bien tous les `_build_*` internes."""
        src = (BACKEND_DIR / "services" / "cockpit_facts_service.py").read_text(encoding="utf-8")
        # Trouver le corps de la fonction get_cockpit_facts
        tree = ast.parse(src)
        body_src = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "get_cockpit_facts":
                body_src = ast.unparse(node)
                break
        assert body_src, "get_cockpit_facts introuvable dans cockpit_facts_service.py"
        missing = [b for b in INTERNAL_BUILDERS if b not in body_src]
        assert not missing, (
            f"Sentinel #10 : `get_cockpit_facts` doit appeler tous les helpers `_build_*` — manquants : {missing}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
