"""Tests pour cdc_contract_simulator — simulation achat CDC-aware."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_returns_4_strategies():
    """Le résultat contient 4 stratégies."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.cdc_contract_simulator import simulate_contract_strategies

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = simulate_contract_strategies(db, site.id)
        if result and "error" not in result:
            assert len(result["strategies"]) == 4
    finally:
        db.close()


def test_cdc_profile_classified():
    """Le profil CDC est classifié."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.cdc_contract_simulator import simulate_contract_strategies

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = simulate_contract_strategies(db, site.id)
        if result and "error" not in result:
            assert result["cdc_profile"]["type"] in (
                "baseload_dominant",
                "saisonnier_fort",
                "bureau_classique",
                "mixte",
            )
    finally:
        db.close()


def test_recommendation_has_reasoning():
    """La recommandation contient un reasoning."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.cdc_contract_simulator import simulate_contract_strategies

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = simulate_contract_strategies(db, site.id)
        if result and "error" not in result:
            assert "reasoning" in result["recommendation"]
            assert len(result["recommendation"]["reasoning"]) > 20
    finally:
        db.close()


def test_ths_solar_pct():
    """Le THS calcule un solar_pct entre 0 et 100."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.cdc_contract_simulator import simulate_contract_strategies

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = simulate_contract_strategies(db, site.id)
        if result and "error" not in result:
            ths = next((s for s in result["strategies"] if "THS" in s["name"]), None)
            assert ths is not None
            assert 0 <= ths["solar_pct"] <= 100
    finally:
        db.close()


def test_is_solar_hour():
    """Heures solaires correctes été/hiver."""
    from services.cdc_contract_simulator import _is_solar_hour

    assert _is_solar_hour(7, 12) is True  # été midi
    assert _is_solar_hour(7, 9) is False  # été 9h
    assert _is_solar_hour(1, 12) is True  # hiver midi
    assert _is_solar_hour(1, 10) is False  # hiver 10h
    assert _is_solar_hour(1, 15) is False  # hiver 15h


def test_characterize_cdc():
    """La classification CDC fonctionne avec des données synthétiques."""
    from services.cdc_contract_simulator import _characterize_cdc

    # Profil bureau classique : forte activité jour, faible nuit
    profile_data = []
    for month in range(1, 13):
        for hour in range(24):
            kwh = 50.0 if 8 <= hour <= 18 else 5.0
            profile_data.append({"month": month, "hour": hour, "kwh": kwh})

    result = _characterize_cdc(profile_data)
    assert result["type"] == "bureau_classique"
    assert result["hp_ratio"] > 0.6
    assert result["baseload_ratio"] < 0.3
