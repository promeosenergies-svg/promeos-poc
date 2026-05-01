"""Phase 28.bis — Sentinel : `_resolve_best_freq` ne retourne JAMAIS toutes
les fréquences (anti quadruple-counting).

Avant Phase 28.bis, `_resolve_best_freq` ligne `return compatible` retournait
les 4 fréquences compatibles (MIN_15 + MIN_30 + HOURLY + DAILY) quand le
filter timestamp ne matchait rien (bug ISO 'T' vs espace SQLite). Les callers
utilisant `frequency.in_(best)` cumulaient alors les 4 fréquences pour la
même journée → quadruple-counting silencieux (J-1 affichait 25.6 MWh au
lieu de ~8 MWh réels).

Ce sentinel verrouille :
  1. `_resolve_best_freq` retourne au plus 1 fréquence pour granularity ≥ 30min
  2. Filter timestamp utilise `func.date(timestamp)` (string-safe SQLite)
  3. Runtime : J-1 cockpit_facts < 15 MWh pour HELIOS S (sanity check
     plausibilité physique : 5 sites tertiaires ne consomment pas 25+ MWh/j)

Ref : Sprint Retro Cockpit Dual Sol2 — anomalie #2 baseline 3× trop basse
(audit utilisateur 2026-05-01).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app

REPO_ROOT = Path(__file__).resolve().parents[2]
TIMESERIES_PY = REPO_ROOT / "backend" / "services" / "ems" / "timeseries_service.py"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


class TestResolveBestFreqNoQuadrupleCount:
    def test_resolve_best_freq_uses_func_date(self):
        """Phase 28.bis : `_resolve_best_freq` utilise `func.date()` (string-safe)
        pour comparer timestamp avec date_from/date_to (cf bug ISO T vs espace
        SQLite documenté dans `j_minus_1_with_fallback`)."""
        src = TIMESERIES_PY.read_text(encoding="utf-8")
        # Présence du fix `func.date(MeterReading.timestamp)`
        # dans la fonction _resolve_best_freq (à minima 2 occurrences :
        # `>=` et `<=`).
        # Recherche scope-restreinte au corps de _resolve_best_freq
        start = src.find("def _resolve_best_freq")
        assert start >= 0, "fonction _resolve_best_freq introuvable"
        next_def = src.find("\ndef ", start + 1)
        body = src[start:next_def] if next_def > 0 else src[start:]
        assert "func.date(MeterReading.timestamp)" in body, (
            "Phase 28.bis : `_resolve_best_freq` doit utiliser "
            "`func.date(MeterReading.timestamp)` pour matcher les timestamps "
            "ISO SQLite (bug T vs espace). Sans ce fix : bucket_count=0 pour "
            "toutes les freq → fallback `return compatible` → quadruple-counting."
        )

    def test_resolve_best_freq_fallback_returns_single_freq(self):
        """Phase 28.bis : le fallback APRÈS la boucle for retourne 1 seule
        fréquence (la plus grossière) au lieu de toutes les freq compatibles.

        Le early-return `len(compatible) <= 1: return compatible` ligne 479
        est OK (au max 1 freq). Le danger était le `return compatible` final
        qui retournait jusqu'à 4 freq quand le filter timestamp échouait.
        """
        src = TIMESERIES_PY.read_text(encoding="utf-8")
        start = src.find("def _resolve_best_freq")
        next_def = src.find("\ndef ", start + 1)
        body = src[start:next_def] if next_def > 0 else src[start:]
        # On cherche le `return compatible` SUITE à la boucle `for freq in
        # reversed(compatible)`. Si présent, c'est le bug Phase 28.bis.
        for_loop_idx = body.find("for freq in reversed(compatible)")
        assert for_loop_idx > 0, "boucle `for freq in reversed(compatible)` introuvable"
        post_loop = body[for_loop_idx:]
        bad_lines = [line for line in post_loop.split("\n") if line.strip() == "return compatible"]
        assert not bad_lines, (
            f"Phase 28.bis : `return compatible` (toutes les freq) APRÈS "
            f"la boucle for provoque un quadruple-counting via "
            f"`frequency.in_(best)`. Utiliser `return [compatible[-1]]` "
            f"(1 seule freq la plus grossière) comme fallback. "
            f"Lignes coupables : {bad_lines}"
        )

    def test_runtime_j_minus_1_under_plausibility_threshold(self, client):
        """Sanity check runtime : J-1 cockpit_facts < 15 MWh pour HELIOS S.

        Plausibilité physique : 5 sites tertiaires (17 500 m²) consomment
        ~3-12 MWh/jour ouvré. Au-delà de 15 MWh, c'est probablement un bug
        de cumul (cf Phase 28.bis : avant fix, J-1 affichait 25.6 MWh =
        4× cumul fréquences).
        """
        r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
        assert r.status_code == 200
        jm1 = r.json()["consumption"]["j_minus_1_mwh"]
        if jm1 == 0:
            pytest.skip("j_minus_1_mwh=0 — DB ou seed indisponible, test non discriminant")
        assert jm1 < 15.0, (
            f"Phase 28.bis sanity : j_minus_1_mwh={jm1} MWh > 15 MWh "
            f"(plausibilité physique HELIOS 5 sites). Probablement un bug de "
            f"cumul fréquences (cf bug `_resolve_best_freq` ligne `return "
            f"compatible`)."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
