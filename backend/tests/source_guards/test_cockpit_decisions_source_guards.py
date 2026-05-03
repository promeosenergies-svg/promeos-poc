"""PROMEOS — Source guards cockpit_decisions_service (Vague 4 EPIC #274).

SG_DEC_01 — pas de constantes hardcodées (7500/0.052/0.227/0.02658/0.068/8.50)
SG_DEC_02 — pas de query SQL via f-string
SG_DEC_03 — doctrine.constants importé (DT_PENALTY_EUR etc.)
SG_DEC_04 — transform_acronym appelé (§6.3 ADR-004)

Ref : services/cockpit_decisions_service.py (582 lignes)
Doctrine §0.D décision A : € traçable réglementaire.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DEC_PATH = os.path.join(_BACKEND_ROOT, "services", "cockpit_decisions_service.py")


def _read() -> str:
    with open(_DEC_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def _strip_docstrings(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"'''[\s\S]*?'''", "", src)


class TestCockpitDecisionsSourceGuards:
    def test_sg_dec_01_no_hardcoded_co2_factors(self):
        """SG_DEC_01 : pas de 0.052 / 0.227 hardcodés (CO₂ factors)."""
        src = _strip_docstrings(_read())
        for value, label in [("0.052", "CO₂ élec"), ("0.227", "CO₂ gaz")]:
            assert value not in src, (
                f"{label} ({value}) hardcodé dans cockpit_decisions_service — "
                "utiliser CO2_FACTOR_ELEC_KGCO2_PER_KWH depuis doctrine.constants"
            )

    def test_sg_dec_01_no_hardcoded_accise(self):
        """SG_DEC_01 : pas de 0.02658 (accise legacy) hardcodé."""
        src = _strip_docstrings(_read())
        assert "0.02658" not in src, "0.02658 hardcodé dans cockpit_decisions_service"

    def test_sg_dec_01_no_hardcoded_price_fallback(self):
        """SG_DEC_01 : pas de 0.068 (PRICE_FALLBACK) assigné directement."""
        src = _strip_docstrings(_read())
        assert not re.search(r"\s=\s0\.068\b", src), "0.068 assigné directement dans cockpit_decisions_service"

    def test_sg_dec_01_no_direct_dt_penalty_literal(self):
        """SG_DEC_01 : 7500 non assigné directement (doit venir DT_PENALTY_EUR)."""
        src = _strip_docstrings(_read())
        assert not re.search(r"=\s*7500\b", src), (
            "7500 assigné directement dans cockpit_decisions_service "
            "— doit venir DT_PENALTY_EUR depuis doctrine.constants"
        )

    def test_sg_dec_02_no_sql_fstring(self):
        """SG_DEC_02 : pas de query SQL construite via f-string."""
        src = _strip_docstrings(_read())
        patterns = [
            r'f"[^"]*\bSELECT\b',
            r"f'[^']*\bSELECT\b",
            r'text\s*\(\s*f["\']',
        ]
        for pattern in patterns:
            assert not re.search(pattern, src, re.IGNORECASE), (
                f"SQL f-string détecté dans cockpit_decisions_service : {pattern!r}"
            )

    def test_sg_dec_03_imports_doctrine_constants(self):
        """SG_DEC_03 : doctrine.constants importé (DT_PENALTY_EUR etc.)."""
        src = _read()
        assert "from doctrine.constants import" in src, (
            "cockpit_decisions_service doit importer depuis doctrine.constants"
        )
        # Vérifie spécifiquement DT_PENALTY_EUR
        assert "DT_PENALTY_EUR" in src, "DT_PENALTY_EUR doit être importé depuis doctrine.constants"

    def test_sg_dec_04_transform_acronym_called(self):
        """SG_DEC_04 : transform_acronym appelé (ADR-004 §6.3 — pas d'acronymes bruts)."""
        src = _read()
        assert "transform_acronym" in src, (
            "cockpit_decisions_service doit appeler doctrine.acronyms.transform_acronym "
            "(ADR-004 §6.3 : zéro acronyme brut dans les titres)"
        )
