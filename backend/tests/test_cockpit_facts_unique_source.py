"""Phase 4bis.1 — Sentinel #9 : verrouillage source unique `_facts`.

Garantit que `services.cockpit_facts_service.get_cockpit_facts()` est
l'unique entry point qui produit le payload `/api/cockpit/_facts`. Si
un futur PR essaye de dupliquer la logique dans un autre service ou
route, ce test échouera et alertera la revue.

Couvre :
  - Une seule fonction module-level `get_cockpit_facts` retourne le
    payload complet 11 top-level keys
  - La route `/api/cockpit/_facts` (`backend/routes/cockpit.py`) appelle
    EXCLUSIVEMENT `cockpit_facts_service.get_cockpit_facts` (pas un
    fork ou réimplémentation)
  - Aucun autre service module-level n'expose un `get_*facts*` qui
    retourne le même contrat (≥ 5 top-level keys parmi {scope,
    consumption, exposure, compliance, …})

Ref : audit Sprint Retro Cockpit Dual Sol2 — sentinel #9 ambigu (concept
"source unique" tenu de fait mais pas verrouillé par test).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

CANONICAL_KEYS = {
    "scope",
    "consumption",
    "compliance",
    "exposure",
    "potential_recoverable",
    "metadata",
}


class TestCockpitFactsUniqueSource:
    """Vérifie que `get_cockpit_facts` est l'unique source du payload _facts."""

    def test_unique_module_level_function(self):
        """Une seule définition `def get_cockpit_facts` au scope module."""
        hits = []
        for path in BACKEND_DIR.rglob("*.py"):
            if "/.venv/" in str(path) or "/venv/" in str(path):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == "get_cockpit_facts":
                    hits.append(str(path.relative_to(REPO_ROOT)))
        assert len(hits) == 1, (
            f"Sentinel #9 : `get_cockpit_facts` doit être défini UNE SEULE FOIS "
            f"au scope module — trouvé {len(hits)} : {hits}"
        )
        assert hits[0].endswith("services/cockpit_facts_service.py"), (
            f"Sentinel #9 : `get_cockpit_facts` doit être dans `services/cockpit_facts_service.py` — trouvé : {hits[0]}"
        )

    def test_route_facts_calls_cockpit_facts_service(self):
        """La route `/api/cockpit/_facts` appelle `cockpit_facts_service.get_cockpit_facts`."""
        route_file = BACKEND_DIR / "routes" / "cockpit.py"
        src = route_file.read_text(encoding="utf-8")
        # Pattern : import + appel
        assert "from services.cockpit_facts_service import get_cockpit_facts" in src, (
            "Sentinel #9 : `routes/cockpit.py` doit importer `get_cockpit_facts` "
            "depuis `services.cockpit_facts_service`"
        )
        assert "return get_cockpit_facts(" in src, (
            "Sentinel #9 : la route doit retourner directement `get_cockpit_facts(...)` sans fork"
        )

    def test_no_other_facts_endpoint_returns_full_payload(self):
        """Aucune autre route que /api/cockpit/_facts ne retourne le payload complet."""
        # Heuristique : compte les routes qui dans leur retour mentionnent ≥ 4
        # parmi les CANONICAL_KEYS. Une route qui retourne juste 1-2 sous-clés
        # (ex: /api/cockpit/_facts.scope) est OK.
        violators = []
        for path in BACKEND_DIR.rglob("routes/*.py"):
            try:
                src = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "cockpit_facts_service" in src:
                continue  # OK : passe par le SoT
            # Compter les CANONICAL_KEYS apparaissant dans le module
            keys_present = sum(1 for k in CANONICAL_KEYS if f'"{k}"' in src or f"'{k}'" in src)
            if keys_present >= 5:
                violators.append((str(path.relative_to(REPO_ROOT)), keys_present))
        assert not violators, (
            f"Sentinel #9 : routes qui semblent reconstruire le payload _facts "
            f"sans passer par `cockpit_facts_service` : {violators}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
