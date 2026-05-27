"""Source-guards Énergie P0b visual credibility (2026-05-27).

Verrous structurels post-sprint claude/energie-p0b-visual-cx-credibility.
Empêchent toute régression silencieuse sur les 7 chantiers :

  G1. Score Monitoring borné [0, 100] côté BE (orchestrator + endpoint).
  G2. Breadcrumb « Portefeuille » (et plus « Regroupement ») pour /portfolio.
  G3. Diagnostic EmptyState avec wording « Aucune anomalie détectée » +
      CTA « Relancer l'analyse » + banner data_gap.
  G4. /usages — pas d'index-as-key dans HeatmapCard (préfixes head-/ademe-).
  G5. Aucun emoji visible dans labels énergie (📈 📊 🔌 🖨).
  G6. /consommations wrapper tabs ne contient plus Memobox.
  G7. NavRegistry.getOrderedModules — admin uniquement si isExpert.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT.parent / "frontend" / "src"
BACKEND_ROUTES_MONITORING = REPO_ROOT / "routes" / "monitoring.py"
BACKEND_MONITORING_ORCHESTRATOR = REPO_ROOT / "services" / "electric_monitoring" / "monitoring_orchestrator.py"
BREADCRUMB = FRONTEND_SRC / "layout" / "Breadcrumb.jsx"
NAV_REGISTRY = FRONTEND_SRC / "layout" / "NavRegistry.js"
CONSOMMATIONS_PAGE = FRONTEND_SRC / "pages" / "ConsommationsPage.jsx"
USAGES_PAGE = FRONTEND_SRC / "pages" / "UsagesDashboardPage.jsx"
DIAG_PAGE = FRONTEND_SRC / "pages" / "ConsumptionDiagPage.jsx"
HEATMAP_CARD = FRONTEND_SRC / "components" / "usages" / "HeatmapCard.jsx"


# ── G1 : Score Monitoring clamp [0, 100] ───────────────────────────────


def test_g1_monitoring_orchestrator_clamps_score():
    """Le persist_snapshot doit clamp data_quality_score + risk_power_score
    sur [0, 100] (brief P0b C1 anti-affichage score 108)."""
    text = BACKEND_MONITORING_ORCHESTRATOR.read_text(encoding="utf-8")
    assert "_clamp_score" in text or "max(0, min(100" in text, (
        "Énergie P0b régression : monitoring_orchestrator ne clamp plus les "
        "scores. Brief C1 : score doit toujours être ∈ [0, 100]."
    )


def test_g1_monitoring_route_clamps_score():
    """L'endpoint /api/monitoring/* doit aussi clamp à la lecture (defense-
    in-depth pour les snapshots legacy persistés avant le fix orchestrator)."""
    text = BACKEND_ROUTES_MONITORING.read_text(encoding="utf-8")
    assert "_clamp_monitoring_score" in text, (
        "Énergie P0b régression : routes/monitoring.py ne clamp plus à la "
        "lecture (defense-in-depth obligatoire pour snapshots legacy)."
    )
    # Au moins 3 callsites attendus (snapshot principal + compare + list).
    callsites = text.count("_clamp_monitoring_score(")
    assert callsites >= 5, (
        f"Énergie P0b régression : seulement {callsites} usage(s) du clamp "
        f"dans routes/monitoring.py — attendu ≥ 5 (1 helper + ≥ 4 dans les"
        f" 3 endpoints data_quality_score + risk_power_score)."
    )


# ── G2 : Breadcrumb « Portefeuille » ────────────────────────────────────


def test_g2_breadcrumb_portfolio_label_is_portefeuille():
    text = BREADCRUMB.read_text(encoding="utf-8")
    assert "portfolio: 'Portefeuille'" in text, (
        "Énergie P0b régression : breadcrumb /portfolio doit afficher "
        "« Portefeuille » (aligné rail + H1 ConsumptionPortfolioPage). "
        "Avant : « Regroupement » désynchronisé."
    )
    assert "portfolio: 'Regroupement'" not in text, "Le label legacy « Regroupement » est interdit pour /portfolio."


# ── G3 : Diagnostic EmptyState 3 variantes + banner data_gap ────────────


def test_g3_diagnostic_emptystate_2_variants_plus_data_gap_banner():
    text = DIAG_PAGE.read_text(encoding="utf-8")
    # Variante 2 : « Aucune anomalie détectée sur la période »
    assert "Aucune anomalie détectée sur la période" in text, (
        "Énergie P0b régression : EmptyState diagnostic doit distinguer "
        "« Aucune anomalie détectée sur la période » (cas 2 : analysé sans "
        "anomalie) du wording legacy « Aucun gisement détecté » (cas 1 : "
        "pas encore analysé). Brief C3."
    )
    # CTA « Relancer l'analyse » pour le cas analysé.
    assert "Relancer l'analyse" in text, "CTA « Relancer l'analyse » manquant (brief C3, cas 2)."
    # Cas 3 : banner inline data_gap dédié.
    assert 'data-testid="diagnostic-data-gap-banner"' in text, (
        "Banner « données insuffisantes » manquant — brief C3 cas 3."
    )


# ── G4 : Duplicate keys /usages HeatmapCard ─────────────────────────────


def test_g4_heatmap_card_no_duplicate_usage_keys():
    """HeatmapCard rend 2× la liste `usages` (header + footer ADEME) dans
    le même parent grid → keys préfixées pour éviter les doublons."""
    text = HEATMAP_CARD.read_text(encoding="utf-8")
    assert "key={`head-${u}`}" in text, (
        "Énergie P0b régression : HeatmapCard header row doit utiliser "
        "key=`head-${u}` (préfixe) pour éviter duplicate key warning avec "
        "la rangée Réf. ADEME."
    )
    assert "key={`ademe-${u}`}" in text, (
        "Énergie P0b régression : HeatmapCard footer row Réf. ADEME doit utiliser key=`ademe-${u}` (préfixe)."
    )


# ── G5 : Aucun emoji corporate dans pages énergie ───────────────────────


_FORBIDDEN_EMOJI = ["📈", "📊", "🔌", "🖨"]


def test_g5_no_corporate_emoji_in_energie_pages():
    """Aucun emoji 📈 📊 🔌 🖨 dans les labels d'onglets / boutons des
    pages énergie principales (brief C5 charte corporate Sol).
    Tolère les mentions en commentaires (// ou /* */ ou docstring)."""
    pages = [USAGES_PAGE, DIAG_PAGE, CONSOMMATIONS_PAGE]
    violations = []
    for page in pages:
        text = page.read_text(encoding="utf-8")
        # Strip line comments + block comments grossièrement avant le test.
        no_line_comments = re.sub(r"//[^\n]*", "", text)
        no_block_comments = re.sub(r"/\*.*?\*/", "", no_line_comments, flags=re.DOTALL)
        for emoji in _FORBIDDEN_EMOJI:
            if emoji in no_block_comments:
                violations.append((page.name, emoji))
    assert not violations, (
        f"Énergie P0b régression : emojis corporate interdits trouvés en "
        f"code (hors commentaires) : {violations}. Brief C5 : utiliser des "
        f"icônes lucide-react."
    )


# ── G6 : Memobox retiré du wrapper Consommations ───────────────────────


def test_g6_consommations_wrapper_no_memobox_tab():
    text = CONSOMMATIONS_PAGE.read_text(encoding="utf-8")
    assert "to: '/kb'" not in text and "label: 'Memobox'" not in text, (
        "Énergie P0b régression : onglet Memobox réintroduit dans le wrapper "
        "Consommations. Brief C6 : /kb reste accessible via module admin + "
        "deep-link, pas via Consommations (saut de contexte cross-module)."
    )


# ── G7 : Administration cachée en mode normal ──────────────────────────


def test_g7_admin_module_hidden_when_not_expert():
    """`getOrderedModules` ne doit inclure le module admin que si isExpert."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    # Le pattern doit être : `if (isExpert && byKey.admin) ordered.push(byKey.admin);`
    m = re.search(
        r"export function getOrderedModules.*?if\s*\(\s*isExpert\s*&&\s*byKey\.admin\s*\)",
        text,
        re.DOTALL,
    )
    assert m, (
        "Énergie P0b régression : getOrderedModules doit gater admin sur "
        "isExpert (`if (isExpert && byKey.admin) ordered.push(byKey.admin)`). "
        "Sans ce garde, ADMINISTRATION serait visible en mode normal."
    )


def test_g7_admin_module_expert_only():
    """Le module admin de NAV_MODULES doit être expertOnly: true."""
    text = NAV_REGISTRY.read_text(encoding="utf-8")
    m = re.search(
        r"key:\s*'admin'.*?expertOnly:\s*(true|false)",
        text,
        re.DOTALL,
    )
    assert m, "Module 'admin' introuvable dans NAV_MODULES"
    assert m.group(1) == "true", f"Module admin doit être expertOnly: true (got {m.group(1)})."
