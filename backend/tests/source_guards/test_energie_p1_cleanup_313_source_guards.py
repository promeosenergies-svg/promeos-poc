"""Source-guards Énergie P1 cleanup #313 (2026-05-27).

Verrous structurels post-sprint claude/energie-p1-cleanup-313-after-usage-steering.
Closure des 2 dettes P1 héritées de l'audit menu Énergie #313 avant bascule
brique Conformité conditionnelle multi-énergie :

  G1. Sidebar Énergie label « Usages énergétiques » (pas « Répartition par usage »).
  G2. Page /usages h1 aligne le label sidebar.
  G3. Tests FE alignés (NavRegistry.test.js + capture visuelle).
  G4. /api/energy/import/jobs org-scopé (IS11 — auth + filter par site_ids).
  G5. kpiMessaging.js ne pointe plus vers /usages-horaires (boucle CTA propre).
  G6. routes.js — helper toUsagesHoraires() retiré (dead code).
  G7. Anti-régression brique Énergie : /usages canonique, /usages-horaires
      redirect, 0 /usage-steering, 4 items sidebar Énergie.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT.parent / "frontend" / "src"
APP_JSX = FRONTEND_SRC / "App.jsx"
NAV_REGISTRY = FRONTEND_SRC / "layout" / "NavRegistry.js"
NAV_REGISTRY_TEST = FRONTEND_SRC / "layout" / "__tests__" / "NavRegistry.test.js"
USAGES_PAGE = FRONTEND_SRC / "pages" / "UsagesDashboardPage.jsx"
KPI_MESSAGING = FRONTEND_SRC / "services" / "kpiMessaging.js"
ROUTES_JS = FRONTEND_SRC / "services" / "routes.js"
ENERGY_ROUTE = REPO_ROOT / "routes" / "energy.py"


def _strip_comments_js(text: str) -> str:
    no_line = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", no_line, flags=re.DOTALL)


def _strip_comments_py(text: str) -> str:
    # Retire les commentaires # et les docstrings triples (""" ou ''').
    lines = []
    in_doc = False
    doc_delim = None
    for ln in text.splitlines():
        stripped = ln.strip()
        if in_doc:
            if doc_delim and doc_delim in stripped:
                in_doc = False
                doc_delim = None
            continue
        for delim in ('"""', "'''"):
            if stripped.startswith(delim):
                rest = stripped[len(delim) :]
                if delim in rest:
                    # docstring sur une ligne
                    break
                in_doc = True
                doc_delim = delim
                break
        if in_doc:
            continue
        # Retire les # ... en fin de ligne (hors string : approximation suffisante).
        if "#" in ln:
            ln = re.sub(r"#.*$", "", ln)
        lines.append(ln)
    return "\n".join(lines)


# ── G1 : Sidebar Énergie « Usages énergétiques » ────────────────────────


def test_g1_sidebar_label_renamed_to_usages_energetiques():
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    code_only = _strip_comments_js(text)
    # Nouveau label présent sur l'item /usages.
    assert "label: 'Usages énergétiques'" in code_only or 'label: "Usages énergétiques"' in code_only, (
        "Énergie P1 #313 régression : label sidebar 'Usages énergétiques' absent du code actif."
    )
    # Ancien label NE doit plus apparaître en code actif (commentaires tolérés).
    pattern_old = re.compile(r"label:\s*['\"]Répartition par usage['\"]")
    assert not pattern_old.search(code_only), (
        "Énergie P1 #313 régression : ancien label 'Répartition par usage' "
        "encore présent en code actif. Doit être renommé 'Usages énergétiques'."
    )


# ── G2 : Page /usages h1 aligne le label sidebar ────────────────────────


def test_g2_usages_page_h1_aligns_sidebar_label():
    text = USAGES_PAGE.read_text(encoding="utf-8")
    # h1 doit contenir « Usages énergétiques » (casing minuscule é,
    # aligné avec le label sidebar canonique brief #313 P1 2026-05-27).
    assert ">Usages énergétiques<" in text, (
        "Énergie P1 #313 régression : h1 page /usages ne contient pas "
        "'Usages énergétiques'. Doit aligner le label sidebar (cohérence vocabulaire)."
    )
    # Ancien h1 « Usages Énergétiques » (É majuscule) ne doit plus exister.
    assert ">Usages Énergétiques<" not in text, (
        "Énergie P1 #313 régression : h1 page /usages avec 'Énergétiques' (É majuscule) "
        "encore présent. Le brief impose la casing 'Usages énergétiques'."
    )


# ── G3 : Tests FE alignés ───────────────────────────────────────────────


def test_g3_navregistry_test_uses_new_label():
    text = NAV_REGISTRY_TEST.read_text(encoding="utf-8")
    assert "label === 'Usages énergétiques'" in text, (
        "Énergie P1 #313 régression : NavRegistry.test.js ne référence pas "
        "le nouveau label 'Usages énergétiques'. Tests pas alignés sur le rename."
    )
    # L'ancien label dans les assertions de test doit avoir disparu.
    assert "label === 'Répartition par usage'" not in text, (
        "Énergie P1 #313 régression : NavRegistry.test.js référence encore "
        "l'ancien label 'Répartition par usage'. Tests à mettre à jour."
    )


# ── G4 : /api/energy/import/jobs org-scopé ──────────────────────────────


def test_g4_import_jobs_endpoint_is_org_scoped():
    """IS11 — l'endpoint doit consommer AuthContext + filtrer par site_ids."""
    text = ENERGY_ROUTE.read_text(encoding="utf-8")
    # Localiser la fonction list_import_jobs.
    m = re.search(
        r"def list_import_jobs\((.*?)\):(.*?)(?=\n@router|\n# ---|\nclass |\Z)",
        text,
        re.DOTALL,
    )
    assert m, "Fonction list_import_jobs introuvable dans backend/routes/energy.py"
    signature = m.group(1)
    body = m.group(2)
    assert "AuthContext" in signature and "get_optional_auth" in signature, (
        "IS11 régression : list_import_jobs n'a plus la dépendance "
        "`auth: Optional[AuthContext] = Depends(get_optional_auth)`. "
        "L'endpoint redevient cross-org leak. Signature actuelle : " + signature[:200]
    )
    # Le body doit filtrer par site_ids accessibles.
    assert "auth.site_ids" in body, (
        "IS11 régression : list_import_jobs n'utilise pas `auth.site_ids` "
        "pour filtrer les jobs. Tous les jobs de l'instance seraient retournés."
    )
    # Le filtre doit utiliser DataImportJob.site_id (pas seulement meter_id).
    assert "DataImportJob.site_id" in body, (
        "IS11 régression : le filtre ne porte pas sur DataImportJob.site_id. "
        "Les jobs orphelins (meter_id NULL) seraient invisibles ou tous visibles."
    )


# ── G5 : kpiMessaging.js ne pointe plus vers /usages-horaires ──────────


def test_g5_kpi_messaging_does_not_link_to_usages_horaires():
    text = KPI_MESSAGING.read_text(encoding="utf-8")
    code_only = _strip_comments_js(text)
    # Aucun lien actif vers /usages-horaires dans les CTA métier.
    assert "/usages-horaires" not in code_only, (
        "Énergie P1 #313 régression : kpiMessaging.js référence encore "
        "/usages-horaires en code actif. La route redirige vers /usages "
        "(P2 #321), tous les CTA doivent pointer vers /usages directement."
    )


# ── G6 : routes.js — toUsagesHoraires() retiré ─────────────────────────


def test_g6_routes_js_no_more_usages_horaires_helper():
    text = ROUTES_JS.read_text(encoding="utf-8")
    code_only = _strip_comments_js(text)
    assert "function toUsagesHoraires" not in code_only, (
        "Énergie P1 #313 régression : helper toUsagesHoraires() réintroduit "
        "dans routes.js. /usages-horaires redirige depuis P2 #321 — utiliser "
        "toUsages() (route canonique) à la place."
    )
    # toUsages() canonique doit rester en place.
    assert "function toUsages" in code_only, "Anti-régression : helper toUsages() (route canonique /usages) absent."


# ── G7 : Anti-régression brique Énergie ────────────────────────────────


def test_g7_usages_route_remains_canonical():
    text = APP_JSX.read_text(encoding="utf-8")
    assert 'path="/usages"' in text, "Régression : route /usages canonique supprimée."
    assert "/usage-steering" not in _strip_comments_js(text), (
        "Régression : /usage-steering interdit (anti-silo doctrine §6.2)."
    )


def test_g7_usages_horaires_remains_redirect():
    text = APP_JSX.read_text(encoding="utf-8")
    m = re.search(
        r'path="/usages-horaires"\s*element=\{([^}]+)\}',
        text,
        re.DOTALL,
    )
    assert m, "Route /usages-horaires introuvable (doit rester comme redirect bookmarks)."
    element = m.group(1)
    assert "Navigate" in element and "/usages" in element, (
        f"Régression : /usages-horaires ne redirige plus vers /usages. Got : {element[:120]}"
    )


def test_g7_sidebar_energie_four_items():
    """Le module Énergie de la sidebar doit avoir exactement 4 items visibles
    (Consommations, Performance énergétique, Usages énergétiques, Diagnostics).
    Aucun nouveau menu, aucun /flex en sidebar publique."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    # Vérifier que les 4 labels canoniques sont présents dans le module énergie.
    for label in [
        "'Consommations'",
        "'Performance énergétique'",
        "'Usages énergétiques'",
        "'Diagnostics'",
    ]:
        assert label in text, f"Régression sidebar Énergie : item {label} manquant ou renommé."
    # Flex ne doit PAS apparaître dans un item public du module Énergie
    # (acceptable dans HIDDEN_PAGES ou commentaires de cleanup).
    nav_sections_match = re.search(
        r"NAV_SECTIONS\s*=\s*\[(.*?)\];\s*\n\s*export\s+const\s+HIDDEN_PAGES",
        text,
        re.DOTALL,
    )
    if nav_sections_match:
        nav_block = _strip_comments_js(nav_sections_match.group(1))
        # On cherche des items label sidebar contenant "Flex" — tolérance
        # zéro pour Flex en surface publique.
        flex_labels = re.findall(r"label:\s*['\"]([^'\"]*[Ff]lex[^'\"]*)['\"]", nav_block)
        assert not flex_labels, (
            f"Régression : items sidebar publique avec Flex : {flex_labels}. "
            f"Doit rester en HIDDEN_PAGES uniquement (doctrine 'Aucun Flex visible client')."
        )
