"""
test_kb_dedup.py — Tests déduplication recos KB.
"""

import pytest

from routes.site_intelligence import _deduplicate_recommendations


def test_dedup_merges_same_code():
    """Recos avec même code sont fusionnées, savings agrégés, max ICE."""
    recos = [
        {
            "recommendation_code": "RECO-LED",
            "title": "Passage LED",
            "estimated_savings_eur_year": 1000,
            "ice_score": 0.65,
        },
        {
            "recommendation_code": "RECO-LED",
            "title": "Passage LED",
            "estimated_savings_eur_year": 800,
            "ice_score": 0.60,
        },
        {
            "recommendation_code": "RECO-LED",
            "title": "Passage LED",
            "estimated_savings_eur_year": 1200,
            "ice_score": 0.65,
        },
    ]
    result = _deduplicate_recommendations(recos)
    assert len(result) == 1
    assert result[0]["estimated_savings_eur_year"] == 3000
    assert result[0]["count"] == 3
    assert result[0]["ice_score"] == 0.65


def test_dedup_keeps_distinct_codes():
    """Recos avec codes différents restent distinctes."""
    recos = [
        {"recommendation_code": "RECO-LED", "title": "Passage LED", "ice_score": 0.65},
        {"recommendation_code": "RECO-BACS", "title": "Conformité BACS", "ice_score": 0.82},
    ]
    result = _deduplicate_recommendations(recos)
    assert len(result) == 2


def test_dedup_sorted_by_ice_desc():
    """Résultat trié par ICE décroissant."""
    recos = [
        {"recommendation_code": "A", "ice_score": 0.3},
        {"recommendation_code": "B", "ice_score": 0.9},
        {"recommendation_code": "C", "ice_score": 0.5},
    ]
    result = _deduplicate_recommendations(recos)
    scores = [r["ice_score"] for r in result]
    assert scores == [0.9, 0.5, 0.3]


def test_dedup_empty_list():
    """Liste vide → liste vide."""
    assert _deduplicate_recommendations([]) == []


def test_dedup_no_code_uses_title():
    """Si pas de recommendation_code, utilise le title comme clé."""
    recos = [
        {"title": "Test reco", "estimated_savings_eur_year": 100},
        {"title": "Test reco", "estimated_savings_eur_year": 200},
    ]
    result = _deduplicate_recommendations(recos)
    assert len(result) == 1
    assert result[0]["estimated_savings_eur_year"] == 300


def test_dedup_aggregates_kwh():
    """Les savings kWh sont aussi agrégés."""
    recos = [
        {"recommendation_code": "A", "estimated_savings_kwh_year": 5000, "ice_score": 0.5},
        {"recommendation_code": "A", "estimated_savings_kwh_year": 3000, "ice_score": 0.4},
    ]
    result = _deduplicate_recommendations(recos)
    assert result[0]["estimated_savings_kwh_year"] == 8000
    assert result[0]["ice_score"] == 0.5  # max conservé
