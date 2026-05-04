"""
PROMEOS — Sprint C-2 Phase 5.3 : Tests cascade EnergyContract.end_date → alerte 90j MVP.

Vérifie :
- Helper _trigger_renewal_alert : fenêtre 90j + idempotence cooldown 30j
- Helper _reset_renewal_alert_flag : reset à None
- Cascade entry "EnergyContract.end_date" : ordre reset AVANT trigger
- Edge cases : end_date None / déjà expiré / hors fenêtre / extension contrat
- Pas de fuite log spam (idempotence)

Cas B MVP (modèle Alert absent) : log structuré + flag.
Modèle Alert dédié reporté Sprint C-5 — D-Phase6-Cascade-Contract-Renewal-001 clôturé MVP.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Helper _trigger_renewal_alert ──────────────────────────────────────────


def _make_contract(end_date=None, last_logged=None, contract_id=42, supplier="EDF", site_id=1):
    """Crée un MagicMock EnergyContract pour tests unit."""
    c = MagicMock()
    c.id = contract_id
    c.site_id = site_id
    c.supplier_name = supplier
    c.end_date = end_date
    c.alerte_renouvellement_logged_at = last_logged
    return c


def test_trigger_renewal_alert_60_days_to_expiry_logs_and_sets_flag(caplog):
    """end_date dans 60j → alerte loguée + flag set."""
    from regops.services.cascade_recompute_service import _trigger_renewal_alert

    contract = _make_contract(end_date=date.today() + timedelta(days=60))
    db = MagicMock()

    before = datetime.utcnow()
    with caplog.at_level(logging.INFO, logger="regops.services.cascade_recompute_service"):
        result = _trigger_renewal_alert(contract, db)

    assert result is not None
    assert "renewal_alert_logged" in result
    assert "60d to expiry" in result
    # Flag mis à jour
    assert contract.alerte_renouvellement_logged_at is not None
    assert contract.alerte_renouvellement_logged_at >= before
    # Log structuré "RENEWAL_ALERT_90D"
    assert any("RENEWAL_ALERT_90D" in r.message for r in caplog.records)


def test_trigger_renewal_alert_120_days_no_alert():
    """end_date dans 120j → hors fenêtre 90j, return None, flag inchangé."""
    from regops.services.cascade_recompute_service import _trigger_renewal_alert

    contract = _make_contract(end_date=date.today() + timedelta(days=120))
    db = MagicMock()

    result = _trigger_renewal_alert(contract, db)
    assert result is None
    assert contract.alerte_renouvellement_logged_at is None  # pas de set


def test_trigger_renewal_alert_already_expired_no_alert():
    """end_date dans le passé → days_to_expiry < 0, return None."""
    from regops.services.cascade_recompute_service import _trigger_renewal_alert

    contract = _make_contract(end_date=date.today() - timedelta(days=10))
    db = MagicMock()

    result = _trigger_renewal_alert(contract, db)
    assert result is None
    assert contract.alerte_renouvellement_logged_at is None


def test_trigger_renewal_alert_no_end_date_no_alert():
    """end_date None → return None."""
    from regops.services.cascade_recompute_service import _trigger_renewal_alert

    contract = _make_contract(end_date=None)
    db = MagicMock()

    result = _trigger_renewal_alert(contract, db)
    assert result is None


def test_trigger_renewal_alert_idempotence_skips_recent_log():
    """Log <30j → skip nouveau log (idempotence anti-spam)."""
    from regops.services.cascade_recompute_service import _trigger_renewal_alert

    recent_log = datetime.utcnow() - timedelta(days=10)
    contract = _make_contract(
        end_date=date.today() + timedelta(days=60),
        last_logged=recent_log,
    )
    db = MagicMock()

    result = _trigger_renewal_alert(contract, db)
    assert result is not None
    assert "alert_already_logged" in result
    assert "10d ago" in result
    # Flag NON modifié (preserve original timestamp)
    assert contract.alerte_renouvellement_logged_at == recent_log


def test_trigger_renewal_alert_replay_after_30_day_cooldown():
    """Log >30j → re-log autorisé (cooldown expiré)."""
    from regops.services.cascade_recompute_service import _trigger_renewal_alert

    old_log = datetime.utcnow() - timedelta(days=45)
    contract = _make_contract(
        end_date=date.today() + timedelta(days=60),
        last_logged=old_log,
    )
    db = MagicMock()

    result = _trigger_renewal_alert(contract, db)
    assert result is not None
    assert "renewal_alert_logged" in result
    # Flag mis à jour avec nouvelle valeur
    assert contract.alerte_renouvellement_logged_at > old_log


# ─── Helper _reset_renewal_alert_flag ───────────────────────────────────────


def test_reset_renewal_alert_flag_clears_timestamp():
    """_reset_renewal_alert_flag → alerte_renouvellement_logged_at = None."""
    from regops.services.cascade_recompute_service import _reset_renewal_alert_flag

    contract = _make_contract(last_logged=datetime.utcnow())
    db = MagicMock()

    result = _reset_renewal_alert_flag(contract, db)
    assert result == "flag_reset"
    assert contract.alerte_renouvellement_logged_at is None


# ─── Cascade entry integration ──────────────────────────────────────────────


def test_cascade_entry_end_date_chains_reset_then_trigger():
    """Cascade EnergyContract.end_date → 2 actions ordonnées (reset puis trigger)."""
    from regops.services.cascade_recompute_service import (
        CASCADE_MAP_MVP_SPRINT_C1,
        cascade_recompute_on_change,
    )

    assert "EnergyContract.end_date" in CASCADE_MAP_MVP_SPRINT_C1
    callables = CASCADE_MAP_MVP_SPRINT_C1["EnergyContract.end_date"]
    assert len(callables) == 2

    contract = _make_contract(
        end_date=date.today() + timedelta(days=45),
        last_logged=datetime.utcnow() - timedelta(days=5),  # serait skipped sans reset
    )
    db = MagicMock()

    result = cascade_recompute_on_change(
        db,
        contract,
        "EnergyContract.end_date",
        old_value=date.today() + timedelta(days=200),
        new_value=date.today() + timedelta(days=45),
        persist=False,
        org_id=999_400,
    )

    output_fields = [a.output_field for a in result.actions]
    # Ordre critique : reset d'abord, puis trigger
    assert output_fields[0] == "alerte_renouvellement_logged_at_reset"
    assert output_fields[1] == "renewal_alert"
    # Le reset a permis le trigger immédiat malgré le log récent (5d)
    assert "renewal_alert_logged" in (result.actions[1].new_value or "")
    assert contract.alerte_renouvellement_logged_at is not None


def test_cascade_end_date_extended_outside_window_no_alert():
    """Old end_date 60d → new end_date 200d (prolongation) → reset + skip (hors fenêtre)."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    contract = _make_contract(
        end_date=date.today() + timedelta(days=200),
        last_logged=datetime.utcnow() - timedelta(days=10),  # log précédent à éliminer
    )
    db = MagicMock()

    result = cascade_recompute_on_change(
        db,
        contract,
        "EnergyContract.end_date",
        old_value=date.today() + timedelta(days=60),
        new_value=date.today() + timedelta(days=200),
        persist=False,
        org_id=999_401,
    )

    # Reset OK
    assert contract.alerte_renouvellement_logged_at is None
    # Trigger return None (hors fenêtre 200d > 90d)
    trigger_action = next(a for a in result.actions if a.output_field == "renewal_alert")
    assert trigger_action.new_value is None


def test_cascade_end_date_shortened_inside_window_immediate_alert():
    """Old end_date 200d → new end_date 30d (raccourcissement) → reset + log immédiat."""
    from regops.services.cascade_recompute_service import cascade_recompute_on_change

    contract = _make_contract(
        end_date=date.today() + timedelta(days=30),
        last_logged=datetime.utcnow() - timedelta(days=2),  # idempotence aurait skip
    )
    db = MagicMock()

    result = cascade_recompute_on_change(
        db,
        contract,
        "EnergyContract.end_date",
        old_value=date.today() + timedelta(days=200),
        new_value=date.today() + timedelta(days=30),
        persist=False,
        org_id=999_402,
    )

    # Reset a permis le trigger immédiat (sans cooldown skip)
    assert contract.alerte_renouvellement_logged_at is not None
    trigger_action = next(a for a in result.actions if a.output_field == "renewal_alert")
    assert trigger_action.new_value is not None
    assert "renewal_alert_logged" in trigger_action.new_value
    assert "30d to expiry" in trigger_action.new_value
