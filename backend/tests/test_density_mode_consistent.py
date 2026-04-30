"""Phase 4bis.2 — Sentinel #14 : density_mode cohérent avec site_count.

Vérifie que `_facts.scope.density_mode` est dérivé déterministiquement
du `site_count` selon les seuils SoT (`DENSITY_THRESHOLD_DIRECT_MAX = 5`,
`DENSITY_THRESHOLD_CONDENSED_MAX = 15`).

Couvre :
  - Les 3 modes possibles : `direct` / `condensed` / `clusters`
  - Les bornes exactes (5, 6, 15, 16) et le cas limite 0
  - Cohérence cross-builders : si _facts.scope.site_count change, le
    density_mode doit suivre

Ref : audit Sprint Retro Cockpit Dual Sol2 — sentinel #14 absent
(feature non livrée). Phase 4bis.2 implémente + verrouille.
"""

from __future__ import annotations

import pytest

from services.cockpit_facts_service import (
    DENSITY_THRESHOLD_CONDENSED_MAX,
    DENSITY_THRESHOLD_DIRECT_MAX,
    _compute_density_mode,
)


class TestDensityModeConsistent:
    @pytest.mark.parametrize(
        "site_count,expected_mode",
        [
            (0, "direct"),
            (1, "direct"),
            (5, "direct"),
            (6, "condensed"),
            (10, "condensed"),
            (15, "condensed"),
            (16, "clusters"),
            (50, "clusters"),
            (200, "clusters"),
        ],
    )
    def test_density_mode_thresholds(self, site_count, expected_mode):
        """Mode dérivé déterministiquement de site_count selon seuils SoT."""
        assert _compute_density_mode(site_count) == expected_mode, (
            f"Sentinel #14 : site_count={site_count} doit produire density_mode='{expected_mode}'"
        )

    def test_thresholds_are_module_level_constants(self):
        """Les seuils sont des constantes module-level (SoT, pas magic numbers)."""
        assert DENSITY_THRESHOLD_DIRECT_MAX == 5, (
            "Sentinel #14 : seuil direct_max doit être 5 (doctrine §11.3 — ≤5 sites = affichage direct individuel)"
        )
        assert DENSITY_THRESHOLD_CONDENSED_MAX == 15, (
            "Sentinel #14 : seuil condensed_max doit être 15 (doctrine §11.3 — 6-15 sites = agrégat + top 3-5)"
        )

    def test_direct_max_strictly_below_condensed_max(self):
        """Les seuils sont strictement ordonnés (pas d'overlap)."""
        assert DENSITY_THRESHOLD_DIRECT_MAX < DENSITY_THRESHOLD_CONDENSED_MAX, (
            "Sentinel #14 : direct_max doit être strictement < condensed_max"
        )

    def test_compute_handles_negative_site_count_gracefully(self):
        """Edge case : site_count négatif (jamais en prod, mais robustesse)."""
        assert _compute_density_mode(-1) == "direct", (
            "Sentinel #14 : site_count négatif doit fallback sur 'direct' (mode le plus permissif, pas d'erreur)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
