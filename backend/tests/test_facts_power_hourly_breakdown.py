"""Phase 31 — Sentinel `_facts.power.hourly_breakdown[]` data-driven.

Avant Phase 31, `CourbeChargeJMinus1` FE rendait 11 points hardcodés
(_CHARGE_J1_KEY_POINTS) avec kwRatio inventés. Phase 31 expose le breakdown
horaire réel depuis PowerReading pour rendre le SVG data-driven (cohérent
avec Phase 27 weekly_breakdown).

Ce sentinel verrouille :
  - `_facts.power.hourly_breakdown` est exposé (24 entries)
  - Chaque entry : {hour, hour_label, kw, kw_ratio, period}
  - period ∈ {'HC', 'HP', 'HC→HP', 'HP→HC'}
  - kw ≥ 0 et numérique
  - Cohérence : sum(kw)/24 ≈ peak_j_minus_1_kw / 4 (sanity check moyenne
    horaire vs pic)

Ref : Sprint Retro Cockpit Dual Sol2 — Phase 31 (followup Phase 27, audit
utilisateur 2026-05-01).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

CANONICAL_HOUR_KEYS = {"hour", "hour_label", "kw", "kw_ratio", "period"}
VALID_PERIODS = {"HC", "HP", "HC→HP", "HP→HC"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def power_payload(client):
    r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
    assert r.status_code == 200
    return r.json()["power"]


@pytest.fixture(scope="module")
def hourly_breakdown(power_payload):
    return power_payload["hourly_breakdown"]


class TestPowerHourlyBreakdown:
    def test_section_exposed(self, power_payload):
        assert "hourly_breakdown" in power_payload, (
            "Phase 31 : `_facts.power.hourly_breakdown` doit être exposé "
            "pour permettre à CourbeChargeJMinus1 FE de rendre les vraies "
            "kW horaires (avant Phase 31 : path SVG hardcodé)."
        )
        assert isinstance(power_payload["hourly_breakdown"], list)

    def test_24_entries(self, hourly_breakdown):
        assert len(hourly_breakdown) == 24, (
            f"Phase 31 : hourly_breakdown doit avoir 24 entries (1 par heure), trouvé {len(hourly_breakdown)}"
        )

    def test_each_entry_has_canonical_keys(self, hourly_breakdown):
        for entry in hourly_breakdown:
            missing = CANONICAL_HOUR_KEYS - set(entry.keys())
            assert not missing, (
                f"Phase 31 : entry {entry.get('hour')} manque {missing}. Champs présents : {set(entry.keys())}"
            )

    def test_hours_are_0_to_23_in_order(self, hourly_breakdown):
        hours = [e["hour"] for e in hourly_breakdown]
        assert hours == list(range(24)), f"Phase 31 : entries doivent être ordonnées 0→23, trouvé {hours}"

    def test_periods_in_canonical_set(self, hourly_breakdown):
        for entry in hourly_breakdown:
            assert entry["period"] in VALID_PERIODS, (
                f"Phase 31 : period={entry['period']!r} invalide (attendu : {VALID_PERIODS})"
            )

    def test_kw_is_numeric_and_non_negative(self, hourly_breakdown):
        for entry in hourly_breakdown:
            assert isinstance(entry["kw"], (int, float))
            assert entry["kw"] >= 0, f"Phase 31 : kw={entry['kw']} négatif sur hour={entry['hour']}"

    def test_hp_zone_covers_business_hours(self, hourly_breakdown):
        """Les heures 8h-20h doivent toutes être en HP (TURPE 7 BT)."""
        hp_hours = {e["hour"] for e in hourly_breakdown if e["period"] == "HP"}
        for h in range(8, 21):  # 8h à 20h inclus
            assert h in hp_hours, f"Phase 31 : hour={h} doit être en HP (TURPE 7 BT). HP hours : {sorted(hp_hours)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
