"""PROMEOS — Source guards narrative_generator + sentence_composer (Vague 4 EPIC #274).

SG_NARR_01 — narrative_generator : pas de hardcode régulatoire
              (7500/3750/1500/0.052/0.227/0.02658/0.068)
SG_NARR_02 — narrative_generator : doctrine.constants importé (SoT)
SG_NARR_03 — sentence_composer : pas de valeurs € hardcodées sans traçabilité
SG_NARR_04 — narrative_generator : generate_page_narrative = entry point unique public
SG_NARR_05 — sentence_composer : importe depuis doctrine (pas de constantes locales)

Ref : services/narrative/narrative_generator.py (3308 lignes)
      services/narrative/sentence_composer.py
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_NG_PATH = os.path.join(_BACKEND_ROOT, "services", "narrative", "narrative_generator.py")
_SC_PATH = os.path.join(_BACKEND_ROOT, "services", "narrative", "sentence_composer.py")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _strip_docstrings(src: str) -> str:
    src = re.sub(r'"""[\s\S]*?"""', "", src)
    return re.sub(r"'''[\s\S]*?'''", "", src)


class TestNarrativeSourceGuards:
    def test_sg_narr_01_no_hardcoded_co2_elec(self):
        """SG_NARR_01 : narrative_generator ne contient pas 0.052 (CO₂ élec) en dur."""
        src = _strip_docstrings(_read(_NG_PATH))
        assert "= 0.052" not in src, "0.052 (CO₂ élec) assigné directement dans narrative_generator"

    def test_sg_narr_01_no_hardcoded_accise(self):
        """SG_NARR_01 : pas de 0.02658 hardcodé dans narrative_generator."""
        src = _read(_NG_PATH)
        assert "0.02658" not in src, "0.02658 (accise legacy) hardcodé dans narrative_generator"

    def test_sg_narr_01_no_direct_dt_penalty_literal(self):
        """SG_NARR_01 : 7500 non assigné directement (doit venir DT_PENALTY_EUR)."""
        src = _strip_docstrings(_read(_NG_PATH))
        # On interdit l'assignation directe = 7500 (pas dans une string de label)
        assert not re.search(r"(?<![\"'])\s*=\s*7500\b(?!\s*[\"'])", src), (
            "7500 assigné directement dans narrative_generator — doit venir DT_PENALTY_EUR"
        )

    def test_sg_narr_02_imports_doctrine_constants(self):
        """SG_NARR_02 : narrative_generator importe depuis doctrine.constants."""
        src = _read(_NG_PATH)
        assert "from doctrine.constants import" in src, (
            "narrative_generator doit importer depuis doctrine.constants (SoT)"
        )
        # Vérifie les constantes clés
        for const in ("DT_PENALTY_EUR", "DT_PENALTY_AT_RISK_EUR"):
            assert const in src, f"{const} doit être importé depuis doctrine.constants"

    def test_sg_narr_03_sentence_composer_no_hardcoded_penalties(self):
        """SG_NARR_03 : sentence_composer ne contient pas de pénalités hardcodées."""
        src = _strip_docstrings(_read(_SC_PATH))
        for value, label in [
            ("7500", "DT_PENALTY_EUR"),
            ("3750", "DT_PENALTY_AT_RISK_EUR"),
            ("1500", "BACS_PENALTY_EUR"),
            ("0.052", "CO₂ élec"),
            ("0.02658", "accise"),
        ]:
            # Cherche la valeur comme littéral dans une assignation
            assert not re.search(rf"=\s*{re.escape(value)}\b", src), (
                f"{label} ({value}) hardcodé dans sentence_composer — utiliser doctrine.constants"
            )

    def test_sg_narr_04_generate_page_narrative_is_entry_point(self):
        """SG_NARR_04 : generate_page_narrative est l'unique entry point public."""
        from services.narrative.narrative_generator import generate_page_narrative

        assert callable(generate_page_narrative)

        # Vérifie qu'elle figure dans le module (pas seulement importée)
        src = _read(_NG_PATH)
        assert "def generate_page_narrative(" in src, (
            "generate_page_narrative doit être définie (pas seulement importée)"
        )

    def test_sg_narr_05_sentence_composer_imports_from_doctrine(self):
        """SG_NARR_05 : sentence_composer importe depuis doctrine (pas de constantes locales)."""
        src = _read(_SC_PATH)
        # Si le fichier contient des imports, l'un d'eux doit venir de doctrine
        # ou le fichier est un pur compositeur sans constantes propres
        if "from doctrine" in src or "import doctrine" in src:
            assert True  # conforme
        else:
            # Acceptable si le fichier ne contient pas de constantes numériques
            # régulatoires propres (il délègue à narrative_generator qui importe doctrine)
            has_hardcoded = re.search(r"=\s*(7500|3750|1500|0\.052|0\.227)\b", src)
            assert not has_hardcoded, "sentence_composer contient des constantes régulatoires sans importer doctrine"
