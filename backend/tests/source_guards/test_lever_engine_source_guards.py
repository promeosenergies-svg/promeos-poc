"""PROMEOS — Source guards lever_engine_service (Vague 4 EPIC #274).

SG_LEV_01 — pas de constante gain € hardcodée sans source SoT
SG_LEV_02 — pas de pondération inline (pondérations dans doctrine/constants.py)
SG_LEV_03 — doctrine.constants importé (COCKPIT_ACTIVATION_THRESHOLD etc.)
SG_LEV_04 — exports publics stables (compute_actionable_levers)

Ref : services/lever_engine_service.py (480 lignes)
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LEV_PATH = os.path.join(_BACKEND_ROOT, "services", "lever_engine_service.py")


def _read() -> str:
    with open(_LEV_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def _strip_docstrings(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"'''[\s\S]*?'''", "", src)


class TestLeverEngineSourceGuards:
    def test_sg_lev_01_no_hardcoded_gain_8500(self):
        """SG_LEV_01 : pas de gain 8500€/site hardcodé sans SoT."""
        src = _strip_docstrings(_read())
        assert not re.search(r"=\s*8500\b", src), (
            "8500 (gain € par site) assigné directement dans lever_engine_service — "
            "doit venir d'une constante doctrine ou du calcul backend pondéré"
        )

    def test_sg_lev_01_no_hardcoded_co2_factor(self):
        """SG_LEV_01 : pas de 0.052 (CO₂ élec) hardcodé."""
        src = _strip_docstrings(_read())
        assert "0.052" not in src, "0.052 (CO₂ élec) hardcodé dans lever_engine_service"

    def test_sg_lev_01_no_hardcoded_price_elec(self):
        """SG_LEV_01 : pas de prix élec 0.068 / 0.13 / 0.15 hardcodé seul."""
        src = _strip_docstrings(_read())
        # On cherche une assignation directe d'un prix élec connu
        for value in ["= 0.068", "= 0.13 ", "= 0.130"]:
            assert value not in src, (
                f"Prix élec {value!r} hardcodé dans lever_engine_service — "
                "utiliser PRICE_ELEC_ETI_2026_EUR_PER_MWH depuis doctrine.constants"
            )

    def test_sg_lev_02_no_inline_weighting(self):
        """SG_LEV_02 : pas de pondération inline (0.5/0.3/0.2 pour DT/BACS/APER)."""
        src = _strip_docstrings(_read())
        # Pondérations doctrinales appartiennent à doctrine/constants.py
        # On détecte un triple pattern poids additionnés = 1.0
        inline_weight = re.search(
            r"0\.[3-5]\s*[+*]\s*\w+\s*[+*]\s*0\.[2-4]\s*[+*]\s*\w+\s*[+*]\s*0\.[1-3]",
            src,
        )
        assert not inline_weight, (
            "Pondération inline DT+BACS+APER détectée dans lever_engine_service — utiliser doctrine.constants"
        )

    def test_sg_lev_03_imports_doctrine_constants(self):
        """SG_LEV_03 : doctrine.constants importé (COCKPIT_ACTIVATION_THRESHOLD etc.)."""
        src = _read()
        assert "from doctrine.constants import" in src, "lever_engine_service doit importer depuis doctrine.constants"
        assert "COCKPIT_ACTIVATION_THRESHOLD" in src, (
            "COCKPIT_ACTIVATION_THRESHOLD doit être importé (seuil activation doctrine)"
        )

    def test_sg_lev_04_compute_actionable_levers_public(self):
        """SG_LEV_04 : compute_actionable_levers est la fonction publique stable."""
        from services.lever_engine_service import compute_actionable_levers

        assert callable(compute_actionable_levers)

        sig = inspect.signature(compute_actionable_levers)
        params = list(sig.parameters.keys())
        # Doit accepter kpis + billing_summary au minimum
        assert "kpis" in params, "paramètre 'kpis' absent de compute_actionable_levers"
