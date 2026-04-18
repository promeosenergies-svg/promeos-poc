"""
Tests append-only event listeners pour Sol V1.

Vérifie que :
- UPDATE SolActionLog sur fields métier → AppendOnlyViolation (parametrize 5 fields)
- UPDATE SolActionLog anonymized=True + anonymized_at → autorisé (RGPD)
- UPDATE SolActionLog anonymized=True seul (sans anonymized_at) → rejeté (cohérence)
- UPDATE SolActionLog mix anonymize + autre field → rejeté
- UPDATE idempotent (no-op, aucun field changé) → autorisé
- DELETE SolActionLog → AppendOnlyViolation (P1-B audit fix)
- UPDATE SolPendingAction fields immuables → AppendOnlyViolation (P0-A audit fix)
- UPDATE SolPendingAction transitions d'état légitimes → autorisé
- Raw SQL contourne le listener → documenté comme limitation connue

Voir models/sol.py → _block_sol_action_log_update / _block_sol_action_log_delete
                    / _block_sol_pending_action_update.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from models.sol import AppendOnlyViolation, SolActionLog, SolPendingAction


# ─────────────────────────────────────────────────────────────────────────────
# SolActionLog — UPDATE restrictions
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "field,new_value",
    [
        ("outcome_code", "tampered_after_fact"),
        ("plan_json", {"total_eur": 9999.99}),
        ("confidence", 0.50),
        ("outcome_message", "post hoc edit"),
        ("state_after", {"fake": "state"}),
    ],
)
def test_update_forbidden_fields_raises(sol_db, sol_action_log_factory, field, new_value):
    """Modifier n'importe quel field métier après insert lève AppendOnlyViolation."""
    log = sol_action_log_factory(outcome_code="success")

    setattr(log, field, new_value)
    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert field in str(exc.value)
    sol_db.rollback()


def test_update_noop_idempotent_allowed(sol_db, sol_action_log_factory):
    """UPDATE sans aucun field changé (session.commit() multiple) → autorisé."""
    log = sol_action_log_factory()
    # Premier commit déjà fait dans factory. Ré-commiter sans change = no-op.
    sol_db.commit()
    sol_db.commit()
    # Doit pas lever
    assert log.id is not None


def test_anonymization_both_fields_allowed(sol_db, sol_action_log_factory):
    """RGPD : anonymized=True + anonymized_at dans la même transaction → OK."""
    log = sol_action_log_factory(outcome_code="success")

    log.anonymized = True
    log.anonymized_at = datetime.now(timezone.utc)
    sol_db.commit()  # ne doit pas lever

    sol_db.refresh(log)
    assert log.anonymized is True
    assert log.anonymized_at is not None
    # Les autres fields sont inchangés
    assert log.outcome_code == "success"


def test_anonymized_true_without_anonymized_at_rejected(sol_db, sol_action_log_factory):
    """Cohérence : anonymized=True sans anonymized_at set → AppendOnlyViolation."""
    log = sol_action_log_factory()

    log.anonymized = True  # anonymized_at reste None
    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert "inconsistent" in str(exc.value).lower() or "anonymized_at" in str(exc.value)
    sol_db.rollback()


def test_anonymization_alongside_metier_field_rejected(sol_db, sol_action_log_factory):
    """Anonymiser + modifier un autre field dans la même tx → rejeté."""
    log = sol_action_log_factory(outcome_code="success")

    log.anonymized = True
    log.anonymized_at = datetime.now(timezone.utc)
    log.outcome_code = "tampered"

    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert "outcome_code" in str(exc.value)
    sol_db.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# SolActionLog — DELETE forbidden (P1-B audit fix)
# ─────────────────────────────────────────────────────────────────────────────


def test_delete_sol_action_log_raises(sol_db, sol_action_log_factory):
    """DELETE physique sur sol_action_log lève AppendOnlyViolation.
    Politique RGPD : anonymisation via le job cron, pas DELETE."""
    log = sol_action_log_factory()

    sol_db.delete(log)
    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert "DELETE" in str(exc.value).upper() or "delete" in str(exc.value).lower()
    sol_db.rollback()


def test_insert_after_insert_allowed(sol_db, sol_org, sol_user):
    """Plusieurs INSERT successifs sur la même table autorisés."""
    for i, phase in enumerate(("proposed", "previewed", "confirmed")):
        log = SolActionLog(
            org_id=sol_org.id,
            user_id=sol_user.id,
            correlation_id=f"corr-insert-{i}",
            intent_kind="invoice_dispute",
            action_phase=phase,
            inputs_hash="f" * 64,
            plan_json={"phase": phase},
        )
        sol_db.add(log)
    sol_db.commit()

    total = sol_db.query(SolActionLog).count()
    assert total == 3


# ─────────────────────────────────────────────────────────────────────────────
# SolPendingAction — immutable fields (P0-A audit fix)
# ─────────────────────────────────────────────────────────────────────────────


def _make_pending(sol_db, sol_org, sol_user, correlation_id="pa-corr-1") -> SolPendingAction:
    pa = SolPendingAction(
        correlation_id=correlation_id,
        org_id=sol_org.id,
        user_id=sol_user.id,
        intent_kind="invoice_dispute",
        plan_json={"v": 1},
        scheduled_for=datetime.now(timezone.utc) + timedelta(minutes=15),
        cancellation_token=f"ct-{correlation_id}",
    )
    sol_db.add(pa)
    sol_db.commit()
    sol_db.refresh(pa)
    return pa


@pytest.mark.parametrize(
    "field,new_value",
    [
        ("correlation_id", "hijacked-correlation"),
        ("plan_json", {"tampered": True}),
        ("intent_kind", "exec_report"),
        ("scheduled_for", datetime.now(timezone.utc) + timedelta(hours=3)),
        ("cancellation_token", "new-token"),
    ],
)
def test_pending_action_immutable_fields_rejected(sol_db, sol_org, sol_user, field, new_value):
    """Modifier correlation_id / plan_json / intent_kind / scheduled_for / cancellation_token → rejeté."""
    pa = _make_pending(sol_db, sol_org, sol_user, correlation_id=f"pa-immut-{field}")

    setattr(pa, field, new_value)
    with pytest.raises(AppendOnlyViolation) as exc:
        sol_db.commit()
    assert field in str(exc.value) or "immutable" in str(exc.value).lower()
    sol_db.rollback()


@pytest.mark.parametrize(
    "target_status,extra_field,extra_value",
    [
        ("executing", None, None),
        ("executed", "executed_at", datetime.now(timezone.utc)),
        ("cancelled", "cancelled_at", datetime.now(timezone.utc)),
    ],
)
def test_pending_action_status_transitions_allowed(
    sol_db, sol_org, sol_user, target_status, extra_field, extra_value
):
    """Transitions d'état légitimes waiting → executing/executed/cancelled autorisées."""
    pa = _make_pending(sol_db, sol_org, sol_user, correlation_id=f"pa-transition-{target_status}")

    pa.status = target_status
    if extra_field:
        setattr(pa, extra_field, extra_value)
    sol_db.commit()  # ne doit pas lever

    sol_db.refresh(pa)
    assert pa.status == target_status


def test_pending_action_cancelled_by_allowed(sol_db, sol_org, sol_user):
    """Ajouter cancelled_by lors d'une annulation → autorisé."""
    pa = _make_pending(sol_db, sol_org, sol_user, correlation_id="pa-cancel-by")

    pa.status = "cancelled"
    pa.cancelled_at = datetime.now(timezone.utc)
    pa.cancelled_by = sol_user.id
    sol_db.commit()

    sol_db.refresh(pa)
    assert pa.cancelled_by == sol_user.id


# ─────────────────────────────────────────────────────────────────────────────
# Limitation connue : raw SQL contourne le listener (documenté DECISIONS_LOG P0-2)
# ─────────────────────────────────────────────────────────────────────────────


def test_raw_sql_update_bypasses_listener_documented(sol_db, sol_action_log_factory):
    """Documente limitation : UPDATE via text() contourne l'event listener.

    Compensé par la règle CI : grep "UPDATE sol_action_log" dans backend/
    (hors migrations) doit retourner 0 hit. Le service layer Sol ne doit
    jamais utiliser raw SQL pour modifier un log d'audit.
    """
    log = sol_action_log_factory()

    # Tentative raw SQL — passe silencieusement (limitation assumée)
    sol_db.execute(
        text("UPDATE sol_action_log SET outcome_code = :v WHERE id = :id"),
        {"v": "raw_sql_bypass", "id": log.id},
    )
    sol_db.commit()

    sol_db.refresh(log)
    # Le bypass a réussi — c'est volontaire, documenté
    assert log.outcome_code == "raw_sql_bypass"
