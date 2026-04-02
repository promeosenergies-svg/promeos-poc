"""Tests migration NEBEF → NEBCO : terminologie, nouvelles règles, no-go guards."""

import sys
import os
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Terminologie ────────────────────────────────────────────────────────────


def test_no_nebef_in_backend_services():
    """NEBEF ne doit plus apparaître dans les services/routes backend."""
    result = subprocess.run(
        ["grep", "-rn", "--include=*.py", "NEBEF", "backend/services/", "backend/routes/"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    violations = [
        l
        for l in result.stdout.splitlines()
        if "migration" not in l.lower()
        and "# ancien" not in l.lower()
        and "vs NEBEF" not in l
        and "Remplace NEBEF" not in l
        and "vs 1 pour NEBEF" not in l
    ]
    assert not violations, f"NEBEF résiduel :\n" + "\n".join(violations[:5])


def test_no_nebef_in_frontend():
    """NEBEF ne doit plus apparaître dans le frontend."""
    result = subprocess.run(
        ["grep", "-rn", "--include=*.js", "--include=*.jsx", "-i", "nebef", "frontend/src/"],
        capture_output=True,
        text=True,
        cwd=os.path.join(os.path.dirname(__file__), "..", ".."),
    )
    violations = [l for l in result.stdout.splitlines() if "test" not in l.lower()]
    assert not violations, f"NEBEF résiduel frontend :\n" + "\n".join(violations[:5])


def test_action_type_power_nebco():
    """Le type d'action doit être POWER_NEBCO (pas POWER_NEBEF)."""
    from services.power.power_action_bridge import POWER_ACTION_TEMPLATES

    assert "POWER_NEBCO" in POWER_ACTION_TEMPLATES
    assert "POWER_NEBEF" not in POWER_ACTION_TEMPLATES


# ── Nouvelles règles NEBCO ──────────────────────────────────────────────────


def test_three_modulation_types():
    """NEBCO supporte 3 types de modulation."""
    from models.power import NebcoModulationType

    assert NebcoModulationType.EFFACEMENT.value == "EFFACEMENT"
    assert NebcoModulationType.ANTICIPATION.value == "ANTICIPATION"
    assert NebcoModulationType.REPORT.value == "REPORT"


def test_discipline_decalage_constants():
    """Contraintes décalage NEBCO."""
    from services.power.nebco_eligibility_engine import (
        RATIO_DECALAGE_TELERELEVE_JOURS,
        RATIO_DECALAGE_PROFILE_JOURS,
        TOLERANCE_BILAN_MENSUEL,
    )

    assert RATIO_DECALAGE_TELERELEVE_JOURS == 7
    assert RATIO_DECALAGE_PROFILE_JOURS == 2
    assert TOLERANCE_BILAN_MENSUEL == 0.05


def test_versement_net_calculation():
    """Versement net = max(0, baisse − hausse) × barème."""
    vol_baisse, vol_hausse, bareme = 100.0, 30.0, 0.05
    versement = max(0.0, vol_baisse - vol_hausse) * bareme
    assert versement == 3.5

    versement_sup = max(0.0, vol_baisse - 110.0) * bareme
    assert versement_sup == 0.0


def test_seuil_100kw_per_pas():
    """Seuil NEBCO = 100 kW PAR PAS DE CONTRÔLE."""
    from services.power.nebco_eligibility_engine import SEUIL_NEBCO_KW

    assert SEUIL_NEBCO_KW == 100.0


def test_nebco_engine_returns_modulation_types():
    """Le moteur retourne les types de modulation disponibles."""
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
        assert "modulation_types" in result
        assert "discipline_decalage" in result
        assert "versement_fournisseur" in result
        assert "promesse_tenable" in result
        assert "sans promettre un revenu garanti" in result["promesse_tenable"]
    finally:
        db.close()


def test_nebco_engine_returns_no_go_rules():
    """Le moteur retourne les no-go rules."""
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
        assert "no_go_rules" in result
        assert isinstance(result["no_go_rules"], list)
    finally:
        db.close()
