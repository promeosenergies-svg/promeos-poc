"""Source-guards Cockpit P1 (2026-05-25) — Executive Narrative.

Verrous structurels :
  G1. route cockpit_strategique.py injecte payload.executive_summary +
      payload.top_priorities depuis le service dédié.
  G2. Le service expose source/formula/unit/period/scope sur chaque KPI
      (doctrine §8.1 — pas de "valeur magique").
  G3. Le composant FE CockpitExecutiveNarrative est intégré dans
      CockpitStrategique.jsx (pas d'orphelin Phase 1 FE).
  G4. Aucune route fabriquée — les CTAs pointent vers /bill-intel,
      /conformite, /patrimoine, /centre-action uniquement (doctrine §6.2).
  G5. Cockpit.jsx et CockpitDecision.jsx restent supprimés (anti-régression
      sprint Cockpit P0 cleanup #303).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE = REPO_ROOT / "services" / "executive_narrative_service.py"
ROUTE = REPO_ROOT / "routes" / "cockpit_strategique.py"
FE_COMPONENT = REPO_ROOT.parent / "frontend" / "src" / "pages" / "cockpit" / "CockpitExecutiveNarrative.jsx"
FE_PAGE = REPO_ROOT.parent / "frontend" / "src" / "pages" / "CockpitStrategique.jsx"
FE_PAGES_DIR = REPO_ROOT.parent / "frontend" / "src" / "pages"


# ── G1 : route injecte executive_summary + top_priorities ─────────────────


def test_g1_route_injects_executive_narrative():
    text = ROUTE.read_text(encoding="utf-8")
    assert "compute_executive_narrative" in text, (
        "routes/cockpit_strategique.py doit appeler compute_executive_narrative()"
    )
    assert 'payload["executive_summary"]' in text, (
        "Le payload doit exposer la clé executive_summary"
    )
    assert 'payload["top_priorities"]' in text, (
        "Le payload doit exposer la clé top_priorities"
    )


# ── G2 : KPIs avec metadata complète (doctrine §8.1) ──────────────────────


def test_g2_service_kpi_has_full_metadata():
    text = SERVICE.read_text(encoding="utf-8")
    # Les 6 clés obligatoires apparaissent dans la signature _kpi() ou son
    # body — chaque KPI doit avoir id, label_fr, value, unit, source, formula,
    # period, scope.
    required = ["id_", "label_fr", "value", "unit", "source", "formula", "period", "scope"]
    for key in required:
        assert key in text, f"Service doit produire la clé {key} sur chaque KPI"


def test_g2_no_magic_value_without_formula():
    """Si on lit value=<nombre> littéral dans un _kpi(), la formule doit être
    référencée juste avant ou après (anti AP : valeur magique sans traçabilité)."""
    text = SERVICE.read_text(encoding="utf-8")
    # On exige que chaque _kpi() call contienne une chaîne "formula="
    kpi_calls = re.findall(r"_kpi\((?:[^()]|\([^()]*\))*\)", text, re.DOTALL)
    # Exclure la définition `def _kpi(*, id_, ...)` (signature, pas un appel).
    kpi_calls = [c for c in kpi_calls if "id_=" in c]
    assert kpi_calls, "Au moins un appel _kpi(...) attendu dans le service"
    for call in kpi_calls:
        assert "formula=" in call, f"_kpi() sans formula= : {call[:120]}..."


# ── G3 : composant FE intégré dans la page ───────────────────────────────


def test_g3_fe_component_imported_by_page():
    page_text = FE_PAGE.read_text(encoding="utf-8")
    assert "CockpitExecutiveNarrative" in page_text, (
        "CockpitStrategique.jsx doit importer/rendre CockpitExecutiveNarrative"
    )
    assert "executiveSummary={payload.executive_summary}" in page_text, (
        "Le composant doit recevoir payload.executive_summary"
    )
    assert "topPriorities={payload.top_priorities}" in page_text, (
        "Le composant doit recevoir payload.top_priorities"
    )


def test_g3_fe_component_exists_with_3_blocks():
    text = FE_COMPONENT.read_text(encoding="utf-8")
    # Les 3 blocs canoniques portent des testids stables.
    assert "exec-situation" in text, "Bloc Situation en 30 secondes manquant"
    assert "exec-top-priorities" in text, "Bloc Top 3 priorités manquant"
    assert "exec-why-microcopy" in text, "Bloc Pourquoi c'est important manquant"


# ── G4 : CTAs canoniques uniquement ──────────────────────────────────────


_CTA_LINK_RE = re.compile(r'cta_link=f?["\'](/[^"\']+)["\']')


def test_g4_service_ctas_point_to_hub_pages_only():
    text = SERVICE.read_text(encoding="utf-8")
    links = _CTA_LINK_RE.findall(text)
    assert links, "Le service doit produire des CTA avec cta_link=..."
    allowed_prefixes = ("/bill-intel", "/conformite", "/patrimoine", "/centre-action")
    for link in links:
        assert link.startswith(allowed_prefixes), (
            f"CTA link {link!r} doit pointer vers une page hub canonique "
            f"(doctrine §6.2) — autorisées : {allowed_prefixes}"
        )


# ── G5 : anti-régression #303 — Cockpit.jsx / CockpitDecision.jsx supprimés


def test_g5_legacy_cockpit_pages_not_reintroduced():
    assert not (FE_PAGES_DIR / "Cockpit.jsx").exists(), (
        "Cockpit.jsx réintroduit — supprimé sprint Cockpit P0 cleanup #303"
    )
    assert not (FE_PAGES_DIR / "CockpitDecision.jsx").exists(), (
        "CockpitDecision.jsx réintroduit — supprimé sprint Cockpit P0 cleanup #303"
    )
