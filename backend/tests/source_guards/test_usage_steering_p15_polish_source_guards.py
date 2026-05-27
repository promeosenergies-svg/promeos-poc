"""Source-guards Usage Steering P1.5 — Action Center loop polish (2026-05-27).

Verrous structurels post-sprint claude/usage-steering-p15-action-center-polish.
Garantissent que la boucle Pilotage → Centre d'Action V4 reste cohérente :

  G1. DOMAIN_LABELS expose « Optimisation énergétique » (pas de jargon
      technique côté FE).
  G2. ListFilterBar permet de filtrer sur domain=optimisation (dropdown
      inclut le domain canonique).
  G3. PilotageSourceBackLink existe + détecte le pattern external_ref
      `pilotage:{type}:site:{id}`.
  G4. PilotageSourceBackLink intégré dans ItemDetailDrawer.
  G5. UsagesDashboardPage utilise `setSite` au mount si ?site=X (mise en
      évidence du site cible au retour depuis drawer V4).
  G6. Source-guards précédents préservés : 0 /usage-steering, 0 jargon
      Flex (NEBCO/AOFD) dans PilotageSourceBackLink.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT.parent / "frontend" / "src"
DOMAIN_LABELS = FRONTEND_SRC / "pages" / "action-center-v4" / "constants" / "classification.js"
LIST_FILTER_BAR = FRONTEND_SRC / "pages" / "action-center-v4" / "components" / "narrative" / "ListFilterBar.jsx"
PILOTAGE_BACK_LINK = (
    FRONTEND_SRC / "pages" / "action-center-v4" / "components" / "drawer" / "PilotageSourceBackLink.jsx"
)
ITEM_DETAIL_DRAWER = FRONTEND_SRC / "pages" / "action-center-v4" / "components" / "drawer" / "ItemDetailDrawer.jsx"
USAGES_PAGE = FRONTEND_SRC / "pages" / "UsagesDashboardPage.jsx"


def _strip_comments(text: str) -> str:
    no_line = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", no_line, flags=re.DOTALL)


# ── G1 : DOMAIN_LABELS expose "Optimisation énergétique" ────────────────


def test_g1_domain_labels_optimisation_label_clair():
    """DOMAIN_LABELS doit mapper `optimisation` → « Optimisation énergétique »
    (libellé utilisateur clair, pas de jargon technique). Brief P1.5 §1."""
    text = DOMAIN_LABELS.read_text(encoding="utf-8")
    assert "optimisation: 'Optimisation énergétique'" in text, (
        "DOMAIN_LABELS doit exposer un libellé utilisateur clair pour "
        "domain=optimisation. Pas de jargon technique côté FE."
    )
    # Anti-confusion : libellés Facturation / Conformité distincts.
    assert "facturation: 'Facturation'" in text
    assert "conformite: 'Conformité'" in text


# ── G2 : ListFilterBar inclut optimisation dans domainOrder ─────────────


def test_g2_list_filter_bar_includes_optimisation():
    """Le dropdown domain de ListFilterBar doit pouvoir filtrer sur
    `optimisation` (pattern de tous les domains canoniques)."""
    text = LIST_FILTER_BAR.read_text(encoding="utf-8")
    # Le composant utilise DOMAIN_LABELS pour générer les options.
    assert "DOMAIN_LABELS" in text, "ListFilterBar doit importer DOMAIN_LABELS pour générer le dropdown domain."
    # Le domainOrder contient le domain « optimisation ».
    domain_order_match = re.search(r"domainOrder\s*=\s*\[(.*?)\]", text, re.DOTALL)
    assert domain_order_match, "domainOrder array introuvable dans ListFilterBar"
    assert "optimisation" in domain_order_match.group(1), (
        "Brief P1.5 §1 : ListFilterBar.domainOrder doit inclure `optimisation` "
        "(filtre indispensable pour la boucle Pilotage → Centre d'Action)."
    )


# ── G3 : PilotageSourceBackLink existe + détecte pattern ───────────────


def test_g3_pilotage_back_link_component_exists():
    assert PILOTAGE_BACK_LINK.exists(), "Composant PilotageSourceBackLink.jsx manquant. Brief P1.5 §2."
    text = PILOTAGE_BACK_LINK.read_text(encoding="utf-8")
    # Détection du pattern external_ref + extraction site_id.
    assert "_PILOTAGE_REF_RE" in text, (
        "PilotageSourceBackLink doit définir une regex pour parser external_ref `pilotage:{type}:site:{id}`."
    )
    # Garde domain=optimisation strict (anti-collision avec facturation/conformite).
    assert "domain !== 'optimisation'" in text, (
        "PilotageSourceBackLink doit retourner null si domain != 'optimisation' "
        "(évite affichage cross-brique parasite)."
    )
    # data-testid stable pour Playwright + tests.
    assert 'data-testid="pilotage-source-back-link"' in text, "testid stable obligatoire (pilotage-source-back-link)."


def test_g3_pilotage_back_link_shows_site_and_insight():
    """Le composant doit afficher le site + type de signal FR clair."""
    text = PILOTAGE_BACK_LINK.read_text(encoding="utf-8")
    assert "Source : Pilotage des usages" in text, (
        "Le label affiché doit commencer par « Source : Pilotage des usages »."
    )
    # Mapping FR par insight_type.
    for insight in ["hors_horaires", "base_load", "pointe", "derive", "data_gap"]:
        assert insight in text, f"Mapping FR pour insight_type `{insight}` manquant dans le back-link."


# ── G4 : Drawer intègre PilotageSourceBackLink ─────────────────────────


def test_g4_drawer_imports_and_renders_pilotage_back_link():
    text = ITEM_DETAIL_DRAWER.read_text(encoding="utf-8")
    assert "PilotageSourceBackLink" in text, (
        "ItemDetailDrawer doit importer et rendre PilotageSourceBackLink "
        "(brief P1.5 §2 — boucle fermée Pilotage → Action → retour source)."
    )
    # Le composant est rendu (pas juste importé) avec item prop.
    assert "<PilotageSourceBackLink item={item} />" in text, (
        "PilotageSourceBackLink doit être rendu avec la prop item dans le drawer."
    )


# ── G5 : ?site=X → setSite au mount (mise en évidence) ─────────────────


def test_g5_usages_page_sets_site_from_url_param():
    """Brief P1.5 §3 : au retour depuis drawer V4, ?site=X doit basculer le
    scope sur le site cible (ScopeBar reflète la sélection)."""
    text = USAGES_PAGE.read_text(encoding="utf-8")
    assert "siteFromUrl" in text or "searchParams.get('site')" in text, (
        "UsagesDashboardPage doit lire le param URL `site` pour la mise en "
        "évidence au retour depuis Centre d'Action V4 drawer."
    )
    assert "setSite(" in text, (
        "UsagesDashboardPage doit appeler setSite() depuis useScope pour "
        "basculer le scope au site cible (brief P1.5 §3)."
    )


# ── G6 : Anti-régression sprints précédents préservés ──────────────────


def test_g6_no_usage_steering_in_back_link():
    text = PILOTAGE_BACK_LINK.read_text(encoding="utf-8")
    assert "/usage-steering" not in text, (
        "PilotageSourceBackLink doit pointer vers /usages?tab=pilotage, JAMAIS /usage-steering."
    )


def test_g6_no_flex_jargon_in_back_link():
    """Le back-link ne doit jamais utiliser NEBCO / AOFD / Flex Intelligence
    (vocabulaire client clair, brief P1 G5)."""
    text = _strip_comments(PILOTAGE_BACK_LINK.read_text(encoding="utf-8"))
    forbidden = ["NEBCO", "AOFD", "Flex Intelligence"]
    violations = [t for t in forbidden if t in text]
    assert not violations, (
        f"Usage Steering P1.5 régression : jargon flex {violations} dans "
        f"PilotageSourceBackLink. Brief P1 : surface client = vocabulaire métier."
    )
