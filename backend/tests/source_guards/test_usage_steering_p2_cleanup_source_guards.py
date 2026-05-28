"""Source-guards Usage Steering P2 — cleanup renderers + horaires (2026-05-27).

Verrous structurels post-sprint claude/usage-steering-p2-renderers-cleanup.
Garantissent que le cleanup ne casse pas la boucle Pilotage → Centre
d'Action V4 → retour source, et préviennent les régressions :

  G1. /usages-horaires redirige vers /usages (route fusionnée).
  G2. ConsumptionContextPage n'est plus rendue (lazy import commenté).
  G3. HIDDEN_PAGES n'expose plus /usages-horaires (cohérent avec la
      redirect).
  G4. UsageSignalCard existe et est utilisé par PilotageTab.
  G5. UsageSignalCard reste lecture pure (0 calcul métier FE).
  G6. PilotageTab utilise UsageSignalCard (pas l'ancien PilotageCard local).
  G7. Anti-régression sprints précédents : /usages canonique, 4ᵉ tab
      pilotage présent, 0 /usage-steering, PilotageSourceBackLink intégré.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT.parent / "frontend" / "src"
APP_JSX = FRONTEND_SRC / "App.jsx"
NAV_REGISTRY = FRONTEND_SRC / "layout" / "NavRegistry.js"
USAGE_SIGNAL_CARD = FRONTEND_SRC / "components" / "usages" / "UsageSignalCard.jsx"
PILOTAGE_TAB = FRONTEND_SRC / "components" / "usages" / "PilotageTab.jsx"
USAGES_PAGE = FRONTEND_SRC / "pages" / "UsagesDashboardPage.jsx"
ITEM_DETAIL_DRAWER = FRONTEND_SRC / "pages" / "action-center-v4" / "components" / "drawer" / "ItemDetailDrawer.jsx"


def _strip_comments(text: str) -> str:
    no_line = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", no_line, flags=re.DOTALL)


# ── G1 : /usages-horaires redirige vers /usages ─────────────────────────


def test_g1_usages_horaires_route_is_redirect():
    text = APP_JSX.read_text(encoding="utf-8")
    m = re.search(
        r'path="/usages-horaires"\s*element=\{([^}]+)\}',
        text,
        re.DOTALL,
    )
    assert m, "Route /usages-horaires introuvable dans App.jsx"
    element = m.group(1)
    assert "Navigate" in element and "/usages" in element, (
        f"Usage Steering P2 régression : /usages-horaires doit redirect vers "
        f"/usages, pas rendre une page legacy. Got element : {element[:120]}"
    )
    assert "ConsumptionContextPage" not in element, "ConsumptionContextPage ne doit plus être rendu (cleanup P2)."


# ── G2 : ConsumptionContextPage lazy import commenté ────────────────────


def test_g2_consumption_context_page_not_imported_active():
    """Le lazy import doit être commenté (page non chargée par Vite).
    Cela préserve la page sur disque jusqu'au cutover L8 mais l'évacue
    du bundle FE actif."""
    text = APP_JSX.read_text(encoding="utf-8")
    # Cherche un import lazy actif (pas dans un commentaire).
    raw = text
    lines = [ln for ln in raw.splitlines() if not ln.lstrip().startswith("//")]
    code_only = "\n".join(lines)
    pattern = re.compile(r"const\s+ConsumptionContextPage\s*=\s*lazy")
    assert not pattern.search(code_only), (
        "Usage Steering P2 régression : lazy import ConsumptionContextPage "
        "réintroduit. La route /usages-horaires redirige vers /usages, le "
        "lazy import doit rester commenté."
    )


# ── G3 : HIDDEN_PAGES n'expose plus /usages-horaires ────────────────────


def test_g3_hidden_pages_no_longer_has_usages_horaires():
    """Cohérence : la route redirige donc l'entrée HIDDEN_PAGES (qui
    avait une `reason` « doublon-sub-page ») est obsolète."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    hidden_block = re.search(
        r"export const HIDDEN_PAGES = \[(.*?)\];",
        text,
        re.DOTALL,
    )
    assert hidden_block, "HIDDEN_PAGES array introuvable"
    block = hidden_block.group(1)
    assert "to: '/usages-horaires'" not in block, (
        "Usage Steering P2 régression : entrée HIDDEN_PAGES /usages-horaires "
        "encore présente. À retirer après cleanup route (brief C1)."
    )


# ── G4 : UsageSignalCard existe ─────────────────────────────────────────


def test_g4_usage_signal_card_exists():
    assert USAGE_SIGNAL_CARD.exists(), (
        "Composant UsageSignalCard.jsx manquant (brief C2 — renderer partagé extrait de PilotageCard)."
    )
    text = USAGE_SIGNAL_CARD.read_text(encoding="utf-8")
    # Export par défaut + named export INSIGHT_LABEL_FR (source unique de vérité).
    assert "export default function UsageSignalCard" in text, "UsageSignalCard doit être l'export par défaut."
    assert "export const INSIGHT_LABEL_FR" in text, (
        "INSIGHT_LABEL_FR doit être exporté comme source unique de vérité "
        "(utilisé aussi par PilotageSourceBackLink drawer V4)."
    )


# ── G5 : UsageSignalCard reste lecture pure (0 calcul métier) ──────────


def test_g5_usage_signal_card_no_business_math():
    """UsageSignalCard ne doit pas calculer d'IPE / ratio / surplus / etc.
    Lecture pure des champs signal.* (doctrine §8.1)."""
    raw = USAGE_SIGNAL_CARD.read_text(encoding="utf-8")
    text = _strip_comments(raw)
    forbidden_patterns = [
        re.compile(r"Math\.round\s*\([^)]*/\s*surface"),
        re.compile(r"Math\.round\s*\([^)]*\*\s*price"),
        re.compile(r"\(\s*val\s*/\s*ademeRef"),
    ]
    for pat in forbidden_patterns:
        assert not pat.search(text), (
            f"Usage Steering P2 régression : calcul métier dans UsageSignalCard "
            f"(pattern interdit {pat.pattern}). Doctrine §8.1 lecture pure."
        )


# ── G6 : PilotageTab utilise UsageSignalCard ────────────────────────────


def test_g6_pilotage_tab_uses_usage_signal_card():
    text = PILOTAGE_TAB.read_text(encoding="utf-8")
    assert "import UsageSignalCard" in text, (
        "PilotageTab doit importer UsageSignalCard (brief C2 — renderer partagé extrait)."
    )
    assert "<UsageSignalCard" in text, "PilotageTab doit rendre <UsageSignalCard/> (pas l'ancien PilotageCard local)."
    # L'ancien composant local PilotageCard doit avoir disparu.
    assert "function PilotageCard" not in text, (
        "Usage Steering P2 régression : ancien composant PilotageCard "
        "local doit être supprimé (remplacé par UsageSignalCard partagé)."
    )


# ── G7 : Anti-régression sprints précédents ────────────────────────────


def test_g7_usages_remains_canonical_route():
    text = APP_JSX.read_text(encoding="utf-8")
    assert 'path="/usages"' in text, "Usage Steering P2 régression : route /usages canonique supprimée."
    assert "/usage-steering" not in _strip_comments(text), (
        "Usage Steering P2 régression : /usage-steering interdit (anti-silo)."
    )


def test_g7_pilotage_source_back_link_preserved():
    text = ITEM_DETAIL_DRAWER.read_text(encoding="utf-8")
    assert "PilotageSourceBackLink" in text, (
        "Usage Steering P2 régression : PilotageSourceBackLink retiré du "
        "drawer (briserait la boucle Pilotage → Action → retour source)."
    )


def test_g7_pilotage_tab_remains_in_all_tabs():
    text = USAGES_PAGE.read_text(encoding="utf-8")
    all_tabs = re.search(r"const ALL_TABS = \[(.*?)\];", text, re.DOTALL)
    assert all_tabs, "ALL_TABS introuvable"
    assert "'pilotage'" in all_tabs.group(1), (
        "Usage Steering P2 régression : 4ᵉ onglet 'pilotage' retiré de ALL_TABS (briserait l'intégration P1 #318)."
    )
