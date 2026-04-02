"""Tests pour power_optimization_service — décomposition pointe + simulation PS."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_optimize_returns_current_situation():
    """Le résultat contient la situation actuelle."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.power_optimization_service import optimize_subscribed_power

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = optimize_subscribed_power(db, site.id)
        assert result is not None
        if "error" not in result:
            assert "current_situation" in result
            assert result["current_situation"]["actual_peak_kw"] > 0
    finally:
        db.close()


def test_peak_decomposition_exists():
    """La décomposition de pointe est retournée."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.power_optimization_service import optimize_subscribed_power

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = optimize_subscribed_power(db, site.id)
        if "error" not in result:
            assert "peak_decomposition" in result
            assert len(result["peak_decomposition"]) > 0
            # La somme des sous-compteurs <= peak (+ résiduel)
            total = sum(d["kw"] for d in result["peak_decomposition"])
            peak = result["current_situation"]["actual_peak_kw"]
            assert total <= peak * 1.05
    finally:
        db.close()


def test_shiftable_flagged_correctly():
    """Chauffage/Clim = shiftable, IT = non shiftable."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.power_optimization_service import optimize_subscribed_power

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = optimize_subscribed_power(db, site.id)
        if "error" in result:
            return
        for d in result["peak_decomposition"]:
            if d["usage"] in ("Chauffage", "Climatisation", "CVC"):
                assert d["shiftable"] is True, f"{d['usage']} should be shiftable"
            if d["usage"] == "IT & Bureautique":
                assert d["shiftable"] is False
    finally:
        db.close()


def test_optimization_has_savings():
    """L'optimisation propose des économies."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.power_optimization_service import optimize_subscribed_power

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = optimize_subscribed_power(db, site.id)
        if "error" in result:
            return
        opt = result["optimization"]
        assert "recommended_ps_kva" in opt
        assert "net_savings_eur" in opt
        assert opt["recommended_ps_kva"] > 0
    finally:
        db.close()


def test_monthly_peak_profile():
    """Le profil mensuel contient 12 mois."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.power_optimization_service import optimize_subscribed_power

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        result = optimize_subscribed_power(db, site.id)
        if "error" in result:
            return
        assert len(result["monthly_peak_profile"]) == 12
    finally:
        db.close()


def test_turpe_power_price_lookup():
    """Les prix TURPE sont positifs pour chaque option."""
    from services.power_optimization_service import TURPE_POWER_PRICE

    for option, price in TURPE_POWER_PRICE.items():
        assert price > 0, f"{option} price should be positive"


def test_weekday_fr():
    """Conversion jour de semaine en français."""
    from services.power_optimization_service import _weekday_fr
    from datetime import datetime

    # 2025-11-03 is a Monday
    ts = datetime(2025, 11, 3, 9, 0)
    assert _weekday_fr(ts) == "lundi"
