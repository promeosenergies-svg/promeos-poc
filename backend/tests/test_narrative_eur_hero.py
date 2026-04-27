"""Sprint 2 Vague A ét3' — Hook € hero universel.

Tests unitaires de l'helper `_promote_eur_kpi_to_hero` qui force kpis[0]
à être un montant € mémorable quand un tel chiffre est disponible parmi
les 3 KPIs hero §5.

Audit personas convergence (CFO P0 + Marie P0 + Investisseur P0 sur 4
audits 27/04/2026) : kpis[0] = chiffre rétine 3s. Rationalisé Vague B
quand label_registries.py émergera (ét8).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.narrative.narrative_generator import (
    NarrativeKpi,
    _has_meaningful_eur,
    _promote_eur_kpi_to_hero,
)


# ── _has_meaningful_eur ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "value, expected",
    [
        # Formats _fmt_eur_short produits par le générateur
        ("450 €", True),
        ("26 k€", True),
        ("1.2 M€", True),
        ("1,2 M€", True),
        # Variantes "/an" (leviers économies cockpit_comex)
        ("26 k€/an", True),
        ("450 €/an", True),
        # Cas dégradés rejetés
        ("0 €", False),
        ("0,0 k€", False),
        ("—", False),
        ("73/100", False),
        ("12 sites", False),
        ("250 kW", False),
        ("", False),
        (None, False),
        # Anti-faux-positif : valeur sans nombre devant
        ("k€", False),
    ],
)
def test_has_meaningful_eur(value, expected):
    assert _has_meaningful_eur(value) is expected


# ── _promote_eur_kpi_to_hero ────────────────────────────────────────


def _kpi(label: str, value: str) -> NarrativeKpi:
    return NarrativeKpi(label=label, value=value)


def test_promote_eur_already_hero_unchanged():
    """Quand kpis[0] est déjà un € non-zero, ordre préservé."""
    kpis = [
        _kpi("Pertes à récupérer", "26 k€"),
        _kpi("Anomalies à traiter", "12"),
        _kpi("Récupérations YTD", "8 k€"),
    ]
    result = _promote_eur_kpi_to_hero(kpis)
    assert [k.label for k in result] == [
        "Pertes à récupérer",
        "Anomalies à traiter",
        "Récupérations YTD",
    ]


def test_promote_eur_swaps_position_1_to_hero():
    """Cas Bill-Intel : Anomalies en [0], Pertes € en [1] → swap."""
    kpis = [
        _kpi("Anomalies à traiter", "12"),
        _kpi("Pertes à récupérer", "26 k€"),
        _kpi("Récupérations YTD", "8 k€"),
    ]
    result = _promote_eur_kpi_to_hero(kpis)
    assert [k.label for k in result] == [
        "Pertes à récupérer",
        "Anomalies à traiter",
        "Récupérations YTD",
    ]


def test_promote_eur_swaps_position_2_to_hero():
    """Cas Patrimoine : Surface en [0], Sites en [1], Mutualisation € en [2]."""
    kpis = [
        _kpi("Surface tertiaire", "12 000 m²"),
        _kpi("Sites en dérive", "3/8"),
        _kpi("Mutualisation 2030", "26 k€/an"),
    ]
    result = _promote_eur_kpi_to_hero(kpis)
    assert [k.label for k in result] == [
        "Mutualisation 2030",
        "Surface tertiaire",
        "Sites en dérive",
    ]


def test_promote_eur_no_eur_unchanged():
    """Cas Flex : aucun KPI €, ordre préservé (Potentiel kW reste hero)."""
    kpis = [
        _kpi("Potentiel pilotable", "250 kW"),
        _kpi("Score Flex moyen", "65/100"),
        _kpi("Énergie annuelle", "320 MWh"),
    ]
    result = _promote_eur_kpi_to_hero(kpis)
    assert [k.label for k in result] == [
        "Potentiel pilotable",
        "Score Flex moyen",
        "Énergie annuelle",
    ]


def test_promote_eur_zero_eur_treated_as_no_eur():
    """`0 €` ne doit PAS être promu en hero (anti-pattern CFO)."""
    kpis = [
        _kpi("Anomalies à traiter", "5"),
        _kpi("Pertes à récupérer", "0 €"),
        _kpi("Récupérations YTD", "0 €"),
    ]
    result = _promote_eur_kpi_to_hero(kpis)
    assert [k.label for k in result] == [
        "Anomalies à traiter",
        "Pertes à récupérer",
        "Récupérations YTD",
    ]


def test_promote_eur_em_dash_treated_as_no_eur():
    """`—` (donnée indisponible) ne doit pas être promu."""
    kpis = [
        _kpi("Score conformité", "73/100"),
        _kpi("Risque financier", "—"),
        _kpi("Exposition", "12 k€"),
    ]
    result = _promote_eur_kpi_to_hero(kpis)
    assert [k.label for k in result] == [
        "Exposition",
        "Score conformité",
        "Risque financier",
    ]


def test_promote_eur_empty_list_returns_empty():
    assert _promote_eur_kpi_to_hero([]) == []


def test_promote_eur_returns_new_list_does_not_mutate_input():
    """Pureté : input intouché, output nouvelle liste."""
    original = [
        _kpi("Anomalies", "12"),
        _kpi("Pertes", "26 k€"),
    ]
    snapshot = list(original)
    _promote_eur_kpi_to_hero(original)
    assert original == snapshot


def test_promote_eur_picks_first_eur_when_multiple_candidates():
    """Si plusieurs KPIs €, on promeut le premier rencontré (préserve
    l'intention éditoriale : kpis[1] est plus important que kpis[2])."""
    kpis = [
        _kpi("Anomalies", "12"),
        _kpi("Pertes à récupérer", "26 k€"),
        _kpi("Récupérations YTD", "8 k€"),
    ]
    result = _promote_eur_kpi_to_hero(kpis)
    assert result[0].label == "Pertes à récupérer"
    assert result[1].label == "Anomalies"
    assert result[2].label == "Récupérations YTD"
