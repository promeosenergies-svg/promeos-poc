"""
PROMEOS — Sprint C-3 Phase 3.6 : Tests cascade DeliveryPoint.grd_code.

Vérifie cascade pivot Phase 3.6 (clôture D-Phase6-Cascade-DeliveryPoint-Fta-001) :
- _recompute_eld_metadata_from_grd_code : lookup ELD ref correct + None si inconnu
- _trigger_bill_recheck : log structuré "BILL_RECHECK_TRIGGERED"
- Cascade entry "DeliveryPoint.grd_code" : 2 actions chaînées
- Résilience : grd_code None / inconnu / ELD inconnue ne crash pas
"""

from __future__ import annotations

import logging
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_dp(grd_code=None, dp_id=42, site_id=1):
    """Crée un MagicMock DeliveryPoint pour tests."""
    dp = MagicMock()
    dp.id = dp_id
    dp.site_id = site_id
    dp.grd_code = grd_code
    return dp


# ─── Helper _recompute_eld_metadata_from_grd_code ───────────────────────────


def test_recompute_eld_metadata_grdf_returns_grd_national():
    from regops.services.cascade_recompute_service import _recompute_eld_metadata_from_grd_code

    dp = _make_dp(grd_code="GRDF")
    db = MagicMock()
    result = _recompute_eld_metadata_from_grd_code(dp, db)
    assert result is not None
    assert result["code"] == "GRDF"
    assert result["type"] == "GRD_NATIONAL"
    assert "GRDF" in result["label"]


def test_recompute_eld_metadata_regaz_returns_eld_locale():
    from regops.services.cascade_recompute_service import _recompute_eld_metadata_from_grd_code

    dp = _make_dp(grd_code="REGAZ")
    db = MagicMock()
    result = _recompute_eld_metadata_from_grd_code(dp, db)
    assert result is not None
    assert result["type"] == "ELD_LOCALE"


def test_recompute_eld_metadata_enedis_returns_none():
    """ENEDIS = élec, hors périmètre ELD gaz → None (pas une erreur)."""
    from regops.services.cascade_recompute_service import _recompute_eld_metadata_from_grd_code

    dp = _make_dp(grd_code="ENEDIS")
    db = MagicMock()
    result = _recompute_eld_metadata_from_grd_code(dp, db)
    assert result is None


def test_recompute_eld_metadata_grd_code_none_returns_none():
    from regops.services.cascade_recompute_service import _recompute_eld_metadata_from_grd_code

    dp = _make_dp(grd_code=None)
    db = MagicMock()
    result = _recompute_eld_metadata_from_grd_code(dp, db)
    assert result is None


# ─── Helper _trigger_bill_recheck ───────────────────────────────────────────


def test_trigger_bill_recheck_logs_structured_event(caplog):
    from regops.services.cascade_recompute_service import _trigger_bill_recheck

    dp = _make_dp(grd_code="GRDF", dp_id=123, site_id=7)
    db = MagicMock()

    with caplog.at_level(logging.INFO, logger="regops.services.cascade_recompute_service"):
        result = _trigger_bill_recheck(dp, db)

    assert result == "bill_recheck_logged for DP 123"
    assert any("BILL_RECHECK_TRIGGERED" in r.message for r in caplog.records)


def test_trigger_bill_recheck_no_db_writes():
    """Anti-cycle : log only, pas d'écriture DB."""
    from regops.services.cascade_recompute_service import _trigger_bill_recheck

    dp = _make_dp(grd_code="REGAZ")
    db = MagicMock()

    _trigger_bill_recheck(dp, db)

    # Aucune méthode DB write appelée (add, flush, commit, query)
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.flush.assert_not_called()


# ─── Cascade entry integration ──────────────────────────────────────────────


def test_cascade_entry_grd_code_chains_eld_metadata_and_bill_recheck():
    """`DeliveryPoint.grd_code` → 2 actions (eld_metadata + bill_recheck)."""
    from regops.services.cascade_recompute_service import (
        CASCADE_MAP_MVP_SPRINT_C1,
        cascade_recompute_on_change,
    )

    assert "DeliveryPoint.grd_code" in CASCADE_MAP_MVP_SPRINT_C1
    callables = CASCADE_MAP_MVP_SPRINT_C1["DeliveryPoint.grd_code"]
    assert len(callables) == 2

    dp = _make_dp(grd_code="REGAZ")
    db = MagicMock()

    result = cascade_recompute_on_change(
        db,
        dp,
        "DeliveryPoint.grd_code",
        old_value="GRDF",
        new_value="REGAZ",
        persist=False,
        org_id=999_500,
    )

    output_fields = {a.output_field for a in result.actions}
    assert "eld_metadata" in output_fields
    assert "bill_recheck" in output_fields

    # eld_metadata pour REGAZ doit retourner ELD_LOCALE
    eld_action = next(a for a in result.actions if a.output_field == "eld_metadata")
    assert eld_action.new_value is not None
    assert eld_action.new_value["type"] == "ELD_LOCALE"
