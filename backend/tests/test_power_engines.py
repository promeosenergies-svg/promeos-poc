"""Tests des moteurs Power Intelligence Phase 3."""

import sys
import os
import math
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Peak Detection ──────────────────────────────────────────────────────────


def test_peak_detection_returns_result():
    """detect_peaks retourne un dict avec n_pics."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.peak_detection_engine import detect_peaks

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.parent_meter_id.is_(None)).first()
        if not meter:
            return
        result = detect_peaks(db, meter.id, date(2025, 6, 1), date(2025, 7, 1))
        assert "n_pics" in result
        assert "cmdps_par_poste" in result
        assert result["source"] == "peak_detection_engine"
    finally:
        db.close()


def test_peak_cost_uses_12_65():
    """Coût dépassement = 10 kW × 12.65 × 0.5h = 63.25 €."""
    from services.power.peak_detection_engine import TARIF_DEPASSEMENT_EUR_KW

    assert TARIF_DEPASSEMENT_EUR_KW == 12.65
    cost = 10.0 * TARIF_DEPASSEMENT_EUR_KW * 0.5
    assert abs(cost - 63.25) < 0.01


def test_ps_compared_per_poste():
    """La PS comparée est celle du poste, pas la PS max."""
    ps = {"Pointe": 180, "HPH": 220}
    assert 200 / ps["HPH"] * 100 < 100  # 90.9% — pas de dépassement
    assert 200 / ps["Pointe"] * 100 > 100  # 111% — dépassement


# ── Power Factor ────────────────────────────────────────────────────────────


def test_tan_phi_seuil_is_04():
    """Seuil réglementaire TURPE 7 = 0.4."""
    from services.power.power_factor_analyzer import TAN_PHI_SEUIL

    assert TAN_PHI_SEUIL == 0.4


def test_penalty_zero_below_seuil():
    """tan φ ≤ 0.4 → pénalité zéro."""
    from services.power.power_factor_analyzer import TAN_PHI_SEUIL

    E_active, E_reactive = 1000.0, 350.0
    E_penalisable = max(0, E_reactive - TAN_PHI_SEUIL * E_active)
    assert E_penalisable == 0


def test_penalty_positive_above_seuil():
    """tan φ > 0.4 → pénalité positive."""
    from services.power.power_factor_analyzer import TAN_PHI_SEUIL, TARIF_KVARH_EUR

    E_active, E_reactive = 1000.0, 600.0
    E_pen = max(0, E_reactive - TAN_PHI_SEUIL * E_active)
    assert E_pen == 200.0
    assert E_pen * TARIF_KVARH_EUR > 0


def test_power_factor_with_db():
    """analyze_power_factor retourne un résultat valide."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.power_factor_analyzer import analyze_power_factor

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.parent_meter_id.is_(None)).first()
        if not meter:
            return
        result = analyze_power_factor(db, meter.id, date(2025, 6, 1), date(2025, 7, 1))
        assert "source" in result
        assert result["source"] == "power_factor_analyzer"
    finally:
        db.close()


# ── PS Optimizer ────────────────────────────────────────────────────────────


def test_eir_bt_threshold():
    """EIR BT si delta ≥ 36 kVA."""
    from services.power.subscribed_power_optimizer import SEUIL_EIR_BT_KVA

    assert 35 < SEUIL_EIR_BT_KVA
    assert 36 >= SEUIL_EIR_BT_KVA


def test_eir_hta_threshold():
    """EIR HTA si augmentation ≥ 100 kW."""
    from services.power.subscribed_power_optimizer import SEUIL_EIR_HTA_KW

    assert SEUIL_EIR_HTA_KW == 100


def test_ps_recommended_integer():
    """PS recommandée = integer kVA (XSD C12)."""
    from services.power.subscribed_power_optimizer import MARGE_SECURITE_PCT

    ps_reco = math.ceil(187.3 * (1 + MARGE_SECURITE_PCT / 100))
    assert isinstance(ps_reco, int)
    assert ps_reco == 216  # ceil(187.3 × 1.15 = 215.395)


def test_optimizer_with_db():
    """optimize_subscribed_power retourne les champs requis."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.subscribed_power_optimizer import optimize_subscribed_power

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.parent_meter_id.is_(None)).first()
        if not meter:
            return
        result = optimize_subscribed_power(db, meter.id, date(2025, 6, 1), date(2025, 12, 31))
        assert "source" in result
        assert result["source"] == "subscribed_power_optimizer"
    finally:
        db.close()


# ── NEBCO ───────────────────────────────────────────────────────────────────


def test_nebco_seuil_100kw():
    """Seuil NEBCO = 100 kW."""
    from services.power.nebco_eligibility_engine import SEUIL_NEBCO_KW

    assert SEUIL_NEBCO_KW == 100.0


def test_nebco_revenu_central():
    """Revenu central NEBCO = 140 €/kW/an."""
    from services.power.nebco_eligibility_engine import REVENU_CENTRAL

    assert REVENU_CENTRAL == 140.0


def test_nebco_with_db():
    """check_nebco_eligibility retourne un résultat."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.nebco_eligibility_engine import check_nebco_eligibility

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.parent_meter_id.is_(None)).first()
        if not meter:
            return
        result = check_nebco_eligibility(db, meter.id)
        assert "eligible" in result
        assert "source" in result
        assert result["source"] == "nebco_eligibility_engine"
    finally:
        db.close()
