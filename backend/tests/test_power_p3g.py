"""Tests Phase 3g — portfolio NEBEF, revenu paramétrable, action bridge."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_nebef_tarif_parametrable():
    """Le tarif NEBEF est paramétrable et change le résultat."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.nebef_eligibility_engine import check_nebef_eligibility

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.parent_meter_id.is_(None)).first()
        if not meter:
            return
        r1 = check_nebef_eligibility(db, meter.id, tarif_central=80.0)
        r2 = check_nebef_eligibility(db, meter.id, tarif_central=200.0)
        if r1.get("potentiel") and r2.get("potentiel"):
            assert r1["potentiel"]["revenu_central_eur_an"] < r2["potentiel"]["revenu_central_eur_an"]
    finally:
        db.close()


def test_nebef_has_justification():
    """Chaque résultat NEBEF a une justification textuelle."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.nebef_eligibility_engine import check_nebef_eligibility

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.parent_meter_id.is_(None)).first()
        if not meter:
            return
        result = check_nebef_eligibility(db, meter.id)
        assert "justification" in result
        assert len(result["justification"]) > 10
    finally:
        db.close()


def test_nebef_has_calcul_formule():
    """Le potentiel NEBEF inclut la formule de calcul."""
    from database.connection import SessionLocal
    from models.energy_models import Meter
    from models.site import Site
    from services.power.nebef_eligibility_engine import check_nebef_eligibility

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return
        meter = db.query(Meter).filter(Meter.site_id == site.id, Meter.parent_meter_id.is_(None)).first()
        if not meter:
            return
        result = check_nebef_eligibility(db, meter.id)
        if result.get("potentiel"):
            assert "calcul" in result["potentiel"]
            assert "formule" in result["potentiel"]["calcul"]
    finally:
        db.close()


def test_action_bridge_nebef_not_eligible():
    """Pas d'action NEBEF si site non éligible technique."""
    from services.power.power_action_bridge import create_nebef_action

    result = create_nebef_action(None, 99, "Test", {"eligible_technique": False})
    assert result["status"] == "not_eligible"


def test_action_bridge_tan_phi_compliant():
    """Pas d'action tan φ si conforme."""
    from services.power.power_action_bridge import create_tan_phi_action

    result = create_tan_phi_action(None, 1, "Paris", {"kpis": {"au_dessus_seuil": False}})
    assert result["status"] == "compliant"


def test_action_bridge_peak_few_peaks():
    """Pas d'action si < 3 pics."""
    from services.power.power_action_bridge import create_peak_alert_action

    result = create_peak_alert_action(None, 1, "Paris", {"n_pics": 2})
    assert result["status"] == "no_action_needed"


def test_action_bridge_ps_no_reduction():
    """Pas d'action PS si pas de réduction recommandée."""
    from services.power.power_action_bridge import create_ps_optim_action

    result = create_ps_optim_action(
        None,
        1,
        "Paris",
        {
            "recommandations_par_poste": [{"action": "OPTIMAL", "ps_actuelle_kva": 250, "ps_recommandee_kva": 240}],
        },
    )
    assert result["status"] == "no_action_needed"


def test_action_templates_complete():
    """Les 4 types d'action sont définis."""
    from services.power.power_action_bridge import POWER_ACTION_TEMPLATES

    assert len(POWER_ACTION_TEMPLATES) == 4
    for key in ("POWER_PS_OPTIM", "POWER_TAN_PHI", "POWER_NEBEF", "POWER_PEAK_ALERT"):
        assert key in POWER_ACTION_TEMPLATES
        assert "title" in POWER_ACTION_TEMPLATES[key]
        assert "rationale" in POWER_ACTION_TEMPLATES[key]
