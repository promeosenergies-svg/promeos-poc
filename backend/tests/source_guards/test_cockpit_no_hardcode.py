"""
PROMEOS — Source-guard anti-hardcode Cockpit Jour (ADR-022 F.20b).

Vérifie que `backend/routes/cockpit.py` ne contient plus de valeurs
hardcodées qui devraient venir des services data-driven (F.16/F.17/F.18).

Bloque la régression vers les anciens hardcodes :
  - "value": 528          → KPI 3 pic doit venir de get_org_peak_kw
  - "value": 121          → ancienne valeur incorrecte (talon nuit)
  - "value": 6.2          → KPI 2 doit venir de get_org_daily_kwh
  - baseline_mwh = 6.5    → doit venir de get_org_baseline_daily_kwh
  - "subscribed_kw": 1500 → doit venir de get_org_subscribed_kw
  - hardcoded series_hp / series_hc literals
  - hardcoded "hl-lyon-dt-2030" etc dans _build_cockpit_jour_highlights

Doctrine ADR-022 anti-pattern #1 : "hardcoder un chiffre KPI dans
routes/cockpit.py sans appel service".
"""

from __future__ import annotations

from pathlib import Path

import pytest

COCKPIT_ROUTE = Path(__file__).resolve().parents[2] / "routes" / "cockpit.py"


@pytest.fixture(scope="module")
def cockpit_source() -> str:
    return COCKPIT_ROUTE.read_text(encoding="utf-8")


def test_no_hardcoded_kpi3_pic_value(cockpit_source: str):
    """KPI 3 pic puissance doit venir de get_org_peak_kw."""
    # Les anciennes valeurs hardcodées 121 et 528 ne doivent plus apparaître
    # dans un payload KPI directement (sauf en commentaire historique).
    forbidden_patterns = ['"value": 121,', '"value": 528,']
    for pattern in forbidden_patterns:
        assert pattern not in cockpit_source, (
            f"Hardcode interdit '{pattern}' encore présent — KPI 3 doit utiliser get_org_peak_kw (cf ADR-022 F.17)"
        )


def test_no_hardcoded_kpi2_conso_value(cockpit_source: str):
    """KPI 2 conso J-1 doit venir de get_org_daily_kwh."""
    forbidden_patterns = ['"value": 6.2,', '"value": 5.0,', '"value": 5,']
    for pattern in forbidden_patterns:
        assert pattern not in cockpit_source, (
            f"Hardcode interdit '{pattern}' encore présent — KPI 2 doit utiliser get_org_daily_kwh (cf ADR-022 F.17)"
        )


def test_no_hardcoded_baseline_constant(cockpit_source: str):
    """Baseline daily MWh doit venir de get_org_baseline_daily_kwh."""
    assert "baseline_mwh = 6.5" not in cockpit_source, (
        "Hardcode baseline_mwh = 6.5 encore présent — doit utiliser get_org_baseline_daily_kwh (cf ADR-022 F.17)"
    )


def test_no_hardcoded_subscribed_kw(cockpit_source: str):
    """Puissance souscrite doit venir de get_org_subscribed_kw."""
    forbidden_patterns = ['"subscribed_kw": 1500,', '"subscribed_kw": 1500\n']
    for pattern in forbidden_patterns:
        assert pattern not in cockpit_source, (
            f"Hardcode interdit '{pattern}' — doit utiliser get_org_subscribed_kw (cf ADR-022 F.17)"
        )


def test_no_hardcoded_hc_zones_in_route(cockpit_source: str):
    """hc_zones doit venir de tariff_periods_service.get_active_hp_hc_zones."""
    # Pattern brut : "hc_zones": [{"from_h": 0... — la version hardcodée.
    forbidden_pattern = '"hc_zones": [\n            {"from_h": 0, "to_h": 7},'
    assert forbidden_pattern not in cockpit_source, (
        "Hardcode hc_zones encore présent — doit utiliser"
        " tariff_periods_service.get_active_hp_hc_zones (cf ADR-022 F.18)"
    )


def test_highlights_use_service_not_inline_dicts(cockpit_source: str):
    """_build_cockpit_jour_highlights doit appeler build_top_n_highlights."""
    assert "build_top_n_highlights" in cockpit_source, (
        "highlights builder doit déléguer à cockpit_highlights_service (cf ADR-022 F.19c)"
    )
    # Les anciens IDs hardcodés ne doivent plus être dans cockpit.py.
    # Ils peuvent vivre dans highlights_detectors.py par contre.
    forbidden_ids = [
        '"id": "hl-lyon-dt-2030"',
        '"id": "hl-toulouse-ems-connector"',
        '"id": "hl-paris-bacs-cvc"',
    ]
    for pattern in forbidden_ids:
        assert pattern not in cockpit_source, (
            f"Hardcode highlight ID '{pattern}' encore présent dans cockpit.py"
            f" — doit venir du service (cf ADR-022 F.19c)"
        )


def test_kpi_builders_use_granularity_service(cockpit_source: str):
    """KPI/Chart builders doivent importer consumption_granularity_service."""
    assert "consumption_granularity_service" in cockpit_source, (
        "cockpit.py doit consommer consumption_granularity_service pour les KPIs/charts data-driven (cf ADR-022 F.17)"
    )
    # Vérifie au moins 1 appel à chaque fonction critique.
    required_calls = [
        "get_org_daily_kwh",
        "get_org_hourly_curve_kw",
        "get_org_peak_kw",
        "get_org_subscribed_kw",
        "get_org_baseline_daily_kwh",
        "get_org_daily_range_kwh",
    ]
    for fn in required_calls:
        assert fn in cockpit_source, f"Service `{fn}` non appelé dans cockpit.py — wiring incomplet"


def test_chart_line_uses_tariff_periods_service(cockpit_source: str):
    """Chart line doit utiliser tariff_periods_service pour les zones HP/HC."""
    assert "tariff_periods_service" in cockpit_source, (
        "cockpit.py doit consommer tariff_periods_service pour les plages HP/HC (cf ADR-022 F.18)"
    )
