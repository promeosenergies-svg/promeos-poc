"""PROMEOS — Source guards cockpit_facts_service (Vague 4 EPIC #274).

SG_FACTS_01 — pas de constantes hardcodées (7500/0.052/0.227/0.02658/0.068/8.50)
SG_FACTS_02 — pas de query SQL via f-string (params SQLAlchemy uniquement)
SG_FACTS_03 — doctrine.constants importé (SoT canonique)
SG_FACTS_04 — exports publics stables (get_cockpit_facts ou équivalent)

Ref : services/cockpit_facts_service.py
"""

from __future__ import annotations

import inspect
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FACTS_PATH = os.path.join(_BACKEND_ROOT, "services", "cockpit_facts_service.py")


def _read() -> str:
    with open(_FACTS_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def _strip_docstrings(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"'''[\s\S]*?'''", "", src)


class TestCockpitFactsSourceGuards:
    def test_sg_facts_01_no_hardcoded_co2_elec(self):
        """SG_FACTS_01 : pas de 0.052 (CO2_FACTOR_ELEC) hardcodé."""
        src = _strip_docstrings(_read())
        assert "0.052" not in src, "0.052 (CO₂ élec) hardcodé dans cockpit_facts_service — utiliser doctrine.constants"

    def test_sg_facts_01_no_hardcoded_co2_gaz(self):
        """SG_FACTS_01 : pas de 0.227 (CO2_FACTOR_GAZ) hardcodé."""
        src = _strip_docstrings(_read())
        assert "0.227" not in src, "0.227 (CO₂ gaz) hardcodé dans cockpit_facts_service — utiliser doctrine.constants"

    def test_sg_facts_01_no_hardcoded_accise(self):
        """SG_FACTS_01 : pas de 0.02658 (accise legacy) hardcodé."""
        src = _strip_docstrings(_read())
        assert "0.02658" not in src, "0.02658 (accise legacy) hardcodé dans cockpit_facts_service"

    def test_sg_facts_01_no_hardcoded_price_fallback(self):
        """SG_FACTS_01 : pas de 0.068 (PRICE_FALLBACK) hardcodé comme literal standalone."""
        src = _strip_docstrings(_read())
        # 0.068 peut apparaître dans des formats de chaîne — on cherche assignment
        assert not re.search(r"\s=\s0\.068\b", src), (
            "0.068 assigné directement dans cockpit_facts_service — utiliser doctrine.constants"
        )

    def test_sg_facts_02_no_sql_fstring(self):
        """SG_FACTS_02 : pas de query SQL via f-string (risque injection)."""
        src = _strip_docstrings(_read())
        # Patterns f-string avec SELECT / WHERE / INSERT
        sql_fstring_patterns = [
            r'f"[^"]*\bSELECT\b',
            r"f'[^']*\bSELECT\b",
            r'f"[^"]*\bWHERE\b.*\{',
            r"f'[^']*\bWHERE\b.*\{",
            r"text\s*\(\s*f[\"']",
        ]
        for pattern in sql_fstring_patterns:
            assert not re.search(pattern, src, re.IGNORECASE), (
                f"Pattern SQL f-string détecté dans cockpit_facts_service : {pattern!r}"
            )

    def test_sg_facts_03_imports_doctrine_constants(self):
        """SG_FACTS_03 : doctrine.constants importé (SoT canonique)."""
        src = _read()
        assert "from doctrine.constants import" in src or "doctrine.constants" in src, (
            "cockpit_facts_service doit importer depuis doctrine.constants"
        )

    def test_sg_facts_04_public_function_exists(self):
        """SG_FACTS_04 : au moins une fonction publique de type get_cockpit_facts."""
        from services import cockpit_facts_service

        # Cherche une fonction publique get_*
        public_fns = [
            name
            for name in dir(cockpit_facts_service)
            if name.startswith("get_") and callable(getattr(cockpit_facts_service, name))
        ]
        assert public_fns, (
            f"Aucune fonction publique get_* dans cockpit_facts_service. "
            f"Symbols: {[n for n in dir(cockpit_facts_service) if not n.startswith('_')][:10]}"
        )
