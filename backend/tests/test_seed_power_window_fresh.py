"""Phase 28 — Sentinel : seed power window doit toujours se terminer aujourd'hui.

Avant Phase 28, `gen_power.py` ligne 138 hardcodait
`end_dt = datetime(2026, 4, 1, 0, 0)`. Quand on lançait un seed après cette
date (ex: 2026-05-01), les PowerReadings s'arrêtaient à J-30 minimum,
provoquant un fallback `peak_source = j-99` et un affichage trompeur
"Mesure du J-99 (CDC J-1 en synchro SGE)".

Cette source-guard verrouille que `gen_power._seed_power_data` (ou son
équivalent) utilise toujours `date.today()` comme fin de fenêtre, garantissant
que toute exécution future du seed produit des PowerReadings J-1.

Ref : Sprint Retro Cockpit Dual Sol2 — anomalie #1 (peak_source j-99).
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GEN_POWER = REPO_ROOT / "backend" / "services" / "demo_seed" / "gen_power.py"


class TestSeedPowerWindowFresh:
    def test_no_hardcoded_end_dt_2026(self):
        """`gen_power.py` ne doit pas hardcoder `datetime(2026, X, X)` comme end_dt."""
        src = GEN_POWER.read_text(encoding="utf-8")
        # Recherche de pattern `end_dt = datetime(<année>, ...)` avec année literal
        # Format attendu Phase 28+ : `end_dt = datetime.combine(date.today(), ...)`
        bad_pattern = "end_dt = datetime(2026"
        assert bad_pattern not in src, (
            f"Phase 28 régression : `gen_power.py` ne doit pas hardcoder "
            f"`{bad_pattern}` comme end_dt. Utiliser `datetime.combine("
            f"date.today(), datetime.min.time())` pour que les PowerReadings "
            f"soient toujours à J-1 quel que soit le moment du seed."
        )

    def test_end_dt_uses_date_today(self):
        """`gen_power.py` utilise bien `date.today()` pour end_dt."""
        src = GEN_POWER.read_text(encoding="utf-8")
        assert "date.today()" in src, (
            "Phase 28 : `gen_power.py` doit utiliser `date.today()` (via datetime.combine) pour la fin de fenêtre seed"
        )

    def test_phase28_comment_present(self):
        """Le commentaire Phase 28 explicatif est présent (anti-régression)."""
        src = GEN_POWER.read_text(encoding="utf-8")
        assert "Phase 28" in src, (
            "Phase 28 : commentaire explicatif manquant dans gen_power.py (la justification du fix doit rester visible)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
