"""
PROMEOS — Source-guards Phase 3.2 + 3.4 (cockpit-sol2 réciprocité).

Phase 3.2 — drill-downs KPI hero :
  - test_kpi_hero_has_drill_down : chaque KPI hero Vue Exé a un href cible
  - 3 cibles canoniques :
    * Trajectoire 2030 → /conformite?scope=org&filter=non_conform
    * Exposition       → /conformite?scope=org&view=exposure_components
    * Potentiel récup. → /actions?filter=open&sort=mwh_desc

Phase 3.4 — routes legacy redirect :
  - test_no_route_legacy_executive : pas de route /executive ni /dashboard
    ni /synthese active dans backend (les redirects sont front-only via App.jsx)

Ref : PROMPT_REFONTE_COCKPIT_DUAL_SOL2_EXECUTION.md §4.B Phase 3.2 + 3.4.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import pytest
from fastapi.testclient import TestClient

from main import app

HEADERS = {"X-Org-Id": "1"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


# ── Phase 3.2 : Drill-downs KPI hero ───────────────────────────────────


class TestKpiHeroHasDrillDown:
    """Chaque KPI hero de la Vue Exécutive expose un drill_down_href cible."""

    def test_all_3_hero_kpis_have_drill_down_href(self, client):
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        assert response.status_code == 200, response.text
        body = response.json().get("data", {})
        kpis = body.get("kpis", [])
        # 3 KPIs hero attendus avec drill_down_href
        kpis_with_drilldown = [k for k in kpis if k.get("drill_down_href")]
        assert len(kpis_with_drilldown) >= 3, (
            f"Seuls {len(kpis_with_drilldown)}/{len(kpis)} KPI hero ont un drill_down_href. "
            f"KPIs : {[(k.get('label'), k.get('drill_down_href')) for k in kpis]}"
        )

    def test_trajectoire_drill_down_to_conformite_non_conform(self, client):
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        kpis = response.json().get("data", {}).get("kpis", [])
        kpi = next((k for k in kpis if "trajectoire" in (k.get("label") or "").lower()), None)
        assert kpi is not None, "KPI Trajectoire 2030 absent"
        href = kpi.get("drill_down_href", "")
        assert "/conformite" in href
        assert "filter=non_conform" in href, f"href={href}"

    def test_exposition_drill_down_to_conformite_exposure_components(self, client):
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        kpis = response.json().get("data", {}).get("kpis", [])
        kpi = next((k for k in kpis if "exposition" in (k.get("label") or "").lower()), None)
        assert kpi is not None, "KPI Exposition financière absent"
        href = kpi.get("drill_down_href", "")
        assert "/conformite" in href
        assert "view=exposure_components" in href, f"href={href}"

    def test_potentiel_drill_down_to_actions_filter_mwh(self, client):
        response = client.get("/api/pages/cockpit_comex/briefing", headers=HEADERS)
        kpis = response.json().get("data", {}).get("kpis", [])
        kpi = next((k for k in kpis if "potentiel" in (k.get("label") or "").lower()), None)
        assert kpi is not None, "KPI Potentiel énergétique récupérable absent"
        href = kpi.get("drill_down_href", "")
        assert "/actions" in href
        assert "filter=open" in href and "mwh_desc" in href, f"href={href}"


# ── Phase 3.bis.c : Cross-builder drill_down_href ──────────────────────


class TestDrillDownHrefCrossBuilder:
    """Phase 3.bis.c — chaque builder de page expose au moins un KPI hero
    avec drill_down_href. Verrouillage anti-régression : un nouveau builder
    ajouté sans drill_down_href doit faire échouer la CI.
    """

    PAGES = [
        ("cockpit_daily", "/cockpit/jour"),
        ("cockpit_comex", "/conformite"),
        ("patrimoine", "/patrimoine"),
        ("conformite", "/conformite"),
        ("bill_intel", "/bill-intel"),
        ("achat_energie", "/achat-energie"),
        ("monitoring", "/monitoring"),
        ("diagnostic", "/diagnostic-conso"),
        ("anomalies", "/anomalies"),
        ("flex", "/flex"),
    ]

    @pytest.mark.parametrize("page,expected_prefix", PAGES)
    def test_each_builder_exposes_drill_down(self, client, page, expected_prefix):
        response = client.get(f"/api/pages/{page}/briefing", headers=HEADERS)
        assert response.status_code == 200, f"page={page} status={response.status_code}"
        kpis = response.json().get("data", {}).get("kpis", [])
        with_drilldown = [k for k in kpis if k.get("drill_down_href")]
        assert with_drilldown, (
            f"Builder {page} n'expose AUCUN KPI hero avec drill_down_href (KPIs: {[k.get('label') for k in kpis]})"
        )
        # Au moins un href doit cibler la page principale du pillar
        hrefs = [k.get("drill_down_href", "") for k in with_drilldown]
        assert any(expected_prefix in h for h in hrefs), (
            f"Builder {page} : aucun drill_down_href ne cible {expected_prefix} (observed: {hrefs})"
        )


# ── Phase 3.4 : Routes legacy backend ──────────────────────────────────


class TestNoRouteLegacyExecutive:
    """Aucune route backend /executive, /dashboard, /synthese active.

    Les redirects sont gérés côté frontend (App.jsx). Le backend
    expose uniquement /api/* — pas de routes /dashboard ni /executive.
    """

    def test_backend_no_dashboard_route(self, client):
        # GET /dashboard sur le backend doit être 404 (pas une page)
        response = client.get("/dashboard")
        assert response.status_code in (404, 405), (
            f"Le backend ne doit pas exposer /dashboard (status {response.status_code})"
        )

    def test_backend_no_executive_route(self, client):
        response = client.get("/executive")
        assert response.status_code in (404, 405)

    def test_backend_no_synthese_route(self, client):
        response = client.get("/synthese")
        assert response.status_code in (404, 405)
