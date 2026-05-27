"""Source-guards Usage Steering P0 truth-contract (2026-05-27).

Verrous structurels post-sprint claude/usage-steering-p0-truth-contract-calculs
(brief P0 §C4). Empêchent toute régression silencieuse sur les 4 axes :

  G1. Aucun /usage-steering dans le code FE (anti-silo brief absolu).
  G2. Aucun menu « Pilotage des usages » hors de /usages (4ᵉ tab interne).
  G3. Calculs métier supprimés des composants usages (KpiStrip, HeatmapCard,
      PowerOptimizationCard) — lecture pure des champs BE.
  G4. Tous les KPI usage exposent unit/source/formula/confidence
      (champ truth_contract dans le payload).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = REPO_ROOT.parent / "frontend" / "src"
USAGES_COMPONENTS = FRONTEND_SRC / "components" / "usages"
USAGE_SERVICE = REPO_ROOT / "services" / "usage_service.py"
POWER_OPT_SERVICE = REPO_ROOT / "services" / "power_optimization_service.py"


# ── G1 : Aucun /usage-steering (anti-silo) ──────────────────────────────


def test_g1_no_usage_steering_anywhere_fe():
    """Aucune occurrence de /usage-steering dans le code FE (routes, links,
    NavRegistry, hooks, services API). Brief P0 absolu."""
    violations = []
    forbidden = re.compile(r'["\']\/usage-steering["\']')
    for f in FRONTEND_SRC.rglob("*.jsx"):
        if "__tests__" in str(f) or ".test." in f.name:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if forbidden.search(text):
            violations.append(f.relative_to(REPO_ROOT.parent))
    for f in FRONTEND_SRC.rglob("*.js"):
        if "__tests__" in str(f) or ".test." in f.name:
            continue
        text = f.read_text(encoding="utf-8", errors="ignore")
        if forbidden.search(text):
            violations.append(f.relative_to(REPO_ROOT.parent))
    assert not violations, (
        "Usage Steering P0 régression : /usage-steering interdit. Pilotage "
        f"= 4ᵉ tab dans /usages, jamais nouveau silo. Violations : {violations}"
    )


# ── G2 : Pas de menu « Pilotage des usages » hors /usages ───────────────


def test_g2_no_pilotage_menu_label_outside_usages():
    """Aucun item NavRegistry n'expose le label « Pilotage des usages »
    (réservé au 4ᵉ tab interne de /usages, jamais menu sidebar)."""
    nav_registry = FRONTEND_SRC / "layout" / "NavRegistry.js"
    text = nav_registry.read_text(encoding="utf-8")
    nav_sections_block = re.search(
        r"export const NAV_SECTIONS = \[(.*?)\];",
        text,
        re.DOTALL,
    )
    assert nav_sections_block, "NAV_SECTIONS array introuvable"
    forbidden = re.compile(r"label:\s*['\"]Pilotage des usages['\"]")
    assert not forbidden.search(nav_sections_block.group(1)), (
        "Usage Steering P0 régression : « Pilotage des usages » présent "
        "comme menu sidebar. Doit rester un 4ᵉ tab interne dans /usages."
    )


# ── G3 : Calculs métier FE supprimés ────────────────────────────────────


def _strip_comments(text: str) -> str:
    """Retire commentaires JS (// et /* */) pour filtrer les références
    historiques dans les tests source-guard (le test ne doit pas être
    déclenché par un commentaire qui *cite* l'ancien calcul)."""
    no_line = re.sub(r"//[^\n]*", "", text)
    return re.sub(r"/\*.*?\*/", "", no_line, flags=re.DOTALL)


def test_g3_kpi_strip_reads_ipe_from_be():
    """KpiStrip ne doit plus calculer ipe (totalKwh/totalSurface). Doit
    lire summary.ipe_kwh_m2 exposé par le BE (brief P0 §C2)."""
    raw = (USAGES_COMPONENTS / "KpiStrip.jsx").read_text(encoding="utf-8")
    text = _strip_comments(raw)
    assert "summary?.ipe_kwh_m2" in text or "summary.ipe_kwh_m2" in text, (
        "KpiStrip doit lire summary.ipe_kwh_m2 (lecture BE, pas calcul FE)."
    )
    forbidden_old_calc = re.compile(r"Math\.round\s*\(\s*totalKwh\s*/\s*totalSurface\s*\)")
    assert not forbidden_old_calc.search(text), (
        "Usage Steering P0 régression : KpiStrip recalcule encore IPE côté FE (violation doctrine §8.1 brief P0)."
    )


def test_g3_kpi_strip_reads_surplus_eur_from_be():
    """KpiStrip doit lire summary.surplus_eur (pas multiplier kwh × prix)."""
    raw = (USAGES_COMPONENTS / "KpiStrip.jsx").read_text(encoding="utf-8")
    text = _strip_comments(raw)
    assert "summary?.surplus_eur" in text or "summary.surplus_eur" in text, (
        "KpiStrip doit lire summary.surplus_eur (lecture BE, pas multiplication FE)."
    )
    forbidden = re.compile(r"surplusKwh\s*\*\s*priceRef")
    assert not forbidden.search(text), "Usage Steering P0 régression : KpiStrip recalcule encore surplusEur."


def test_g3_heatmap_card_reads_ratio_from_be():
    """HeatmapCard doit lire ratio_vs_ademe_pct_by_usage du BE (pas Math)."""
    raw = (USAGES_COMPONENTS / "HeatmapCard.jsx").read_text(encoding="utf-8")
    text = _strip_comments(raw)
    assert "ratio_vs_ademe_pct_by_usage" in text, (
        "HeatmapCard doit lire sites[].ratio_vs_ademe_pct_by_usage (lecture BE)."
    )
    forbidden = re.compile(r"Math\.round\s*\(\s*\(\s*val\s*/\s*ademeRef\s*-\s*1\s*\)\s*\*\s*100\s*\)")
    assert not forbidden.search(text), (
        "Usage Steering P0 régression : HeatmapCard recalcule encore ratio vs ADEME côté FE (violation doctrine §8.1)."
    )


def test_g3_power_optimization_reads_utilization_safe_from_be():
    """PowerOptimizationCard doit lire utilization_pct_safe et
    overflow_status exposés par le BE."""
    text = (USAGES_COMPONENTS / "PowerOptimizationCard.jsx").read_text(encoding="utf-8")
    assert "utilization_pct_safe" in text and "overflow_status" in text, (
        "PowerOptimizationCard doit lire utilization_pct_safe + overflow_status "
        "exposés par /api/usages/power-optimization (brief P0 §C2)."
    )


# ── G4 : Truth contract — KPI usage exposent unit/source/formula/conf ──


def test_g4_scoped_dashboard_exposes_truth_contract():
    """get_scoped_usages_dashboard doit retourner un dict truth_contract
    contenant unit + source + period + formula_ref + confidence pour les
    chiffres critiques (ipe_kwh_m2, surplus_eur, total_eur)."""
    text = USAGE_SERVICE.read_text(encoding="utf-8")
    assert '"truth_contract"' in text or "'truth_contract'" in text, (
        "scoped-dashboard doit exposer un champ `truth_contract` (brief P0 §C4)."
    )
    for required in ('"unit"', '"source"', '"formula_ref"', '"confidence"'):
        assert required in text, f"truth_contract doit exposer {required} sur les KPI critiques."


def test_g4_power_optimization_exposes_truth_contract():
    """optimize_subscribed_power doit retourner un dict truth_contract
    pour utilization_pct_safe + overflow_status."""
    text = POWER_OPT_SERVICE.read_text(encoding="utf-8")
    assert "truth_contract" in text, "power_optimization doit exposer truth_contract (brief P0 §C4)."
    assert '"utilization_pct_safe"' in text and '"overflow_status"' in text, (
        "truth_contract doit couvrir utilization_pct_safe + overflow_status."
    )


def test_g4_portfolio_compare_exposes_truth_contract():
    """get_portfolio_usage_comparison doit exposer le truth_contract pour
    ipe_total + ratio_vs_ademe_pct."""
    text = USAGE_SERVICE.read_text(encoding="utf-8")
    # Le truth_contract dans get_portfolio_usage_comparison doit contenir
    # ratio_vs_ademe_pct + ipe_total.
    portfolio_block = re.search(
        r"def get_portfolio_usage_comparison.*?(?=\ndef |\Z)",
        text,
        re.DOTALL,
    )
    assert portfolio_block, "Fonction get_portfolio_usage_comparison introuvable"
    block = portfolio_block.group(0)
    assert '"truth_contract"' in block, "portfolio-compare doit exposer truth_contract."
    assert '"ratio_vs_ademe_pct"' in block, "truth_contract doit documenter ratio_vs_ademe_pct."
