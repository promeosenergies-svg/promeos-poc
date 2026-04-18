"""Tests SolContext builder Phase 2.5."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from models.sol import SolActionLog, SolOrgPolicy
from sol.context import _load_last_3_actions, _load_or_default_policy
from sol.schemas import AgenticMode


# ─────────────────────────────────────────────────────────────────────────────
# _load_or_default_policy
# ─────────────────────────────────────────────────────────────────────────────


def test_load_default_policy_when_none(sol_db, sol_org):
    policy_dict = _load_or_default_policy(sol_db, sol_org.id)

    assert policy_dict["agentic_mode"] == AgenticMode.PREVIEW_ONLY.value
    assert policy_dict["confidence_threshold"] == 0.85
    assert policy_dict["grace_period_seconds"] == 900
    assert policy_dict["tone_preference"] == "vous"
    assert policy_dict["dry_run_until"] is None


def test_load_existing_policy(sol_db, sol_org):
    policy = SolOrgPolicy(
        org_id=sol_org.id,
        agentic_mode="full_agentic",
        confidence_threshold=0.95,
        grace_period_seconds=1800,
        tone_preference="vous",
    )
    sol_db.add(policy)
    sol_db.commit()

    loaded = _load_or_default_policy(sol_db, sol_org.id)
    assert loaded["agentic_mode"] == "full_agentic"
    assert loaded["confidence_threshold"] == 0.95
    assert loaded["grace_period_seconds"] == 1800


# ─────────────────────────────────────────────────────────────────────────────
# _load_last_3_actions
# ─────────────────────────────────────────────────────────────────────────────


def test_load_last_3_actions_empty(sol_db, sol_org):
    actions = _load_last_3_actions(sol_db, sol_org.id)
    assert actions == []


def test_load_last_3_actions_limited(sol_db, sol_org, sol_user, sol_action_log_factory):
    # Créer 5 actions
    for i in range(5):
        sol_action_log_factory(correlation_id=f"corr-ctx-{i}", outcome_code=f"out-{i}")

    actions = _load_last_3_actions(sol_db, sol_org.id)
    assert len(actions) == 3
    # Ordre descending par created_at — donc dernier créé en premier
    # (les created_at peuvent être identiques en SQLite résolution seconde,
    # on vérifie juste la structure)
    for a in actions:
        assert "correlation_id" in a
        assert "intent_kind" in a
        assert "action_phase" in a


def test_load_last_3_actions_scoped_to_org(sol_db, sol_org, sol_user, sol_action_log_factory):
    sol_action_log_factory(correlation_id="corr-own-1")
    sol_action_log_factory(correlation_id="corr-own-2")

    # Créer une org "étrangère" et une action dedans
    from models.organisation import Organisation
    other_org = Organisation(nom="Other Org", actif=True)
    sol_db.add(other_org)
    sol_db.commit()

    foreign_log = SolActionLog(
        org_id=other_org.id,
        user_id=sol_user.id,
        correlation_id="corr-foreign-1",
        intent_kind="invoice_dispute",
        action_phase="proposed",
        inputs_hash="f" * 64,
        plan_json={},
    )
    sol_db.add(foreign_log)
    sol_db.commit()

    # _load_last_3_actions(org_id=sol_org.id) ne doit PAS retourner l'action étrangère
    actions = _load_last_3_actions(sol_db, sol_org.id)
    correlation_ids = {a["correlation_id"] for a in actions}
    assert "corr-foreign-1" not in correlation_ids
    assert "corr-own-1" in correlation_ids or "corr-own-2" in correlation_ids
