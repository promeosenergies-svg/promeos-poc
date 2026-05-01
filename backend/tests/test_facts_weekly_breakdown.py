"""Phase 27 — Sentinel `_facts.consumption.weekly_breakdown[]`.

Avant Phase 27, la card SVG ConsoSevenDaysBars rendait 7 hauteurs hardcodées
(L 8 MWh, M 7,7 MWh, …, S 11,7 MWh anomalie). Phase 26.bis avait ajouté des
tooltips natifs <title> au hover mais avec valeurs estimées depuis position
pixel. Phase 27 expose le breakdown réel depuis la DB pour rendre le SVG
data-driven.

Ce sentinel verrouille :
  - `_facts.consumption.weekly_breakdown` est exposé dans le payload
  - C'est une liste de 7 entries (J-7 → J-1 ordonnées chronologiquement)
  - Chaque entry expose les 8 champs canoniques utilisés par le FE :
    `day_iso`, `day_label`, `day_letter`, `mwh`, `baseline_mwh`,
    `is_anomaly`, `delta_pct`, `low_confidence`
  - `is_anomaly` = bool (delta_pct vs baseline > 25 %)
  - `low_confidence` = bool (weekend, samedi/dimanche)

Ref : Sprint Retro Cockpit Dual Sol2 — Phase 27 (post-revue Claude externe
2026-05-01).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

CANONICAL_DAY_KEYS = {
    "day_iso",
    "day_label",
    "day_letter",
    "mwh",
    "baseline_mwh",
    "is_anomaly",
    "delta_pct",
    "low_confidence",
}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def facts_payload(client):
    r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
    assert r.status_code == 200, f"HTTP {r.status_code}"
    return r.json()


@pytest.fixture(scope="module")
def weekly_breakdown(facts_payload):
    return facts_payload["consumption"]["weekly_breakdown"]


class TestWeeklyBreakdown:
    def test_section_exposed_in_consumption(self, facts_payload):
        """`_facts.consumption.weekly_breakdown` exposé."""
        consumption = facts_payload["consumption"]
        assert "weekly_breakdown" in consumption, (
            "Phase 27 : `_facts.consumption.weekly_breakdown` doit être exposé "
            "pour permettre à ConsoSevenDaysBars FE de rendre les vraies MWh "
            "(avant Phase 27 : hauteurs SVG hardcodées)"
        )
        assert isinstance(consumption["weekly_breakdown"], list), "Phase 27 : weekly_breakdown doit être une liste"

    def test_seven_entries_chronological(self, weekly_breakdown):
        """Exactement 7 entries (J-7 → J-1) ordonnées chronologiquement."""
        assert len(weekly_breakdown) == 7, (
            f"Phase 27 : weekly_breakdown doit avoir 7 entries (J-7 → J-1), trouvé {len(weekly_breakdown)}"
        )
        # Ordre chronologique : day_iso croissants
        dates = [d["day_iso"] for d in weekly_breakdown]
        assert dates == sorted(dates), (
            f"Phase 27 : entries doivent être ordonnées chronologiquement (J-7 → J-1), trouvé : {dates}"
        )

    def test_each_entry_has_canonical_keys(self, weekly_breakdown):
        """Chaque entry expose les 8 champs canoniques."""
        for entry in weekly_breakdown:
            missing = CANONICAL_DAY_KEYS - set(entry.keys())
            assert not missing, (
                f"Phase 27 : entry {entry.get('day_iso')} manque {missing}. Champs présents : {set(entry.keys())}"
            )

    def test_day_letter_is_lmmjvsd(self, weekly_breakdown):
        """`day_letter` ∈ {L, M, J, V, S, D}."""
        valid_letters = {"L", "M", "J", "V", "S", "D"}
        for entry in weekly_breakdown:
            assert entry["day_letter"] in valid_letters, (
                f"Phase 27 : day_letter={entry['day_letter']!r} invalide (attendu : {valid_letters})"
            )

    def test_day_label_is_french(self, weekly_breakdown):
        """`day_label` est le nom complet français du jour."""
        valid_labels = {
            "Lundi",
            "Mardi",
            "Mercredi",
            "Jeudi",
            "Vendredi",
            "Samedi",
            "Dimanche",
        }
        for entry in weekly_breakdown:
            assert entry["day_label"] in valid_labels, f"Phase 27 : day_label={entry['day_label']!r} invalide"

    def test_mwh_is_numeric_and_positive_or_zero(self, weekly_breakdown):
        """`mwh` est numérique ≥ 0 (pas de valeur négative ni string)."""
        for entry in weekly_breakdown:
            assert isinstance(entry["mwh"], (int, float)), (
                f"Phase 27 : mwh doit être numérique, trouvé {type(entry['mwh'])}"
            )
            assert entry["mwh"] >= 0, f"Phase 27 : mwh doit être ≥ 0, trouvé {entry['mwh']}"

    def test_low_confidence_true_on_weekends(self, weekly_breakdown):
        """`low_confidence` est True pour samedi/dimanche, False sinon."""
        for entry in weekly_breakdown:
            is_weekend = entry["day_label"] in ("Samedi", "Dimanche")
            assert entry["low_confidence"] == is_weekend, (
                f"Phase 27 : {entry['day_label']} doit avoir "
                f"low_confidence={is_weekend}, trouvé {entry['low_confidence']}"
            )

    def test_is_anomaly_consistent_with_delta_pct(self, weekly_breakdown):
        """`is_anomaly` = True ⇔ |delta_pct| > 25."""
        for entry in weekly_breakdown:
            delta_abs = abs(entry["delta_pct"])
            expected_anomaly = delta_abs > 25
            assert entry["is_anomaly"] == expected_anomaly, (
                f"Phase 27 cohérence : {entry['day_label']} delta={entry['delta_pct']}% "
                f"doit donner is_anomaly={expected_anomaly}, trouvé {entry['is_anomaly']}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
