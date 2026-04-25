"""Tests for alert_action_mapper (Gap #5 CX V2)."""

from services.alert_action_mapper import (
    get_suggested_action,
    is_alert_actionable,
    ALERT_TO_TEMPLATE_MAP,
)


def test_all_12_tier1_alerts_mapped():
    """Les 12 alertes Tier-1 du PowerEngine/DataQualityEngine doivent être mappées."""
    tier1_alerts = [
        "BASE_NUIT_ELEVEE",
        "WEEKEND_ANORMAL",
        "DERIVE_TALON",
        "PIC_ANORMAL",
        "P95_HAUSSE",
        "DEPASSEMENT_PUISSANCE",
        "RUPTURE_PROFIL",
        "HORS_HORAIRES",
        "COURBE_PLATE",
        "DONNEES_MANQUANTES",
        "DOUBLONS_DST",
        "VALEURS_NEGATIVES",
    ]
    for alert_type in tier1_alerts:
        assert alert_type in ALERT_TO_TEMPLATE_MAP, f"{alert_type} non mappé"
        assert is_alert_actionable(alert_type)


def test_get_suggested_action_with_savings():
    result = get_suggested_action("BASE_NUIT_ELEVEE", {"estimated_savings_eur": 5000})
    assert result["template_key"] == "programmation-horaire"
    assert result["category"] == "optimisation"
    assert result["estimated_impact_eur"] == 5000


def test_get_suggested_action_with_penalty():
    result = get_suggested_action("DEPASSEMENT_PUISSANCE", {"estimated_penalty_eur": 12000})
    assert result["template_key"] == "optimisation-puissance"
    assert result["estimated_impact_eur"] == 12000


def test_get_suggested_action_data_quality_no_impact():
    """Les alertes data_quality n'ont pas d'impact EUR estimé."""
    result = get_suggested_action("DONNEES_MANQUANTES", {"estimated_savings_eur": 999})
    assert result["template_key"] == "import-donnees-manquantes"
    assert result["estimated_impact_eur"] is None


def test_unknown_alert_returns_none():
    assert get_suggested_action("UNKNOWN_ALERT_XYZ") is None
    assert is_alert_actionable("UNKNOWN_ALERT_XYZ") is False


def test_compliance_alerts_mapped():
    assert is_alert_actionable("DT_A_RISQUE")
    assert is_alert_actionable("BACS_MISSING")
    assert is_alert_actionable("CONTRACT_EXPIRY")
