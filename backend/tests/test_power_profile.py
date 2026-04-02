"""Tests pour power_profile_service — KPIs puissance CDC."""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_power_profile_returns_kpis():
    """Le profil puissance retourne P_max, P_mean, P_base, facteur de forme."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.power_profile_service import get_power_profile

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = (
            db.query(Meter)
            .filter(
                Meter.site_id == site.id,
                Meter.parent_meter_id.is_(None),
            )
            .first()
        )
        if not meter:
            return

        result = get_power_profile(db, meter.id, date(2025, 6, 1), date(2025, 7, 1))
        if result["data_available"]:
            kpis = result["kpis"]
            assert kpis["P_max_kw"] > 0
            assert kpis["P_mean_kw"] > 0
            assert kpis["P_base_kw"] >= 0
            assert kpis["P_base_kw"] <= kpis["P_mean_kw"]
            assert kpis["facteur_forme"] > 0
            assert kpis["facteur_forme"] <= 1.0
    finally:
        db.close()


def test_power_profile_has_contract():
    """Le profil puissance inclut le contrat PowerContract."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.power_profile_service import get_power_profile

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = (
            db.query(Meter)
            .filter(
                Meter.site_id == site.id,
                Meter.parent_meter_id.is_(None),
            )
            .first()
        )
        if not meter:
            return

        result = get_power_profile(db, meter.id, date(2025, 6, 1), date(2025, 7, 1))
        if result["data_available"] and result.get("contract"):
            c = result["contract"]
            assert "fta_code" in c
            assert "ps_par_poste_kva" in c
            assert isinstance(c["ps_par_poste_kva"], dict)
    finally:
        db.close()


def test_power_profile_empty_period():
    """Période sans données retourne data_available=False."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.power_profile_service import get_power_profile

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = (
            db.query(Meter)
            .filter(
                Meter.site_id == site.id,
                Meter.parent_meter_id.is_(None),
            )
            .first()
        )
        if not meter:
            return

        result = get_power_profile(db, meter.id, date(2020, 1, 1), date(2020, 2, 1))
        assert result["data_available"] is False
    finally:
        db.close()


def test_power_profile_tan_phi():
    """Le tan φ est calculé si données réactives disponibles."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.power_profile_service import get_power_profile

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = (
            db.query(Meter)
            .filter(
                Meter.site_id == site.id,
                Meter.parent_meter_id.is_(None),
            )
            .first()
        )
        if not meter:
            return

        result = get_power_profile(db, meter.id, date(2025, 6, 1), date(2025, 7, 1))
        if result["data_available"]:
            tan_phi = result["kpis"]["tan_phi_mean"]
            if tan_phi is not None:
                assert 0 < tan_phi < 1  # tan φ réaliste bureau
    finally:
        db.close()


def test_fta_segments_complete():
    """Le référentiel FTA contient 17 formules tarifaires."""
    from models.power import FTA_SEGMENTS

    assert len(FTA_SEGMENTS) == 17
    assert "HTACU5" in FTA_SEGMENTS
    assert "BTSUPCU4" in FTA_SEGMENTS
    assert "HTAST5" in FTA_SEGMENTS  # nouveau Stockeur TURPE 7
    assert "BTINFMUDT" in FTA_SEGMENTS
    for code, fta in FTA_SEGMENTS.items():
        assert "postes" in fta
        assert len(fta["postes"]) > 0


def test_compteur_sets():
    """Les sets de types de compteurs sont cohérents."""
    from models.power import COMPTEURS_CDC, COMPTEURS_PA_KVA, COMPTEURS_PA_KW, COMPTEURS_DEPASSEMENT_DQ

    assert "Linky" in COMPTEURS_CDC
    assert "ICE" in COMPTEURS_PA_KW
    assert "CJE" in COMPTEURS_PA_KVA
    assert "SAPHIR" in COMPTEURS_DEPASSEMENT_DQ
    # PA_KVA et PA_KW ne doivent pas se chevaucher
    assert not (COMPTEURS_PA_KVA & COMPTEURS_PA_KW)
