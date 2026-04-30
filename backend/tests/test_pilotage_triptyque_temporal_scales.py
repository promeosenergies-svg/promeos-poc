"""Phase 4bis.3 — Sentinel #23 : triptyque temporel Pilotage cohérent.

La doctrine §11.3 décrit le Cockpit Pilotage comme un **triptyque temporel** :
court terme (J-1), moyen terme (mois courant vs N-1), long terme
(annuel + trajectoire 2030). Ces 3 échelles doivent être exposées
ENSEMBLE dans le payload `_facts` pour qu'un Energy Manager voie en
30s le tempo récent + la dérive du mois + la cible 2030 sans switcher
d'écran.

Ce sentinel verrouille la **présence simultanée** des 3 échelles
temporelles dans `_facts.consumption` + `_facts.power`, en garantissant
qu'aucune Phase future ne droppe silencieusement l'une des 3.

Couvre :
  - Court terme : `consumption.j_minus_1_mwh` + `power.peak_j_minus_1_kw`
  - Moyen terme : `consumption.monthly_vs_n1` (object avec ≥ 4 sous-clés)
  - Long terme : `consumption.annual_mwh` + `consumption.trajectory_2030_score`
  - Cohérence : si une échelle est exposée, toutes le sont (pas de drop
    partiel).

Ref : audit Sprint Retro Cockpit Dual Sol2 — sentinel #23 ambigu.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def facts_payload(client):
    r = client.get("/api/cockpit/_facts?org_id=1&period=current_week")
    assert r.status_code == 200, f"HTTP {r.status_code} sur /api/cockpit/_facts"
    return r.json()


class TestPilotageTriptyqueTemporalScales:
    """Vérifie la présence simultanée des 3 échelles temporelles du triptyque."""

    # ── Court terme — J-1 (besoin Energy Manager 30s) ─────────────────────

    def test_short_term_consumption_j_minus_1(self, facts_payload):
        """Court terme : `consumption.j_minus_1_mwh` exposé (peut être 0)."""
        consumption = facts_payload["consumption"]
        assert "j_minus_1_mwh" in consumption, "Sentinel #23 court terme : `consumption.j_minus_1_mwh` requis"
        assert isinstance(consumption["j_minus_1_mwh"], (int, float)), (
            "Sentinel #23 : `j_minus_1_mwh` doit être numérique"
        )

    def test_short_term_power_peak(self, facts_payload):
        """Court terme : `power.peak_j_minus_1_kw` exposé (point de mesure J-1)."""
        power = facts_payload["power"]
        assert "peak_j_minus_1_kw" in power, "Sentinel #23 court terme : `power.peak_j_minus_1_kw` requis"
        assert isinstance(power["peak_j_minus_1_kw"], (int, float)), (
            "Sentinel #23 : `peak_j_minus_1_kw` doit être numérique"
        )

    # ── Moyen terme — Mois courant vs N-1 (lissage saisonnier) ───────────

    def test_medium_term_monthly_vs_n1(self, facts_payload):
        """Moyen terme : `consumption.monthly_vs_n1` est un objet structuré."""
        consumption = facts_payload["consumption"]
        assert "monthly_vs_n1" in consumption, "Sentinel #23 moyen terme : `consumption.monthly_vs_n1` requis"
        mvs = consumption["monthly_vs_n1"]
        assert isinstance(mvs, dict), "Sentinel #23 : `monthly_vs_n1` doit être un objet structuré"

    def test_medium_term_monthly_has_required_subkeys(self, facts_payload):
        """`monthly_vs_n1` expose les 4 sous-clés canoniques."""
        mvs = facts_payload["consumption"]["monthly_vs_n1"]
        required = {
            "current_month_label",
            "current_month_mwh",
            "previous_year_month_normalized_mwh",
            "delta_pct_dju_adjusted",
        }
        missing = required - set(mvs.keys())
        assert not missing, (
            f"Sentinel #23 moyen terme : `monthly_vs_n1` manque {missing}. Sous-clés présentes : {set(mvs.keys())}"
        )

    # ── Long terme — Annuel + Trajectoire 2030 ────────────────────────────

    def test_long_term_annual_mwh(self, facts_payload):
        """Long terme : `consumption.annual_mwh` exposé (12 mois glissants)."""
        consumption = facts_payload["consumption"]
        assert "annual_mwh" in consumption, "Sentinel #23 long terme : `consumption.annual_mwh` requis"
        assert isinstance(consumption["annual_mwh"], (int, float)), "Sentinel #23 : `annual_mwh` doit être numérique"

    def test_long_term_trajectory_2030_score(self, facts_payload):
        """Long terme : `consumption.trajectory_2030_score` exposé."""
        consumption = facts_payload["consumption"]
        assert "trajectory_2030_score" in consumption, (
            "Sentinel #23 long terme : `consumption.trajectory_2030_score` requis"
        )

    # ── Cohérence cross-échelles (ne droppe pas une échelle silencieusement) ──

    def test_three_scales_present_simultaneously(self, facts_payload):
        """Les 3 échelles temporelles sont exposées ensemble (pas de drop partiel)."""
        consumption = facts_payload["consumption"]
        power = facts_payload["power"]
        # Court / Moyen / Long
        scales = {
            "short_term_j_minus_1": "j_minus_1_mwh" in consumption and "peak_j_minus_1_kw" in power,
            "medium_term_monthly": "monthly_vs_n1" in consumption,
            "long_term_annual": "annual_mwh" in consumption and "trajectory_2030_score" in consumption,
        }
        missing = [name for name, present in scales.items() if not present]
        assert not missing, (
            f"Sentinel #23 : triptyque temporel incomplet. Échelle(s) "
            f"absente(s) : {missing}. Doctrine §11.3 exige les 3 échelles "
            f"ensemble pour que l'Energy Manager voie en 30s le tempo "
            f"récent + dérive du mois + cible 2030."
        )

    def test_temporal_scales_have_consistent_units(self, facts_payload):
        """Les échelles temporelles utilisent des unités MWh cohérentes."""
        consumption = facts_payload["consumption"]
        # Toutes les valeurs énergétiques doivent être en MWh, pas kWh ni Wh
        for key in ("j_minus_1_mwh", "annual_mwh"):
            value = consumption.get(key)
            if value is not None and value > 0:
                # Sanity check : J-1 < 100 MWh (5 sites tertiaires)
                # Annual < 50 000 MWh
                assert value < 100_000, (
                    f"Sentinel #23 : `{key}={value}` semble être en kWh "
                    f"plutôt qu'en MWh (>100k impossible pour 5 sites)"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
