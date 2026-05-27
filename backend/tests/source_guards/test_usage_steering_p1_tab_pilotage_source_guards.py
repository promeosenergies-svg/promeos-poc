"""Source-guards Usage Steering P1 — 4ᵉ onglet Pilotage des usages (2026-05-27).

Verrous structurels post-sprint claude/usage-steering-p1-tab-pilotage
(brief P1 §C5). Empêchent toute régression silencieuse sur les axes :

  G1. Aucun /usage-steering (anti-silo strict).
  G2. Aucun nouveau menu sidebar (« Pilotage des usages » = tab interne).
  G3. Aucun key={site.name} ou key={s.name} dans Recharts (anti-doublon
      seed HELIOS sites homonymes).
  G4. Aucun fallback Math.min métier dans PowerOptimizationCard.
  G5. Aucun revenu flex chiffré côté FE (brief « pas de NEBCO/AOFD client »).
  G6. Onglet pilotage présent dans ALL_TABS de UsagesDashboardPage.
  G7. POST /api/usages/pilotage/sync-action est idempotent (external_ref
      pattern strict + référence test BE existant pour idempotence DB).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT.parent / "frontend" / "src"
USAGES_PAGE = FRONTEND_SRC / "pages" / "UsagesDashboardPage.jsx"
PILOTAGE_TAB = FRONTEND_SRC / "components" / "usages" / "PilotageTab.jsx"
POWER_OPT_CARD = FRONTEND_SRC / "components" / "usages" / "PowerOptimizationCard.jsx"
CDC_SIM_CARD = FRONTEND_SRC / "components" / "usages" / "CdcSimulationCard.jsx"
FLEX_BUBBLE = FRONTEND_SRC / "components" / "usages" / "FlexBubbleChart.jsx"
BACKEND_USAGES = REPO_ROOT / "routes" / "usages.py"
NAV_REGISTRY = FRONTEND_SRC / "layout" / "NavRegistry.js"


def _strip_comments(text: str) -> str:
    no_line = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", no_line, flags=re.DOTALL)


# ── G1 : Aucun /usage-steering ──────────────────────────────────────────


def test_g1_no_usage_steering_anywhere_fe():
    forbidden = re.compile(r'["\']\/usage-steering["\']')
    violations = []
    for f in FRONTEND_SRC.rglob("*.jsx"):
        if "__tests__" in str(f) or ".test." in f.name:
            continue
        text = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if forbidden.search(text):
            violations.append(f.relative_to(REPO_ROOT.parent))
    for f in FRONTEND_SRC.rglob("*.js"):
        if "__tests__" in str(f) or ".test." in f.name:
            continue
        text = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if forbidden.search(text):
            violations.append(f.relative_to(REPO_ROOT.parent))
    assert not violations, (
        f"Usage Steering P1 régression : /usage-steering interdit. Pilotage "
        f"= 4ᵉ tab dans /usages. Violations : {violations}"
    )


# ── G2 : Aucun nouveau menu sidebar « Pilotage des usages » ─────────────


def test_g2_no_pilotage_menu_in_nav_sections():
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    nav_sections = re.search(r"export const NAV_SECTIONS = \[(.*?)\];", text, re.DOTALL)
    assert nav_sections, "NAV_SECTIONS introuvable"
    forbidden = re.compile(r"label:\s*['\"]Pilotage des usages['\"]")
    assert not forbidden.search(nav_sections.group(1)), (
        "Usage Steering P1 régression : « Pilotage des usages » présent "
        "comme menu sidebar. Doit rester un 4ᵉ tab interne dans /usages."
    )


# ── G3 : Aucun key={X.name} dans Recharts/maps usages ──────────────────


def test_g3_no_name_only_keys_in_usages_components():
    """Aucun composant usages ne doit utiliser `key={X.name}` seul (HELIOS
    contient des sites homonymes → duplicate-key warnings). Pattern
    composite stable obligatoire (id ?? `${idx}-${name}`)."""
    files = [CDC_SIM_CARD, FLEX_BUBBLE]
    forbidden = re.compile(r"key=\{[a-zA-Z_]\w*\.name\}")
    violations = []
    for f in files:
        text = _strip_comments(f.read_text(encoding="utf-8", errors="ignore"))
        if forbidden.search(text):
            violations.append(f.name)
    assert not violations, (
        f"Usage Steering P1 régression : key={{X.name}} interdit dans "
        f"composants usages — cause duplicate-key Recharts sur HELIOS "
        f"(sites homonymes). Utiliser key composite stable. "
        f"Violations : {violations}"
    )


# ── G4 : Aucun fallback Math.min métier dans PowerOptimizationCard ─────


def test_g4_no_math_min_fallback_in_power_optimization():
    """Le fallback `Math.min(cs.utilization_pct, 100)` doit avoir disparu
    de PowerOptimizationCard (BE garantit utilization_pct_safe après P0
    #317). Si BE absent → "—" affiché, jamais recalcul FE."""
    text = _strip_comments(POWER_OPT_CARD.read_text(encoding="utf-8"))
    forbidden = re.compile(r"Math\.min\s*\(\s*cs\.utilization_pct")
    assert not forbidden.search(text), (
        "Usage Steering P1 régression : fallback Math.min(cs.utilization_pct) "
        "réintroduit dans PowerOptimizationCard. Le BE garantit "
        "utilization_pct_safe (truth_contract P0)."
    )


# ── G5 : Aucun revenu flex chiffré côté FE (PilotageTab) ───────────────


def test_g5_no_flex_revenue_jargon_in_pilotage_tab():
    """Le 4ᵉ onglet ne doit jamais mentionner NEBCO / AOFD / « revenu
    flex » en surface client. Brief P1 : pas de jargon Flex."""
    text = _strip_comments(PILOTAGE_TAB.read_text(encoding="utf-8"))
    forbidden_terms = ["NEBCO", "AOFD", "revenu flex", "Flex Intelligence"]
    violations = [t for t in forbidden_terms if t in text]
    assert not violations, (
        f"Usage Steering P1 régression : jargon flex {violations} présent "
        f"dans PilotageTab. Brief P1 : surface client = vocabulaire métier "
        f"(« Pilotage des usages », « fenêtre favorable », pas de NEBCO)."
    )


# ── G6 : Onglet pilotage présent dans ALL_TABS ──────────────────────────


def test_g6_pilotage_tab_in_all_tabs():
    text = USAGES_PAGE.read_text(encoding="utf-8")
    all_tabs_match = re.search(r"const ALL_TABS = \[(.*?)\];", text, re.DOTALL)
    assert all_tabs_match, "ALL_TABS introuvable dans UsagesDashboardPage"
    block = all_tabs_match.group(1)
    assert "'pilotage'" in block or '"pilotage"' in block, (
        "Usage Steering P1 : onglet 'pilotage' doit être dans ALL_TABS de UsagesDashboardPage (brief C1)."
    )
    assert "Pilotage des usages" in block, "Le label « Pilotage des usages » doit être présent dans ALL_TABS."


def test_g6_pilotage_tab_uses_internal_url_state():
    """Le tab pilotage doit utiliser ?tab=pilotage (useSearchParams), pas
    une nouvelle route /usage-steering."""
    text = USAGES_PAGE.read_text(encoding="utf-8")
    assert "useSearchParams" in text, (
        "UsagesDashboardPage doit utiliser useSearchParams pour sync URL ?tab=pilotage (brief C1)."
    )


# ── G7 : Endpoint POST sync-action idempotent ──────────────────────────


def test_g7_sync_action_endpoint_idempotent_pattern():
    """L'endpoint /pilotage/sync-action doit vérifier external_ref pattern
    + lookup idempotent + skip si CLOSED (brief C3 « action clôturée non
    ressuscitée »)."""
    text = BACKEND_USAGES.read_text(encoding="utf-8")
    assert '@router.post("/pilotage/sync-action")' in text, "Endpoint POST /pilotage/sync-action manquant (brief C3)."
    # Vérifie le pattern external_ref + skip CLOSED + 409.
    assert 'startswith("pilotage:")' in text, (
        "L'endpoint doit valider external_ref pattern `pilotage:` (anti-collision)."
    )
    assert "LifecycleState.CLOSED.value" in text, (
        "L'endpoint doit checker lifecycle_state == CLOSED pour ne pas ressusciter une action clôturée (brief C3)."
    )
    assert "status_code=409" in text, "L'endpoint doit retourner 409 si action déjà CLOSED."
