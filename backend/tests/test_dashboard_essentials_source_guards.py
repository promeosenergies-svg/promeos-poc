"""PROMEOS — Source guards dashboard_essentials_service (Vague 4 EPIC #274).

SG_DASH_01 — exports publics stables (build_dashboard_essentials, build_watchlist,
              check_consistency, build_executive_summary, build_executive_kpis)
SG_DASH_02 — pas de logique bousculée par refonte (signatures stables)
SG_DASH_03 — pas de constantes régulatoires hardcodées (7500/0.052/0.227)
SG_DASH_04 — DashboardEssentials dataclass exportée

Ref : services/dashboard_essentials_service.py (1240 lignes)
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DASH_PATH = os.path.join(_BACKEND_ROOT, "services", "dashboard_essentials_service.py")


def _read() -> str:
    with open(_DASH_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def _strip_docstrings(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"'''[\s\S]*?'''", "", src)


class TestDashboardEssentialsPublicAPI:
    """SG_DASH_01 — exports publics stables."""

    EXPECTED_PUBLIC = [
        "build_watchlist",
        "check_consistency",
        "build_top_sites",
        "build_executive_summary",
        "build_executive_kpis",
        "build_dashboard_essentials",
    ]

    def test_sg_dash_01_all_public_functions_present(self):
        """SG_DASH_01 : toutes les fonctions publiques connues sont présentes."""
        from services import dashboard_essentials_service

        for fn_name in self.EXPECTED_PUBLIC:
            fn = getattr(dashboard_essentials_service, fn_name, None)
            assert fn is not None and callable(fn), (
                f"Fonction publique '{fn_name}' manquante dans dashboard_essentials_service"
            )

    def test_sg_dash_04_dashboard_essentials_dataclass(self):
        """SG_DASH_04 : DashboardEssentials dataclass exportée."""
        from services.dashboard_essentials_service import DashboardEssentials

        assert DashboardEssentials is not None


class TestDashboardEssentialsSignatures:
    """SG_DASH_02 — signatures stables (anti-régression refonte)."""

    def test_sg_dash_02_build_watchlist_signature(self):
        """SG_DASH_02 : build_watchlist(kpis, sites) signature stable."""
        from services.dashboard_essentials_service import build_watchlist

        sig = inspect.signature(build_watchlist)
        params = list(sig.parameters.keys())
        assert "kpis" in params, "paramètre 'kpis' absent de build_watchlist"

    def test_sg_dash_02_build_dashboard_essentials_signature(self):
        """SG_DASH_02 : build_dashboard_essentials accepte sites (au minimum)."""
        from services.dashboard_essentials_service import build_dashboard_essentials

        sig = inspect.signature(build_dashboard_essentials)
        params = list(sig.parameters.keys())
        assert "sites" in params, "paramètre 'sites' absent de build_dashboard_essentials"

    def test_sg_dash_02_build_executive_summary_exists(self):
        """SG_DASH_02 : build_executive_summary existe et est callable."""
        from services.dashboard_essentials_service import build_executive_summary

        assert callable(build_executive_summary)

    def test_sg_dash_02_check_consistency_returns_result(self):
        """SG_DASH_02 : check_consistency(kpis={}) retourne un ConsistencyResult."""
        from services.dashboard_essentials_service import ConsistencyResult, check_consistency

        result = check_consistency({})
        assert isinstance(result, ConsistencyResult), (
            f"check_consistency({{}}) doit retourner ConsistencyResult, got {type(result)}"
        )


class TestDashboardEssentialsNoHardcode:
    """SG_DASH_03 — pas de constantes régulatoires hardcodées."""

    def test_sg_dash_03_no_hardcoded_co2_factor(self):
        """SG_DASH_03 : pas de 0.052 (CO₂ élec) hardcodé."""
        src = _strip_docstrings(_read())
        assert "= 0.052" not in src, "0.052 (CO₂ élec) assigné directement dans dashboard_essentials_service"

    def test_sg_dash_03_no_hardcoded_dt_penalty(self):
        """SG_DASH_03 : 7500 non assigné directement (doit venir doctrine)."""
        src = _strip_docstrings(_read())
        assert not re.search(r"=\s*7500\b", src), "7500 assigné directement dans dashboard_essentials_service"

    def test_sg_dash_03_no_hardcoded_accise(self):
        """SG_DASH_03 : pas de 0.02658 (accise legacy) hardcodé."""
        src = _strip_docstrings(_read())
        assert "0.02658" not in src, "0.02658 (accise legacy) hardcodé dans dashboard_essentials_service"
