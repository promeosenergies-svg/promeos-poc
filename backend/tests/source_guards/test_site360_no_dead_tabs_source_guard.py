"""
PROMEOS — Source-guard Site360 onglets vides / routes mortes (Sprint Site360 P0).

Doctrine P0 :
- Aucun onglet visible ne doit être vide / mort / décoratif.
- Aucun label « Analytics » (jargon EN) dans la registry des onglets.
- Aucun lien `href="#"` exposé.
- Aucun placeholder « TODO » / « Coming soon » / « À venir » / « Lorem ».
- Aucune navigation vers `/achat-assistant` (route morte historique
  remplacée par `/achat-energie`).
- L'accent canonique « Évaluation RegOps » est conservé (jamais
  « Evaluation RegOps » sans accent dans le texte rendu).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


pytestmark = pytest.mark.fast


REPO_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = REPO_ROOT / "frontend" / "src"

SITE360_FILES = [
    "pages/Site360.jsx",
    "pages/site360/site360TabsRegistry.js",
]


def _read(rel: str) -> str:
    path = FRONTEND / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _code_without_comments(content: str) -> str:
    """Retire les lignes commentaires (// + *)."""
    out: list[str] = []
    for line in content.split("\n"):
        s = line.strip()
        if s.startswith("//") or s.startswith("*"):
            continue
        out.append(line)
    return "\n".join(out)


class TestSite360NoDeadTabsP0:
    """Sprint Site360 P0 — onglets vides / routes mortes."""

    def test_registry_file_exists(self):
        path = FRONTEND / "pages" / "site360" / "site360TabsRegistry.js"
        assert path.exists(), (
            "frontend/src/pages/site360/site360TabsRegistry.js manquant — "
            "registry canonique des onglets Site360 (Sprint P0)."
        )

    def test_no_analytics_label_in_registry(self):
        """Sprint P0 — le label « Analytics » est interdit (jargon EN).

        Remplacement canonique : « Analyse énergétique ».
        """
        src = _read("pages/site360/site360TabsRegistry.js")
        assert src
        assert "label: 'Analyse énergétique'" in src, (
            "Registry doit déclarer label: 'Analyse énergétique' pour le tab analytics (P0)."
        )
        # Aucun literal `label: 'Analytics'`
        assert not re.search(r"label:\s*['\"]Analytics['\"]", src), (
            "Registry ne doit plus contenir label: 'Analytics' (jargon EN)."
        )

    def test_no_dead_achat_assistant_route(self):
        """Sprint P0 — `/achat-assistant` est une route morte (404).

        Remplacement canonique : `/achat-energie` (cf. App.jsx).
        """
        for rel in SITE360_FILES:
            src = _read(rel)
            if not src:
                continue
            assert "achat-assistant" not in src, (
                f"{rel} contient la route morte « achat-assistant » — utiliser SITE360_CANONICAL_ROUTES.achatEnergie."
            )

    def test_accent_evaluation_regops(self):
        """Sprint P0 — accent canonique « Évaluation RegOps » obligatoire."""
        src = _read("pages/Site360.jsx")
        assert src
        code = _code_without_comments(src)
        # Le label JSX rendu (`>Evaluation RegOps<`) sans accent est interdit
        assert not re.search(r">\s*Evaluation RegOps\s*<", code), (
            "Site360.jsx — label JSX « Evaluation RegOps » sans accent détecté ; utiliser « Évaluation RegOps »."
        )
        assert "Évaluation RegOps" in code, "Site360.jsx — accent canonique « Évaluation RegOps » manquant."

    def test_no_href_hash_in_site360(self):
        """Aucun lien `href="#"` (lien mort) dans Site360.jsx."""
        src = _read("pages/Site360.jsx")
        assert src
        code = _code_without_comments(src)
        assert not re.search(r'href=["\']#["\']', code), (
            'Site360.jsx contient `href="#"` — chaque lien doit pointer '
            "vers une route canonique (cf. SITE360_CANONICAL_ROUTES)."
        )

    def test_no_placeholder_jargon_rendered(self):
        """Aucun placeholder visuel type « TODO », « À venir », « Coming soon ».

        Patterns recherchés en JSX rendu (entre `>` et `<`).
        """
        for rel in SITE360_FILES:
            src = _read(rel)
            if not src:
                continue
            code = _code_without_comments(src)
            forbidden = [
                r">\s*À venir\s*<",
                r">\s*Coming soon\s*<",
                r">\s*TODO\s*<",
                r">\s*FIXME\s*<",
                r">\s*Lorem ipsum",
                r">\s*undefined\s*<",
                r">\s*NaN\s*<",
                r">\s*\[object Object\]\s*<",
            ]
            for pattern in forbidden:
                m = re.search(pattern, code, re.IGNORECASE)
                assert not m, f"{rel} expose un placeholder interdit en JSX rendu : « {m.group(0) if m else pattern} »"

    def test_registry_imported_by_site360(self):
        """Site360.jsx doit consommer la registry canonique."""
        src = _read("pages/Site360.jsx")
        assert src
        assert "site360TabsRegistry" in src, (
            "Site360.jsx doit importer la registry canonique (./site360/site360TabsRegistry)."
        )
        assert "getEnabledSite360Tabs" in src, (
            "Site360.jsx doit utiliser getEnabledSite360Tabs() pour dériver le tableau d'onglets visibles."
        )

    def test_registry_declares_9_enabled_tabs_with_contract(self):
        """Les 9 onglets attendus sont déclarés avec contrat complet."""
        src = _read("pages/site360/site360TabsRegistry.js")
        assert src
        expected_ids = [
            "resume",
            "conso",
            "analytics",
            "factures",
            "reconciliation",
            "conformite",
            "actions",
            "puissance",
            "usages",
        ]
        for tab_id in expected_ids:
            assert f"id: '{tab_id}'" in src, f"Registry doit déclarer l'onglet « {tab_id} »."
        # Chaque tab doit déclarer status + renderMode + testId
        assert src.count("status:") >= 9
        assert src.count("renderMode:") >= 9
        assert src.count("testId:") >= 9
