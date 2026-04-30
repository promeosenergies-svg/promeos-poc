"""Phase 4bis.2 — Sentinel #15 : HELIOS = mode `direct`.

Vérifie qu'avec le pack démo HELIOS (5 sites) le payload `_facts.scope`
expose `density_mode = 'direct'` ET les `density_thresholds` SoT.

Couvre :
  - End-to-end : appel `get_cockpit_facts(db, org_id=1)` → `scope.density_mode`
  - Présence de `density_thresholds` (objet avec `direct_max` + `condensed_max`)
  - Cohérence : `site_count <= direct_max` ⇒ density_mode == "direct"

Ref : audit Sprint Retro Cockpit Dual Sol2 — sentinel #15 absent. Phase 4bis.2.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestDensityModeHeliosDirect:
    def test_facts_scope_has_density_mode(self, client):
        """`_facts.scope.density_mode` est exposé (plus null comme pré-Phase 4bis)."""
        r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
        assert r.status_code == 200, f"HTTP {r.status_code} sur /api/cockpit/_facts"
        scope = r.json()["scope"]
        assert "density_mode" in scope, "Sentinel #15 : scope.density_mode doit être exposé dans le payload"
        assert scope["density_mode"] is not None, (
            "Sentinel #15 : scope.density_mode ne doit plus être null (régression Phase 4bis.2)"
        )

    def test_facts_scope_has_density_thresholds(self, client):
        """`_facts.scope.density_thresholds` expose les seuils SoT."""
        r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
        scope = r.json()["scope"]
        assert "density_thresholds" in scope, (
            "Sentinel #15 : scope.density_thresholds doit être exposé "
            "pour que le frontend puisse expliquer le mode au CFO"
        )
        thresholds = scope["density_thresholds"]
        assert thresholds["direct_max"] == 5, (
            f"Sentinel #15 : direct_max doit être 5, trouvé {thresholds.get('direct_max')}"
        )
        assert thresholds["condensed_max"] == 15, (
            f"Sentinel #15 : condensed_max doit être 15, trouvé {thresholds.get('condensed_max')}"
        )

    def test_helios_5_sites_mode_direct(self, client):
        """HELIOS S = 5 sites → density_mode == 'direct' (cf #15)."""
        r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
        scope = r.json()["scope"]
        assert scope["site_count"] == 5, (
            f"Précondition : pack HELIOS S = 5 sites, trouvé {scope['site_count']}. "
            f"Si tu as réseedé un autre pack, lance "
            f"`python -m services.demo_seed --pack helios --size S --reset`"
        )
        assert scope["density_mode"] == "direct", (
            f"Sentinel #15 : HELIOS 5 sites doit produire density_mode='direct', trouvé '{scope['density_mode']}'"
        )

    def test_density_mode_consistent_with_site_count(self, client):
        """Cohérence : density_mode dérivé déterministiquement de site_count."""
        r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
        scope = r.json()["scope"]
        sc = scope["site_count"]
        thresholds = scope["density_thresholds"]
        if sc <= thresholds["direct_max"]:
            expected = "direct"
        elif sc <= thresholds["condensed_max"]:
            expected = "condensed"
        else:
            expected = "clusters"
        assert scope["density_mode"] == expected, (
            f"Sentinel #14+15 : density_mode='{scope['density_mode']}' "
            f"incohérent avec site_count={sc} et thresholds={thresholds} "
            f"(attendu : '{expected}')"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
